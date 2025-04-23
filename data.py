import collections
import json
import orjson
import os
import re

BlueArchiveData = collections.namedtuple(
    'BlueArchiveData',
    ['characters', 'characters_ai', 'characters_localization', 'characters_skills', 'characters_stats', 'characters_cafe_tags', 
     'costumes',
    'skills', 'skills_localization','skill_additional_tooltip','translated_characters','translated_skills',
    'weapons', 'gear',
    'character_potential', 'character_potential_stat',
    'currencies','translated_currencies',
    'items',
    'equipment',
    'recipes', 'recipes_ingredients', 
    'favor_levels', 'favor_rewards', 
    'memory_lobby','etc_localization', 'localization', 
    'character_dialog','character_dialog_event','character_dialog_standard','character_dialog_subtitle','character_voice','character_voice_subtitle',
    'levelskill','logiceffectdata',
    'guide_mission','guide_mission_season','localize_code',
    'furniture', 'furniture_group', 'cafe_interaction', 
    'campaign_stages', 'campaign_stage_rewards', 'campaign_strategy_objects', 'campaign_units', 
    'week_dungeon', 'week_dungeon_reward', 'week_dungeon_open_schedule',
    'event_content_seasons', 'event_content_stages', 'event_content_stage_rewards', 'event_content_stage_total_rewards', 'event_content_mission', 'event_content_character_bonus', 'event_content_currency', 'event_content_shop_info', 'event_content_shop', 'event_content_location_reward', 'event_content_zone', 'event_content_box_gacha_manage', 'event_content_box_gacha_shop', 'event_content_fortune_gacha', 'event_content_fortune_gacha_modify', 'event_content_fortune_gacha_shop', 'event_content_card', 'event_content_card_shop', 'event_content_treasure', 'event_content_treasure_round', 'event_content_treasure_reward', 'event_content_treasure_cell_reward', 'event_content_collection',
    'minigame_mission',
    'minigame_dream_collection_scenario', 'minigame_dream_daily_point', 'minigame_dream_ending', 'minigame_dream_ending_reward', 'minigame_dream_info', 'minigame_dream_parameter', 'minigame_dream_replay_scenario', 'minigame_dream_schedule', 'minigame_dream_schedule_result', 'minigame_dream_timeline', 'minigame_dream_voice',
    'minigame_defense_info', 'minigame_defense_stage', 'minigame_defense_character_ban', 'minigame_defense_fixed_stat', 
    'ground', 
    'gacha_elements', 'gacha_elements_recursive', 'gacha_groups',
    'strategymaps','goods', 'stages',
    'raid_stage', 'raid_stage_reward', 'raid_stage_season_reward', 'raid_ranking_reward',
    'world_raid_stage','world_raid_stage_reward', 'world_raid_boss_group', 
    'eliminate_raid_stage', 'eliminate_raid_stage_reward', 'eliminate_raid_stage_season_reward', 'eliminate_raid_ranking_reward',
    'multi_floor_raid_stage', 'multi_floor_raid_reward', 'multi_floor_raid_stat_change',
    'time_attack_dungeon', 'time_attack_dungeon_geas', 'time_attack_dungeon_reward',
    'bgm','voice','voice_spine',
    'operator',
    'field_season', 'field_world_map_zone', 'field_quest', 'field_reward', 'field_evidence', 'field_keyword', 'field_date', 'field_interaction', 'field_content_stage', 'field_content_stage_reward',
    'emblem'
    ]
)


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
        skills_localization=        load_combined_localization(path_primary, path_secondary, path_translation, 'LocalizeSkillExcelTable.json'),
        skill_additional_tooltip =  load_file_grouped(path_primary, 'SkillAdditionalTooltipExcelTable.json', key='GroupId'),
        translated_characters =     load_file(os.path.join(path_translation, 'LocalizeCharProfile.json'), key='CharacterId', load_multipart=False),
        translated_skills =         load_file(os.path.join(path_translation, 'Skills.json'), key='GroupId', load_multipart=False),
        weapons =                   load_generic(path_primary, 'CharacterWeaponExcelTable.json', key='Id'),
        gear =                      load_gear(path_primary),
        character_potential=        load_file_grouped(path_primary, 'CharacterPotentialExcelTable.json', key='Id'),
        character_potential_stat=   load_file_grouped(path_primary, 'CharacterPotentialStatExcelTable.json', key='PotentialStatGroupId'),
        currencies=                 load_generic(path_primary, 'CurrencyExcelTable.json', key='ID'),
        translated_currencies=      load_file(os.path.join(path_translation, 'Currencies.json'), load_multipart=False),
        items=                      load_generic(path_primary, 'ItemExcelTable.json'),
        equipment=                  load_generic(path_primary, 'EquipmentExcelTable.json'),
        recipes=                    load_generic(path_primary, 'RecipeExcelTable.json'),
        recipes_ingredients=        load_generic(path_primary, 'RecipeIngredientExcelTable.json'),
        favor_levels=               load_favor_levels(path_primary),
        favor_rewards=              load_favor_rewards(path_primary),
        memory_lobby=               load_generic(path_primary, 'MemoryLobbyExcelTable.json', key='Id'),
        etc_localization=           load_combined_localization(path_primary, path_secondary, path_translation, 'LocalizeEtcExcelTable.json'),
        localization=               load_localization(path_primary, path_secondary, path_translation),
        character_dialog=           load_character_dialog(path_primary, path_secondary, path_translation, 'CharacterDialogExcelTable.json'),
        character_dialog_event=     load_character_dialog(path_primary, path_secondary, path_translation, 'CharacterDialogEventExcelTable.json', match_id='OriginalCharacterId', aux_prefix='event'),
        character_dialog_standard=  load_character_dialog_standard(path_translation),
        character_dialog_subtitle=  load_character_subtitle(path_primary, path_secondary, path_translation, 'CharacterDialogSubtitleExcelTable.json', match_id='CharacterId'),
        character_voice=            load_file_grouped(path_primary, 'CharacterVoiceExcelTable.json', key='CharacterVoiceGroupId'),
        character_voice_subtitle=   load_character_subtitle(path_primary, path_secondary, path_translation, 'CharacterVoiceSubtitleExcelTable.json', match_id='CharacterVoiceGroupId'),
        levelskill =                load_levelskill(path_primary),
        logiceffectdata =           load_skill_logiceffectdata(path_primary),
        guide_mission =             load_generic(path_primary, 'GuideMissionExcelTable.json'),
        guide_mission_season =      load_generic(path_primary, 'GuideMissionSeasonExcelTable.json'),
        localize_code =             load_combined_localization(path_primary, path_secondary, path_translation, 'LocalizeCodeExcelTable.json'),
        furniture=                  load_generic(path_primary, 'FurnitureExcelTable.json'),
        furniture_group=            load_generic(path_primary, 'FurnitureGroupExcelTable.json'),
        cafe_interaction=           load_generic(path_primary, 'CafeInteractionExcelTable.json', key='CharacterId'),
        campaign_stages=            load_generic(path_primary, 'CampaignStageExcelTable.json'),
        campaign_stage_rewards=     load_file_grouped(path_primary, 'CampaignStageRewardExcelTable.json', 'GroupId'),
        campaign_strategy_objects=  load_generic(path_primary, 'CampaignStrategyObjectExcelTable.json'),
        campaign_units=             load_generic(path_primary, 'CampaignUnitExcelTable.json'),
        week_dungeon=               load_generic(path_primary, 'WeekDungeonExcelTable.json', key='StageId'),
        week_dungeon_reward=        load_file_grouped(path_primary, 'WeekDungeonRewardExcelTable.json', key='GroupId'),
        week_dungeon_open_schedule= load_generic(path_primary, 'WeekDungeonOpenScheduleExcelTable.json', key='WeekDay'),
        event_content_seasons=      load_event_content_seasons(path_primary),
        event_content_stages=       load_generic(path_primary, 'EventContentStageExcelTable.json'),
        event_content_stage_rewards=load_file_grouped(path_primary, 'EventContentStageRewardExcelTable.json', 'GroupId'),
        event_content_stage_total_rewards= load_generic(path_primary, 'EventContentStageTotalRewardExcelTable.json'),
        event_content_mission=      load_generic(path_primary, 'EventContentMissionExcelTable.json'),
        event_content_character_bonus= load_file_grouped(path_primary, 'EventContentCharacterBonusExcelTable.json', 'EventContentId'),
        event_content_currency=     load_file_grouped(path_primary, 'EventContentCurrencyItemExcelTable.json', 'EventContentId'),
        event_content_shop_info=    load_file_grouped(path_primary, 'EventContentShopInfoExcelTable.json', 'EventContentId'),
        event_content_shop=         load_file_grouped(path_primary, 'EventContentShopExcelTable.json', 'EventContentId'),
        event_content_zone=         load_generic(path_primary, 'EventContentZoneExcelTable.json'),
        event_content_location_reward = load_generic(path_primary, 'EventContentLocationRewardExcelTable.json'),
        event_content_box_gacha_manage= load_file_grouped(path_primary, 'EventContentBoxGachaManageExcelTable.json', 'EventContentId'),
        event_content_box_gacha_shop= load_file_grouped(path_primary, 'EventContentBoxGachaShopExcelTable.json', 'EventContentId'),
        event_content_fortune_gacha=load_generic(path_primary, 'EventContentFortuneGachaExcelTable.json', key='FortuneGachaGroupId'),
        event_content_fortune_gacha_modify=load_file_grouped(path_primary, 'EventContentFortuneGachaModifyExcelTable.json', 'EventContentId'),
        event_content_fortune_gacha_shop= load_file_grouped(path_primary, 'EventContentFortuneGachaShopExcelTable.json', 'EventContentId'),
        event_content_card=         load_generic(path_primary, 'EventContentCardExcelTable.json', key='CardGroupId'),
        event_content_card_shop=    load_file_grouped(path_primary, 'EventContentCardShopExcelTable.json', 'EventContentId'),
        event_content_treasure=     load_generic(path_primary, 'EventContentTreasureExcelTable.json', key='EventContentId'),
        event_content_treasure_round= load_file_grouped(path_primary, 'EventContentTreasureRoundExcelTable.json', 'EventContentId'),
        event_content_treasure_reward= load_generic(path_primary, 'EventContentTreasureRewardExcelTable.json', key='Id'),
        event_content_treasure_cell_reward= load_generic(path_primary, 'EventContentTreasureCellRewardExcelTable.json', key='Id'),
        event_content_collection=   load_file_grouped(path_primary, 'EventContentCollectionExcelTable.json', 'EventContentId'),
        minigame_mission=           load_file_grouped(path_primary, 'MiniGameMissionExcelTable.json', 'EventContentId'),
        minigame_dream_collection_scenario= load_file_grouped(path_primary, 'MiniGameDreamCollectionScenarioExcelTable.json', 'EventContentId'),
        minigame_dream_daily_point= load_file_grouped(path_primary, 'MiniGameDreamDailyPointExcelTable.json', 'EventContentId'),
        minigame_dream_ending=      load_file_grouped(path_primary, 'MiniGameDreamEndingExcelTable.json', 'EventContentId'),
        minigame_dream_ending_reward= load_file_grouped(path_primary, 'MiniGameDreamEndingRewardExcelTable.json', 'EventContentId'),
        minigame_dream_info=        load_file_grouped(path_primary, 'MiniGameDreamInfoExcelTable.json', 'EventContentId'),
        minigame_dream_parameter=   load_file_grouped(path_primary, 'MiniGameDreamParameterExcelTable.json', 'EventContentId'),
        minigame_dream_replay_scenario= load_file_grouped(path_primary, 'MiniGameDreamReplayScenarioExcelTable.json', 'EventContentId'),
        minigame_dream_schedule=    load_file_grouped(path_primary, 'MiniGameDreamScheduleExcelTable.json', 'EventContentId'),
        minigame_dream_schedule_result= load_file_grouped(path_primary, 'MiniGameDreamScheduleResultExcelTable.json', 'EventContentId'),
        minigame_dream_timeline=    load_file_grouped(path_primary, 'MiniGameDreamTimelineExcelTable.json', 'EventContentId'),
        minigame_dream_voice=       load_file_grouped(path_primary, 'MinigameDreamVoiceExcelTable.json', 'EventContentId'),
        minigame_defense_info=      load_generic(path_primary, 'MiniGameDefenseInfoExcelTable.json', key='EventContentId'),
        minigame_defense_stage=     load_generic(path_primary, 'MiniGameDefenseStageExcelTable.json'),
        minigame_defense_character_ban= load_file_grouped(path_primary, 'MiniGameDefenseCharacterBanExcelTable.json', 'EventContentId'),
        minigame_defense_fixed_stat=load_generic(path_primary, 'MiniGameDefenseFixedStatExcelTable.json', key='MinigameDefenseFixedStatId'),
        ground =                    load_generic(path_primary, 'GroundExcelTable.json'),
        gacha_elements=             load_file_grouped(path_primary, 'GachaElementExcelTable.json', 'GachaGroupID'),
        gacha_elements_recursive=   load_file_grouped(path_primary, 'GachaElementRecursiveExcelTable.json', 'GachaGroupID'),
        gacha_groups=               load_generic(path_primary, 'GachaGroupExcelTable.json', key='ID'),
        strategymaps=               load_strategymaps(path_primary),
        goods=                      load_generic(path_primary, 'GoodsExcelTable.json'),
        stages=                     load_stages(path_primary),
        raid_stage=                 load_file_grouped(path_primary, 'RaidStageExcelTable.json', 'RaidBossGroup'),
        raid_stage_reward=          load_file_grouped(path_primary, 'RaidStageRewardExcelTable.json', 'GroupId'),
        raid_stage_season_reward=   load_generic(path_primary, 'RaidStageSeasonRewardExcelTable.json', key='SeasonRewardId'),
        raid_ranking_reward=        load_file_grouped(path_primary, 'RaidRankingRewardExcelTable.json', 'RankingRewardGroupId'),
        #world_raid_season=          load_generic(path_primary, 'WorldRaidSeasonManageExcelTable.json', key='SeasonId'),
        world_raid_stage=           load_file_grouped(path_primary, 'WorldRaidStageExcelTable.json', 'WorldRaidBossGroupId'),
        world_raid_stage_reward=    load_file_grouped(path_primary, 'WorldRaidStageRewardExcelTable.json', 'GroupId'),
        world_raid_boss_group=      load_generic(path_primary, 'WorldRaidBossGroupExcelTable.json', key='WorldRaidBossGroupId'),
        eliminate_raid_stage=       load_file_grouped(path_primary, 'EliminateRaidStageExcelTable.json', 'RaidBossGroup'),#moved out to season data, deprecated 
        eliminate_raid_stage_reward=load_file_grouped(path_primary, 'EliminateRaidStageRewardExcelTable.json', 'GroupId'),
        eliminate_raid_stage_season_reward=load_generic(path_primary, 'EliminateRaidStageSeasonRewardExcelTable.json', key='SeasonRewardId'),
        eliminate_raid_ranking_reward=load_file_grouped(path_primary, 'EliminateRaidRankingRewardExcelTable.json', 'RankingRewardGroupId'),
        multi_floor_raid_stage=     load_file_grouped(path_primary, 'MultiFloorRaidStageExcelTable.json', 'BossGroupId'),
        multi_floor_raid_reward=    load_file_grouped(path_primary, 'MultiFloorRaidRewardExcelTable.json', key='RewardGroupId'),
        multi_floor_raid_stat_change=load_generic(path_primary, 'MultiFloorRaidStatChangeExcelTable.json', key='StatChangeId'),
        bgm=                        load_bgm(path_primary, path_translation),
        time_attack_dungeon=        load_generic(path_primary, 'TimeAttackDungeonExcelTable.json', key='Id'),
        time_attack_dungeon_geas=   load_generic(path_primary, 'TimeAttackDungeonGeasExcelTable.json', key='Id'),
        time_attack_dungeon_reward= load_generic(path_primary, 'TimeAttackDungeonRewardExcelTable.json', key='Id'),
        voice=                      load_generic(path_primary, 'VoiceExcelTable.json', key='Id'),
        #voice_common=               load_generic(path_primary, 'VoiceCommonExcelTable.json', key='VoiceEvent'),
        #voice_logic_effect=         load_generic(path_primary, 'VoiceLogicEffectExcelTable.json', key='LogicEffectNameHash'),
        voice_spine=                load_generic(path_primary, 'VoiceSpineExcelTable.json', key='Id'),
        operator=                   load_generic(path_primary, 'OperatorExcelTable.json', key='UniqueId'),
        
        field_season =              load_generic(path_primary, 'FieldSeasonExcelTable.json', key='UniqueId'),
        field_world_map_zone =      load_generic(path_primary, 'FieldWorldMapZoneExcelTable.json', key='Id'),
        field_quest =               load_file_grouped(path_primary, 'FieldQuestExcelTable.json', 'FieldSeasonId'),
        field_reward =              load_file_grouped(path_primary, 'FieldRewardExcelTable.json', 'GroupId'),
        field_evidence =            load_generic(path_primary, 'FieldEvidenceExcelTable.json', key='UniqueId'),
        field_keyword =             load_generic(path_primary, 'FieldKeywordExcelTable.json', key='UniqueId'),
        field_date =                load_generic(path_primary, 'FieldDateExcelTable.json', key='UniqueId'),
        field_interaction =         load_generic(path_primary, 'FieldInteractionExcelTable.json', key='UniqueId'),
        field_content_stage =       load_generic(path_primary, 'FieldContentStageExcelTable.json'),
        field_content_stage_reward= load_file_grouped(path_primary, 'FieldContentStageRewardExcelTable.json', 'GroupId'),
        emblem=                     load_generic(path_primary, 'EmblemExcelTable.json', key='Id'),
    )


