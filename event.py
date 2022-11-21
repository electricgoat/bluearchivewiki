import collections
import os
import re
import traceback
import copy
import argparse

from enum import IntFlag, auto
from jinja2 import Environment, FileSystemLoader
from data import load_data
from model import Item, Furniture, FurnitureGroup, Character
from model_stages import EventStage
from events.mission_desc import mission_desc


args = None
data = None

items = {}
furniture = {}

stages = {}
missions = {}

total_rewards = {}


class Card(IntFlag):
    PROBABILITY = auto()
    QUANTITY = auto()


def parse_stages(season_id):
    global args, data
    stages = []

    for stage in data.event_content_stages.values():
        if stage['EventContentId'] != season_id:
            continue
    
        stage = EventStage.from_data(stage['Id'], data)
        stages.append(stage)

    return stages
    

def wiki_itemcard(reward, *params):
    # match reward.prob:
    #     case 100:
    #         probability = ''
    #     case _:
    card_type = reward.type != 'Character' and 'ItemCard' or 'CharacterCard'

    if Card.PROBABILITY in params: probability = f'|probability={reward.prob:g}'
    else: probability = ''

    if Card.QUANTITY in params: quantity = reward.amount>1 and '|quantity='+str(reward.amount) or ''
    else: quantity = ''

    return '{{'+card_type+'|'+reward.name+quantity+probability+'|text=|60px|block}}'



