import re
from shared.functions import hashkey
from shared.glossary import CLUBS
from shared.tag_map import TAG_MAP

item_types = {
        'MaterialItem':'Ooparts of any tier',
        'MaterialItemN':'Tier 1 Ooparts',
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
        'Tier2Piece': 'Tier 2 equipment blueprints',
        'Tier3Piece': 'Tier 3 equipment blueprints',
        'Tier4Piece': 'Tier 4 equipment blueprints',
        'Tier5Piece': 'Tier 5 equipment blueprints',
        'Tier6Piece': 'Tier 6 equipment blueprints',
        'Tier7Piece': 'Tier 7 equipment blueprints',
        'Tier8Piece': 'Tier 8 equipment blueprints',
        'Tier9Piece': 'Tier 9 equipment blueprints',
    }

enemy_tags = CLUBS | {
        #enemies
        'DecagrammatonSPO': 'Decagrammaton',
}


map_descriptions = {
    'MISSION_CLEAR_ACCOUNT_LEVEL_UP':1033750787,
    #'Mission_Get_Specific_Item_Count':999, #event token redeem 
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
    'MISSION_USE_ACTION_POINT':1282336120,
    'Event_Mission_Kill_DecagrammatonSPO':1276704409,
    'Event_Mission_DiceRace_Use_Dice_Count':1086597895,
    'Event_Mission_DiceRace_Finish_Lap_Count':3628171236,
    'Event_Mission_Complete_Mission_All':546921936,
    'Event_MISSION_CLEAR_CAMPAIGN_STAGE_DIFFICULTY_Hard':9999990003,
    'Event_Mission_Complete_Campaign_Stage_Story': 9999990004,
    'Event_Mission_Complete_Campaign_Stage_Quest': 9999990005,
    'Mission_Event_Location_At_Specipic_Rank_808': 4069346749,
    'Event_Mission_Omikuji_Count': 1910182025,
    'Event_Mission_Daily_Complete_Mission': 373831186,
    'Event_Mission_Conquest_Get_Tile_Count': 9999990007,
    'Mission_Event_Location_At_Specipic_Rank_824': 260494932,
    'Mission_Event_Location_At_Specipic_Rank_817': 816893370,
    'Event_Mission_Complete_Mission_Challenge_Count': 9999990008,
    'Event_Mission_Complete_Mission_Challenge_Count_817': 9999990008,
    'MISSION_CLEAR_SCHEDULE_IN_DU_1': 3664015476,
    'MISSION_CLEAR_SCHEDULE_IN_DU_2': 616759800,
    'Event_Mission_WorldRaid_JoinToBossNumber': 2946961325,
    'Event_Mission_WorldRaid_JoinWithTag_Abydos': 1685706037,
    'Event_Mission_TBG_Complete_Round_Count': 1240110750,
    'Event_Mission_TBG_Complete_Thema1_Normal': 3285415668,
    'Event_Mission_TBG_Complete_Thema2_Normal': 2074176759,
    'Event_Mission_TBG_Complete_Thema3_Normal': 3986099473,
    'Event_Mission_TBG_Complete_Thema4_Normal': 107350320,
    'Event_Mission_TBG_Complete_Thema2_Hidden': 2905801638,
    'Event_Mission_TBG_Complete_Thema4_Hidden': 3584453321,
    'Event_Mission_Complete_Campaign_Stage': 538150987,
    'Event_Mission_Omikuji_Count_832': 2417672652,
    'Mission_Clear_Specific_Chaserdungeon': 1859421411,
    'Mission_Clear_Specific_Schooldungeon': 2400906688,
    'Mission_Clear_Specific_Weekdungeon': 4187819492,
    'MISSION_CLEAR_SCHEDULE_IN_Abydos_1': 3289015374,
}



