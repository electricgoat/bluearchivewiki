import os
import copy
from jinja2 import Environment, FileSystemLoader

import shared.functions
from events.mission_desc import mission_desc
from classes.Stage import DefenseStage
from classes.RewardParcel import RewardParcel

missing_localization = None
missing_code_localization = None
missing_etc_localization = None

data = {}
characters = {}
items = {}
furniture = {}
emblems = {}

total_rewards = {}
total_milestone_rewards = {}


def parse_stages(season_id):
    global data
    global missing_localization, missing_etc_localization
    stages = []

    for stage in data.minigame_defense_stage.values():
        if stage['EventContentId'] != season_id:
            continue
        stage = DefenseStage.from_data(stage['Id'], data, wiki_card=wiki_card, missing_localization=missing_localization, missing_etc_localization=missing_etc_localization)
        stages.append(stage)
                
    return stages


# def parse_missions(season_id):
#     global data, characters, items, furniture, emblems

#     missions = data.minigame_mission[season_id]
#     missing_descriptions = []
#     global total_rewards
 
#     for mission in missions:
        
#         mission_desc(mission, data, missing_descriptions, items=items, furniture=furniture)

#         mission['RewardItemNames'] = []
#         mission['RewardItemCards'] = []
    
#         for index, _ in enumerate(mission['MissionRewardParcelType']):
#             mission_reward_parcels(mission, index)
            
#             if mission['Category'] in ["MiniGameEvent", 'MiniGameScore']:
#                 if mission['MissionRewardParcelId'][index] not in total_rewards:
#                     total_rewards[mission['MissionRewardParcelId'][index]] = {}
#                     total_rewards[mission['MissionRewardParcelId'][index]]['Id'] = mission['MissionRewardParcelId'][index]
#                     total_rewards[mission['MissionRewardParcelId'][index]]['Amount'] = mission['MissionRewardAmount'][index]
#                     total_rewards[mission['MissionRewardParcelId'][index]]['Type'] = mission['MissionRewardParcelType'][index]
#                     total_rewards[mission['MissionRewardParcelId'][index]]['IsCompletionReward'] = False
#                 else:
#                     total_rewards[mission['MissionRewardParcelId'][index]]['Amount'] += mission['MissionRewardAmount'][index]
#                 # if mission['TabNumber'] == 0:
#                 #     total_rewards[mission['MissionRewardParcelId'][index]]['IsCompletionReward'] = True   
        
#     for item in total_rewards.values():
#         total_reward_card(item)

#     return missions



# def parse_milestone_rewards(season_id):
#     global args, data
#     global total_milestone_rewards

#     milestones = [x for x in data.event_content_stage_total_rewards.values() if x['EventContentId'] == season_id]

#     for mission in milestones:        
#         mission['DescriptionEn'] = f"Event Points: {mission['RequiredEventItemAmount']}"

#         mission['RewardItemNames'] = []
#         mission['RewardItemCards'] = []
    
#         for index, _ in enumerate(mission['RewardParcelType']):
#             mission['MissionRewardParcelType'] = mission['RewardParcelType']
#             mission['MissionRewardParcelId'] = mission['RewardParcelId']
#             mission['MissionRewardAmount'] = mission['RewardParcelAmount']

#             mission_reward_parcels(mission, index)  

#             if (mission['RewardParcelType'][index], mission['RewardParcelId'][index]) not in total_milestone_rewards:
#                 total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])] = {}
#                 total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])]['Id'] = mission['RewardParcelId'][index]
#                 total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])]['Amount'] = mission['RewardParcelAmount'][index]
#                 total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])]['Type'] = mission['RewardParcelType'][index]
#                 total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])]['IsCompletionReward'] = False
#             else:
#                 total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])]['Amount'] += mission['RewardParcelAmount'][index]
  
#     for item in total_milestone_rewards.values():
#         total_reward_card(item)

#     return milestones



# def mission_reward_parcels(mission, index):
#     global data, characters, items, furniture, emblems

#     if mission['MissionRewardParcelType'][index] == 'Item':
#         mission['RewardItemNames'].append(items[mission['MissionRewardParcelId'][index]].name_en )
#         mission['RewardItemCards'].append('{{ItemCard|'+items[mission['MissionRewardParcelId'][index]].name_en+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
#         #print(data.items[mission['MissionRewardParcelId'][index]].name_en)
#     elif mission['MissionRewardParcelType'][index] == 'Furniture':
#         mission['RewardItemNames'].append(furniture[mission['MissionRewardParcelId'][index]].name_en )
#         mission['RewardItemCards'].append('{{FurnitureCard|'+furniture[mission['MissionRewardParcelId'][index]].name_en+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
#         #print(data.furniture[mission['MissionRewardParcelId'][index]].name_en)
#     elif mission['MissionRewardParcelType'][index] == 'Equipment':
#         mission['RewardItemNames'].append(data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
#         mission['RewardItemCards'].append('{{ItemCard|'+data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn']+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
#         #print(data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
#     elif mission['MissionRewardParcelType'][index] == 'Currency':
#         mission['RewardItemNames'].append(data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
#         mission['RewardItemCards'].append('{{ItemCard|'+data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn']+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
#         #print(data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
#     elif mission['MissionRewardParcelType'][index] == 'Emblem':
#         mission['RewardItemNames'].append(emblems[mission['MissionRewardParcelId'][index]].name)
#         mission['RewardItemCards'].append('{{TitleCard|'+emblems[mission['MissionRewardParcelId'][index]].name+'}}')
#     else:
#         mission['RewardItemNames'].append("UNKNOWN REWARD TYPE")
#         print (f"Unknown reward parcel type {mission['MissionRewardParcelType'][index]}")

