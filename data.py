import collections
import json
import os

BlueArchiveData = collections.namedtuple(
    'BlueArchiveData',
    ['characters', 'characters_ai', 'characters_localization', 'characters_skills', 'characters_stats', 'characters_cafe_tags', 
    'skills', 'skills_localization','translated_characters','translated_skills',
    'weapons', 'translated_weapons', 'gear',
    'currencies','translated_currencies',
    'items', #'translated_items',
    'equipment',
    'recipes', 'recipes_ingredients', 
    'favor_levels', 'favor_rewards', 
    'memory_lobby','etc_localization',
    'character_dialog','character_dialog_event','character_dialog_standard',
    'scenario_script_favor','levelskill','logiceffectdata',
    'guide_mission','guide_mission_season','localize_code', 'localization',
    'furniture', 'furniture_group',
    'campaign_stages', 'campaign_stage_rewards', 'campaign_strategy_objects', 'campaign_units', 
    'event_content_seasons', 'event_content_stages', 'event_content_stage_rewards', 'event_content_stage_total_rewards', 'event_content_mission', 'event_content_character_bonus', 'event_content_currency', 'event_content_shop_info', 'event_content_shop', 'event_content_location_reward', 'event_content_zone', 'event_content_box_gacha_manage', 'event_content_box_gacha_shop', 
    'ground', 
    'gacha_elements', 'gacha_elements_recursive', 'gacha_groups',
    'strategymaps','goods', 'stages']
)

# BlueArchiveTranslations = collections.namedtuple(
#     'BlueArchiveTranslations',
#     ['strategies']
# )


