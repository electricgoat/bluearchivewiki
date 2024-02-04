import collections
import json
import os
import re

BlueArchiveData = collections.namedtuple(
    'BlueArchiveData',
    ['characters', 'characters_ai', 'characters_localization', 'characters_skills', 'characters_stats', 'characters_cafe_tags', 
     'costumes',
    'skills', 'skills_localization','skill_additional_tooltip','translated_characters','translated_skills',
    'weapons', 'gear',
    'currencies','translated_currencies',
    'items', #'translated_items',
    'equipment',
    'recipes', 'recipes_ingredients', 
    'favor_levels', 'favor_rewards', 
    'memory_lobby','etc_localization', 'localization', 
    'character_dialog','character_dialog_event','character_dialog_standard',
    'scenario_script_favor','levelskill','logiceffectdata',
    'guide_mission','guide_mission_season','localize_code',
    'furniture', 'furniture_group', 'cafe_interaction', 
    'campaign_stages', 'campaign_stage_rewards', 'campaign_strategy_objects', 'campaign_units', 
    'event_content_seasons', 'event_content_stages', 'event_content_stage_rewards', 'event_content_stage_total_rewards', 'event_content_mission', 'event_content_character_bonus', 'event_content_currency', 'event_content_shop_info', 'event_content_shop', 'event_content_location_reward', 'event_content_zone', 'event_content_box_gacha_manage', 'event_content_box_gacha_shop', 'event_content_fortune_gacha_shop', 'event_content_card', 'event_content_card_shop', 
    'ground', 
    'gacha_elements', 'gacha_elements_recursive', 'gacha_groups',
    'strategymaps','goods', 'stages',
    'raid_stage', 'raid_stage_reward', 'raid_stage_season_reward', 'raid_ranking_reward',
    'world_raid_stage','world_raid_stage_reward', 'world_raid_boss_group', 
    'eliminate_raid_stage', 'eliminate_raid_stage_reward', 'eliminate_raid_stage_season_reward', 'eliminate_raid_ranking_reward',
    'bgm','voice','voice_spine',
    'operator',
    'field_season', 'field_world_map_zone', 'field_quest', 'field_reward', 'field_evidence', 'field_keyword', 'field_date', 'field_interaction', 'field_content_stage', 'field_content_stage_reward',
    'emblem'
    ]
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
        costumes=                   load_generic(path_primary, 'CostumeExcelTable.json', key='CostumeGroupId'),
        skills=                     load_generic(path_primary, 'SkillExcelTable.json'),
        #skills_localization=        load_combined_localization(path_primary, path_secondary, path_translation, 'LocalizeSkillExcelTable.json'),
        skills_localization=        load_generic(path_primary, 'LocalizeSkillExcelTable.json', key='Key'),
        skill_additional_tooltip =  load_file_grouped(os.path.join(path_primary, 'DB', 'SkillAdditionalTooltipExcelTable.json'), key='GroupId'),
        translated_characters =     load_characters_translation(path_translation),
        translated_skills =         load_skills_translation(path_translation),
        weapons =                   load_generic(path_primary, 'CharacterWeaponExcelTable.json', key='Id'),
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
        etc_localization=           load_combined_localization(path_primary, path_secondary, path_translation, 'LocalizeEtcExcelTable.json'),
        localization=               load_localization(path_primary, path_secondary, path_translation),
        character_dialog=           load_character_dialog(path_primary, path_secondary, path_translation, 'CharacterDialogExcelTable.json'),
        character_dialog_event=     load_character_dialog(path_primary, path_secondary, path_translation, 'CharacterDialogEventExcelTable.json', match_id='OriginalCharacterId', aux_prefix='event'),
        character_dialog_standard=  load_character_dialog_standard(path_translation),
        scenario_script_favor=load_scenario_script_favor(path_primary, path_secondary, path_translation),
        levelskill = load_levelskill(path_primary),
        logiceffectdata = load_skill_logiceffectdata(path_primary),
        guide_mission =             load_generic(path_primary, 'GuideMissionExcelTable.json'),
        guide_mission_season =      load_generic(path_primary, 'GuideMissionSeasonExcelTable.json'),
        localize_code =             load_combined_localization(path_primary, path_secondary, path_translation, 'LocalizeCodeExcelTable.json'),
        furniture=                  load_generic(path_primary, 'FurnitureExcelTable.json'),
        furniture_group=            load_generic(path_primary, 'FurnitureGroupExcelTable.json'),
        cafe_interaction=           load_generic(path_primary, 'CafeInteractionExcelTable.json', key='CharacterId'),
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
        event_content_fortune_gacha_shop= load_event_content_fortune_gacha_shop(path_primary),
        event_content_card=         load_generic(path_primary, 'EventContentCardExcelTable.json', key='CardGroupId'),
        event_content_card_shop=    load_event_content_card_shop(path_primary),
        ground =                    load_generic(path_primary, 'GroundExcelTable.json'),
        gacha_elements=             load_gacha_elements(path_primary),
        gacha_elements_recursive=   load_gacha_elements_recursive(path_primary),
        gacha_groups=               load_generic(path_primary, 'GachaGroupExcelTable.json', key='ID'),
        strategymaps=               load_strategymaps(path_primary),
        goods=                      load_generic(path_primary, 'GoodsExcelTable.json'),
        stages=                     load_stages(path_primary),
        raid_stage=                 load_file_grouped(os.path.join(path_primary, 'Excel', 'RaidStageExcelTable.json'), 'RaidBossGroup'),
        raid_stage_reward=          load_file_grouped(os.path.join(path_primary, 'Excel', 'RaidStageRewardExcelTable.json'), 'GroupId'),
        raid_stage_season_reward=   load_generic(path_primary, 'RaidStageSeasonRewardExcelTable.json', key='SeasonRewardId'),
        raid_ranking_reward=        load_file_grouped(os.path.join(path_primary, 'Excel', 'RaidRankingRewardExcelTable.json'), 'RankingRewardGroupId'),
        #world_raid_season=          load_generic(path_primary, 'WorldRaidSeasonManageExcelTable.json', key='SeasonId'),
        world_raid_stage=           load_file_grouped(os.path.join(path_primary, 'Excel', 'WorldRaidStageExcelTable.json'), 'WorldRaidBossGroupId'), #load_generic(path_primary, 'WorldRaidStageExcelTable.json'),
        world_raid_stage_reward=    load_world_raid_stage_reward(path_primary),
        world_raid_boss_group=      load_generic(path_primary, 'WorldRaidBossGroupExcelTable.json', key='WorldRaidBossGroupId'),
        eliminate_raid_stage=       load_file_grouped(os.path.join(path_primary, 'Excel', 'EliminateRaidStageExcelTable.json'), 'RaidBossGroup'),
        eliminate_raid_stage_reward=load_file_grouped(os.path.join(path_primary, 'Excel', 'EliminateRaidStageRewardExcelTable.json'), 'GroupId'),
        eliminate_raid_stage_season_reward=load_generic(path_primary, 'EliminateRaidStageSeasonRewardExcelTable.json', key='SeasonRewardId'),
        eliminate_raid_ranking_reward=load_file_grouped(os.path.join(path_primary, 'Excel', 'EliminateRaidRankingRewardExcelTable.json'), 'RankingRewardGroupId'),
        bgm=                        load_bgm(path_primary, path_translation),
        voice=                      load_generic(path_primary, 'VoiceExcelTable.json', key='Id'),
        voice_spine=                load_generic(path_primary, 'VoiceSpineExcelTable.json', key='Id'),
        operator=                   load_generic(path_primary, 'OperatorExcelTable.json', key='UniqueId'),
        
        field_season =              load_generic(path_primary, 'FieldSeasonExcelTable.json', key='UniqueId'),
        field_world_map_zone =      load_generic(path_primary, 'FieldWorldMapZoneExcelTable.json', key='Id'),
        field_quest =               load_file_grouped(os.path.join(path_primary, 'Excel', 'FieldQuestExcelTable.json'), 'FieldSeasonId'),
        field_reward =              load_file_grouped(os.path.join(path_primary, 'Excel', 'FieldRewardExcelTable.json'), 'GroupId'),
        field_evidence =            load_generic(path_primary, 'FieldEvidenceExcelTable.json', key='UniqueId'),
        field_keyword =             load_generic(path_primary, 'FieldKeywordExcelTable.json', key='UniqueId'),
        field_date =                load_generic(path_primary, 'FieldDateExcelTable.json', key='UniqueId'),
        field_interaction =         load_generic(path_primary, 'FieldInteractionExcelTable.json', key='UniqueId'),
        field_content_stage =       load_generic(path_primary, 'FieldContentStageExcelTable.json'),
        field_content_stage_reward= load_file_grouped(os.path.join(path_primary, 'Excel', 'FieldContentStageRewardExcelTable.json'), 'GroupId'),
        emblem=                     load_generic(path_primary, 'EmblemExcelTable.json', key='Id'),
    )