#     return



# def total_reward_card(item):
#     global data, character, items, furniture, emblems
#     icon_size = ['80px','60px']

#     if item['Type'] == 'Item':
#         item['Name'] = (items[item['Id']].name_en )
#         item['Card'] = ('{{ItemCard|'+items[item['Id']].name_en+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
#         item['Tags'] = items[item['Id']].tags
#     elif item['Type'] == 'Furniture':
#         item['Name'] = (furniture[item['Id']].name_en )
#         item['Card'] = ('{{FurnitureCard|'+furniture[item['Id']].name_en+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
#     elif item['Type'] == 'Equipment':
#         item['Name'] = (data.etc_localization[data.equipment[item['Id']]['LocalizeEtcId']]['NameEn'])
#         item['Card'] = ('{{ItemCard|'+data.etc_localization[ data.equipment[item['Id']]['LocalizeEtcId']]['NameEn']+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
#     elif item['Type'] == 'Currency':
#         item['Name'] = (data.etc_localization[data.currencies[item['Id']]['LocalizeEtcId']]['NameEn'])
#         item['Card'] = ('{{ItemCard|'+data.etc_localization[ data.currencies[item['Id']]['LocalizeEtcId']]['NameEn']+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
#     elif item['Type'] == 'Emblem':
#         item['Name'] = (emblems[item['Id']].name)
#         item['Card'] = ('{{TitleCard|'+emblems[item['Id']].name+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|text=}}')
#     else:
#         item['Name'] = ("UNKNOWN REWARD TYPE")
#         print (f"Unknown reward parcel type {item['Type']}")

#     return





def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)


def get_mode_defense(season_id: int, ext_data, ext_characters, ext_items, ext_furniture, ext_emblems, ext_missing_localization, ext_missing_code_localization, ext_missing_etc_localization):
    global data, characters, items, furniture, emblems
    global missing_localization, missing_code_localization, missing_etc_localization
    data = ext_data
    characters = ext_characters
    items = ext_items
    furniture = ext_furniture
    emblems = ext_emblems
    missing_localization = ext_missing_localization
    missing_code_localization = ext_missing_code_localization
    missing_etc_localization = ext_missing_etc_localization

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.globals['len'] = len
    
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['nl2br'] = shared.functions.nl2br
    env.filters['nl2p'] = shared.functions.nl2p


    title = 'Hi-Lo Ha-Lo Minigame'
    wikitext = {'title':f"=={title}==", 'intro':'', 'banned':'', 'stages':'', 'collection':'', 'missions':''}


    template = env.get_template('template_defense_intro.txt')
    wikitext['intro'] = template.render(name=title, defense_info = data.minigame_defense_info[season_id])
    #print(wikitext['intro'])

    template = env.get_template('template_banned_characters.txt')
    ban_ids = [x['CharacterId'] for x in data.minigame_defense_character_ban[season_id]]
    wikitext['banned'] = template.render(character_names = [characters[x].wiki_name for x in characters if x in ban_ids ])
    #print(wikitext['banned'])


    stages = {}

    DIFFICULTY_NAMES = {'Normal':'Story', 'Hard':'Normal', 'VeryHard':'Challenge'}
    stage_reward_types = {x: [] for x in DIFFICULTY_NAMES.keys()}
    stages = parse_stages(season_id)

    for stage in stages:
        for reward_tag in stage.rewards.keys():
            if reward_tag not in stage_reward_types[stage.difficulty]:
                stage_reward_types[stage.difficulty].append(reward_tag)

    template = env.get_template('template_defense_stages.txt')
    for difficulty in stage_reward_types:
        stages_filtered = [x for x in stages if x.difficulty == difficulty]
        if len(stages_filtered): 
            #for stage in stages_filtered: print(stage.rewards)
            wikitext['stages'] += template.render(stage_type=DIFFICULTY_NAMES[difficulty], stages=stages_filtered, reward_types=stage_reward_types[difficulty], rewardcols = len(stage_reward_types[difficulty]))
    #print(wikitext['stages'])




            
    return '\n'.join(wikitext.values())