def load_generic(path, filename:str, key:str|None='Id', load_db:bool=True, load_multipart:bool=False):
    #DB files take priority if they are present
    file_path = os.path.join(path, 'DB', filename)
    if not load_db or not os.path.exists(file_path): file_path = os.path.join(path, 'Excel', filename)

    return load_file(file_path, key, load_multipart)


def load_file(file, key:str|None='Id', load_multipart:bool=False):
    multipart_file = file.rsplit('.',1)[0]+ '$.' + file.rsplit('.',1)[1]

    if load_multipart and os.path.exists(multipart_file.replace('$', str(1))):
        #print(f"Found multipart version of {file}")
        data = []
        i = 1
        while os.path.exists(multipart_file.replace('$', str(i))):
            with open(multipart_file.replace('$', str(i)), encoding="utf8") as f: data += orjson.loads(f.read())['DataList']
            i += 1
        if key is not None: return {item[key]: item for item in data}
        else: return data
        
    elif os.path.exists(file): 
        with open(file, encoding="utf8") as f:
            data = orjson.loads(f.read())
        if key is not None: return {item[key]: item for item in data['DataList']}
        else: return data['DataList']
    
    else:
        print(f'WARNING - file {file} is not present')
        return {}


def load_json(path, filename):
    with open(os.path.join(path, 'Excel', filename),encoding="utf8") as f:
        data = orjson.loads(f.read())

    return data['DataList']


