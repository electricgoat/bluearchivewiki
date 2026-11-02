import os
import itertools
import traceback
import argparse

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data
from raid import get_boss_skills
from multifloor_raid_seasons import prepare_seasons
import raid_rewards
import shared.functions
from shared.MissingTranslations import MissingTranslations
from shared.standard_dictionaries import build_standard_dictionaries

MODE = raid_rewards.LIMIT_BREAK

REWARDS_NOTES = {
    2: "The Global version's season had the boss levels and stats of [[Limit Break Assault/Season 4 rewards|Season 4]].", #Global Season 2 came after the rework of the floors that JP had with Season 3: it had the new boss levels and stats, and the old rewards
}

#TODO fix equipment blueprint raffle boxes/ choice ticket of tiers 2 to 6 on the wiki
STAND_INS = {('Item', 61100 + tier): ('Item', 150028 + tier) for tier in range(5)}

missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_skill_localization = MissingTranslations("translation/missing/LocalizeSkillExcelTable.json")
missing_code_localization = MissingTranslations("translation/missing/LocalizeCodeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")

args = {}

characters = {}
items = {}
furniture = {}
emblems = {}

season_data = {}



def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    type, id = STAND_INS.get((type, id), (type, id))
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)



def generate():
    global args, data, season_data

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['colorize'] = shared.functions.colorize
    env.filters['nl2br'] = shared.functions.nl2br


    seasons = raid_rewards.seasons_as_ran(MODE, prepare_seasons(season_data['jp'].multi_floor_raid_season, 'jp', data), args['translation'])
    seasons = raid_rewards.global_seasons(seasons, prepare_seasons(season_data['gl'].multi_floor_raid_season, 'gl', data))
    seasons = [x | {'rewards_note': REWARDS_NOTES.get(x['SeasonId'])} for x in seasons]
    rewards = {x['SeasonId']: raid_rewards.floor_rewards(x.get('Floors') or raid_rewards.floors(x['OpenRaidBossGroupId'], data), wiki_card) for x in seasons}
    rewards_wikitexts = raid_rewards.rewards_pages(MODE, seasons, rewards, env)

    os.makedirs(os.path.join(args['outdir'], 'raids'), exist_ok=True)
    for season in seasons:
        print (f"Working on season {season['SeasonId']}")
        stages = data.multi_floor_raid_stage[season['OpenRaidBossGroupId']]

        durations = '/'.join(dict.fromkeys(shared.functions.format_ms_duration(stage['BattleDuration']) for stage in stages))
        wikitext = f"\n==Boss Info==\nBattle time for this boss is {durations}.\n" + MODE.section + "\n"


        #The boss has other skills every few floors: a table for each run of floors with the same ones
        template = env.get_template('./raid/template_boss_skilltable.txt')
        skilltables = {}
        for skill_list_group, floors in itertools.groupby(stages, key=lambda x: data.costumes[data.characters[x['RaidCharacterId']]['CostumeGroupId']]['CharacterSkillListGroupId']):
            floors = list(floors)
            stage = {'character_skills': get_boss_skills(skill_list_group, data, missing_skill_localization)}
            skilltables[raid_rewards.ranks(floors[0]['Difficulty'], floors[-1]['Difficulty'])] = template.render(stage=stage, skills_localization=data.skills_localization, skillbg=True)

        template = env.get_template('./raid/template_boss_skills.txt')
        wikitext += template.render(skilltables=skilltables)


        wikitext += "==Unit recommendations==\n"
        wikitext += "\n[[Category:Raid boss]]"

        armors = dict.fromkeys(shared.functions.armor_type(x['challenge']) for x in seasons if x['raid'] == season['raid'])
        template = env.get_template('./raid/template_multifloor_raid_intro.txt')
        wikitext = template.render(info=season['raid'], raid_page=raid_rewards.raid_page(MODE, season['raid']), armors=list(armors)) + wikitext


        with open(os.path.join(args['outdir'], 'raids', f"multifloor_raid_season_{season['SeasonId']}.txt"), 'w+', encoding="utf8") as f:
            f.write(wikitext)

        boss_name = season['raid'].shortname.replace(' ', '_')
        with open(os.path.join(args['outdir'], 'raids', f"multifloor_rewards_{boss_name}_season_{season['SeasonId']:02d}.txt"), 'w+', encoding="utf8") as f:
            f.write(rewards_wikitexts[season['SeasonId']])

    if wiki.site != None:
        raid_rewards.publish(MODE, seasons, rewards_wikitexts, args)



def init_data():
    global args, data, season_data
    global characters, items, furniture, emblems

    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    season_data['jp'] = load_season_data(args['data_primary'])
    season_data['gl'] = load_season_data(args['data_secondary'])

    characters, items, furniture, emblems = build_standard_dictionaries(data, missing_localization, missing_etc_localization)


def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish the rewards pages of the current and previous seasons, and purge their raids\' pages to show them')
    parser.add_argument('-season_id', type=int, nargs='+', metavar='ID', help='Seasons to publish instead, by SeasonId')
    parser.add_argument('-all_seasons', action='store_true', help='Publish every season instead')

    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    try:
        init_data()
        generate()

        missing_localization.write()
        missing_skill_localization.write()
        missing_code_localization.write()
        missing_etc_localization.write()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
