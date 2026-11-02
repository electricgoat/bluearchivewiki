import os
import argparse
from collections import Counter
from typing import NamedTuple

from jinja2 import Environment, FileSystemLoader

import shared.functions
from data import load_data, load_tactical_relay_data, BlueArchiveData, BlueArchiveTacticalRelayData
from model import Item
from classes.Character import Character
from classes.Furniture import Furniture
from classes.Emblem import Emblem
from shared.MissingTranslations import MissingTranslations
from shared.standard_dictionaries import build_standard_dictionaries

missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")


#LocalizeExcelTable keys of the lobby buttons
STAGE_NAMES = {'Explosion': 1300413998, 'Pierce': 2593570114, 'Mystic': 2829214206, 'Sonic': 560982211}

#difficulty levels as localized
LEVELS = {'Normal': 'A', 'Hard': 'B', 'VeryHard': 'C'}

#EngraveTreeType, each with a reward group of the stage
REWARD_TYPES = ['Ego', 'Conscious', 'Unconscious']

ARMOR_TYPES = ['Normal', 'LightArmor', 'HeavyArmor', 'CompositeArmor', 'Unarmed', 'ElasticArmor']
BULLET_TYPES = ['Normal', 'Explosion', 'Pierce', 'Chemical', 'Mystic', 'Sonic']
MATCHUPS = ['Resist', 'Normal', 'Effective', 'Weak']


class TacticalRelayContext(NamedTuple):
    """The loaded game data and dictionaries, and the characters by DevName, which stage files spawn them by."""
    data: BlueArchiveData
    relay: BlueArchiveTacticalRelayData
    characters: dict[int, Character]
    items: dict[int, Item]
    furniture: dict[int, Furniture]
    emblems: dict[int, Emblem]
    units: dict[str, dict]

    def wiki_card(self, type: str, id: int, **params) -> str:
        return shared.functions.wiki_card(type, id, self.data, self.characters, self.items, self.furniture, self.emblems, **params)


env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))


def generate(ctx: TacticalRelayContext, outdir: str):
    seasons = sorted(ctx.relay.stages)
    if len(seasons) > 1: print(f"The stage table has seasons {seasons}, the page shows the last one's")
    rows = sorted(ctx.relay.stages[seasons[-1]], key=lambda x: (int(x['StageNumber']), list(LEVELS).index(x['StageDifficulty'])))
    stages = {}
    for row in rows: stages.setdefault(row['StageType'], []).append(row)

    #The passive skills of every stage make the mode's rules, the others a stage's special rule
    common = [x for x in passives(ctx, rows[0]) if all(x in passives(ctx, row) for row in rows)]

    wikitext = env.get_template('templates/template_tactical_relay.txt').render(
        intro = intro(ctx, seasons[-1], rows),
        squads = squads(ctx, rows, common),
        battle = battle(ctx, rows, common),
        stages = [stage(ctx, x, common) for x in stages.values()],
        levels = levels(rows),
        rewards = rewards(ctx, rows),
        achievements = achievements(ctx, rows),
    )

    os.makedirs(os.path.join(outdir, 'modes'), exist_ok=True)
    with open(os.path.join(outdir, 'modes', 'Virtual_Aptitude_Test.txt'), 'w', encoding="utf8") as f:
        f.write(wikitext)


def intro(ctx: TacticalRelayContext, season_id: int, rows: list[dict]) -> dict:
    """When the season runs, the most squads a level takes, the mission that opens the mode, and the clears its ranking waits for."""
    #The season row's dates are placeholders, its achievements run as long as the season
    missions = season_missions(ctx, rows)
    stage = ctx.data.campaign_stages[ctx.relay.open_condition['TacticalRelay']['CampaignStageId']] #CHAPTER05_Normal_Main_Stage05
    return {
        'period': date_range(min(x['StartDate'] for x in missions), max(x['EndDate'] for x in missions)),
        'squads': max(x['EchelonCount'] for x in rows),
        'unlock': f"{int(stage['Name'].split('_')[0].removeprefix('CHAPTER'))}-{stage['StageNumber']}",
        'ranking': ctx.relay.seasons[season_id]['SeasonRankStillCounting'],
    }


