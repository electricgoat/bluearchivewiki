from dataclasses import replace
import os
import re
import sys
import traceback
#import json
import copy
import argparse

from jinja2 import Environment, FileSystemLoader

from data import load_data
from model import Character, Item
from classes.Furniture import Furniture
from events.mission_desc import mission_desc
from shared.functions import hashkey

args = None
data = None
characters = {}
missions = None
missing_descriptions = []



def generate():
    global args
    global data 
    global characters
    items = {}
    furniture = {}
    total_rewards = {'Item':{},'Furniture':{},'Equipment':{},'Currency':{},'Character':{}}

    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            char = Character.from_data(character['Id'], data)
            characters[char.id] = char
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()

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
            print(f'Failed to parse for item {item}: {err}')
            traceback.print_exc()
            continue
    

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('events/template_guide_missions.txt')

    missions = copy.copy(data.guide_mission)
    season = data.guide_mission_season[args['id']]
    season['StartDate'] = f"{season['StartDate'][0:10]}T{season['StartDate'][11:16]}+09"
    season['EndDate'] = f"{season['EndDate'][0:10]}T{season['EndDate'][11:16]}+09"
    season['CollectibleItemName'] = items[season["RequirementParcelId"]].name_en
    season['CollectibleItemCard'] = '{{ItemCard|'+season['CollectibleItemName']+'}}'#+'|quantity='+str(season['RequirementParcelAmount'])+'}}'

    print(f"Title localize {hashkey(season['TitleLocalizeCode'])}")


    for mission in data.guide_mission.values():
        if mission['SeasonId'] != args['id']:
            missions.pop(mission['Id'])
            continue
        mission_desc(mission, data, missing_descriptions, items, furniture)

        mission['RewardItemNames'] = []
        mission['RewardItemCards'] = []
    
        for index, _ in enumerate(mission['MissionRewardParcelType']):
            if mission['MissionRewardParcelType'][index] == 'Item':
                mission['RewardItemNames'].append(items[mission['MissionRewardParcelId'][index]].name_en )
                mission['RewardItemCards'].append('{{ItemCard|'+items[mission['MissionRewardParcelId'][index]].name_en+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
                #print(items[mission['MissionRewardParcelId'][index]].name_en)
            elif mission['MissionRewardParcelType'][index] == 'Furniture':
                mission['RewardItemNames'].append(furniture[mission['MissionRewardParcelId'][index]].name_en )
                mission['RewardItemCards'].append('{{FurnitureCard|'+furniture[mission['MissionRewardParcelId'][index]].name_en+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
                #print(furniture[mission['MissionRewardParcelId'][index]].name_en)
            elif mission['MissionRewardParcelType'][index] == 'Equipment':
                mission['RewardItemNames'].append(data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
                mission['RewardItemCards'].append('{{ItemCard|'+data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn']+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
                #print(data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
            elif mission['MissionRewardParcelType'][index] == 'Currency':
                mission['RewardItemNames'].append(data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
                mission['RewardItemCards'].append('{{ItemCard|'+data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn']+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
                #print(data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
            elif mission['MissionRewardParcelType'][index] == 'Character':
                mission['RewardItemNames'].append(characters[mission['MissionRewardParcelId'][index]].wiki_name)
                mission['RewardItemCards'].append('{{CharacterCard|'+characters[mission['MissionRewardParcelId'][index]].wiki_name+'}}')
            else:
                mission['RewardItemNames'].append("UNKNOWN REWARD TYPE")
                print (f"Unknown reward parcel type {mission['MissionRewardParcelType'][index]}")
            
            if mission['MissionRewardParcelId'][index] not in total_rewards[mission['MissionRewardParcelType'][index]]:
                total_rewards[mission['MissionRewardParcelType'][index]][mission['MissionRewardParcelId'][index]] = {}
                total_rewards[mission['MissionRewardParcelType'][index]][mission['MissionRewardParcelId'][index]]['Id'] = mission['MissionRewardParcelId'][index]
                total_rewards[mission['MissionRewardParcelType'][index]][mission['MissionRewardParcelId'][index]]['Amount'] = mission['MissionRewardAmount'][index]
                total_rewards[mission['MissionRewardParcelType'][index]][mission['MissionRewardParcelId'][index]]['Type'] = mission['MissionRewardParcelType'][index]
                total_rewards[mission['MissionRewardParcelType'][index]][mission['MissionRewardParcelId'][index]]['IsCompletionReward'] = False
            else:
                total_rewards[mission['MissionRewardParcelType'][index]][mission['MissionRewardParcelId'][index]]['Amount'] += mission['MissionRewardAmount'][index]
            if mission['TabNumber'] == 0:
                total_rewards[mission['MissionRewardParcelType'][index]][mission['MissionRewardParcelId'][index]]['IsCompletionReward'] = True


    icon_size = ['80px','60px']
    for item in total_rewards['Item'].values():
        item['Name'] = (items[item['Id']].name_en )
        item['Card'] = ('{{ItemCard|'+items[item['Id']].name_en+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
        item['Tags'] = items[item['Id']].tags

    for item in total_rewards['Furniture'].values():
        item['Name'] = (furniture[item['Id']].name_en )
        item['Card'] = ('{{FurnitureCard|'+furniture[item['Id']].name_en+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')

    for item in total_rewards['Equipment'].values():
        item['Name'] = (data.etc_localization[data.equipment[item['Id']]['LocalizeEtcId']]['NameEn'])
        item['Card'] = ('{{ItemCard|'+data.etc_localization[ data.equipment[item['Id']]['LocalizeEtcId']]['NameEn']+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')

    for item in total_rewards['Currency'].values():
        item['Name'] = (data.etc_localization[data.currencies[item['Id']]['LocalizeEtcId']]['NameEn'])
        item['Card'] = ('{{ItemCard|'+data.etc_localization[ data.currencies[item['Id']]['LocalizeEtcId']]['NameEn']+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')

    for item in total_rewards['Character'].values():
        item['Name'] = (characters[item['Id']].wiki_name)
        item['Card'] = ('{{CharacterCard|'+characters[item['Id']].wiki_name+'}}')


    with open(os.path.join(args['outdir'], 'events', f"guide_mission_season_{args['id']}.txt"), 'w', encoding="utf8") as f:
        wikitext = template.render(season=season, missions=missions.values(), total_rewards=total_rewards, tab_count = len(set([x['TabNumber'] for x in missions.values()])) )
        f.write(wikitext)




def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('id', metavar='ID_NUMBER', help='Guide mission id to export')
    parser.add_argument('-data_primary', metavar='DIR', help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary', metavar='DIR', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation', metavar='DIR', help='Additional translations directory')
    parser.add_argument('-outdir', metavar='DIR', help='Output directory')

    args = vars(parser.parse_args())
    args['id'] = int(args['id'])

    args['data_primary'] = args['data_primary'] == None and '../ba-data/jp' or args['data_primary']
    args['data_secondary'] = args['data_secondary'] == None and '../ba-data/global' or args['data_secondary']
    args['translation'] = args['translation'] == None and 'translation' or args['translation']
    args['outdir'] = args['outdir'] == None and 'out' or args['outdir']
    print(args)


    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