def load_data(path_primary, path_secondary, path_translation):
    return BlueArchiveData(
        characters=                 load_generic(path_primary, 'CharacterExcelTable.json'),
        characters_ai=              load_generic(path_primary, 'CharacterAIExcelTable.json'),
        characters_localization=    load_generic(path_primary, 'LocalizeCharProfileExcelTable.json', key='CharacterId'),
        characters_skills=          load_characters_skills(path_primary),
        characters_stats=           load_generic(path_primary, 'CharacterStatExcelTable.json', key='CharacterId'),
        characters_cafe_tags =      load_generic(path_primary, 'CharacterAcademyTagsExcelTable.json'),
        skills=                     load_generic(path_primary, 'SkillExcelTable.json'),
        skills_localization=        load_generic(path_primary, 'LocalizeSkillExcelTable.json', key='Key'),
        translated_characters =     load_characters_translation(path_translation),
        translated_skills =         load_skills_translation(path_translation),
        weapons =                   load_generic(path_primary, 'CharacterWeaponExcelTable.json', key='Id'),
        translated_weapons =        load_weapons_translation(path_translation),
        gear =                      load_gear(path_primary),
        currencies=                 load_generic(path_primary, 'CurrencyExcelTable.json', key='ID'),
        translated_currencies=      load_currencies_translation(path_translation),
        items=                      load_generic(path_primary, 'ItemExcelTable.json'),
        equipment=                  load_generic(path_primary, 'EquipmentExcelTable.json'),
        #translated_items=load_items_translation(path_translation),
        recipes=                    load_generic(path_primary, 'RecipeExcelTable.json'),
        recipes_ingredients=        load_generic(path_primary, 'RecipeIngredientExcelTable.json'),
        favor_levels=load_favor_levels(path_primary),
        favor_rewards=load_favor_rewards(path_primary),
        memory_lobby=               load_generic(path_primary, 'MemoryLobbyExcelTable.json', key='CharacterId'),
        etc_localization=load_etc_localization(path_primary, path_secondary, path_translation),
        character_dialog=load_character_dialog(path_primary, path_secondary, path_translation, 'CharacterDialogExcelTable.json'),
        character_dialog_event=load_character_dialog(path_primary, path_secondary, path_translation, 'CharacterDialogEventExcelTable.json'),
        character_dialog_standard=load_character_dialog_standard(path_translation),
        scenario_script_favor=load_scenario_script_favor(path_primary, path_secondary, path_translation),
        levelskill = load_levelskill(path_primary),
        logiceffectdata = load_skill_logiceffectdata(path_primary),
        guide_mission =             load_generic(path_primary, 'GuideMissionExcelTable.json'),
        guide_mission_season =      load_generic(path_primary, 'GuideMissionSeasonExcelTable.json'),
        localize_code = load_localize_code(path_primary, path_secondary, path_translation),
        localization=load_localization(path_primary, path_secondary, path_translation),
        furniture=                  load_generic(path_primary, 'FurnitureExcelTable.json'),
        furniture_group=            load_generic(path_primary, 'FurnitureGroupExcelTable.json'),
        campaign_stages=            load_generic(path_primary, 'CampaignStageExcelTable.json'),
        campaign_stage_rewards=     load_campaign_stage_rewards(path_primary),
        campaign_strategy_objects=  load_generic(path_primary, 'CampaignStrategyObjectExcelTable.json'),
        campaign_units=             load_generic(path_primary, 'CampaignUnitExcelTable.json'),
        event_content_seasons=      load_event_content_seasons(path_primary),
        event_content_stages=       load_generic(path_primary, 'EventContentStageExcelTable.json'),
        event_content_stage_rewards=load_event_content_stage_rewards(path_primary),
        event_content_stage_total_rewards = load_generic(path_primary, 'EventContentStageTotalRewardExcelTable.json'),
        event_content_mission=      load_generic(path_primary, 'EventContentMissionExcelTable.json'),
        event_content_character_bonus= load_event_content_character_bonus(path_primary),
        event_content_currency=     load_event_content_currency(path_primary),
        event_content_shop_info=    load_event_content_shop_info(path_primary),
        event_content_shop=         load_event_content_shop(path_primary),
        event_content_zone=         load_generic(path_primary, 'EventContentZoneExcelTable.json'),
        event_content_location_reward = load_generic(path_primary, 'EventContentLocationRewardExcelTable.json'),
        event_content_box_gacha_manage= load_event_content_box_gacha_manage(path_primary),
        event_content_box_gacha_shop= load_event_content_box_gacha_shop(path_primary),
        ground =                    load_generic(path_primary, 'GroundExcelTable.json'),
        gacha_elements=             load_gacha_elements(path_primary),
        gacha_elements_recursive=   load_gacha_elements_recursive(path_primary),
        gacha_groups=               load_generic(path_primary, 'GachaGroupExcelTable.json', key='ID'),
        strategymaps=               load_strategymaps(path_primary),
        goods=                      load_generic(path_primary, 'GoodsExcelTable.json'),
        stages=                     load_stages(path_primary),
    )



def load_generic(path, filename, key='Id'):
    return load_file(os.path.join(path, 'Excel', filename), key)


def load_file(file, key='Id'):
    with open(file,encoding="utf8") as f:
        data = json.load(f)

    return {item[key]: item for item in data['DataList']}


def load_file_grouped(file, key="Id"):
    with open(file,encoding="utf8") as f:
        data = json.load(f)
    groups = collections.defaultdict(list)
    for item in data['DataList']:
        groups[item[key]].append(item)

    return dict(groups)


def load_characters_skills(path):
    with open(os.path.join(path, 'Excel', 'CharacterSkillListExcelTable.json'),encoding="utf8") as f:
        data = json.load(f)

    return {
        (character_skill['CharacterId'], character_skill['MinimumGradeCharacterWeapon'], character_skill["MinimumTierCharacterGear"], character_skill['IsFormConversion']): character_skill
        for character_skill
        in data['DataList']
    }

def load_characters_translation(path):
    return load_file(os.path.join(path, 'CharProfile.json'), key='CharacterId')


def load_weapons_translation(path):
    return load_file(os.path.join(path, 'Weapons.json'), key='Id')

def load_gear(path):
    with open(os.path.join(path, 'Excel', 'CharacterGearExcelTable.json'),encoding="utf8") as f:
        data = json.load(f)
        f.close()

    return {
        (gear['CharacterId'], gear['Tier']): gear
        for gear
        in data['DataList']
    }