def load_file_grouped(path, filename, key='Id'):
    #DB files take priority if they are present
    file_path = os.path.join(path, 'DB', filename)
    if not os.path.exists(file_path): file_path = os.path.join(path, 'Excel', filename)
    with open(file_path, encoding="utf8") as f:
        data = orjson.loads(f.read())
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
    data = load_generic(path, 'CharacterSkillListExcelTable.json', key=None, load_db=True)

    return {
        (character_skill['CharacterSkillListGroupId'], character_skill['MinimumGradeCharacterWeapon'], character_skill["MinimumTierCharacterGear"], character_skill['FormIndex']): character_skill
        for character_skill
        in data
    }


def load_gear(path):
    data = load_generic(path, 'CharacterGearExcelTable.json', key=None, load_db=True)

    return {
        (gear['CharacterId'], gear['Tier']): gear
        for gear
        in data
    }

def load_favor_levels(path):
    data = load_generic(path, 'FavorLevelRewardExcelTable.json', key=None, load_db=True)

    return {
        (favor_level['CharacterId'], favor_level['FavorLevel']): favor_level
        for favor_level
        in data
    }

def load_favor_rewards(path):
    data = load_generic(path, 'AcademyFavorScheduleExcelTable.json', key=None, load_db=True)

    return {
        (favor_rewards['CharacterId'], favor_rewards['FavorRank']): favor_rewards
        for favor_rewards
        in data
    }
  

