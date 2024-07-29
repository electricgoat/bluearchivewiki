from events.mission_desc import mission_desc

missing_localization = None
missing_code_localization = None
missing_etc_localization = None

data = {}
characters = {}
items = {}
furniture = {}
emblems = {}


def parse_minigame_missions(season_id, ext_data, ext_characters, ext_items, ext_furniture, ext_emblems, ext_missing_localization, ext_missing_code_localization, ext_missing_etc_localization):
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

    missions = data.minigame_mission[season_id]
    missing_descriptions = []

    total_rewards = {}
 
    for mission in missions:
        
        mission_desc(mission, data, missing_descriptions, items=items, furniture=furniture)

        mission['RewardItemNames'] = []
        mission['RewardItemCards'] = []
    
        for index, _ in enumerate(mission['MissionRewardParcelType']):
            mission_reward_parcels(mission, index)
            
            if mission['Category'] in ["MiniGameEvent", 'MiniGameScore']:
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
        
    for item in total_rewards.values():
        total_reward_card(item)

    return missions, total_rewards


def mission_reward_parcels(mission, index):
    global data, characters, items, furniture, emblems

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
    elif mission['MissionRewardParcelType'][index] == 'Emblem':
        mission['RewardItemNames'].append(emblems[mission['MissionRewardParcelId'][index]].name)
        mission['RewardItemCards'].append('{{TitleCard|'+emblems[mission['MissionRewardParcelId'][index]].name+'}}')
    else:
        mission['RewardItemNames'].append("UNKNOWN REWARD TYPE")
        print (f"Unknown reward parcel type {mission['MissionRewardParcelType'][index]}")

    return



def total_reward_card(item):
    global data, characters, items, furniture, emblems
    icon_size = ['80px','60px']

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
    elif item['Type'] == 'Emblem':
        item['Name'] = (emblems[item['Id']].name)
        item['Card'] = ('{{TitleCard|'+emblems[item['Id']].name+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|text=}}')
    else:
        item['Name'] = ("UNKNOWN REWARD TYPE")
        print (f"Unknown reward parcel type {item['Type']}")

    return