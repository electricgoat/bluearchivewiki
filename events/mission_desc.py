import re

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
        'Tier2Piece': 'Tier 2 equipment blueprints',
        'Tier3Piece': 'Tier 3 equipment blueprints',
        'Tier4Piece': 'Tier 4 equipment blueprints',
        'Tier5Piece': 'Tier 5 equipment blueprints',
        'Tier6Piece': 'Tier 6 equipment blueprints',
        'Tier7Piece': 'Tier 7 equipment blueprints',
        'Tier8Piece': 'Tier 8 equipment blueprints',
        'Tier9Piece': 'Tier 9 equipment blueprints',
    }

enemy_tags = {
        #clubs
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
        'EmptyClub': 'no club',

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




def mission_desc(mission, data, missing_descriptions = [], items = None, furniture = None):

    localize_id = None    
    mission['AutoLocalized'] = False

    #Matching by Description is a finer sieve than condition type, it's used because some conditions are used for differently-phrased missions
    if f"localize_{mission['Description']}" in globals():
        globals()[f"localize_{mission['Description']}"](mission, data, items, furniture)
    elif f"localize_{mission['CompleteConditionType'].replace('Reset_','')}" in globals():
        globals()[f"localize_{mission['CompleteConditionType'].replace('Reset_','')}"](mission)


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


def localize_ClearEventStageTimeLimitFromSecond(mission):
    desc_jp = '任務ステージ$1 $2を$3秒以内にクリア'
    desc_en = 'Clear $2 $1 within $3 seconds'

    idlen = len(str(mission['EventContentId']))
    difficulty = int(str(mission['CompleteConditionParameter'][0])[idlen:idlen+1])
    difficulty_names = ['','Story','Quest','Challenge']

    stage = str(mission['CompleteConditionParameter'][0])[idlen+2:idlen+4].lstrip('0')

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


def localize_EventCompleteCampaignStageMinimumTurn(mission):
    desc_jp = '$2のステージ$1を$3ターン以内にクリア'
    desc_en = 'Clear $2 $1 within $3 turns'

    idlen = len(str(mission['EventContentId']))
    difficulty = int(str(mission['CompleteConditionParameter'][0])[idlen:idlen+1])
    difficulty_names = ['','Story','Quest','Challenge']

    stage = str(mission['CompleteConditionParameter'][0])[idlen+2:idlen+4].lstrip('0')

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


def localize_CompleteMission(mission):
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


def localize_GetItemWithTagCount(mission):
    desc_jp = '$1を$2個獲得する'
    desc_en = 'Acquire $2 $1'

    if type(mission['CompleteConditionParameterName']) is list:
        for index, etag in enumerate(mission['CompleteConditionParameterName']):
            mission['CompleteConditionParameterName'][index] = get_item_type(mission['CompleteConditionParameterName'][index])
        tag = " or ".join(mission['CompleteConditionParameterName'])
    else:
        tag =  get_item_type(mission['CompleteConditionParameterName'])

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_GetEquipmentWithTagCount(mission):
    global item_types

    desc_jp = '$1を$2個獲得する'
    desc_en = 'Acquire $2 $1'

    
    if type(mission['CompleteConditionParameterName']) is list and len(mission['CompleteConditionParameterName'])==1: mission['CompleteConditionParameterName'] = mission['CompleteConditionParameterName'][0] 

    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', item_types[mission['CompleteConditionParameterName']]).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', item_types[mission['CompleteConditionParameterName']]).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_ClearBattleWithTagCount(mission):
    global enemy_tags

    desc_jp = '-'
    desc_en = 'Clear any stage with a student from $1 $2 time(s)'

    tag = mission['CompleteConditionParameterName'] in enemy_tags and enemy_tags[mission['CompleteConditionParameterName']] or mission['CompleteConditionParameterName']
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_KillEnemyWithTagCount(mission):
    global enemy_tags

    desc_jp = '-'
    desc_en = 'Defeat any enemy from $1 $2 time(s)'

    if type(mission['CompleteConditionParameterName']) is list:
        for index, etag in enumerate(mission['CompleteConditionParameterName']):
            mission['CompleteConditionParameterName'][index] = etag in enemy_tags and enemy_tags[etag] or etag
        tag = " or ".join(mission['CompleteConditionParameterName'])
    else:
        tag = mission['CompleteConditionParameterName'] in enemy_tags and enemy_tags[mission['CompleteConditionParameterName']] or mission['CompleteConditionParameterName']

    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1', tag).replace('$2',str(mission['CompleteConditionCount']))) 

    mission['AutoLocalized'] = True
    return True


def localize_ConquerSpecificStepTileAll(mission):
    desc_jp = 'エリア$1をすべて占領'
    desc_en = 'Occupy all of area $1'
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('$1',str(mission['CompleteConditionParameter'][2]+1))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('$1',str(mission['CompleteConditionParameter'][2]+1))) 

    mission['AutoLocalized'] = True
    return True


def localize_UpgradeConquestBaseTileCount(mission):
    desc_jp = 'Lv.{0}拠点を{1}個保有する'
    desc_en = 'Own {1} Lv. {0} base(s)'
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('{1}',str(mission['CompleteConditionCount'])).replace('{0}',str(mission['CompleteConditionParameter'][2]))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('{1}',str(mission['CompleteConditionCount'])).replace('{0}',str(mission['CompleteConditionParameter'][2]))) 

    mission['AutoLocalized'] = True
    return True


def localize_KillConquestBoss(mission):
    desc_jp = 'エリア{0}のボスを倒す'
    desc_en = 'Defeat the area {0} boss'
    
    mission['DescriptionJp'] = description_cleanup(desc_jp.replace('{0}',str(mission['CompleteConditionParameter'][2]+1))) 
    mission['DescriptionEn'] = description_cleanup(desc_en.replace('{0}',str(mission['CompleteConditionParameter'][2]+1))) 

    mission['AutoLocalized'] = True
    return True


def localize_ClearEventConquestTileTimeLimitFromSecond(mission):
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
    boss_names = {10814000: 'Wakamo (Swimsuit)', 10814100: 'Wakamo (Hovercraft)'}

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
    boss_names = {301200: 'Wakamo (Swimsuit)', 302200: 'Wakamo (Hovercraft)'}

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
    
    text = text in item_types and item_types[text] or text
    if re.search(r"^Token_S\d+$", text, re.MULTILINE): text = 'Event Tokens'

    return text
