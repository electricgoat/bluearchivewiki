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
from classes.Furniture import Furniture
from classes.Emblem import Emblem
from raid_seasons import RAIDS, SEASON_IGNORE, SEASON_NOTES
import shared.functions
from shared.MissingTranslations import MissingTranslations

args = None

data = None
characters = {}
items = {}
furniture = {}
emblems = {}

season_data = {'jp':None, 'gl':None}
missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_skill_localization = MissingTranslations("translation/missing/LocalizeSkillExcelTable.json")
missing_code_localization = MissingTranslations("translation/missing/LocalizeCodeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")


class SeasonReward(object):
    def __init__(self, id, parcel_type, parcel_id, parcel_name, amount):
        self.id = id
        self.parcel_type = parcel_type
        self.parcel_id = parcel_id
        self.parcel_name = parcel_name
        self.amount = amount

    @property
    def items(self):
        items_list = []
        for i in range(len(self.parcel_type)):
            items_list.append({'parcel_type':self.parcel_type[i], 'parcel_id':self.parcel_id[i], 'parcel_name':self.parcel_name[i], 'amount':self.amount[i]}) 
        return items_list
    
    @property
    def wiki_items(self):
        items_list = []
        for i in range(len(self.parcel_type)):
            items_list.append(wiki_card(self.parcel_type[i], self.parcel_id[i], quantity=self.amount[i], text='', block=True, size='60px' )) 
        return items_list
    
    def format_wiki_items(self, **params):
        items_list = []
        for i in range(len(self.parcel_type)):
            items_list.append(wiki_card(self.parcel_type[i], self.parcel_id[i], quantity=self.amount[i], **params )) 
        return items_list


    @classmethod
    def from_data(cls, id: int, data): #note that this takes actual table such as data.raid_stage_season_reward
        item = data[id]
        
        return cls(
            item['SeasonRewardId'],
            item['SeasonRewardParcelType'],
            item['SeasonRewardParcelUniqueId'],
            item['SeasonRewardParcelUniqueName'],
            item['SeasonRewardAmount'],
        )
    

def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)



def get_raid_boss_data(group):
    global args, data, season_data
    global missing_skill_localization

    boss_data = {}

    boss_data['stage'] = data.raid_stage[group]
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
        rewards = SeasonReward.from_data(season['SeasonRewardId'][i], data.raid_stage_season_reward)
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
    ranking_rewards = data.raid_ranking_reward[season['RankingRewardGroupId']]
    for entry in ranking_rewards:
        reward = SeasonReward(entry['Id'], entry['RewardParcelType'], entry['RewardParcelUniqueId'], entry['RewardParcelUniqueName'], entry['RewardParcelAmount'])
        entry['reward'] = reward
        if entry['RankEnd'] == 0: entry['RankEnd'] = '∞'
    return ranking_rewards



def get_boss_skills(skill_list_group_id, data, missing_skill_localization):

    SKILL_LISTS = {'NormalSkillGroupId':'Normal', 'ExSkillGroupId':'EX', 'PublicSkillGroupId':'Public', 'PassiveSkillGroupId':'Passive', 'LeaderSkillGroupId':'Leader', 'ExtraPassiveSkillGroupId':'Sub', 'HiddenPassiveSkillGroupId':'Hidden'}

    skill_list_group = data.characters_skills[(skill_list_group_id, 0, 0, False)]
    
    #skills appear to be referenced by GroupId rather than Id, so prepare a better data structure
    skills_by_groupid = {item['GroupId']: item for item in data.skills.values()}

    skill_data = [
        {
            **skills_by_groupid[skill_id], 
            'SkillType': SKILL_LISTS[skill_group],
            'IconName': skills_by_groupid[skill_id]['IconName'][skills_by_groupid[skill_id]['IconName'].rfind('/') + 1:]
        }
        for skill_group in SKILL_LISTS.keys()
        for skill_id in skill_list_group[skill_group]
    ]

    for skill in skill_data:
        loc_data = data.skills_localization[skill['LocalizeSkillId']]
        if 'NameEn' not in loc_data and loc_data.get('NameJp', "") != "":
            missing_skill_localization.add_entry(loc_data)

    return skill_data





def generate():
    global args, data, season_data
    global missing_code_localization

    boss_groups = ['OpenRaidBossGroup']
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
    for season in season_data[region].raid_season.values():
        print (f"Working on season {season['SeasonId']}")
        wikitext = "\n==Boss Info==\n===Stats===\n"        

        template = env.get_template('./raid/template_raid_boss.txt')
        for group in boss_groups:
            boss_data[season[group][0]]= get_raid_boss_data(season[group][0])

            durations = '/'.join(set([shared.functions.format_ms_duration(stage['BattleDuration']) for stage in boss_data[season[group][0]]['stage']]))
            wikitext += f"Battle time for this boss is {durations}.\n"
            wikitext += template.render(season_data=season, boss_data=boss_data[season[group][0]])
 
            template = env.get_template('./raid/template_boss_skilltable.txt')
            skilltables = {stage['Difficulty']:template.render(stage=stage, skills_localization = data.skills_localization) for stage in boss_data[season[group][0]]['stage']}
            template = env.get_template('./raid/template_boss_skills.txt')
            wikitext += template.render(skilltables=skilltables)


        wikitext += "\n=Unit recommendations=\n"

        template = env.get_template('./raid/template_ranking_rewards.txt')
        wikitext += template.render(rewards=get_ranking_rewards(season))


        template = env.get_template('./raid/template_cumulative_score_rewards.txt')
        get_cumulative_rewads(season)
        wikitext += template.render(season=season, total_rewards=total_cumulative_rewards(season))

        
        localization_id = boss_data[season[group][0]]['stage'][0]['BossBGInfoKey']
        #print(f"localize_code id is {localization_id}")
        try:
            blurb = 'En' in data.localize_code[localization_id] and data.localize_code[localization_id]['En'] or data.localize_code[localization_id]['Jp']
        except:
            blurb = ''
            if localization_id in data.localize_code: missing_code_localization.add_entry(data.localize_code[localization_id])
        template = env.get_template('./raid/template_raid_intro.txt')
        wikitext = template.render(info=RAIDS[season['OpenRaidBossGroup'][0].split('_',1)[0]], blurb=blurb, season_data=season) + wikitext


        with open(os.path.join(args['outdir'], 'raids' ,f"raid_season_{season['SeasonId']}.txt"), 'w+', encoding="utf8") as f:
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