def mission_desc(mission, data, missing_descriptions = [], items = None, furniture = None):

    localize_id = None    
    mission['AutoLocalized'] = False

    
    key = isinstance(mission['Description'], int) and mission['Description'] or hashkey(mission['Description'])
    if key in data.localization:
        #print (f"Key {key} found in localization data")
        mission['DescriptionJp'] = description_cleanup(data.localization[key].get('Jp').replace('{0}', str(mission['CompleteConditionCount']))) 
        mission['DescriptionEn'] = description_cleanup(data.localization[key].get('En', '').replace('{0}', str(mission['CompleteConditionCount']))) 
        if 'En' not in data.localization[key]: print (f"Untranslated mission localize id {key}")
        #else: return


    #Matching by Description is a finer sieve than condition type, it's used because some conditions are used for differently-phrased missions
    if f"localize_{mission['Description']}" in globals():
        globals()[f"localize_{mission['Description']}"](mission, data, items, furniture)
    elif f"localize_{mission['CompleteConditionType'].replace('Reset_','')}" in globals():
        globals()[f"localize_{mission['CompleteConditionType'].replace('Reset_','')}"](mission, data)


    if not mission['AutoLocalized'] and mission['Description'] not in map_descriptions.keys() and key not in data.localization :
        missing_descriptions.append(mission['Description'])
        print (f"Missing localization mapping {key} for {mission['Description']} of {mission}")
        return False

    
    if not mission['AutoLocalized'] and mission['Description'] in map_descriptions.keys() and map_descriptions[mission['Description']] in data.localize_code.keys():
        localize_id = map_descriptions[mission['Description']]
        mission['LocalizeId'] = localize_id
        if 'Jp' in data.localize_code[localize_id]:
            mission['DescriptionJp'] = description_cleanup(data.localize_code[localize_id]['Jp'].replace('{0}', str(mission['CompleteConditionCount']))) 
        if 'En' in data.localize_code[localize_id]:
            mission['DescriptionEn'] = description_cleanup(data.localize_code[localize_id]['En'].replace('{0}', str(mission['CompleteConditionCount']))) 



def localize_DreamGetSpecificParameter(mission, data):
    key = isinstance(mission['Description'], int) and mission['Description'] or hashkey(mission['Description'])
    desc_jp = data.localization[key].get('Jp')
    desc_en = data.localization[key].get('En', '')

    params = {x['Id']:x for x in data.minigame_dream_parameter[mission['EventContentId']]}
    condition_param = data.localization[params[mission['CompleteConditionParameter'][1]]['LocalizeEtcId']]

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('{0}', str(mission['CompleteConditionCount'])).replace('{1}', condition_param.get('Jp'))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('{0}', str(mission['CompleteConditionCount'])).replace('{1}', condition_param.get('En'))) 

    mission['AutoLocalized'] = True
    return True


def localize_DreamGetSpecificScheduleCount(mission, data):
    key = isinstance(mission['Description'], int) and mission['Description'] or hashkey(mission['Description'])
    desc_jp = data.localization[key].get('Jp')
    desc_en = data.localization[key].get('En', '')

    params = {x['DreamMakerScheduleGroupId']:x for x in data.minigame_dream_schedule[mission['EventContentId']]}
    condition_param = data.localization[params[mission['CompleteConditionParameter'][1]]['LocalizeEtcId']]

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('{0}', str(mission['CompleteConditionCount'])).replace('{1}', condition_param.get('Jp'))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('{0}', str(mission['CompleteConditionCount'])).replace('{1}', condition_param.get('En'))) 

    mission['AutoLocalized'] = True
    return True


def localize_CompleteScheduleWithTagCount(mission, data):
    desc_jp = '受け入れ済みの$2の生徒と$1回スケジュールを実行する'
    desc_en = 'Schedule a lesson with student from $2 $1 time(s)'
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', str(mission['CompleteConditionCount'])).replace('$2',mission['CompleteConditionParameterTag'])) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', str(mission['CompleteConditionCount'])).replace('$2',mission['CompleteConditionParameterTag'])) 

    mission['AutoLocalized'] = True
    return True


def localize_ClearSchoolDungeonCount(mission, data):
    desc_jp = ''
    desc_en = 'Participate in School Exchange $1 time(s)'

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_ClearSpecificScenario(mission, data):
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