def load_favor_levels(path):
    with open(os.path.join(path, 'Excel', 'FavorLevelRewardExcelTable.json'),encoding="utf8") as f:
        data = json.load(f)
        f.close()

    return {
        (favor_level['CharacterId'], favor_level['FavorLevel']): favor_level
        for favor_level
        in data['DataList']
    }

def load_favor_rewards(path):
    with open(os.path.join(path, 'Excel', 'AcademyFavorScheduleExcelTable.json'),encoding="utf8") as f:
        data = json.load(f)
        f.close()

    return {
        (favor_rewards['CharacterId'], favor_rewards['FavorRank']): favor_rewards
        for favor_rewards
        in data['DataList']
    }
  

def load_currencies_translation(path):
    return load_file(os.path.join(path, 'Currencies.json'))

# def load_items_translation(path):
#     return load_file(os.path.join(path, 'Items.json'))

def load_skills_translation(path):
    return load_file(os.path.join(path, 'Skills.json'), key='GroupId')


def load_etc_localization(path_primary, path_secondary, translation):
    data_primary = load_file(os.path.join(path_primary, 'Excel', 'LocalizeEtcExcelTable.json'), key='Key')
    data_secondary = load_file(os.path.join(path_secondary, 'Excel', 'LocalizeEtcExcelTable.json'), key='Key')
    data_aux = None

    index_list = list(data_primary.keys())
    index_list.extend(x for x in list(data_secondary.keys()) if x not in index_list)

    if os.path.exists(os.path.join(translation, 'LocalizeEtcExcelTable.json')):
        print(f'Loading additional translations from {translation}/LocalizeEtcExcelTable.json')
        data_aux = load_file(os.path.join(translation, 'LocalizeEtcExcelTable.json'))

        index_list.extend(x for x in list(data_aux.keys()) if x not in index_list)

    for index in index_list:
        try: 
            if data_aux != None and index in data_aux:
                #print(f'Loading aux translation {index}')
                data_primary[index] = data_aux[index] 
            else :
                #print(f'Loading secondary data translation {index}')
                data_primary[index] = data_secondary[index] 
        except KeyError:
            #print (f'No secondary data for localize item {index}')
            continue
    
    return data_primary


def load_localize_code(path_primary, path_secondary, translation):
    data_primary = load_file(os.path.join(path_primary, 'Excel', 'LocalizeCodeExcelTable.json'), key='Key')
    data_secondary = load_file(os.path.join(path_secondary, 'Excel', 'LocalizeCodeExcelTable.json'), key='Key')
    data_aux = None

    index_list = list(data_primary.keys())
    index_list.extend(x for x in list(data_secondary.keys()) if x not in index_list)

    if os.path.exists(os.path.join(translation, 'LocalizeCodeExcelTable.json')):
        print(f'Loading additional translations from {translation}/LocalizeCodeExcelTable.json')
        data_aux = load_file(os.path.join(translation, 'LocalizeCodeExcelTable.json'))

        index_list.extend(x for x in list(data_aux.keys()) if x not in index_list)

    for index in index_list:
        try: 
            if data_aux != None and index in data_aux:
                #print(f'Loading aux translation {index}')
                data_primary[index] = data_aux[index] 
            else :
                #print(f'Loading secondary data translation {index}')
                data_primary[index] = data_secondary[index] 
        except KeyError:
            #print (f'No secondary data for localize item {index}')
            continue
    
    return data_primary



