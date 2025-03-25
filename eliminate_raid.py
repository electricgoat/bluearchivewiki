import collections
import os
import re
import traceback
#import copy
import argparse
from datetime import datetime

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data
from model import Item, Character
from classes.Furniture import Furniture, FurnitureGroup
from classes.Emblem import Emblem
from classes.RaidSeasonReward import RaidSeasonReward
from raid import get_boss_skills
from raid_seasons import RAIDS
from eliminate_raid_seasons import SEASON_IGNORE, SEASON_NOTES
import shared.functions
from shared.MissingTranslations import MissingTranslations

missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_skill_localization = MissingTranslations("translation/missing/LocalizeSkillExcelTable.json")
missing_code_localization = MissingTranslations("translation/missing/LocalizeCodeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")

args = None

data = None
characters = {}
items = {}
furniture = {}
emblems = {}

season_data = {'jp':None, 'gl':None}



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



def get_cumulative_rewads(season):
    global args, data, season_data
    season['rewards'] = []

    for i in range(len(season['SeasonRewardId'])):
        rewards = RaidSeasonReward.from_data(season['SeasonRewardId'][i], data.eliminate_raid_stage_season_reward, wiki_card)
        season['rewards'].append(rewards)

    #print(season['rewards'])
    return season['rewards']

    

def total_cumulative_rewards(season):
    global args, data
    total_rewards = {}
    wiki_total_rewards = []
    
    for i in range(len(season['rewards'])):
        for item in season['rewards'][i].items:
            if (item['parcel_type'], item['parcel_id']) not in total_rewards:
                total_rewards[(item['parcel_type'], item['parcel_id'])] = item
            else:
                total_rewards[(item['parcel_type'], item['parcel_id'])]['amount'] += item['amount']
    #print(total_rewards)

    for item in sorted(total_rewards.values(), key=shared.functions.item_sort_order):
        wiki_total_rewards.append(wiki_card(item['parcel_type'], item['parcel_id'], quantity=item['amount'], text='', block=True, size='60px' ))
    #print(wiki_total_rewards)
    return wiki_total_rewards


def get_ranking_rewards(season): 
    ranking_rewards = data.eliminate_raid_ranking_reward[season['RankingRewardGroupId']]
    for entry in ranking_rewards:
        reward = RaidSeasonReward(entry['Id'], entry['RewardParcelType'], entry['RewardParcelUniqueId'], entry['RewardParcelUniqueName'], entry['RewardParcelAmount'], wiki_card)
        entry['reward'] = reward
        if entry['RankEnd'] == 0: entry['RankEnd'] = '∞'
    return ranking_rewards


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
    

    region = 'jp'
    for season in season_data[region].eliminate_raid_season.values():
        print(f"Working on season {season['SeasonId']}")
        wikitext = ''
        

        template = env.get_template('./raid/template_eliminate_raid_boss.txt')
        for group in boss_groups:
            boss_data[season[group]] = get_raid_boss_data(season[group])
            wikitext += template.render(season_data=season, boss_data=boss_data[season[group]])

        wikitext = "==Boss Info==\n<tabber>\n" + wikitext + "\n</tabber>\n"


        template = env.get_template('./raid/template_boss_skilltable.txt')
        skilltables = {stage['Difficulty']: template.render(stage=stage, skills_localization=data.skills_localization) for stage in boss_data[season[group]]['stage']}

        template = env.get_template('./raid/template_boss_skills.txt')
        wikitext += template.render(skilltables=shared.functions.deduplicate_dict_values(skilltables))

        template = env.get_template('./raid/template_ranking_rewards.txt')
        wikitext += template.render(rewards=get_ranking_rewards(season))


        template = env.get_template('./raid/template_cumulative_score_rewards.txt')
        get_cumulative_rewads(season)
        wikitext += template.render(season=season, total_rewards=total_cumulative_rewards(season))


        with open(os.path.join(args['outdir'], 'raids', f"eliminate_raid_season_{season['SeasonId']}.txt"), 'w+', encoding="utf8") as f:
            f.write(wikitext)



def init_data():
    global args, data, season_data
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    season_data['jp'] = load_season_data(args['data_primary'])
    #season_data['gl'] = load_season_data(args['data_secondary'])

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':#  not in ['Release', 'Complete']:
            continue

        try:
            character = Character.from_data(character['Id'], data)
            characters[character.id] = character
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue

    for item in data.items.values():
        try:
            item = Item.from_data(item['Id'], data)
            items[item.id] = item
        except Exception as err:
            print(f'Failed to parse for item {item}: {err}')
            traceback.print_exc()
            continue

    for item in data.furniture.values():
        try:
            item = Furniture.from_data(item['Id'], data)
            furniture[item.id] = item
        except Exception as err:
            print(f'Failed to parse for furniture {item}: {err}')
            traceback.print_exc()
            continue

    for emblem_id in data.emblem:
        try:
            emblem = Emblem.from_data(emblem_id, data, characters, missing_etc_localization, missing_localization)
            emblems[emblem.id] = emblem
        except Exception as err:
            print(f'Failed to parse emblem {emblem_id}: {err}')
            traceback.print_exc()
   

def main():
    global args

    parser = argparse.ArgumentParser()
    #parser.add_argument('season_id',        metavar='SeasonId', help='Eliminate raid season id')
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')

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

