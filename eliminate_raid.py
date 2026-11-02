import os
import traceback
import argparse

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data
from raid import get_boss_skills
from eliminate_raid_seasons import prepare_seasons
import raid_rewards
import shared.functions
from shared.MissingTranslations import MissingTranslations
from shared.standard_dictionaries import build_standard_dictionaries

MODE = raid_rewards.GRAND_ASSAULT

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
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)



def get_raid_boss_data(group):
    global args, data, season_data
    global missing_skill_localization

    boss_data = {}

    boss_data['stage'] = data.eliminate_raid_stage[group]
    for stage in boss_data['stage']:
        #print (f"RaidCharacterId: {stage['RaidCharacterId']} {stage['RaidBossGroup']} {stage['Difficulty']}")
        stage['ground'] = data.ground[stage['GroundId']]
        stage['character'] = data.characters[stage['RaidCharacterId']]
        stage['characters_stats'] = data.characters_stats[stage['RaidCharacterId']]
        stage['character_skills'] = get_boss_skills(data.costumes[data.characters[stage['RaidCharacterId']]['CostumeGroupId']]['CharacterSkillListGroupId'], data, missing_skill_localization)

    return boss_data



def generate():
    global args, data, season_data  

    boss_groups = ['OpenRaidBossGroup01', 'OpenRaidBossGroup02', 'OpenRaidBossGroup03']
    boss_data = {}

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['ms_duration'] = shared.functions.format_ms_duration
    env.filters['colorize'] = shared.functions.colorize
    env.filters['nl2br'] = shared.functions.nl2br
    

    seasons = raid_rewards.seasons_as_ran(MODE, prepare_seasons(season_data['jp'].eliminate_raid_season, 'jp'), args['translation'])
    seasons = raid_rewards.global_seasons(seasons, prepare_seasons(season_data['gl'].eliminate_raid_season, 'gl'), season_data['gl'].eliminate_raid_ranking_reward)
    rewards ={x['SeasonId']: raid_rewards.season_rewards(x, data.eliminate_raid_ranking_reward, data.eliminate_raid_stage_season_reward, wiki_card) for x in seasons}
    rewards_wikitexts = raid_rewards.rewards_pages(MODE, seasons, rewards, env)

    os.makedirs(os.path.join(args['outdir'], 'raids'), exist_ok=True)
    for season in seasons:
        print(f"Working on season {season['SeasonId']}")
        wikitext = ''
        

        template = env.get_template('./raid/template_eliminate_raid_boss.txt')
        for group in boss_groups:
            boss_data[season[group]] = get_raid_boss_data(season[group])
            wikitext += template.render(season_data=season, boss_data=boss_data[season[group]])

        durations = '/'.join(dict.fromkeys(shared.functions.format_ms_duration(stage['BattleDuration']) for x in boss_groups for stage in boss_data[season[x]]['stage']))
        wikitext = f"\n==Boss Info==\n===Stats===\nBattle time for this boss is {durations}.\n<tabber>\n" + wikitext + "\n</tabber>\n"


        template = env.get_template('./raid/template_boss_skilltable.txt')
        skilltables = {stage['Difficulty']: template.render(stage=stage, skills_localization=data.skills_localization) for stage in boss_data[season[group]]['stage']}

        template = env.get_template('./raid/template_boss_skills.txt')
        wikitext += template.render(skilltables=shared.functions.deduplicate_dict_values(skilltables))


        wikitext += "==Unit recommendations==\n"
        wikitext += MODE.section
        wikitext += "\n\n[[Category:Raid boss]]"

        template = env.get_template('./raid/template_eliminate_raid_intro.txt')
        wikitext = template.render(info=season['raid'], raid_page=raid_rewards.raid_page(MODE, season['raid']), season_data=season) + wikitext


        with open(os.path.join(args['outdir'], 'raids', f"eliminate_raid_season_{season['SeasonId']}.txt"), 'w+', encoding="utf8") as f:
            f.write(wikitext)

        boss_name = season['raid'].shortname.replace(' ', '_')
        with open(os.path.join(args['outdir'], 'raids', f"eliminate_rewards_{boss_name}_season_{season['SeasonId']:02d} ({season['SeasonDisplay']}).txt"), 'w+', encoding="utf8") as f:
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
    #parser.add_argument('season_id',        metavar='SeasonId', help='Eliminate raid season id')
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