def load_combined_localization(path_primary, path_secondary, path_translation, filename, key='Key'):

    data_primary = load_generic(path_primary, filename, key, load_db=True, load_multipart=True)
    data_secondary = load_generic(path_secondary, filename, key, load_db=True, load_multipart=True)
    data_aux = load_file(os.path.join(path_translation, filename), key, load_multipart=False)

    combined_keys = set(data_primary.keys()).union(data_secondary.keys())
    if data_aux:
        combined_keys = combined_keys.union(data_aux.keys())
        #print(f'Loading additional translations from {os.path.join(path_translation, filename)}')

    for index in combined_keys:
        if data_aux and index in data_aux:
            data_primary[index] = data_aux[index]
        elif index in data_secondary:
            data_primary[index] = data_secondary[index]

    return data_primary



def load_character_dialog(path_primary, path_secondary, path_translation, filename, match_id = 'CharacterId', aux_prefix = 'dialog')->list:
    dp = {}
    ds = {}
    da = {}
    data = []
    data_aux = []

    data_primary = load_generic(path_primary, filename, key=None)
    data_secondary = load_generic(path_secondary, filename, key=None)

    for file in os.listdir(path_translation + '/audio/'):
        if not file.endswith('.json') or not file.startswith(aux_prefix):
            continue

        #print(f'Loading additional audio translations from {path_translation}/audio/{file}')
        data_aux += load_file(os.path.join(path_translation + '/audio/', file), key=None)
    

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