def localize_ClearSpecificCampaignStageCount(mission, data):
    desc_jp = 'エリア[[$1]] $2をクリア'
    desc_en = 'Clear $2 Mission [[$1]]'

    difficulty = int(str(mission['CompleteConditionParameter'][-1])[3:4])
    difficulty_names = ['','Normal','Hard']

    stage = str(mission['CompleteConditionParameter'][-1])[1:3].lstrip('0')+'-'+str(mission['CompleteConditionParameter'][0])[5:7].lstrip('0')+(difficulty == 2 and 'H' or '')

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', stage)
                                                          .replace('$2', difficulty_names[difficulty])
                                                    ) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', stage)
                                                          .replace('$2', difficulty_names[difficulty])
                                                    )

    mission['AutoLocalized'] = True
    return True


def localize_ClearCampaignStageTimeLimitFromSecond(mission, data):
    desc_jp = '任務ステージ[[$1]]$2を$3秒以内にクリア'
    desc_en = 'Clear $2 Mission [[$1]] within $3 seconds'

    difficulty = int(str(mission['CompleteConditionParameter'][-1])[3:4])
    difficulty_names = ['','Normal','Hard']

    stage = str(mission['CompleteConditionParameter'][-1])[1:3].lstrip('0')+'-'+str(mission['CompleteConditionParameter'][0])[5:7].lstrip('0')+(difficulty == 2 and 'H' or '')

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


def localize_ClearEventStageTimeLimitFromSecond(mission, data):
    desc_jp = '任務ステージ$1 $2を$3秒以内にクリア'
    desc_en = 'Clear $2 $1 within $3 seconds'

    idlen = len(str(mission['EventContentId']))
    difficulty = int(str(mission['CompleteConditionParameter'][-1])[idlen:idlen+1])
    difficulty_names = ['','Story','Quest','Challenge']

    stage = str(mission['CompleteConditionParameter'][-1])[idlen+2:idlen+4].lstrip('0')

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


def localize_EventCompleteCampaignStageMinimumTurn(mission, data):
    desc_jp = '$2のステージ$1を$3ターン以内にクリア'
    desc_en = 'Clear $2 $1 within $3 turns'

    idlen = len(str(mission['EventContentId']))
    difficulty = int(str(mission['CompleteConditionParameter'][-1])[idlen:idlen+1])
    difficulty_names = ['','Story','Quest','Challenge']

    stage = str(mission['CompleteConditionParameter'][-1])[idlen+2:idlen+4].lstrip('0')

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


def localize_CompleteMission(mission, data):
    desc_jp = 'イベントのチャレンジミションを$1個以上クリア'
    desc_en = 'Complete $1 Achievement Missions'

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', str(mission['CompleteConditionCount']))
                                                    ) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', str(mission['CompleteConditionCount']))
                                                    )

    mission['AutoLocalized'] = True
    return True