def load_generic(path, filename, key='Id'):
    return load_file(os.path.join(path, 'Excel', filename), key)


def load_generic_db(path, filename, key='Id'):
    return load_file(os.path.join(path, 'DB', filename), key)


def load_file(file, key='Id'):
    if os.path.exists(file): 
        with open(file,encoding="utf8") as f:
            data = json.load(f)
        return {item[key]: item for item in data['DataList']}
    else:
        print(f'WARNING - file {file} is not present')
        return {}


def load_json(path, filename):
    with open(os.path.join(path, 'Excel', filename),encoding="utf8") as f:
        data = json.load(f)

    return data['DataList']


def load_file_grouped(file, key="Id"):
    with open(file,encoding="utf8") as f:
        data = json.load(f)
    groups = collections.defaultdict(list)
    for item in data['DataList']:
        groups[item[key]].append(item)

    return dict(groups)



# Even old JP script keeps getting tweaked, so clean out some formatting changes for better matching
# aggresive option removes ALL line breaks to hopefully match more lines, non-aggressively cleaned line is then actually used
def line_cleanup(text, aggresive = False): 
    text = text.replace('\n\r','\n').replace('\r','').replace(' \n','\n').replace('\n ','\n').strip()
    if (aggresive): 
        text = text.replace('\n','').replace(' ','').strip()
        text = re.sub(r'\[.*?\]', '', text)
        if (text.endswith('。')): text = text[:-1]
    return text


