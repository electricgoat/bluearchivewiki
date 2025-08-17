import collections
import os
import re
import traceback
import copy
import argparse
from datetime import datetime

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data
from model import Item, Character
from classes.Furniture import Furniture, FurnitureGroup
from classes.Emblem import Emblem

from raid import get_boss_skills
from raid_seasons import RAIDS
from multifloor_raid_seasons import SEASON_IGNORE, SEASON_NOTES
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

BRACKETS = [[1,24], [25,49], [50,74], [75,99], [100,124]]


class StageReward(object):
    def __init__(self, id, parcel_type, parcel_id, parcel_name, amount):
        self.id = id
        self.parcel_type = parcel_type
        self.parcel_id = parcel_id
        self.parcel_name = parcel_name
        self.amount = amount

    @property
    def item(self):
        return {'parcel_type':self.parcel_type, 'parcel_id':self.parcel_id, 'parcel_name':self.parcel_name, 'amount':self.amount}
    
    @property
    def wiki_items(self):
        return wiki_card(self.parcel_type, self.parcel_id, quantity=self.amount, text='' )
    
    def format_wiki_items(self, **params):
        return wiki_card(self.parcel_type, self.parcel_id, quantity=self.amount, **params )
    
    def __repr__(self):
        return str(self.__dict__)



def reward_sort_order(item):
    sort_value = item.parcel_id
    match item.parcel_type:
        case 'Item':
            sort_value += 200000
        case 'Equipment':
            sort_value += 100000
        case 'Currency':
            sort_value += 3000000
        case 'Character':
            sort_value += 900000
        case 'Furniture':
            sort_value += 800000
        case _:
            pass
    
    match item.parcel_id:
        case 23: #eligma
            sort_value += 2200000
        case 7 | 9 | 70 | 71: #raid coins
            sort_value += 2100000
        case _:
            pass

    return sort_value




def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)


def get_raid_boss_data(group):
    global args, data, season_data
    global missing_skill_localization

    boss_data = {}

    boss_data['stage'] = data.multi_floor_raid_stage[group]

    unlock_req = 0
    for i, stage in enumerate(boss_data['stage']): 
        #print (f"RaidCharacterId: {stage['RaidCharacterId']} {stage['BossCharacterId']} {stage['Difficulty']}")
        stage['ground'] = data.ground[stage['GroundId']]
        stage['character'] = data.characters[stage['RaidCharacterId']]
        stage['characters_stats'] = data.characters_stats[stage['RaidCharacterId']]
        stage['total_stat_bonus'] = total_stat_bonus(stage['StatChangeId'], stage['RaidCharacterId'])
        stage['total_stats'] = total_stats(data.characters_stats[stage['RaidCharacterId']], stage['total_stat_bonus'])
        stage['clear_rewards'] = clear_rewards(stage['RewardGroupId'])
        stage['skill_list_group_id'] = data.costumes[data.characters[stage['RaidCharacterId']]['CostumeGroupId']]['CharacterSkillListGroupId']
        stage['character_skills'] = get_boss_skills(stage['skill_list_group_id'], data, missing_skill_localization)

        if i==0 or i==123:
            stage['protected'] = True
        if stage['StageOpenCondition'] != unlock_req:
            stage['protected'] = True
            boss_data['stage'][i-1]['protected'] = True

        unlock_req = stage['StageOpenCondition']

    boss_data['reward_subtotal'] = {}
    for bracket in BRACKETS:
        boss_data['reward_subtotal'][bracket[1]] = reward_subtotal(bracket, boss_data['stage'])
        
    return boss_data


def total_stat_bonus(stat_change_id:list, character_id:int):
    global data

    total = {}

    for entry in [x for x in data.multi_floor_raid_stat_change.values() if x['StatChangeId'] in stat_change_id and character_id in x['ApplyCharacterId']]:
        for i, stat_type in enumerate(entry["StatType"]):
            if stat_type not in total:
                total[stat_type] = {"StatAdd": 0, "StatMultiply": 0}
            total[stat_type]["StatAdd"] += entry["StatAdd"][i]
            total[stat_type]["StatMultiply"] += entry["StatMultiply"][i]

    return total


def total_stats(character_stats, bonus_stats):
    character_stats = copy.copy(character_stats)
    for stat in character_stats:
        statname = stat.replace('100','')
        if statname in bonus_stats:
            #print(f"{stat}: {character_stats[stat]} -> ",end='')
            character_stats[stat] = round((character_stats[stat]+bonus_stats[statname]['StatAdd']) * (1 + bonus_stats[statname]['StatMultiply']/10000))
            #print(character_stats[stat])

    return character_stats


def clear_rewards(reward_group_id):
    global data
    rewards = []

    for reward in data.multi_floor_raid_reward[reward_group_id]:
        rewards.append(StageReward(0, reward['ClearStageRewardParcelType'], reward['ClearStageRewardParcelUniqueID'], '', reward['ClearStageRewardAmount']))

    return rewards


def reward_subtotal(bracket, stages):
    start,end = bracket
    total_rewards = {}

    for stage in [x for x in stages if x['Difficulty'] in range(start,end+1)]:
        for item in stage['clear_rewards']:
            if (item.parcel_type, item.parcel_id) not in total_rewards:
                total_rewards[(item.parcel_type, item.parcel_id)] = copy.copy(item)
            else:
                total_rewards[(item.parcel_type, item.parcel_id)].amount += item.amount

    return {'bracket':bracket, 'rewards': sorted(total_rewards.values(), key=reward_sort_order)}



def generate():
    global args, data, season_data  

    boss_data = {}

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['colorize'] = shared.functions.colorize
    env.filters['nl2br'] = shared.functions.nl2br
    

    region = 'jp'
    for season in season_data[region].multi_floor_raid_season.values():
        print (f"Working on season {season['SeasonId']}")

        boss_data[season['OpenRaidBossGroupId']]= get_raid_boss_data(season['OpenRaidBossGroupId'])

        template = env.get_template('./raid/template_multifloor_raid_boss.txt')
        wikitext_levels = template.render(season_data=season, boss_data=boss_data[season['OpenRaidBossGroupId']])


        stages_to_export = {}
        stages = boss_data[season['OpenRaidBossGroupId']]['stage']

        bracket_start = bracket_end = stages[0]['Difficulty']
        skillgroup_start = stages[0]['skill_list_group_id']

        for index, stage in enumerate(stages):
            bracket_curr = stage['Difficulty']
            skillgroup_curr = stage['skill_list_group_id']
            if skillgroup_start == skillgroup_curr:
                bracket_end = bracket_curr
            else:
                stages_to_export[f"{bracket_start}~{bracket_end}"] = stages[index-1]
                bracket_start = bracket_curr
                skillgroup_start = skillgroup_curr

        stages_to_export[f"{bracket_start}~{bracket_end}"] = stages[-1]

        template = env.get_template('./raid/template_boss_skilltable.txt')
        skilltables = {title:template.render(stage=stage, skills_localization = data.skills_localization, skillbg = True) for title, stage in stages_to_export.items()}
        template = env.get_template('./raid/template_boss_skills.txt')
        wikitext_skills = template.render(skilltables=skilltables)


        wikitext = "==Boss Info==\n" + wikitext_levels + "\n" + wikitext_skills

        with open(os.path.join(args['outdir'], 'raids' ,f"multifloor_raid_season_{season['SeasonId']}.txt"), 'w+', encoding="utf8") as f:
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

