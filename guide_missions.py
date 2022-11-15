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
from model import Item, Furniture, FurnitureGroup

args = None
data = None
missions = None
missing_descriptions = []

item_types = {
        'MaterialItem':'Ooparts of any tier',
        'MaterialItemR':'Tier 2 Ooparts',
        'MaterialItemSR':'Tier 3 Ooparts',
        'MaterialItemSSR':'Tier 4 Ooparts',
        'SecretStone':'Eligma',
        'FavorItem':'Gifts for students',
        'BookItem':'Tech Notes',
        'CDItem':'Tactical Training Blu-rays',
        'ExpItem':'Activity reports',
        'ExpEquip':'Enhancement Stones of any tier',
        'Piece':'Equipment Blueprints of any tier',
        'WeaponExpEquip':'[[Unique weapons]] components',
        'Hat': 'Hat blueprints',
        'Gloves': 'Gloves blueprints',
        'Shoes': 'Shoes blueprints',
        'Bag': 'Bag blueprints',
        'Badge': 'Badge blueprints',
        'Hairpin': 'Hairpin blueprints',
        'Charm': 'Charm blueprints',
        'Watch': 'Watch blueprints',
        'Necklace': 'Necklace blueprints',
    }

clubs = {
        'Countermeasure': 'Countermeasure Council',
        'GourmetClub': 'Gourmet Research Club',
        'RemedialClass': 'Supplemental Classes Club',
        'SisterHood': 'Sisterhood',
        'Kohshinjo68': 'Handyman 68',
        'CleanNClearing': 'Cleaning & Clearing',
        'Shugyobu': 'Inner Discipline Club',
        'MatsuriOffice': 'Festival Organization Committee',
        'Endanbou': 'Chinese alchemy study group',
        'Class227': 'Class No. 227',
        'HoukagoDessert': 'After School Sweets Club',
        'GameDev': 'Game Development Club',
        'Veritas': 'Veritas',
        'Engineer': 'Engineering Club',
        'KnightsHospitaller': 'Rescue Knights',
        'FoodService': 'School Lunch Club',
        'PandemoniumSociety': 'Pandemonium Society',
        'RabbitPlatoon': 'RABBIT Platoon',
        'Emergentology': 'Emergency Medicine Department',
        'RedwinterSecretary': 'Red Winter Secretariat',
        'Fuuki': 'Disciplinary Committee',
        'NinpoKenkyubu': 'Ninjutsu Research Department',
        'anzenkyoku': 'Community Safety Bureau',
        'Justice': 'Justice Actualization Committee',
        'TrinityVigilance': 'Vigilante Corps',
        'Onmyobu': 'Yin-Yang Сlub',
        'BookClub': 'Library Committee',
        'Meihuayuan': 'Plum Blossom Garden',
        'TrainingClub': 'Training Club',
        'SPTF': 'Supernatural Phenomenon Task Force',
        'TheSeminar': 'Seminar',
        'AriusSqud': 'Arius Squad',
        'EmptyClub': 'no club'
}

map_descriptions = {
    'MISSION_CLEAR_ACCOUNT_LEVEL_UP':1033750787,
    'Mission_Get_Specific_Item_Count':999, #event token redeem 
    'MISSION_CLEAR_SPECIFIC_SCENARIO_MAIN_02':856660351,
    'MISSION_CLEAR_SCHEDULE_IN_Millenium_1':9999990001,
    'MISSION_CLEAR_SCHEDULE_IN_Millenium_2':335064968,
    'MISSION_CLEAR_SCHEDULE_IN_Millenium_3':2039883679,
    'MISSION_CLEAR_CAMPAIGN_STAGE_DIFFICULTY_NORMAL':3452893853,
    'MISSION_CLEAR_CAMPAIGN_STAGE_DIFFICULTY_HARD':4209844389,  
    'MISSION_CLEAR_SCHEDULE_IN_SchaleResidence_ArcadeCenter':9999990002,
    'Mission_Schale_Office_At_Specipic_Rank':3638053631,
    'Mission_Schale_Residence_At_Specipic_Rank':3180890437,
    'MISSION_Character_LIMITBREAK':2160474459,
    'MISSION_CHARACTER_SKILL_LEVEL_UP_COUNT':2974642405,
    'MISSION_CLEAR_EQUIPMENT_LEVEL_UP_COUNT':2490203958,
    'MISSION_CLEAR_EQUIPMENT_TIER_UP_COUNT':1464479618,
    'MISSION_CHARACTER_SPECIFIC_LEVEL_COUNT':3383040034,
    'MISSION_USE_GEM':2443754493,
    'MISSION_USE_GOLD':3553550028,
    'MISSION_GET_CHARACTER_COUNT':4260571357,
    'MISSION_GET_CHARACTER_GEHENNA_COUNT':3839565178,
    'Mission_ShopBuyAP_Count':4109224226,
    'MISSION_CAFE_COMFORT':1867335861,
    'Mission_Cafe_Rank_Count':1766036111,
    'MISSION_DAILY_LOGIN':3140972389,
    'Mission_Schedule_Count':383264321,
    'Mission_Total_Get_Clear_Star_Count':2500747902,
    'Mission_Craft_Count':4193814424,
}