def load_characters_skills(path):
    with open(os.path.join(path, 'Excel', 'CharacterSkillListExcelTable.json'),encoding="utf8") as f:
        data = json.load(f)

    return {
        (character_skill['CharacterSkillListGroupId'], character_skill['MinimumGradeCharacterWeapon'], character_skill["MinimumTierCharacterGear"], character_skill['FormIndex']): character_skill
        for character_skill
        in data['DataList']
    }


def load_characters_translation(path):
    return load_file(os.path.join(path, 'LocalizeCharProfile.json'), key='CharacterId')


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


def load_combined_localization(path_primary, path_secondary, path_translation, filename, key='Key'):
    data_primary = load_file(os.path.join(path_primary, 'Excel', filename), key)
    data_secondary = load_file(os.path.join(path_secondary, 'Excel', filename), key)
    data_aux = None

    index_list = list(data_primary.keys())
    index_list.extend(x for x in list(data_secondary.keys()) if x not in index_list)

    if os.path.exists(os.path.join(path_translation, filename)):
        print(f'Loading additional translations from {path_translation}/{filename}')
        data_aux = load_file(os.path.join(path_translation, filename), key)

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



def load_character_dialog(path_primary, path_secondary, path_translation, filename, match_id = 'CharacterId', aux_prefix = 'dialog'):
    dp = {}
    ds = {}
    da = {}
    data = []
    data_aux = []

    with open(os.path.join(path_primary, 'Excel', filename), encoding="utf8") as f:
        data_primary = json.load(f)['DataList']

    with open(os.path.join(path_secondary, 'Excel', filename), encoding="utf8") as f:
        data_secondary = json.load(f)['DataList']

    for file in os.listdir(path_translation + '/audio/'):
        if not file.endswith('.json') or not file.startswith(aux_prefix):
            continue

        #print(f'Loading additional audio translations from {path_translation}/audio/{file}')
        with open(os.path.join(path_translation + '/audio/', file), encoding="utf8") as f:
            data_aux += json.load(f)['DataList']
    

    for line in data_secondary:
        ds[(line[match_id], line['DialogCategory'], line_cleanup(line['LocalizeJP'], aggresive=True))] = line 

    for line in data_aux:
        da[(line[match_id], line['DialogCategory'], line_cleanup(line['LocalizeJP'], aggresive=True))] = line 

    for line in data_primary:
        dp[(line[match_id], line['DialogCategory'], line_cleanup(line['LocalizeJP'], aggresive=True))] = line 
        try: 
            line['LocalizeJP'] = line_cleanup(line['LocalizeJP'])

            if (line[match_id], line['DialogCategory'], line_cleanup(line['LocalizeJP'], aggresive=True)) in da: line['LocalizeEN'] = line_cleanup(da[(line[match_id], line['DialogCategory'], line_cleanup(line['LocalizeJP'], aggresive=True))]['LocalizeEN'])
            elif (line[match_id], line['DialogCategory'], line_cleanup(line['LocalizeJP'], aggresive=True)) in ds: line['LocalizeEN'] = line_cleanup(ds[(line[match_id], line['DialogCategory'], line_cleanup(line['LocalizeJP'], aggresive=True))]['LocalizeEN'])
            elif 'LocalizeEN' not in line: line['LocalizeEN'] = ''

        except KeyError:
            #print (f"Localization not found {dp[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'])]}")
            line['LocalizeEN'] = ''
            pass

        data.append(line)

    #Force aux lines into the list if they are missing there completely
    for key, line in da.items():
        if key not in dp: 
            line['LocalizeJP'] = line_cleanup(line['LocalizeJP'])
            line['LocalizeEN'] = line_cleanup(line['LocalizeEN'])
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

            if (type(skill_info) is list): data[skill_info[0]['GroupName']] = skill_info[0] #pre-1.35
            elif (type(skill_info) is dict): data[skill_info['SkillDataKey']] = skill_info
            else: print(f"ERROR - file {file} with unknown data of type {type(skill_info)}")

    return data