def localize_Mission_Get_Specific_Item_Count(mission, data, items, furniture):

    desc_jp = '$1を$2個獲得する'
    desc_en = 'Acquire $2 $1'

    if type(mission['CompleteConditionParameter']) is list:
        for index, etag in enumerate(mission['CompleteConditionParameter']):
            mission['CompleteConditionParameter'][index] = mission['CompleteConditionParameter'][index] in items and items[mission['CompleteConditionParameter'][index]].name_en or f"Item {mission['CompleteConditionParameter'][index]}"
        tag = " or ".join(mission['CompleteConditionParameter'])
    else:
        tag = mission['CompleteConditionParameter'][index] in items and items[mission['CompleteConditionParameter'][index]].name_en or f"Item {mission['CompleteConditionParameter'][index]}"

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_GetItemWithTagCount(mission, data):
    desc_jp = '$1を$2個獲得する'
    desc_en = 'Acquire $2 $1'

    if type(mission['CompleteConditionParameterTag']) is list:
        for index, etag in enumerate(mission['CompleteConditionParameterTag']):
            mission['CompleteConditionParameterTag'][index] = get_item_type(mission['CompleteConditionParameterTag'][index])
        tag = " or ".join(mission['CompleteConditionParameterTag'])
    else:
        tag =  get_item_type(mission['CompleteConditionParameterTag'])

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_GetEquipmentWithTagCount(mission, data):
    global item_types

    desc_jp = '$1を$2個獲得する'
    desc_en = 'Acquire $2 $1'

    for i, tag in enumerate(mission['CompleteConditionParameterTag']):
        if tag in TAG_MAP.keys(): mission['CompleteConditionParameterTag'][i] = TAG_MAP[tag]
    
    if type(mission['CompleteConditionParameterTag']) is list and len(mission['CompleteConditionParameterTag'])==1: mission['CompleteConditionParameterTag'] = mission['CompleteConditionParameterTag'][0] 

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', item_types[mission['CompleteConditionParameterTag']]).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', item_types[mission['CompleteConditionParameterTag']]).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_ClearBattleWithTagCount(mission, data = None):
    global enemy_tags

    desc_jp = '-'
    desc_en = 'Clear any stage with a student from $1 $2 time(s)'

    tag = mission['CompleteConditionParameterTag'] in enemy_tags and enemy_tags[mission['CompleteConditionParameterTag']] or mission['CompleteConditionParameterTag']
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_KillEnemyWithTagCount(mission, data = None):
    global enemy_tags

    desc_jp = '-'
    desc_en = 'Defeat any enemy from $1 $2 time(s)'

    if type(mission['CompleteConditionParameterTag']) is list:
        for index, etag in enumerate(mission['CompleteConditionParameterTag']):
            mission['CompleteConditionParameterTag'][index] = etag in enemy_tags and enemy_tags[etag] or etag
        tag = " or ".join(mission['CompleteConditionParameterTag'])
    else:
        tag = mission['CompleteConditionParameterTag'] in enemy_tags and enemy_tags[mission['CompleteConditionParameterTag']] or mission['CompleteConditionParameterTag']

    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_ConquerSpecificStepTileAll(mission, data = None):
    desc_jp = 'エリア$1をすべて占領'
    desc_en = 'Occupy all of area $1'
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1',str(mission['CompleteConditionParameter'][2]+1))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1',str(mission['CompleteConditionParameter'][2]+1))) 

    mission['AutoLocalized'] = True
    return True


def localize_UpgradeConquestBaseTileCount(mission, data = None):
    desc_jp = 'Lv.{0}拠点を{1}個保有する'
    desc_en = 'Own {1} Lv. {0} base(s)'
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('{1}',str(mission['CompleteConditionCount'])).replace('{0}',str(mission['CompleteConditionParameter'][2]))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('{1}',str(mission['CompleteConditionCount'])).replace('{0}',str(mission['CompleteConditionParameter'][2]))) 

    mission['AutoLocalized'] = True
    return True


def localize_KillConquestBoss(mission, data = None):
    desc_jp = 'エリア{0}のボスを倒す'
    desc_en = 'Defeat the area {0} boss'
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('{0}',str(mission['CompleteConditionParameter'][2]+1))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('{0}',str(mission['CompleteConditionParameter'][2]+1))) 

    mission['AutoLocalized'] = True
    return True


def localize_ClearEventConquestTileTimeLimitFromSecond(mission, data = None):
    desc_jp = '-'
    desc_en = 'Clear Challenge {0} within {1} second(s)'

    clevel = str(mission['CompleteConditionParameter'][0])[-1:]
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('{1}',str(mission['CompleteConditionCount'])).replace('{0}',str(clevel))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('{1}',str(mission['CompleteConditionCount'])).replace('{0}',str(clevel))) 

    mission['AutoLocalized'] = True
    return True


def localize_Event_Mission_Complete_Campaign_Stage_Ground_TimeLimit(mission, data, items, furniture):
    desc_jp = '任務ステージ$1 $2を$3秒以内にクリア'
    desc_en = 'Clear $2 $1 within $3 seconds'

    idlen = len(str(mission['EventContentId']))
    difficulty = int(str(mission['CompleteConditionParameter'][-1])[idlen:idlen+1])
    difficulty_names = ['','Story','Quest','Challenge']

    stage = str(mission['CompleteConditionParameter'][-1])[idlen+2:idlen+4].lstrip('0')

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


def localize_Event_Mission_Complete_Campaign_Stage_Main_TimeLimit(mission, data, items, furniture):
    return localize_Event_Mission_Complete_Campaign_Stage_Ground_TimeLimit(mission, data, items, furniture)
     