map_descriptions_all = {  #for reference only
    'Mission_Get_Specific_Item_Count':1,
    
    'MISSION_CLEAR_SPECIFIC_CAMPAIGN_STAGE':1,
    'MISSION_CLEAR_SPECIFIC_SCENARIO_MAIN_01':2597267329,
    'MISSION_CLEAR_SPECIFIC_SCENARIO_MAIN_02':856660351,
    'MISSION_CLEAR_SPECIFIC_SCENARIO_MAIN_03':1559463659,
    'MISSION_CLEAR_SPECIFIC_SCENARIO_MAIN_04':1,

    'Mission_Clear_Specific_Weekdungeon':1,
    'Mission_Clear_Specific_Weekdungeon_Timelimit':999,
    'Mission_Clear_Specific_Chaserdungeon':1,
    'Mission_Clear_Specific_Chaserdungeon_Timelimit':999,

    'MISSION_KILL_ENEMY_TAG_LARGE':1796370081,

    'MISSION_KILL_ENEMY_TAG_REDHELMET':1,
    'MISSION_KILL_ENEMY_TAG_ENEMYYUUKA':1,
    'MISSION_KILL_ENEMY_TAG_SUKEBAN':3044899148,
    'MISSION_KILL_ENEMY_TAG_KAITENRANGER_PINK':1,
    'MISSION_KILL_ENEMY_TAG_HELMET':1,
    'MISSION_KILL_ENEMY_TAG_ENEMYAKARI':1,
    'MISSION_KILL_ENEMY_TAG_BLACKMARKET_DROID':1,
    'MISSION_KILL_ENEMY_TAG_HELICOPTER':1,
    'MISSION_KILL_ENEMY_TAG_SHIELD':1,
    'MISSION_KILL_ENEMY_TAG_GOLIATH':1,
    'MISSION_KILL_ENEMY_TAG_GEHENNA':1,
    'MISSION_KILL_ENEMY_TAG_ENEMYIORI':1,
    'MISSION_KILL_ENEMY_TAG_DROID':1,
    'MISSION_CLEAR_CHARACTER_LEVEL_UP_COUNT':1,
    'Mission_Clear_Weekdungeon':1,

    'MISSION_KILL_ENEMY_TAG_ENEMYKOTORI':999,
    'Mission_Clear_Specific_Schooldungeon_TimeLimit':999,
    'MISSION_CLEAR_SCHEDULE_IN_StudyRoom':999,
    
    'MISSION_KILL_ENEMY_TAG_MEDIUM':1107780056,

    'MISSION_CLEAR_SCHEDULE_IN_AVRoom':999,
    
    'MISSION_CLEAR_SCHEDULE_IN_Gym':999,

    'MISSION_KILL_ENEMY_TAG_DRONE':999,

    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_Abydos':370693275,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_Justice':3130787843,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_Gehenna':1521286612,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_Trinity':3264920614,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_Millennium':999,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_Hyakkiyako':999,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_Shanhaijing':999,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_RedWinter':999,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_CleanNClearing':999,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_Countermeasure':999,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_Kohshinjo68':999,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_TheSeminar':999,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_Veritas':999,
    'MISSION_CLEAR_SCHEDULE_CHARACTER_TAG_GameDev':999,

    'MISSION_GET_ITEM_TAG_SECRETSTONE':999,
    'MISSION_KILL_ENEMY_TAG_Kaitenranger':999,
    
    'MISSION_GET_FURNITURE_TAG_Furniture':999,
    
    'MISSION_GET_ITEM_TAG_FavorItem':999,
    'MISSION_KILL_ENEMY_TAG_GASMASK_LIGHTARMOR':999,
    'Mission_Battle_Win_With_Tag_Trinity':999,
    'MISSION_KILL_ENEMY_TAG_SMALL':817850220,
    'Mission_Battle_Win_With_Tag_Gehenna':999,
    'Mission_Clear_Specific_Campaign_Stage_Timelimit':999,

    'Mission_Battle_Win_With_Tag_Millennium':999,

    'Mission_Battle_Win_With_Tag_Abydos':999,

    'Mission_Battle_Win_With_Tag_Hyakkiyako':999,

    'Mission_Battle_Win_With_Tag_RedWinter':999,

    'Mission_Battle_Win_With_Tag_Shanhaijing':999,

    'MISSION_GET_EQUIPMENT_TAG_PIECE':999,
    'Mission_Get_Equipment_Tag_WeaponExpEquip':999,
    'Mission_Get_Item_Tag_BookItem':999,
    'Mission_Get_Item_Tag_CDItem':999,
    'Mission_Get_Item_Tag_Favor':999,
    'Mission_Battle_Win_With_Tag_Cover':999,
    'Mission_Battle_Win_With_Tag_Uncover':999,
    'Mission_Join_Arena':999,
    'MISSION_KILL_ENEMY_TAG_Millennium_SCHOOL':999,
    'MISSION_KILL_ENEMY_TAG_Gehenna_SCHOOL':999,
    'MISSION_KILL_ENEMY_TAG_Trinity_SCHOOL':999,
    'MISSION_USE_ACTION_POINT':999,
    'MISSION_CLEAR_SCHEDULE_IN_Gehenna_2':999,
    'Mission_Battle_Win_With_Tag_GourmetClub':999,
    'Mission_Battle_Win_With_Tag_CleanNClearing':999,
    'MISSION_CLEAR_SCHEDULE_IN_Triniy_3':999,
    'Mission_Battle_Win_With_Tag_Fuuki':999,
    'Mission_Get_Item_Tag_ExpItem':999,
    'Mission_Get_Item_Tag_ExpEquip':999,

    'MISSION_KILL_ENEMY_TAG_GameDev':999,
    'MISSION_KILL_ENEMY_TAG_Kohshinjo68':999,

    'MISSION_KILL_ENEMY_TAG_Justice':999,
    'MISSION_CLEAR_SCHEDULE_IN_SchaleResidence_ArcadeCenter':999,

    'Mission_Battle_Win_With_Tag_Veritas':999,
    'Mission_Battle_Win_With_Tag_GameDev':999,
    'Mission_Battle_Win_With_Tag_Engineer':999,}