def load_character_subtitle(path_primary, path_secondary, path_translation, filename, match_id = 'CharacterId', aux_prefix = 'standard'):
    dp = {}
    ds = {}
    da = {}
    data = []
    data_aux = []

    data_primary = load_generic(path_primary, filename, key=None)
    data_secondary = load_generic(path_secondary, filename, key=None)

    for file in os.listdir(path_translation + '/audio/'):
        if not file.endswith('.json') or not file.startswith(aux_prefix):
            continue

        #print(f'Loading additional audio translations from {path_translation}/audio/{file}')
        data_aux += load_file(os.path.join(path_translation + '/audio/', file), key=None)
    data_aux = [x for x in data_aux if 'LocalizeCVGroup' in x and x['LocalizeCVGroup'] is not None] #ignore legacy non-subtitle entries

    for line in data_secondary:
        ds[(line[match_id], line['LocalizeCVGroup'])] = line 

    for line in data_aux:
        da[(line[match_id], line['LocalizeCVGroup'])] = line 

    for line in data_primary:
        dp[(line[match_id], line['LocalizeCVGroup'])] = line 
        try: 
            line['LocalizeJP'] = line_cleanup(line['LocalizeJP'])

            if (line[match_id], line['LocalizeCVGroup']) in da: line['LocalizeEN'] = line_cleanup(da[(line[match_id], line['DialogCategory'])]['LocalizeEN'])
            elif (line[match_id], line['LocalizeCVGroup']) in ds: line['LocalizeEN'] = line_cleanup(ds[(line[match_id], line['DialogCategory'])]['LocalizeEN'])
            elif 'LocalizeEN' not in line: line['LocalizeEN'] = ''

        except KeyError:
            #print (f"Localization not found {dp[(line[match_id], line['LocalizeCVGroup'], line['LocalizeJP'])]}")
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
            data_aux += orjson.loads(f.read())['DataList']

    for line in data_aux:
        data[line['VoiceClip']] = line 

    return data