def localize_Event_Mission_Complete_Campaign_Stage_Minimum_Turn(mission, data, items, furniture):
    desc_jp = '$2のステージ$1を$3ターン以内にクリア'
    desc_en = 'Clear $2 $1 within $3 turns'

    idlen = len(str(mission['EventContentId']))
    difficulty = int(str(mission['CompleteConditionParameter'][-1])[idlen:idlen+1])
    difficulty_names = ['','Story','Quest','Challenge']

    stage = str(mission['CompleteConditionParameter'][-1])[idlen+2:idlen+4].lstrip('0')

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


def localize_Event_Mission_Clear_Specific_Campaign_Stage(mission, data, items, furniture):
    desc_jp = 'エリア$1 $2をクリア'
    desc_en = 'Clear $2 $1 of the event'

    idlen = len(str(mission['EventContentId']))
    difficulty = int(str(mission['CompleteConditionParameter'][-1])[idlen:idlen+1])
    difficulty_names = ['','Story','Quest','Challenge']

    stage = str(mission['CompleteConditionParameter'][-1])[idlen+2:idlen+4].lstrip('0')

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', stage)
                                                          .replace('$2', difficulty_names[difficulty])
                                                    ) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', stage)
                                                          .replace('$2', difficulty_names[difficulty])
                                                    )

    mission['AutoLocalized'] = True
    return True


def localize_Event_Mission_WorldRaid_DamageToBoss(mission, data, items, furniture):
    desc_jp = '$1に$2以上ダメージ'
    desc_en = 'Deal $1 damage to $2'

    #TODO actually properly localize those
    boss_names = {81400: 'Wakamo (Swimsuit)', 81410: 'Wakamo (Hovercraft)',
                  814000: 'Wakamo (Swimsuit)', 814100: 'Wakamo (Hovercraft)',
                  10814000: 'Wakamo (Swimsuit)', 10814100: 'Wakamo (Hovercraft)'}

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', str(mission['CompleteConditionCount']))
                                                          .replace('$2', boss_names[mission['CompleteConditionParameter'][1]])
                                                    ) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', str(mission['CompleteConditionCount']))
                                                          .replace('$2', boss_names[mission['CompleteConditionParameter'][1]])
                                                    )
    
    mission['AutoLocalized'] = True
    return True


def localize_Event_Mission_WorldRaid_TimeLimit(mission, data, items, furniture):
    desc_jp = '$1$2を$3秒以内にクリア'
    desc_en = 'Defeat $1 on $2 within $3 seconds'

    #TODO actually properly localize those
    boss_names = {81400: 'Wakamo (Swimsuit)', 81410: 'Wakamo (Hovercraft)',
                  814000: 'Wakamo (Swimsuit)', 814100: 'Wakamo (Hovercraft)',
                  10814000: 'Wakamo (Swimsuit)', 10814100: 'Wakamo (Hovercraft)', 301200: 'Wakamo (Swimsuit)', 302200: 'Wakamo (Hovercraft)'}

    difficulty = int(str(mission['CompleteConditionParameter'][1])[6:7])
    difficulty_names = ['','Normal','Hard','VeryHard']


    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', boss_names[int(str(mission['CompleteConditionParameter'][1])[:-3])])
                                                          .replace('$2', difficulty_names[difficulty])
                                                          .replace('$3', str(mission['CompleteConditionCount']))
                                                    ) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', boss_names[int(str(mission['CompleteConditionParameter'][1])[:-3])])
                                                          .replace('$2', difficulty_names[difficulty])
                                                          .replace('$3', str(mission['CompleteConditionCount']))
                                                    )

    mission['AutoLocalized'] = True
    return True



def description_cleanup(text):
    #text = re.sub('1回', 'once', text)
    text = text.replace(' 1 time(s)', ' once')
    text = text.replace(' 2 time(s)', ' twice')
    text = text.replace('time(s)', 'times') 
    text = text.replace(' 1 laps', ' 1 lap')
    text = text.replace(' 1 base(s)', ' 1 base')
    text = text.replace(' base(s)', ' bases')
    text = text.replace(' second(s)', ' seconds')

    return text


def get_item_type(text):
    global item_types
    
    if text in TAG_MAP.keys(): text = TAG_MAP[text]
    if text in item_types: text = item_types[text]

    if re.search(r"^Token_S\d+$", text, re.MULTILINE): text = 'Event Tokens'

    return text