def generate():
    global args
    global data 
    items = {}
    furniture = {}
    total_rewards = {}

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
    

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('template_guide_missions.txt')

    missions = copy.copy(data.guide_mission)
    season = data.guide_mission_season[args['season']]
    season['StartDate'] = f"{season['StartDate'][0:10]}T{season['StartDate'][11:16]}+09"
    season['EndDate'] = f"{season['EndDate'][0:10]}T{season['EndDate'][11:16]}+09"
    season['CollectibleItemName'] = items[season["RequirementParcelId"]].name_en
    season['CollectibleItemCard'] = '{{ItemCard|'+season['CollectibleItemName']+'}}'#+'|quantity='+str(season['RequirementParcelAmount'])+'}}'


    for mission in data.guide_mission.values():
        if mission['SeasonId'] != args['season']:
            missions.pop(mission['Id'])
            continue
        mission_desc(mission)

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
            else:
                mission['RewardItemNames'].append("UNKNOWN REWARD TYPE")
                print (f"Unknown reward parcel type {mission['MissionRewardParcelType'][index]}")
            
            if mission['MissionRewardParcelId'][index] not in total_rewards:
                total_rewards[mission['MissionRewardParcelId'][index]] = {}
                total_rewards[mission['MissionRewardParcelId'][index]]['Id'] = mission['MissionRewardParcelId'][index]
                total_rewards[mission['MissionRewardParcelId'][index]]['Amount'] = mission['MissionRewardAmount'][index]
                total_rewards[mission['MissionRewardParcelId'][index]]['Type'] = mission['MissionRewardParcelType'][index]
                total_rewards[mission['MissionRewardParcelId'][index]]['IsCompletionReward'] = False
            else:
                total_rewards[mission['MissionRewardParcelId'][index]]['Amount'] += mission['MissionRewardAmount'][index]
            if mission['TabNumber'] == 0:
                total_rewards[mission['MissionRewardParcelId'][index]]['IsCompletionReward'] = True




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



    with open(os.path.join(args['outdir'], f"guide_mission_season_{args['season']}.txt"), 'w', encoding="utf8") as f:
        wikitext = template.render(season=season, missions=missions.values(), total_rewards=total_rewards.values())
        f.write(wikitext)




