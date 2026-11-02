import os
import re
import argparse
import traceback

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data
from time_attack_dungeon_seasons import prepare_seasons, geas_icons
import shared.functions
from shared.MissingTranslations import MissingTranslations

MODE_PAGE = 'Joint Firing Drill'

#The HP column of each exercise type's pages, and the side of the units it lists: the enemies, or the totems summoned on the players' side
HP_COLUMNS = {
    'Shooting': ('HP', 'Enemy'),
    'Defense':  ('HP', 'Enemy'),
    'Assault':  ('HP (Totem)', 'Ally'),
}

#The game's StatLevelUpType (the columns of StatLevelInterpolationExcelTable) and WeaponType, by value
STAT_LEVEL_UP_TYPES = ['Standard', 'Premature', 'LateBloom', 'Obstacle', 'TimeAttack']
WEAPON_TYPES = ['None', 'SG', 'SMG', 'AR', 'GL', 'HG', 'RL', 'SR', 'DSMG', 'RG', 'DSG', 'Vulcan', 'Missile', 'Cannon', 'Taser', 'MG', 'Binah', 'MT', 'Relic', 'FT', 'Akemi', 'KetherCannon']

#What an ability's modifier checks of a unit, and its IncludeType: 2 takes the units that fail the check
MODIFIERS = {
    'CharacterIdConditionalModifierDAO':   lambda x, unit: (unit['Id'] in x['CharacterIdList'], x['IncludeType']),
    'PersonalityIdConditionalModifierDAO': lambda x, unit: (unit['PersonalityId'] in x['PersonalityIdList'], x['IncludeType']),
    'WeaponConditionalModifierDAO':        lambda x, unit: (WEAPON_TYPES[x['WeaponConstraint']['Weapon']] == unit['WeaponType'], x['WeaponConstraint']['IncludeType']),
}

missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")

args = {}

characters_by_devname = {}
season_data = {}



def exercise_page(season):
    return f"{MODE_PAGE}/{season['type']} Exercise {season['number']}"



def dao_type(node):
    return node.get('$type', '').split(',')[0].split('.')[-1]



def walk(node):
    """Every dict in a tree of JSON data"""
    if isinstance(node, dict):
        yield node
        node = list(node.values())
    if isinstance(node, list):
        for x in node:
            yield from walk(x)



def localized(key, field):
    """A field of a LocalizeEtcExcelTable text in English, or in Japanese if it has no English yet"""
    text = data.etc_localization.get(key, {})
    if text and not text.get(field + 'En'): missing_etc_localization.add_entry(text)
    return text.get(field + 'En') or text.get(field + 'Jp', '')



def stage_waves(ground):
    """The units of a stage by wave, the sections of its stage files: the characters it spawns, enemies, and those its skills summon, with their side"""
    waves = []
    for section in [x for name in ground['StageFileName'] for x in data.stages[name]['Sections']]:
        units = [(x['SpawnData']['SpawnTemplateId'], 'Enemy') for x in walk(section) if 'SpawnData' in x]
        units += [(x['UniqueName'], 'Enemy' if x['SummonAsEnemy'] else 'Ally')
                  for command in walk(section) if dao_type(command) == 'GroundCommandUseSkill'
                  for x in walk(data.levelskill[command['SkillGroupId']]) if dao_type(x) == 'CharacterEntityDAO']
        waves.append([(characters_by_devname[name], side) for name, side in dict.fromkeys(units)])

    return waves