def load_skill_logiceffectdata(path):
    with open(os.path.join(path, 'Battle', 'logiceffectdata.json'), encoding="utf8") as f:
        data = json.load(f)

    return {item['StringId']: item for item in data}



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

def load_event_content_fortune_gacha_shop(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'EventContentFortuneGachaShopExcelTable.json'), 'EventContentId')

def load_event_content_card_shop(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'EventContentCardShopExcelTable.json'), 'EventContentId')

def load_world_raid_stage_reward(path):
    return load_file_grouped(os.path.join(path, 'Excel', 'WorldRaidStageRewardExcelTable.json'), 'GroupId')


def load_bgm(path_primary, path_translation):
    #data_primary = load_file(os.path.join(path_primary, 'Excel', 'BGMExcelTable.json'))
    data_primary = load_file(os.path.join(path_primary, 'DB', 'BGMExcelTable.json'))
    data_aux = None

    if os.path.exists(os.path.join(path_translation, 'BGM.json')):
        print(f'Loading additional translations from {path_translation}/BGM.json')
        data_aux = load_file(os.path.join(path_translation, 'BGM.json'))

        for id in data_aux.keys():
            if id in data_primary: data_primary[id] |= (data_aux[id])
            else: print(f'   ...track {id} is not listed in the BGMExcelTable.json')
    
    return data_primary