def mission_desc(mission):

    localize_id = None    
    mission['AutoLocalized'] = False

    if mission['CompleteConditionType'] == 'CompleteScheduleWithTagCount':
        localize_CompleteScheduleWithTagCount(mission)

    if mission['CompleteConditionType'] == 'ClearSchoolDungeonCount':
        localize_ClearSchoolDungeonCount(mission)

    if mission['CompleteConditionType'] == 'ClearSpecificScenario':
        localize_ClearSpecificScenario(mission)

    if mission['CompleteConditionType'] == 'ClearSpecificCampaignStageCount':
        localize_ClearSpecificCampaignStageCount(mission)

    if mission['CompleteConditionType'] == 'ClearCampaignStageTimeLimitFromSecond':
        localize_ClearCampaignStageTimeLimitFromSecond(mission)

    if mission['CompleteConditionType'] == 'GetItemWithTagCount':
        localize_GetItemWithTagCount(mission)

    if mission['CompleteConditionType'] == 'GetEquipmentWithTagCount':
        localize_GetEquipmentWithTagCount(mission)
        
    if mission['CompleteConditionType'] == 'ClearBattleWithTagCount':
        localize_ClearBattleWithTagCount(mission)
   
    if mission['CompleteConditionType'] == 'KillEnemyWithTagCount':
        localize_KillEnemyWithTagCount(mission)
      


    if not mission['AutoLocalized'] and mission['Description'] not in map_descriptions.keys() and mission['Description'] not in missing_descriptions:
        missing_descriptions.append(mission['Description'])
        print (f"Missing localization mapping for {mission['Description']} of {mission}")
        return False

    
    if not mission['AutoLocalized'] and mission['Description'] in map_descriptions.keys() and map_descriptions[mission['Description']] in data.localize_code.keys():
        localize_id = map_descriptions[mission['Description']]
        mission['LocalizeId'] = localize_id
        if 'Jp' in data.localize_code[localize_id]:
            mission['DescriptionJp'] = description_cleanup(data.localize_code[localize_id]['Jp'].replace('{0}', str(mission['CompleteConditionCount']))) 
        if 'En' in data.localize_code[localize_id]:
            mission['DescriptionEn'] = description_cleanup(data.localize_code[localize_id]['En'].replace('{0}', str(mission['CompleteConditionCount']))) 


def localize_CompleteScheduleWithTagCount(mission):
    desc_jp = '受け入れ済みの$2の生徒と$1回スケジュールを実行する'
    desc_en = 'Schedule a lesson with student from $2 $1 time(s)'

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', str(mission['CompleteConditionCount'])).replace('$2',mission['CompleteConditionParameterName'])) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', str(mission['CompleteConditionCount'])).replace('$2',mission['CompleteConditionParameterName'])) 

    mission['AutoLocalized'] = True
    return True