def parse_missions(season_id):
    global args, data, missions
    missions = copy.copy(data.event_content_mission)
    missing_descriptions = []
    global total_rewards

    
    for mission in data.event_content_mission.values():
        if mission['EventContentId'] != season_id:
            missions.pop(mission['Id'])
            continue
        
        mission_desc(mission, data, missing_descriptions)

        mission['RewardItemNames'] = []
        mission['RewardItemCards'] = []
    
        for index, _ in enumerate(mission['MissionRewardParcelType']):
            if mission['MissionRewardParcelType'][index] == 'Item':
                mission['RewardItemNames'].append(items[mission['MissionRewardParcelId'][index]].name_en )
                mission['RewardItemCards'].append('{{ItemCard|'+items[mission['MissionRewardParcelId'][index]].name_en+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
                #print(data.items[mission['MissionRewardParcelId'][index]].name_en)
            elif mission['MissionRewardParcelType'][index] == 'Furniture':
                mission['RewardItemNames'].append(furniture[mission['MissionRewardParcelId'][index]].name_en )
                mission['RewardItemCards'].append('{{FurnitureCard|'+furniture[mission['MissionRewardParcelId'][index]].name_en+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
                #print(data.furniture[mission['MissionRewardParcelId'][index]].name_en)
            elif mission['MissionRewardParcelType'][index] == 'Equipment':
                mission['RewardItemNames'].append(data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
                mission['RewardItemCards'].append('{{ItemCard|'+data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn']+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
                #print(data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
            elif mission['MissionRewardParcelType'][index] == 'Currency':
                mission['RewardItemNames'].append(data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
                mission['RewardItemCards'].append('{{ItemCard|'+data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn']+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
                #print(data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
            else:
                mission['RewardItemNames'].append("UNKNOWN REWARD TYPE")
                print (f"Unknown reward parcel type {mission['MissionRewardParcelType'][index]}")
            
            if mission['Category'] == "EventAchievement":
                if mission['MissionRewardParcelId'][index] not in total_rewards:
                    total_rewards[mission['MissionRewardParcelId'][index]] = {}
                    total_rewards[mission['MissionRewardParcelId'][index]]['Id'] = mission['MissionRewardParcelId'][index]
                    total_rewards[mission['MissionRewardParcelId'][index]]['Amount'] = mission['MissionRewardAmount'][index]
                    total_rewards[mission['MissionRewardParcelId'][index]]['Type'] = mission['MissionRewardParcelType'][index]
                    total_rewards[mission['MissionRewardParcelId'][index]]['IsCompletionReward'] = False
                else:
                    total_rewards[mission['MissionRewardParcelId'][index]]['Amount'] += mission['MissionRewardAmount'][index]
                # if mission['TabNumber'] == 0:
                #     total_rewards[mission['MissionRewardParcelId'][index]]['IsCompletionReward'] = True
        
        
    icon_size = ['80px','60px']
    for item in total_rewards.values():
        if item['Type'] == 'Item':
            item['Name'] = (items[item['Id']].name_en )
            item['Card'] = ('{{ItemCard|'+items[item['Id']].name_en+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
            item['Tags'] = items[item['Id']].tags
        elif item['Type'] == 'Furniture':
            item['Name'] = (furniture[item['Id']].name_en )
            item['Card'] = ('{{FurnitureCard|'+furniture[item['Id']].name_en+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
        elif item['Type'] == 'Equipment':
            item['Name'] = (data.etc_localization[data.equipment[item['Id']]['LocalizeEtcId']]['NameEn'])
            item['Card'] = ('{{ItemCard|'+data.etc_localization[ data.equipment[item['Id']]['LocalizeEtcId']]['NameEn']+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
        elif item['Type'] == 'Currency':
            item['Name'] = (data.etc_localization[data.currencies[item['Id']]['LocalizeEtcId']]['NameEn'])
            item['Card'] = ('{{ItemCard|'+data.etc_localization[ data.currencies[item['Id']]['LocalizeEtcId']]['NameEn']+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
        else:
            item['Name'] = ("UNKNOWN REWARD TYPE")
            print (f"Unknown reward parcel type {item['Type']}")


    return missions




def generate():
    global args, data, stages, missions
    global items, furniture
    global total_rewards


    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])


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

   

    season = data.event_content_seasons[(args['event_season'], "Stage")]


    if (args['event_season'], "Stage") in data.event_content_seasons:
        stages = parse_stages(data.event_content_seasons[(args['event_season'], "Stage")]['EventContentId'])

    if (args['event_season'], "Mission") in data.event_content_seasons:
        missions = parse_missions(data.event_content_seasons[(args['event_season'], "Mission")]['EventContentId'])
    
    
    stage_reward_types = {x: [] for x in ['Normal', 'Hard', 'VeryHard']}

    for stage in stages:
        for reward_tag in stage.rewards:
            if reward_tag not in stage_reward_types[stage.difficulty]:
                stage_reward_types[stage.difficulty].append(reward_tag)


    wikitext_stages = ''
    difficulty_names = {'Normal':'Story','Hard':'Quest','VeryHard':'Challenge'}
    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.globals['wiki_itemcard'] = wiki_itemcard

    for difficulty in stage_reward_types:
        template = env.get_template('events/template_event_stages.txt')
        wikitext_stages += template.render(stage_type=difficulty_names[difficulty], stages=[x for x in stages if x.difficulty == difficulty], reward_types=stage_reward_types[difficulty], rewardcols = len(stage_reward_types[difficulty]), Card=Card)


    template = env.get_template('events/template_event.txt')
    wikitext_event = template.render(season=season)

    template = env.get_template('events/template_event_missions.txt')
    wikitext_missions = template.render(season=season, missions=missions.values(), total_rewards=total_rewards.values())

    with open(os.path.join(args['outdir'], 'events' ,f"event_{season['EventContentId']}.txt"), 'w', encoding="utf8") as f:
        f.write(wikitext_event+wikitext_stages+wikitext_missions)





def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('event_season', metavar='SEASON_NUMBER', help='Event mission season to export')
    parser.add_argument('-data_primary', metavar='DIR', help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary', metavar='DIR', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation', metavar='DIR', help='Additional translations directory')
    parser.add_argument('-outdir', metavar='DIR', help='Output directory')

    args = vars(parser.parse_args())
    args['event_season'] = int(args['event_season'])

    args['data_primary'] = args['data_primary'] == None and '../ba-data/jp' or args['data_primary']
    args['data_secondary'] = args['data_secondary'] == None and '../ba-data/global' or args['data_secondary']
    args['translation'] = args['translation'] == None and '../bluearchivewiki/translation' or args['translation']
    args['outdir'] = args['outdir'] == None and 'out' or args['outdir']
    print(args)

    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()

    

if __name__ == '__main__':
    main()