# This merges multiple files from secondary path since they were all moved to a single DB table
def load_localization(path_primary, path_secondary, path_translation):
    ds = {}
    da = {}
    data_secondary = []
    data_aux = []

    data_primary = load_file(os.path.join(path_primary, 'DB', 'LocalizeExcelTable.json'), key='Key')

    if os.path.exists(os.path.join(path_secondary, 'DB', 'LocalizeExcelTable.json')):
        data_secondary = load_file(os.path.join(path_secondary, 'DB', 'LocalizeExcelTable.json'), key='Key')
        #print(f'Loaded secondary script data from LocalizeExcelTable.json, {len(data_secondary)} entries')
    else:
        with open(os.path.join(path_secondary, 'Excel', 'LocalizeScenarioExcelTable.json'), encoding="utf8") as f: data_secondary += json.load(f)['DataList']
        with open(os.path.join(path_secondary, 'Excel', 'LocalizeCodeExcelTable.json'), encoding="utf8") as f: data_secondary += json.load(f)['DataList']
        with open(os.path.join(path_secondary, 'Excel', 'LocalizePrefabExcelTable.json'), encoding="utf8") as f: data_secondary += json.load(f)['DataList']
        with open(os.path.join(path_secondary, 'Excel', 'LocalizeOperatorExcelTable.json'), encoding="utf8") as f: data_secondary += json.load(f)['DataList']
        with open(os.path.join(path_secondary, 'Excel', 'LocalizeInformationExcelTable.json'), encoding="utf8") as f: data_secondary += json.load(f)['DataList']
        data_secondary = {item['Key']: item for item in data_secondary}

    
    if os.path.exists(os.path.join(path_translation, 'LocalizeExcelTable.json')):
        print(f'Loading additional translations from {path_translation}/LocalizeExcelTable.json')
        data_aux = load_file(os.path.join(path_translation, 'LocalizeExcelTable.json'), key='Key')

    found = 0
    for key, line in data_primary.items():
        if key in data_aux:
            line['En'] = data_aux[key]['En']
            #if line['Jp'] != data_aux[key]['Jp']: print(f"LocalizeExcelTable: Unmatched primary↔aux Jp line {key}: {line['Jp']} | {data_aux[key]['Jp']}" )
            found += 1
        elif key in data_secondary:
            line['En'] = data_secondary[key]['En']
            #if line['Jp'] != data_secondary[key]['Jp']: print(f"LocalizeExcelTable: Unmatched primary↔secondary Jp line {key}: {line['Jp']} | {data_secondary[key]['Jp']}" )
            found += 1

    print(f"LocalizeExcelTable: Found {found}/{len(data_primary)} translations")
    return data_primary


#TODO switch to using new DB scenario_script everywhere
BlueArchiveScenarioData = collections.namedtuple(
    'BlueArchiveScenarioData',
    ['scenario_script', 'scenario_script_favor']
)


def load_scenario_data(path_primary, path_secondary, path_translation):
    return BlueArchiveScenarioData(
        scenario_script=load_db_scenario_script(path_primary, path_secondary, path_translation),
        scenario_script_favor=load_scenario_script_favor(path_primary, path_secondary, path_translation) #Deprecated
    )


def load_db_scenario_script(path_primary, path_secondary, path_translation):
    ds = {}
    da = {}
    data = []
    data_aux = []

    with open(os.path.join(path_primary, 'DB', 'ScenarioScriptExcelTable.json'), encoding="utf8") as f:
        data_primary = json.load(f)['DataList']
        #print(f'Loaded primary script data from ScenarioScriptExcelTable.json, {len(data_primary)} entries')

    secondary_db_file = os.path.join(path_secondary, 'DB', 'ScenarioScriptExcelTable.json')
    if os.path.exists(secondary_db_file): 
        with open(secondary_db_file, encoding="utf8") as f:
            data_secondary = json.load(f)['DataList']
            #print(f'Loaded secondary script data from ScenarioScriptExcelTable.json, {len(data_primary)} entries')
    else: 
        data_secondary = load_multipart_file(path_secondary, 'ScenarioScriptFavor$ExcelTable.json', [1,2,3,4,5])
        
    for file in os.listdir(path_translation + '/scenario/'):
        if not file.endswith('.json'):
            continue
        #print(f'Loading additional scenario translations from {path_translation}/scenario/{file}')
        with open(os.path.join(path_translation + '/scenario/', file), encoding="utf8") as f:
            data_aux += json.load(f)['DataList']

    for line in data_secondary:
        ds[(line['GroupId'], line_cleanup(line['ScriptKr'], aggresive=True),  line_cleanup(line['TextJp'], aggresive=True))] = line 

    for line in data_aux:
        da[(line['GroupId'], line_cleanup(line['ScriptKr'], aggresive=True),  line_cleanup(line['TextJp'], aggresive=True))] = line 

    for line in data_primary:
        try: 
            line['ScriptKr'] = line_cleanup(line['ScriptKr'])
            line['TextJp'] = line_cleanup(line['TextJp'])
            if (line['GroupId'], line_cleanup(line['ScriptKr'], aggresive=True),  line_cleanup(line['TextJp'], aggresive=True)) in da:               
                line['TextEn'] = da[(line['GroupId'], line_cleanup(line['ScriptKr'], aggresive=True), line_cleanup(line['TextJp'], aggresive=True))]['TextEn']
            elif (line['GroupId'], line_cleanup(line['ScriptKr'], aggresive=True),  line_cleanup(line['TextJp'], aggresive=True)) in ds: 
                line['TextEn'] = ds[(line['GroupId'], line_cleanup(line['ScriptKr'], aggresive=True), line_cleanup(line['TextJp'], aggresive=True))]['TextEn']
            elif 'TextEn' not in line: line['TextEn'] = ''

        except KeyError:
            #print (f"Localization not found {dp[(line['GroupId'], line['ScriptKr'], line['TextJp'])]}")
            line['TextEn'] = ''
            pass

        data.append(line)

    return data