def localize_ClearSchoolDungeonCount(mission):
    desc_jp = ''
    desc_en = 'Participate in School Exchange $1 time(s)'

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_ClearSpecificScenario(mission):
    desc_jp = 'メインストーリー第$1編$2章$3話をクリア'
    desc_en = 'Complete Volume $1, Chapter $2, Episode $3 of the main story'

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', str(mission['CompleteConditionParameter'][0])[0:1])
                                                          .replace('$2', str(mission['CompleteConditionParameter'][0])[1:2])
                                                          .replace('$3', str(mission['CompleteConditionParameter'][0])[2:4].lstrip('0'))
                                                    ) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', str(mission['CompleteConditionParameter'][0])[0:1])
                                                          .replace('$2', str(mission['CompleteConditionParameter'][0])[1:2])
                                                          .replace('$3', str(mission['CompleteConditionParameter'][0])[2:4].lstrip('0'))
                                                    )

    mission['AutoLocalized'] = True
    return True


def localize_ClearSpecificCampaignStageCount(mission):
    desc_jp = 'エリア[[$1]] $2をクリア'
    desc_en = 'Clear $2 Mission [[$1]]'

    difficulty = int(str(mission['CompleteConditionParameter'][0])[3:4])
    difficulty_names = ['','Normal','Hard']

    stage = str(mission['CompleteConditionParameter'][0])[1:3].lstrip('0')+'-'+str(mission['CompleteConditionParameter'][0])[5:7].lstrip('0')+(difficulty == 2 and 'H' or '')

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', stage)
                                                          .replace('$2', difficulty_names[difficulty])
                                                    ) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', stage)
                                                          .replace('$2', difficulty_names[difficulty])
                                                    )

    mission['AutoLocalized'] = True
    return True


def localize_ClearCampaignStageTimeLimitFromSecond(mission):
    desc_jp = '任務ステージ[[$1]]$2を$3秒以内にクリア'
    desc_en = 'Clear $2 Mission [[$1]] within $3 seconds'

    difficulty = int(str(mission['CompleteConditionParameter'][0])[3:4])
    difficulty_names = ['','Normal','Hard']

    stage = str(mission['CompleteConditionParameter'][0])[1:3].lstrip('0')+'-'+str(mission['CompleteConditionParameter'][0])[5:7].lstrip('0')+(difficulty == 2 and 'H' or '')

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', stage)
                                                          .replace('$2', difficulty_names[difficulty])
                                                          .replace('$3', str(mission['CompleteConditionCount']))
                                                    ) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', stage)
                                                          .replace('$2', difficulty_names[difficulty])
                                                          .replace('$3', str(mission['CompleteConditionCount']))
                                                    )

    mission['AutoLocalized'] = True
    return True


def localize_GetItemWithTagCount(mission):
    global item_types

    desc_jp = '$1を$2個獲得する'
    desc_en = 'Acquire $2 $1'

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', item_types[mission['CompleteConditionParameterName']]).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', item_types[mission['CompleteConditionParameterName']]).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_GetEquipmentWithTagCount(mission):
    global item_types

    desc_jp = '$1を$2個獲得する'
    desc_en = 'Acquire $2 $1'

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', item_types[mission['CompleteConditionParameterName']]).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', item_types[mission['CompleteConditionParameterName']]).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_ClearBattleWithTagCount(mission):
    global clubs

    desc_jp = '-'
    desc_en = 'Clear any stage with a student from $1 $2 time(s)'

    tag = mission['CompleteConditionParameterName'] in clubs and clubs[mission['CompleteConditionParameterName']] or mission['CompleteConditionParameterName']
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_KillEnemyWithTagCount(mission):
    global clubs

    desc_jp = '-'
    desc_en = 'Defeat any student from $1 $2 time(s)'

    tag = mission['CompleteConditionParameterName'] in clubs and clubs[mission['CompleteConditionParameterName']] or mission['CompleteConditionParameterName']
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True




def description_cleanup(text):
    #text = re.sub('1回', 'once', text)
    text = text.replace(' 1 time(s)', ' once')
    text = text.replace(' 2 time(s)', ' twice')
    text = text.replace('time(s)', 'times') 

    return text



def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('season', metavar='SEASON_NUMBER', help='Guide mission season to export')
    parser.add_argument('-data_primary', metavar='DIR', help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary', metavar='DIR', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation', metavar='DIR', help='Additional translations directory')
    parser.add_argument('-outdir', metavar='DIR', help='Output directory')

    args = vars(parser.parse_args())
    args['season'] = int(args['season'])

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