def hp_changes(geas, side):
    """The changes to MaxHP the geas's passive skills make to units of a side, as (modifiers that limit it to some units, amount, change in 1/10000).
    A change that depends on what the pages don't show, such as the team, is left out."""
    changes = []
    for skill, level in zip(geas[f'{side}PassiveSkillId'], geas[f'{side}PassiveSkillLevel']):
        left_out = set()
        for ability in walk(data.levelskill[skill]):
            effects = [x for group in ability.get('LogicEffectGroupIds', []) for x in data.logic_effects_npc.get(group, [])
                       if x['Level'] == level and dao_type(x) == 'StatChangeEffectDAO' and x['StatType'] == 1]
            unknown = {dao_type(x) for x in ability.get('Modifiers', [])} - set(MODIFIERS)
            if effects and unknown: left_out |= unknown
            elif effects: changes += [(ability.get('Modifiers', []), x['BaseAmount'], x['TargetCoefficientAmount']) for x in effects]

        if left_out: print (f"Geas {geas['Id']}: leaving the MaxHP changes of {skill} out, they depend on {', '.join(sorted(left_out))}")

    return changes



def unit_hp(unit, ground, changes):
    """A unit's HP on a stage: its stat at the stage's level, rounded, with the changes that apply to it, added then multiplied"""
    stats = data.characters_stats[unit['Id']]
    level = ground.get('Level' + unit['TacticEntityType'], ground['LevelNPC'])
    interpolation = data.stat_level_interpolation[level]['StatTypeIndex'][STAT_LEVEL_UP_TYPES.index(unit['StatLevelUpType'])] if level > 1 else 0
    amount, ratio = int(stats['MaxHP1'] + (stats['MaxHP100'] - stats['MaxHP1']) * interpolation / 10000 + 0.5), 10000

    for modifiers, base, coefficient in changes:
        if all(check == (include != 2) for check, include in [MODIFIERS[dao_type(x)](x, unit) for x in modifiers]):
            amount, ratio = amount + base, ratio + coefficient

    return int(amount * ratio / 10000 + 0.5)



def hp_waves(geas, side):
    """The (portrait, name, HP) of the units of a side on a geas's stage by wave, in the order of their HP before the geas"""
    ground = data.ground[geas['GroundId']]
    changes = hp_changes(geas, side)
    entry = lambda unit: (data.costumes[unit['CostumeGroupId']].get('InformationPacel', '').split('/')[-1], localized(unit['LocalizeEtcId'], 'Name'), unit_hp(unit, ground, changes))

    return [[entry(unit) for unit in sorted([unit for unit, unit_side in wave if unit_side == side], key=lambda x: unit_hp(x, ground, []))]
            for wave in stage_waves(ground)]



def hp_cell(waves):
    """The HP column's cell of a stage from the (portrait, name, HP) of each wave's listed units: one wave's if they are all alike,
    units by icon where a wave has several"""
    if all(x == waves[0] for x in waves): waves = waves[:1]
    #The wiki has the enemies' icons under their portraits' names without EnemyInfo_
    lines = [('' if len(waves) == 1 else f"Wave {n}: ") + ('' if len(wave) == 1 else f"{{{{Icon|{portrait.removeprefix('EnemyInfo_')}|title={name}}}}} ") + f"{hp:,}"
             for n, wave in enumerate(waves, 1) for portrait, name, hp in wave]

    return lines[0] if len(lines) == 1 else '\n'.join(f"<p>{x}</p>" for x in lines)



def exercise(season):
    """What a season's page shows: an image, and each phase's HP, time, special rules and what those do"""
    hp_header, side = HP_COLUMNS.get(season['type'], (None, None))
    phases = []

    for geas in season['geas']:
        waves = hp_waves(geas, side) if side else []
        phases.append({
            'difficulty': geas['Difficulty'],
            'waves': waves,
            'hp': hp_cell(waves) if side else '',
            'time': shared.functions.format_ms_duration(geas['BattleDuration']),
            'icons': geas_icons(geas),
            'notes': '\n'.join(shared.functions.nl2br(localized(x, 'Description')) for x in geas['GeasLocalizeEtcKey'][2:]), #after terrain and armor
        })

    icon = data.time_attack_dungeon[season['DungeonId']]['IconPath'].split('/')[-1]
    return {
        'image': next((portrait for wave in phases[0]['waves'] for portrait, name, hp in wave if portrait), icon),
        'hp_header': hp_header,
        'phases': phases,
    }