def load_character_dialog(path_primary, path_secondary, path_translation,  filename):
    #dp = {}
    ds = {}
    da = {}
    data = []
    data_aux = []

    with open(os.path.join(path_primary, 'Excel', filename), encoding="utf8") as f:
        data_primary = json.load(f)['DataList']

    with open(os.path.join(path_secondary, 'Excel', filename), encoding="utf8") as f:
        data_secondary = json.load(f)['DataList']

    for file in os.listdir(path_translation + '/audio/'):
        if not file.endswith('.json') or file.startswith('standard_'):
            continue

        #print(f'Loading additional audio translations from {path_translation}/audio/{file}')
        with open(os.path.join(path_translation + '/audio/', file), encoding="utf8") as f:
            data_aux += json.load(f)['DataList']
    

    for line in data_secondary:
        ds[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'].replace('\n\r','\n').replace('\r',''))] = line 

    for line in data_aux:
        da[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'].replace('\n\r','\n').replace('\r',''))] = line 

    for line in data_primary:
        try: 
            line['LocalizeJP'] = line['LocalizeJP'].replace('\n\r','\n').replace('\r','')

            if (line['CharacterId'], line['DialogCategory'], line['LocalizeJP']) in da: line['LocalizeEN'] = da[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'])]['LocalizeEN'].replace('\n\r','\n')
            elif (line['CharacterId'], line['DialogCategory'], line['LocalizeJP']) in ds: line['LocalizeEN'] = ds[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'])]['LocalizeEN'].replace('\n\r','\n')
            elif 'LocalizeEN' not in line: line['LocalizeEN'] = ''

        except KeyError:
            #print (f"Localization not found {dp[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'])]}")
            line['LocalizeEN'] = ''
            pass

        data.append(line)

    return data


def load_character_dialog_standard(path_translation):
    data = {}
    data_aux = []

    for file in os.listdir(path_translation + '/audio/'):
        if not file.endswith('.json') or not file.startswith('standard_'):
            continue

        #print(f'Loading additional audio translations from {path_translation}/audio/{file}')
        with open(os.path.join(path_translation + '/audio/', file), encoding="utf8") as f:
            data_aux += json.load(f)['DataList']

    for line in data_aux:
        data[line['VoiceClip']] = line 

    return data


def load_levelskill(path):
    data = {}
    for file in os.listdir(path + '/LevelSkill/'):
        if not file.endswith('.json'):
            continue

        with open(os.path.join(path + '/LevelSkill/', file), encoding="utf8") as f:
            skill_info = json.load(f)
            data[skill_info[0]['GroupName']] = skill_info[0]

    return data


def load_skill_logiceffectdata(path):
    with open(os.path.join(path, 'Battle', 'logiceffectdata.json'), encoding="utf8") as f:
        data = json.load(f)

    return {item['StringId']: item for item in data}


def load_localization(path_primary, path_secondary, translation):
    data_primary = load_file(os.path.join(path_primary, 'Excel', 'LocalizeEtcExcelTable.json'), key='Key')
    data_secondary = load_file(os.path.join(path_secondary, 'Excel', 'LocalizeEtcExcelTable.json'), key='Key')
    data_aux = None

    index_list = list(data_primary.keys())
    index_list.extend(x for x in list(data_secondary.keys()) if x not in index_list)


    if os.path.exists(os.path.join(translation, 'LocalizeEtcExcelTable.json')):
        #print(f'Loading additional translations from {translation}/LocalizeEtcExcelTable.json')
        data_aux = load_file(os.path.join(translation, 'LocalizeEtcExcelTable.json'))

        index_list.extend(x for x in list(data_aux.keys()) if x not in index_list)

    for index in index_list:
        try: 
            if data_aux != None and index in data_aux:
                data_primary[index] = data_aux[index] 
                #print(f'Loaded aux translation {index}')
            else :
                data_primary[index] = data_secondary[index] 
                #print(f'Loaded aux translation {index}')
            #print (f'FOUND secondary data for localize item {index}')
        except KeyError:
            #print (f'No secondary data for localize item {index}')
            continue
    
    return data_primary



def load_campaign_stage_rewards(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'CampaignStageRewardExcelTable.json'), 'GroupId')


def load_event_content_seasons(path):
    with open(os.path.join(path, 'Excel', 'EventContentSeasonExcelTable.json'),encoding="utf8") as f:
        data = json.load(f)
        f.close()

    return {
        (season['EventContentId'], season['EventContentType']): season
        for season
        in data['DataList']
    }
  

def load_event_content_stage_rewards(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'EventContentStageRewardExcelTable.json'), 'GroupId')

def load_strategies_translations(path):
    return load_file(os.path.join(path, 'Strategies.json'), key='Name')

def load_gacha_elements(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'GachaElementExcelTable.json'), 'GachaGroupID')

def load_gacha_elements_recursive(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'GachaElementRecursiveExcelTable.json'), 'GachaGroupID')