def squads(ctx: TacticalRelayContext, rows: list[dict], common: list[str]) -> dict:
    """When the TCS slots use their EX skills, the attack type buff, the Affection Rank Buff, and Level Sync on each level."""
    slots = ctx.relay.apc_slots[same(rows, 'ApcSlotDefineId')]
    bond = next(x for x in skill_effects(ctx, common) if dao_type(x) == 'StatChangeByFavorRankEffectDAO')
    return {
        'tcs': [{'first': slots[f'ApcSlotStartCooltime{i:02}'] // 1000, 'every': slots[f'ApcSlotCooltime{i:02}'] // 1000} for i in range(1, slots['ApcSlotAmount'] + 1)],
        'synergy': synergy(ctx, common),
        'bond': percent(bond['TargetCoefficientAmount'] * bond['RatePerFavorRank'] // 10000),
        'level_sync': [level_sync(level, ctx.relay.level_adjustment[difficulty]) for difficulty, level in LEVELS.items()],
    }


def synergy(ctx: TacticalRelayContext, skills: list[str]) -> list[tuple[int, str]]:
    """The attack type buff: students deal more damage when the squad has a number of students of same attack type."""
    steps = set()
    for ability in [x for skill in skills for x in walk(ctx.data.levelskill[skill])]:
        counts = [x['CountMin'] for x in ability.get('Modifiers', []) if dao_type(x) == 'CountListLogicEffectTemplateModifierDAO']
        increases = [x['TargetCoefficientAmount'] for x in effects(ctx, ability.get('LogicEffectGroupIds', [])) if x.get('StatType') == 59] #DamageRatio2Increase
        steps |= {(count, increase) for count in counts for increase in increases}

    return [(count, percent(increase)) for count, increase in sorted(steps)]


def level_sync(level: str, row: dict) -> dict:
    """The level, skill levels and equipment Level Sync raises students to."""
    equipment = [f"T{row[f'EquipSlotTier{i:02}']} Lv.{row[f'EquipSlotLevel{i:02}']}" if row[f'EquipSlotTier{i:02}'] else '—' for i in (1, 2, 3)]
    return {'level': level, 'skills': [row[x] for x in ('Level', 'ExSkillLevel', 'PublicSkillLevel', 'PassiveSkillLevel', 'ExtraPassiveSkillLevel')], 'equipment': equipment}


def battle(ctx: TacticalRelayContext, rows: list[dict], common: list[str]) -> dict:
    """The damage enemies take, their extra HP, Limit Break, and the Strikers' immunity on entering the field."""
    rules = skill_effects(ctx, common)
    extra_hp = next(x for x in rules if dao_type(x) == 'MaxHpOverHealEffectDAO') #BonusSource 1 is MaxHP
    immunity = next(x for x in rules if x.get('TargetStatus') == 'ImmuneDamageAll')
    gauge = limit_break_gauge(ctx, rows[0])
    [skill] = gauge['LimitBreakSkills']
    if skill['LimitGaugeCost'] != gauge['MaxGauge']: print(f"Limit Break costs {skill['LimitGaugeCost']} of a gauge of {gauge['MaxGauge']}, the page says a full gauge")
    cost = next(x for x in skill_effects(ctx, [skill['skillGroupId']]) if dao_type(x) == 'SkillCostChangeEffectDAO')
    return {
        'damage': damage_table(ctx, [unit for row in rows for units in sections(ctx, row) for unit in units]),
        'extra_hp': {'amount': percent(extra_hp['BonusRate']), 'duration': extra_hp['TemporaryHpReducePeriod'] * 10000 // extra_hp['TemporaryHpReduceByHealAmountRate'] // 1000},
        'limit_break': {'duration': cost['EndConditionArgument'] // 1000, **gauge_bonus(ctx, rows, gauge['MaxGauge'])},
        'immunity': immunity['Duration'] // 1000,
    }


def damage_table(ctx: TacticalRelayContext, units: list[dict]) -> dict:
    """The damage enemies take by armor and attack type: the usual rate of the matchup, times the rate the enemies take it at."""
    rates = Counter(tuple(ctx.data.characters_stats[x['Id']][f'{m}DamagedRatio'] for m in MATCHUPS) for x in units)
    if len(rates) > 1: print(f"The enemies take damage at several rates {dict(rates)}, the page shows the most common")
    rate = dict(zip(MATCHUPS, rates.most_common(1)[0][0]))
    factors = {(x['BulletType'], x['ArmorType']): x for x in ctx.relay.damage_factors}
    usual = {x['DamageAttribute']: x['DamageRate'] for x in ctx.relay.damage_factors}
    cell = lambda factor: (factor['DamageAttribute'], percent(factor['DamageRate'] * rate[factor['DamageAttribute']] // 10000))
    return {
        'matchups': [(m, percent(usual[m] * rate[m] // 10000), percent(usual[m])) for m in MATCHUPS],
        'bullets': [shared.functions.damage_type(x) for x in BULLET_TYPES],
        'rows': [(shared.functions.armor_type(armor), [cell(factors[(bullet, armor)]) for bullet in BULLET_TYPES]) for armor in ARMOR_TYPES],
    }


def gauge_bonus(ctx: TacticalRelayContext, rows: list[dict], gauge: int) -> dict:
    """How the bond ranks of all owned students raise the Limit Break gauge's capacity, by a step every so many ranks."""
    bonus = ctx.relay.favor_bonus[same(rows, 'FavorCollectionScoreBonusId')]
    steps = [(bonus[f'RequiredScore{i:02}'], next(x['AddValue'] for x in skill_effects(ctx, [bonus[f'AppliedSkillGroupId{i:02}']]) if dao_type(x) == 'BlackBoardAddMaxEffectDAO'))
             for i in range(1, 21)]
    if any((ranks, add) != (steps[0][0] * n, steps[0][1]) for n, (ranks, add) in enumerate(steps, 1)): print(f"The gauge grows by uneven steps {steps}, the page says every {steps[0][0]}")
    return {'every': shared.functions.format_thousands(steps[0][0]), 'step': percent(steps[0][1] * 10000 // gauge), 'up_to': shared.functions.format_thousands(steps[-1][0]), 'most': percent(sum(x for _, x in steps) * 10000 // gauge)}


def stage(ctx: TacticalRelayContext, rows: list[dict], common: list[str]) -> dict:
    """A stage's row of the stage table: name, terrain, enemies by armor type, the most common first, special rule, and the enemies' level on each level.
    The stage's sections alternate between its two armor types, which the run checks."""
    enemies = {}
    for row in rows:
        armors = (row['EnemyArmorType'], row['EnemySubArmorType'])
        for n, units in enumerate(sections(ctx, row)):
            if {x['ArmorType'] for x in units} != {armors[n % 2]}: print(f"{row['Name']} section {n + 1} has other enemies than {armors[n % 2]} ones")
            for unit in units: enemies.setdefault(unit['ArmorType'], Counter())[localized_etc(ctx, unit['LocalizeEtcId'], 'Name')] += 1

    rule_skills = dict.fromkeys(x for row in rows for x in passives(ctx, row) if x not in common)
    gauge = limit_break_gauge(ctx, rows[0])['MaxGauge']
    gains = {x['AddValue'] for x in skill_effects(ctx, rule_skills) if dao_type(x) == 'BlackBoardAddEffectDAO' and x['BlackBoardKey'] == 'LimitGauge'}
    return {
        'name': localized(ctx, STAGE_NAMES[rows[0]['StageType']]),
        'terrain': shared.functions.environment_type(rows[0]['StageTopography']),
        'enemies': [(shared.functions.armor_type(armor), merged(names)) for armor, names in enemies.items()],
        #The tips list the terrain and the two armor types first
        'rules': [(localized_etc(ctx, x, 'Name'), shared.functions.nl2br(localized_etc(ctx, x, 'Description'))) for x in rows[0]['WaveInfoTipLocalizeEtcId'][3:]],
        'gains': [percent(x * 10000 // gauge) for x in sorted(gains)],
        'enemy_levels': [ctx.data.ground[x['GroundID']]['LevelMinion'] for x in rows],
    }


def sections(ctx: TacticalRelayContext, row: dict) -> list[list[dict]]:
    """The enemies each section of a stage's level spawns, leaving out units without a portrait (a dummy holding passive skills)."""
    spawned = []
    for name in ctx.data.ground[row['GroundID']]['StageFileName']:
        for section in ctx.data.stages[name]['Sections']:
            units = [ctx.units[x['SpawnData']['SpawnTemplateId']] for x in walk(section) if 'SpawnData' in x]
            spawned.append([x for x in units if ctx.data.costumes[x['CostumeGroupId']].get('InformationPacel')])

    return spawned


def merged(counts: Counter) -> list[str]:
    """Names with their variants in parentheses merged, the most common first: Beach Thug (SMG, MG, SR)"""
    variants, totals = {}, Counter()
    for name, count in counts.items():
        base, _, variant = name.partition(' (')
        variants.setdefault(base, []).append(variant.removesuffix(')'))
        totals[base] += count

    return [f"{base} ({', '.join(x)})" if all(x) else base for base, x in sorted(variants.items(), key=lambda x: -totals[x[0]])]


def levels(rows: list[dict]) -> list[dict]:
    """The rows of the level table, which every stage shares."""
    table = []
    for difficulty, level in LEVELS.items():
        stages = [x for x in rows if x['StageDifficulty'] == difficulty]
        waves = same(stages, 'WavesPerSections')
        table.append({
            'level': level,
            'sections': len(waves),
            'waves': sum(waves),
            'squads': same(stages, 'EchelonCount'),
            'time': shared.functions.format_ms_duration(same(stages, 'BattleDuration')),
            'ap': same(stages, 'StageEnterCostAmount'),
            'recommended': same(stages, 'RecommandLevel'),
        })

    return table


def rewards(ctx: TacticalRelayContext, rows: list[dict]) -> dict:
    """The coins each wave cleared gives on each level, and expiration info. So far every stage of a level gives the same,
    whichever reward type the player picks, which the run checks."""
    waves = {}
    for difficulty, level in LEVELS.items():
        groups = [[(x['ClearWave'], x['RewardParcelType'], x['RewardId'], x['RewardAmount']) for x in ctx.relay.rewards[row[f'StageRewardId{type}']]]
                  for row in rows if row['StageDifficulty'] == difficulty for type in REWARD_TYPES]
        if any(x != groups[0] for x in groups): print(f"Level {level}'s stages or reward types give different rewards, the page shows the first's")
        for wave, type, id, amount in groups[0]: waves.setdefault(wave, {})[level] = (type, id, amount)

    [(type, id)] = {(type, id) for wave in waves.values() for type, id, amount in wave.values()}
    coin = ctx.data.items[id]
    return {
        'coin': ctx.wiki_card(type, id),
        'waves': {wave: [f"{amounts[x][2]:,}" if x in amounts else '' for x in LEVELS.values()] for wave, amounts in sorted(waves.items())},
        'expiry': coin['ExpirationDateTime'][:16],
        'expiry_change': {'card': ctx.wiki_card(coin['ExpiryChangeParcelType'], coin['ExpiryChangeId']), 'amount': coin['ExpiryChangeAmount']},
    }


def achievements(ctx: TacticalRelayContext, rows: list[dict]) -> dict:
    """The season's achievements of clearing a stage's last wave a number of times, the levels with the same ones together, and what they give in all."""
    missions = season_missions(ctx, rows)
    groups, totals = {}, Counter()
    for row in rows:
        ladder = sorted([x for x in missions if x['CompleteConditionParameter'][0] == row['Id']], key=lambda x: x['CompleteConditionCount'])
        if any(x['CompleteConditionParameter'][1] != sum(row['WavesPerSections']) for x in ladder): print(f"{row['Name']} has achievements for another wave than its last")
        key = tuple((x['CompleteConditionCount'], parcel_cards(ctx, x)) for x in ladder)
        groups.setdefault(key, []).append(f"{localized(ctx, STAGE_NAMES[row['StageType']])} {LEVELS[row['StageDifficulty']]}")
        for x in ladder: totals.update({(type, id): amount for type, id, amount in zip(x['MissionRewardParcelType'], x['MissionRewardParcelId'], x['MissionRewardAmount'])})

    return {
        'groups': [{'levels': levels, 'ladder': list(key)} for key, levels in groups.items()],
        'count': len(missions),
        'totals': [ctx.wiki_card(type, id, quantity=amount) for (type, id), amount in sorted(totals.items())],
    }


def season_missions(ctx: TacticalRelayContext, rows: list[dict]) -> list[dict]:
    ids = {x['Id'] for x in rows}
    return [x for x in ctx.relay.missions if x['CompleteConditionParameter'][0] in ids]


def parcel_cards(ctx: TacticalRelayContext, mission: dict) -> str:
    return ' '.join(ctx.wiki_card(type, id, quantity=amount if amount > 1 else None) for type, id, amount in zip(mission['MissionRewardParcelType'], mission['MissionRewardParcelId'], mission['MissionRewardAmount']))


def passives(ctx: TacticalRelayContext, row: dict) -> list[str]:
    ground = ctx.data.ground[row['GroundID']]
    return ground['AllyPassiveSkillId'] + ground['EnemyPassiveSkillId']


def limit_break_gauge(ctx: TacticalRelayContext, row: dict) -> dict:
    """The stage file's command setting up the Limit Break gauge: its size, the Limit Break skill and its cost."""
    return next(x for name in ctx.data.ground[row['GroundID']]['StageFileName'] for x in walk(ctx.data.stages[name]) if dao_type(x) == 'GroundCommandSetLimitBreakGauge')


def skill_effects(ctx: TacticalRelayContext, skills) -> list[dict]:
    """The effects skills name anywhere, also in texts listing several, and the effects those name in turn."""
    names = [x for x in dict.fromkeys(name for skill in skills for name in texts(ctx.data.levelskill[skill])) if x in ctx.data.logic_effects_npc]
    for name in names: #grows as it goes
        names += [x for x in dict.fromkeys(texts(ctx.data.logic_effects_npc[name])) if x in ctx.data.logic_effects_npc and x not in names]

    return effects(ctx, names)


def effects(ctx: TacticalRelayContext, names) -> list[dict]:
    """The LogicEffect_NPC rows of effect groups."""
    return [x for name in names for x in ctx.data.logic_effects_npc.get(name, [])]


def same(rows: list[dict], field: str):
    """A field the rows share. If they don't, it says so and takes the first row's."""
    values = list(dict.fromkeys(str(x[field]) for x in rows))
    if len(values) > 1: print(f"The stages differ in {field} ({', '.join(values)}), the page shows {values[0]}")
    return rows[0][field]


def walk(node):
    """Every dict in a tree of JSON data"""
    if isinstance(node, dict):
        yield node
        node = list(node.values())
    if isinstance(node, list):
        for x in node:
            yield from walk(x)


def texts(node) -> list[str]:
    """Every text in a tree of JSON data, a text listing several split up"""
    if isinstance(node, str): return node.split(', ')
    if isinstance(node, dict): node = list(node.values())
    return [x for value in node for x in texts(value)] if isinstance(node, list) else []


def dao_type(node: dict) -> str:
    return node.get('$type', '').split(',')[0].split('.')[-1]


def percent(amount: int) -> str:
    """A rate in 1/10000 as a percentage"""
    return f"{amount / 100:g}%"


def date_range(start: str, end: str) -> str:
    """A {{DateRange}} of two times of the data (UTC+9), which the wiki shows in the reader's time zone."""
    return f"{{{{DateRange|{shared.functions.format_datetime(start)}|{shared.functions.format_datetime(end)}}}}}"


def localized(ctx: TacticalRelayContext, key: int) -> str:
    """A LocalizeExcelTable text in English, or in Japanese until it has a translation"""
    text = ctx.data.localization.get(key, {})
    if text and not text.get('En'): missing_localization.add_entry(text)
    return text.get('En') or text.get('Jp', '')


def localized_etc(ctx: TacticalRelayContext, key: int, field: str) -> str:
    """A field of a LocalizeEtcExcelTable text in English, or in Japanese until it has a translation"""
    text = ctx.data.etc_localization.get(key, {})
    if text and not text.get(field + 'En'): missing_etc_localization.add_entry(text)
    return text.get(field + 'En') or text.get(field + 'Jp', '')


def init(args: dict) -> TacticalRelayContext:
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    return TacticalRelayContext(
        data = data,
        relay = load_tactical_relay_data(args['data_primary']),
        **build_standard_dictionaries(data)._asdict(),
        units = {x['DevName']: x for x in data.characters.values()},
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')

    args = vars(parser.parse_args())
    print(args)

    ctx = init(args)
    generate(ctx, args['outdir'])
    missing_localization.write()
    missing_etc_localization.write()


if __name__ == '__main__':
    main()