def generate():
    global args, data, season_data

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('./templates/template_time_attack_dungeon.txt')

    seasons = prepare_seasons(season_data['jp'].time_attack_dungeon_season, 'jp', data)
    wikitexts = {}

    os.makedirs(os.path.join(args['outdir'], 'events'), exist_ok=True)
    for season in seasons:
        print (f"Working on season {season['Id']}, {season['type']} Exercise {season['number']}")
        wikitexts[season['Id']] = template.render(**exercise(season))

        with open(os.path.join(args['outdir'], 'events', f"time_attack_dungeon_season_{season['Id']:02d} ({season['type']} Exercise {season['number']}).txt"), 'w', encoding="utf8") as f:
            f.write(wikitexts[season['Id']])

    if wiki.site != None:
        publish(seasons, wikitexts)



def publish(seasons, wikitexts):
    """Publishes the pages of the chosen seasons, by default the last two, where they differ from the wiki's. A page someone else edited last
    is left as it is, unless chosen by -season_id or -all_seasons. A new page gets a tab in its section of the mode's page."""
    if args['all_seasons']: chosen = seasons
    elif args['season_id']: chosen = [x for x in seasons if x['Id'] in args['season_id']]
    else: chosen = seasons[-2:]

    bot = wiki.user_name()
    new = []
    for season in chosen:
        page, wikitext = exercise_page(season), wikitexts[season['Id']]
        editor = wiki.last_editor(page)
        if editor not in (None, bot) and not (args['all_seasons'] or args['season_id']):
            print (f"{page} was last edited by {editor}, leaving it as it is")
        elif editor is None or not wiki.page_exists(page, wikitext):
            print (f"Publishing {page}")
            wiki.publish(page, wikitext, 'Generated Joint Firing Drill exercise page')
            if editor is None: new.append(season)

    if new: list_in_tabs(new)



def list_in_tabs(seasons):
    """Lists new exercise pages in the tabs of their sections on the mode's page, latest first, labelled as the others are"""
    text = old_text = wiki.site('parse', page=MODE_PAGE, prop='wikitext')['parse']['wikitext']
    number = lambda line: int((re.findall(r'(\d+)\|', line) or [0])[0]) #a line is 'Joint Firing Drill/Shooting Exercise 16|Exercise 16'

    for season in seasons:
        tabs = re.search(rf"==\s*{season['type']} Exercise\s*==.*?<tabbertransclude>\n(.*?)</tabbertransclude>", text, re.S)
        if not tabs:
            print (f"{MODE_PAGE} has no tabs of {season['type']} exercises to list {exercise_page(season)} in")
            continue

        lines = tabs.group(1).splitlines()
        if any(x.split('|')[0] == exercise_page(season) for x in lines): continue
        label = re.sub(r'\d+$', str(season['number']), lines[0].split('|')[-1]) if lines else f"Exercise {season['number']}"
        lines.insert(sum(number(x) > season['number'] for x in lines), f"{exercise_page(season)}|{label}")
        text = text[:tabs.start(1)] + ''.join(x + '\n' for x in lines) + text[tabs.end(1):]

    if text != old_text:
        wiki.publish(MODE_PAGE, text, 'Listed new exercises')



def init_data():
    global args, data, season_data
    global characters_by_devname

    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    season_data['jp'] = load_season_data(args['data_primary'])

    characters_by_devname = {x['DevName']: x for x in data.characters.values()}


def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish the pages of the current and previous exercises that the wiki lacks or the bot edited last, and list new ones in the tabs')
    parser.add_argument('-season_id', type=int, nargs='+', metavar='ID', help='Seasons to publish instead, by Id, over what the wiki has')
    parser.add_argument('-all_seasons', action='store_true', help='Publish every season instead, over what the wiki has')

    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    try:
        init_data()
        generate()
        missing_etc_localization.write()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