def load_multipart_file(path, filename, entries: list):
    data = []
    for i in entries: 
        with open(os.path.join(path, 'Excel', filename.replace('$', str(i))), encoding="utf8") as f: data += json.load(f)['DataList']
    return data
    


#Deprecated
def load_scenario_script_favor(path_primary, path_secondary, path_translation):
    data = []
    #data['DataList'] = []

    for i in range(1,3): data += load_scenario_script_favor_part(path_primary, path_secondary, path_translation, i)

    return data

#Deprecated
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
        ds[(line['GroupId'], line_cleanup(line['ScriptKr'], aggresive=True),  line_cleanup(line['TextJp'], aggresive=True))] = line 

    for line in data_aux:
        da[(line['GroupId'], line_cleanup(line['ScriptKr'], aggresive=True),  line_cleanup(line['TextJp'], aggresive=True))] = line 

    for line in data_primary:
        try: 
            line['ScriptKr'] = line_cleanup(line['ScriptKr'])
            line['TextJp'] = line_cleanup(line['TextJp'])
            if (line['GroupId'], line_cleanup(line['ScriptKr'], aggresive=True),  line_cleanup(line['TextJp'], aggresive=True)) in da: line['TextEn'] = da[(line['GroupId'], line['ScriptKr'], line['TextJp'])]['TextEn']
            elif (line['GroupId'], line_cleanup(line['ScriptKr'], aggresive=True),  line_cleanup(line['TextJp'], aggresive=True)) in ds: line['TextEn'] = ds[(line['GroupId'], line['ScriptKr'], line['TextJp'])]['TextEn']
            elif 'TextEn' not in line: line['TextEn'] = ''

        except KeyError:
            #print (f"Localization not found {dp[(line['GroupId'], line['ScriptKr'], line['TextJp'])]}")
            line['TextEn'] = ''
            pass

        data.append(line)

    return data



BlueArchiveSeasonData = collections.namedtuple(
    'BlueArchiveSeasonData',
    ['raid_season', 'world_raid_season', 'eliminate_raid_season', 'event_content_season', 'week_dungeon', 'week_dungeon_reward', 'week_dungeon_open_schedule']
)

def load_season_data(path):
    return BlueArchiveSeasonData(
        raid_season=            load_generic(path, 'RaidSeasonManageExcelTable.json', key='SeasonId'),
        world_raid_season=      load_generic(path, 'WorldRaidSeasonManageExcelTable.json', key='SeasonId'),
        eliminate_raid_season=  load_generic(path, 'EliminateRaidSeasonManageExcelTable.json', key='SeasonId'),
        event_content_season=   load_event_content_seasons(path),
        week_dungeon=           load_generic(path, 'WeekDungeonExcelTable.json', key='StageId'),
        week_dungeon_reward=    load_file_grouped(os.path.join(path, 'Excel', 'WeekDungeonRewardExcelTable.json'), 'GroupId'),
        week_dungeon_open_schedule= load_generic(path, 'WeekDungeonOpenScheduleExcelTable.json', key='WeekDay'),
    )