def load_levelskill(path):
    data = {}
    for file in os.listdir(path + '/LevelSkill/'):
        if not file.endswith('.json'):
            continue

        with open(os.path.join(path + '/LevelSkill/', file), encoding="utf8") as f:
            skill_info = orjson.loads(f.read())

            if (type(skill_info) is list): data[skill_info[0]['GroupName']] = skill_info[0] #pre-1.35
            elif (type(skill_info) is dict): data[skill_info['SkillDataKey']] = skill_info
            else: print(f"ERROR - file {file} with unknown data of type {type(skill_info)}")

    return data


def load_skill_logiceffectdata(path):
    with open(os.path.join(path, 'DB', 'LogicEffectData.json'), encoding="utf8") as f:
        data = orjson.loads(f.read())

    return {item['StringId']: convert_boolean_strings(item) for item in data}

def convert_boolean_strings(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = convert_boolean_strings(value)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = convert_boolean_strings(obj[i])
    elif isinstance(obj, str):
        if obj.lower() == "true":
            return True
        elif obj.lower() == "false":
            return False
    return obj


def load_event_content_seasons(path):
    with open(os.path.join(path, 'Excel', 'EventContentSeasonExcelTable.json'),encoding="utf8") as f:
        data = orjson.loads(f.read())
        f.close()

    return {
        (season['EventContentId'], season['EventContentType']): season
        for season
        in data['DataList']
    }
  

def load_strategymaps(path_primary):
    data = {}
    
    for file in os.listdir(path_primary + '/HexaMap/'):
        if not file.endswith('.json') or not file.startswith('strategymap_'):
            continue
        
        with open(os.path.join(path_primary, 'HexaMap', file), encoding="utf8") as f:
            data[file[12:file.index('.')]] = orjson.loads(f.read())

    return data


def load_stages(path_primary):
    data = {}
    stage_path = os.path.join(path_primary, 'Stage')

    for file in os.listdir(stage_path):
        if not file.endswith('.json') or "newleveltest" in file:
            #print(f'Skipping {file} as it contains "newleveltest" in the name.')
            continue

        file_path = os.path.join(stage_path, file)
        with open(file_path, "rb") as f:
            data[file[:file.index('.')]] = orjson.loads(f.read())

    return data


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


def load_localization(path_primary, path_secondary, path_translation):
    ds = {}
    da = {}
    data_secondary = []
    data_aux = []

    data_primary = load_file(os.path.join(path_primary, 'DB', 'LocalizeExcelTable.json'), key='Key')
    data_secondary = load_file(os.path.join(path_secondary, 'DB', 'LocalizeExcelTable.json'), key='Key')
    #print(f'Loaded secondary script data from LocalizeExcelTable.json, {len(data_secondary)} entries')

    if os.path.exists(os.path.join(path_translation, 'LocalizeExcelTable.json')):
        print(f'Loading additional translations from {path_translation}/LocalizeExcelTable.json')
        data_aux = load_file(os.path.join(path_translation, 'LocalizeExcelTable.json'), key='Key')

    found = 0
    for key, line in data_primary.items():
        if key in data_aux and key in data_secondary and data_aux[key]['En'] != data_secondary[key]['En']:
            #print(f"Retaining official translation as EnGlobal:\n AUX :{data_aux[key]['En']}\n GLOB:{data_secondary[key]['En']}")
            line['EnGlobal'] = data_secondary[key]['En']
        if key in data_aux:
            line['En'] = data_aux[key]['En']
            #if line['Jp'] != data_aux[key]['Jp']: print(f"LocalizeExcelTable: Unmatched primary↔aux Jp line {key}: {line['Jp']} | {data_aux[key]['Jp']}" )
            found += 1
        elif key in data_secondary:
            line['En'] = data_secondary[key]['En']
            #if line['Jp'] != data_secondary[key]['Jp']: print(f"LocalizeExcelTable: Unmatched primary↔secondary Jp line {key}: {line['Jp']} | {data_secondary[key]['Jp']}" )
            found += 1

    print(f"LocalizeExcelTable: Found {found}/{len(data_primary)} translations")

    #Force aux lines into the list if they are missing there completely
    data_primary = {**data_aux, **data_primary}

    return data_primary


#TODO switch to using new DB scenario_script everywhere
BlueArchiveScenarioData = collections.namedtuple(
    'BlueArchiveScenarioData',
    ['scenario_script', 'scenario_character_name']
)


def load_scenario_data(path_primary, path_secondary, path_translation):
    return BlueArchiveScenarioData(
        scenario_script=load_db_scenario_script(path_primary, path_secondary, path_translation),
        scenario_character_name=load_combined_localization(path_primary, path_secondary, path_translation, 'ScenarioCharacterNameExcelTable.json', key='CharacterName')
    )


def load_db_scenario_script(path_primary, path_secondary, path_translation):
    ds = {}
    da = {}
    data = []
    data_aux = []

    data_primary = load_file(os.path.join(path_primary, 'DB', 'ScenarioScriptExcelTable.json'), key=None, load_multipart=True)
    #print(f'Loaded primary script data from ScenarioScriptExcelTable.json, {len(data_primary)} entries')

    data_secondary = load_file(os.path.join(path_secondary, 'DB', 'ScenarioScriptExcelTable.json'), key=None, load_multipart=True)
    #print(f'Loaded secondary script data from ScenarioScriptExcelTable.json, {len(data_secondary)} entries')
        
    for file in os.listdir(path_translation + '/scenario/'):
        if not file.endswith('.json'):
            continue
        #print(f'Loading additional scenario translations from {path_translation}/scenario/{file}')
        with open(os.path.join(path_translation + '/scenario/', file), encoding="utf8") as f:
            data_aux += orjson.loads(f.read())['DataList']

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


# Deprecated game-native multipart file loading
# def load_multipart_file(path, filename, entries: list):
#     data = []
#     for i in entries: 
#         with open(os.path.join(path, 'Excel', filename.replace('$', str(i))), encoding="utf8") as f: data += orjson.loads(f.read())['DataList']
#     return data
    



BlueArchiveSeasonData = collections.namedtuple(
    'BlueArchiveSeasonData',
    ['raid_season', 'world_raid_season', 'eliminate_raid_season', 'eliminate_raid_stage', 'multi_floor_raid_season',
     'event_content_season', 
     'time_attack_dungeon_season',
     'shop_recruit']
)

def load_season_data(path):
    return BlueArchiveSeasonData(
        raid_season=            load_generic(path, 'RaidSeasonManageExcelTable.json', key='SeasonId'),
        world_raid_season=      load_generic(path, 'WorldRaidSeasonManageExcelTable.json', key='SeasonId'),
        eliminate_raid_season=  load_generic(path, 'EliminateRaidSeasonManageExcelTable.json', key='SeasonId'),
        eliminate_raid_stage=   load_file_grouped(path, 'EliminateRaidStageExcelTable.json', 'RaidBossGroup'),
        multi_floor_raid_season=load_generic(path, 'MultiFloorRaidSeasonManageExcelTable.json', key='SeasonId'),
        event_content_season=   load_event_content_seasons(path),
        time_attack_dungeon_season= load_generic(path, 'TimeAttackDungeonSeasonManageExcelTable.json', key=None),
        shop_recruit =          load_generic(path, 'ShopRecruitExcelTable.json'),
    )