def load_strategymaps(path_primary):
    data = {}
    
    for file in os.listdir(path_primary + '/HexaMap/'):
        if not file.endswith('.json') or not file.startswith('strategymap_'):
            continue
        
        with open(os.path.join(path_primary, 'HexaMap', file), encoding="utf8") as f:
            data[file[12:file.index('.')]] = json.load(f)

    return data


def load_stages(path_primary):
    data = {}
    
    for file in os.listdir(path_primary + '/Stage/'):
        if not file.endswith('.json'):
            continue
        
        with open(os.path.join(path_primary, 'Stage', file), encoding="utf8") as f:
            data[file[:file.index('.')]] = json.load(f)

    return data


    
def load_event_content_character_bonus(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'EventContentCharacterBonusExcelTable.json'), 'EventContentId')

def load_event_content_currency(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'EventContentCurrencyItemExcelTable.json'), 'EventContentId')

def load_event_content_shop_info(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'EventContentShopInfoExcelTable.json'), 'EventContentId')

def load_event_content_shop(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'EventContentShopExcelTable.json'), 'EventContentId')

def load_event_content_box_gacha_manage(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'EventContentBoxGachaManageExcelTable.json'), 'EventContentId')

def load_event_content_box_gacha_shop(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'EventContentBoxGachaShopExcelTable.json'), 'EventContentId')





BlueArchiveScenarioData = collections.namedtuple(
    'BlueArchiveScenarioData',
    ['scenario_script_favor']
)


def load_scenario_data(path_primary, path_secondary, path_translation):
    return BlueArchiveScenarioData(
        scenario_script_favor=load_scenario_script_favor(path_primary, path_secondary, path_translation)
    )


def load_scenario_script_favor(path_primary, path_secondary, path_translation):
    data = []
    #data['DataList'] = []

    for i in range(1,3): data += load_scenario_script_favor_part(path_primary, path_secondary, path_translation, i)

    return data


def load_scenario_script_favor_part(path_primary, path_secondary, path_translation, part):
    ds = {}
    da = {}
    data = []
    data_aux = []

    with open(os.path.join(path_primary, 'Excel', f'ScenarioScriptFavor{part}ExcelTable.json'), encoding="utf8") as f:
        data_primary = json.load(f)['DataList']
        #print(f'Loaded primary script data from ScenarioScriptFavor{part}ExcelTable.json, {len(data_primary)} entries')

    with open(os.path.join(path_secondary, 'Excel', f'ScenarioScriptFavor{part}ExcelTable.json'), encoding="utf8") as f:
        data_secondary = json.load(f)['DataList']
        #print(f'Loaded secondary script data from ScenarioScriptFavor{part}ExcelTable.json, {len(data_primary)} entries')

    for file in os.listdir(path_translation + '/scenario/'):
        if not file.endswith('.json'):
            continue

        #print(f'Loading additional scenario translations from {path_translation}/scenario/{file}')
        with open(os.path.join(path_translation + '/scenario/', file), encoding="utf8") as f:
            data_aux += json.load(f)['DataList']

    for line in data_secondary:
        ds[(line['GroupId'], line['ScriptKr'], line['TextJp'])] = line 

    for line in data_aux:
        da[(line['GroupId'], line['ScriptKr'], line['TextJp'])] = line 

    for line in data_primary:
        try: 
            
            if (line['GroupId'], line['ScriptKr'], line['TextJp']) in da: line['TextEn'] = da[(line['GroupId'], line['ScriptKr'], line['TextJp'])]['TextEn']
            elif (line['GroupId'], line['ScriptKr'], line['TextJp']) in ds: line['TextEn'] = ds[(line['GroupId'], line['ScriptKr'], line['TextJp'])]['TextEn']
            elif 'TextEn' not in line: line['TextEn'] = ''

        except KeyError:
            #print (f"Localization not found {dp[(line['GroupId'], line['ScriptKr'], line['TextJp'])]}")
            line['TextEn'] = ''
            pass

        data.append(line)

    return data

