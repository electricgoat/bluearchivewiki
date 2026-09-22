import re
from shared.functions import hashkey
from shared.glossary import CLUBS
from shared.tag_map import TAG_MAP, map_tag, map_tags

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

enemy_tags = CLUBS | TAG_MAP | {
        #enemies
        'DecagrammatonSPO': 'Decagrammaton',
}

EVENT_DIFFICULTIES = ['', 'Story', 'Quest', 'Challenge']


def mission_desc(mission, data, missing_descriptions = None, items = None, furniture = None):
    """Put the mission's Japanese and English descriptions on it: its localized text, filled in by the localizer of its condition type if there is one."""
    mission['AutoLocalized'] = False

    key = description_key(mission)
    if key in data.localization:
        mission['DescriptionJp'] = description_cleanup(data.localization[key].get('Jp').replace('{0}', str(mission['CompleteConditionCount'])))
        mission['DescriptionEn'] = description_cleanup(data.localization[key].get('En', '').replace('{0}', str(mission['CompleteConditionCount'])))
        if 'En' not in data.localization[key]: print (f"Untranslated mission localize id {key}")

    localizer = LOCALIZERS.get(mission['CompleteConditionType'].replace('Reset_',''))
    if localizer is not None: localizer(mission, data, items, furniture)

    if not mission['AutoLocalized'] and key not in data.localization:
        if missing_descriptions is not None: missing_descriptions.append(mission['Description'])
        print (f"Missing localization mapping {key} for {mission['Description']} of {mission}")
        return False


def description_key(mission) -> int:
    return isinstance(mission['Description'], int) and mission['Description'] or hashkey(mission['Description'])


def localized_description(mission, data) -> tuple[str, str]:
    """The Japanese and English texts of the mission's localized description, placeholders included."""
    localization = data.localization[description_key(mission)]
    return localization.get('Jp'), localization.get('En', '')


def fill(text: str, values: dict) -> str:
    """Replace each placeholder of values in the text, in order."""
    for placeholder, value in values.items():
        text = text.replace(placeholder, str(value))
    return text


def describe(mission, desc_jp: str, desc_en: str) -> bool:
    mission['DescriptionJp'] = description_cleanup(desc_jp)
    mission['DescriptionEn'] = description_cleanup(desc_en)
    mission['AutoLocalized'] = True
    return True


def dungeon_stage(mission, dungeon_names: dict[int, str]) -> str:
    """The dungeon and stage letter of the stage id in the mission's first condition parameter."""
    stage_id = str(mission['CompleteConditionParameter'][0])
    return f"{dungeon_names.get(int(stage_id[1:3]), '')} {chr(ord('A') + int(stage_id[4:]) - 1)}"


def campaign_stage(mission) -> tuple[str, str]:
    """The name (like 12-3H) and difficulty of the campaign stage in the mission's condition parameters."""
    parameters = mission['CompleteConditionParameter']
    difficulty = int(str(parameters[-1])[3:4])
    stage = str(parameters[-1])[1:3].lstrip('0') + '-' + str(parameters[0])[5:7].lstrip('0') + ('H' if difficulty == 2 else '')
    return stage, ['', 'Normal', 'Hard'][difficulty]


def event_stage(mission, offset: int = 0) -> tuple[str, int]:
    """The number and difficulty index of the event stage in the mission's last condition parameter: the event id (plus offset digits), the difficulty, a digit, the stage number."""
    idlen = len(str(mission['EventContentId'])) + offset
    parameter = str(mission['CompleteConditionParameter'][-1])
    return parameter[idlen+2:idlen+4].lstrip('0'), int(parameter[idlen:idlen+1])


def tag_names(tags, names: dict) -> str:
    """The tag, or the tags joined by "or", as names spells them."""
    return " or ".join(names.get(x) or x for x in ([tags] if isinstance(tags, str) else tags))


def localize_ClearSpecificChaserDungeonCount(mission, data, items, furniture):
    desc_jp, desc_en = localized_description(mission, data)
    values = {'{0}': dungeon_stage(mission, {1: 'Overpass', 2: 'Desert Railroad', 3: 'Classroom'}), '{1}': mission['CompleteConditionCount']}
    return describe(mission, fill(desc_jp, values), fill(desc_en, values))


def localize_ClearSpecificFindGiftAndBloodDungeonCount(mission, data, items, furniture):
    desc_jp, desc_en = localized_description(mission, data)
    values = {'{0}': dungeon_stage(mission, {11: 'Base Defense', 21: 'Item Retrieval'}), '{1}': mission['CompleteConditionCount']}
    return describe(mission, fill(desc_jp, values), fill(desc_en, values))


def localize_ClearSpecificSchoolDungeonCount(mission, data, items, furniture):
    desc_jp, desc_en = localized_description(mission, data)
    values = {'{0}': dungeon_stage(mission, {1: 'Trinity', 2: 'Gehenna', 3: 'Millennium'}), '{1}': mission['CompleteConditionCount']}
    return describe(mission, fill(desc_jp, values), fill(desc_en, values))


def localize_Achieve_EquipmentAtSpecificTierUpCount(mission, data, items, furniture):
    desc_jp, desc_en = localized_description(mission, data)
    values = {'{0}': ', '.join(str(x) for x in mission['CompleteConditionParameter']), '{1}': mission['CompleteConditionCount']}
    return describe(mission, fill(desc_jp, values), fill(desc_en, values))


def localize_DreamGetSpecificParameter(mission, data, items, furniture):
    desc_jp, desc_en = localized_description(mission, data)

    params = {x['Id']:x for x in data.minigame_dream_parameter[mission['EventContentId']]}
    condition_param = data.localization[params[mission['CompleteConditionParameter'][1]]['LocalizeEtcId']]

    return describe(mission, fill(desc_jp, {'{0}': mission['CompleteConditionCount'], '{1}': condition_param.get('Jp')}),
                             fill(desc_en, {'{0}': mission['CompleteConditionCount'], '{1}': condition_param.get('En')}))


def localize_DreamGetSpecificScheduleCount(mission, data, items, furniture):
    desc_jp, desc_en = localized_description(mission, data)

    params = {x['DreamMakerScheduleGroupId']:x for x in data.minigame_dream_schedule[mission['EventContentId']]}
    condition_param = data.localization[params[mission['CompleteConditionParameter'][1]]['LocalizeEtcId']]

    return describe(mission, fill(desc_jp, {'{0}': mission['CompleteConditionCount'], '{1}': condition_param.get('Jp')}),
                             fill(desc_en, {'{0}': mission['CompleteConditionCount'], '{1}': condition_param.get('En')}))


def localize_CompleteScheduleWithTagCount(mission, data, items, furniture):
    tags = mission['CompleteConditionParameterTag']
    values = {'$1': mission['CompleteConditionCount'], '$2': " or ".join(map_tags(tags)) if isinstance(tags, list) else map_tag(tags)}
    return describe(mission, fill('受け入れ済みの$2の生徒と$1回スケジュールを実行する', values), fill('Schedule a lesson with student from $2 $1 time(s)', values))


def localize_ClearSchoolDungeonCount(mission, data, items, furniture):
    values = {'$1': mission['CompleteConditionCount']}
    return describe(mission, fill('', values), fill('Participate in School Exchange $1 time(s)', values))


def localize_ClearSpecificScenario(mission, data, items, furniture):
    scenario = str(mission['CompleteConditionParameter'][0])
    values = {'$1': scenario[0:1], '$2': scenario[1:2], '$3': scenario[2:4].lstrip('0')}
    return describe(mission, fill('メインストーリー第$1編$2章$3話をクリア', values), fill('Complete Volume $1, Chapter $2, Episode $3 of the main story', values))


def localize_ClearSpecificCampaignStageCount(mission, data, items, furniture):
    stage, difficulty = campaign_stage(mission)
    values = {'$1': stage, '$2': difficulty}
    return describe(mission, fill('エリア[[Missions/$1|$1]] $2をクリア', values), fill('Clear $2 Mission [[Missions/$1|$1]]', values))


def localize_ClearCampaignStageTimeLimitFromSecond(mission, data, items, furniture):
    stage, difficulty = campaign_stage(mission)
    values = {'$1': stage, '$2': difficulty, '$3': mission['CompleteConditionCount']}
    return describe(mission, fill('任務ステージ[[Missions/$1|$1]]$2を$3秒以内にクリア', values), fill('Clear $2 Mission [[Missions/$1|$1]] within $3 seconds', values))


def localize_ClearEventStageTimeLimitFromSecond(mission, data, items, furniture):
    stage, difficulty = event_stage(mission)
    values = {'$1': stage, '$2': EVENT_DIFFICULTIES[difficulty], '$3': mission['CompleteConditionCount']}
    return describe(mission, fill('任務ステージ$1 $2を$3秒以内にクリア', values), fill('Clear $2 $1 within $3 seconds', values))


def localize_EventCompleteCampaignStageMinimumTurn(mission, data, items, furniture):
    stage, difficulty = event_stage(mission)
    values = {'$1': stage, '$2': EVENT_DIFFICULTIES[difficulty], '$3': mission['CompleteConditionCount']}
    return describe(mission, fill('$2のステージ$1を$3ターン以内にクリア', values), fill('Clear $2 $1 within $3 turns', values))


def localize_CompleteMission(mission, data, items, furniture):
    values = {'$1': mission['CompleteConditionCount']}
    return describe(mission, fill('イベントのチャレンジミションを$1個以上クリア', values), fill('Complete $1 Achievement Missions', values))


def localize_GetItemWithTagCount(mission, data, items, furniture):
    tags = mission['CompleteConditionParameterTag']
    values = {'$1': " or ".join(get_item_type(x) for x in tags) if isinstance(tags, list) else get_item_type(tags), '$2': mission['CompleteConditionCount']}
    return describe(mission, fill('$1を$2個獲得する', values), fill('Acquire $2 $1', values))


def localize_GetEquipmentWithTagCount(mission, data, items, furniture):
    tags = mission['CompleteConditionParameterTag']
    values = {'$1': item_types[tags] if isinstance(tags, str) else " or ".join(item_types[map_tag(x)] for x in tags), '$2': mission['CompleteConditionCount']}
    return describe(mission, fill('$1を$2個獲得する', values), fill('Acquire $2 $1', values))


def localize_GetSpecificItemCount(mission, data, items, furniture):
    assert items is not None
    count = mission['CompleteConditionCount']

    toget_jp = ', '.join(f"{items[x].name_jp}を{count}" for x in mission['CompleteConditionParameter'])
    toget_en = ', '.join(f"{count} {items[x].name_en}" for x in mission['CompleteConditionParameter'])
    return describe(mission, fill('$1個獲得する', {'$1': toget_jp}), fill('Acquire $1', {'$1': toget_en}))


def localize_ClearBattleWithTagCount(mission, data, items, furniture):
    values = {'$1': tag_names(mission['CompleteConditionParameterTag'], enemy_tags), '$2': mission['CompleteConditionCount']}
    return describe(mission, fill('-', values), fill('Clear any stage with a student from $1 $2 time(s)', values))


def localize_KillEnemyWithTagCount(mission, data, items, furniture):
    values = {'$1': tag_names(mission['CompleteConditionParameterTag'], enemy_tags), '$2': mission['CompleteConditionCount']}
    return describe(mission, fill('-', values), fill('Defeat any enemy from $1 $2 time(s)', values))


def localize_ConquerSpecificStepTileAll(mission, data, items, furniture):
    values = {'$1': mission['CompleteConditionParameter'][2]+1}
    return describe(mission, fill('エリア$1をすべて占領', values), fill('Occupy all of area $1', values))


def localize_UpgradeConquestBaseTileCount(mission, data, items, furniture):
    values = {'{1}': mission['CompleteConditionCount'], '{0}': mission['CompleteConditionParameter'][2]}
    return describe(mission, fill('Lv.{0}拠点を{1}個保有する', values), fill('Own {1} Lv. {0} base(s)', values))


def localize_KillConquestBoss(mission, data, items, furniture):
    values = {'{0}': mission['CompleteConditionParameter'][2]+1}
    return describe(mission, fill('エリア{0}のボスを倒す', values), fill('Defeat the area {0} boss', values))


def localize_ClearEventConquestTileTimeLimitFromSecond(mission, data, items, furniture):
    values = {'{1}': mission['CompleteConditionCount'], '{0}': str(mission['CompleteConditionParameter'][0])[-1:]}
    return describe(mission, fill('-', values), fill('Clear Challenge {0} within {1} second(s)', values))


def localize_ClearSpecificDefenseStage(mission, data, items, furniture):
    desc_jp, desc_en = localized_description(mission, data)
    stage, difficulty = event_stage(mission, offset=1)
    values = {'{0}': stage, '{1}': ['', 'Story', 'Normal', 'Challenge'][difficulty], '{2}': mission['CompleteConditionCount']}
    return describe(mission, fill(desc_jp, values), fill(desc_en, values))


#CompleteConditionParameter is [event id, equipment tier], CompleteConditionCount is always 1
def localize_JankenEquipmentTierCheckCount(mission, data, items, furniture):
    desc_jp, desc_en = localized_description(mission, data)
    values = {'{0}': mission['CompleteConditionParameter'][-1]}
    return describe(mission, fill(desc_jp, values), fill(desc_en, values))


#CompleteConditionParameter is [event id, janken stage id], CompleteConditionCount is the score to reach
def localize_JankenGetSpecificScore(mission, data, items, furniture):
    desc_jp, desc_en = localized_description(mission, data)

    stage = data.minigame_janken_stage.get(mission['CompleteConditionParameter'][-1])
    if stage is None:
        print(f"Janken score mission {mission['Id']} refers to unknown stage {mission['CompleteConditionParameter'][-1]}")
        return False

    stage_type = data.localization.get(stage['StageTypeLocalize'], {})
    stage_jp = f"{stage_type.get('Jp') or stage['JankenStageType']} {stage['StageDisplay']}"
    stage_en = f"{stage_type.get('En') or stage_type.get('Jp') or stage['JankenStageType']} {stage['StageDisplay']}"

    return describe(mission, fill(desc_jp, {'{0}': stage_jp, '{1}': mission['CompleteConditionCount']}),
                             fill(desc_en, {'{0}': stage_en, '{1}': mission['CompleteConditionCount']}))


#Localizers by CompleteConditionType, without its Reset_ prefix
LOCALIZERS = {
    'ClearSpecificChaserDungeonCount': localize_ClearSpecificChaserDungeonCount,
    'ClearSpecificFindGiftAndBloodDungeonCount': localize_ClearSpecificFindGiftAndBloodDungeonCount,
    'ClearSpecificSchoolDungeonCount': localize_ClearSpecificSchoolDungeonCount,
    'Achieve_EquipmentAtSpecificTierUpCount': localize_Achieve_EquipmentAtSpecificTierUpCount,
    'DreamGetSpecificParameter': localize_DreamGetSpecificParameter,
    'DreamGetSpecificScheduleCount': localize_DreamGetSpecificScheduleCount,
    'CompleteScheduleWithTagCount': localize_CompleteScheduleWithTagCount,
    'ClearSchoolDungeonCount': localize_ClearSchoolDungeonCount,
    'ClearSpecificScenario': localize_ClearSpecificScenario,
    'ClearSpecificCampaignStageCount': localize_ClearSpecificCampaignStageCount,
    'ClearCampaignStageTimeLimitFromSecond': localize_ClearCampaignStageTimeLimitFromSecond,
    'ClearEventStageTimeLimitFromSecond': localize_ClearEventStageTimeLimitFromSecond,
    'EventCompleteCampaignStageMinimumTurn': localize_EventCompleteCampaignStageMinimumTurn,
    'CompleteMission': localize_CompleteMission,
    'GetItemWithTagCount': localize_GetItemWithTagCount,
    'GetEquipmentWithTagCount': localize_GetEquipmentWithTagCount,
    'GetSpecificItemCount': localize_GetSpecificItemCount,
    'ClearBattleWithTagCount': localize_ClearBattleWithTagCount,
    'KillEnemyWithTagCount': localize_KillEnemyWithTagCount,
    'ConquerSpecificStepTileAll': localize_ConquerSpecificStepTileAll,
    'UpgradeConquestBaseTileCount': localize_UpgradeConquestBaseTileCount,
    'KillConquestBoss': localize_KillConquestBoss,
    'ClearEventConquestTileTimeLimitFromSecond': localize_ClearEventConquestTileTimeLimitFromSecond,
    'ClearSpecificDefenseStage': localize_ClearSpecificDefenseStage,
    'JankenEquipmentTierCheckCount': localize_JankenEquipmentTierCheckCount,
    'JankenGetSpecificScore': localize_JankenGetSpecificScore,
}


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
    if text in TAG_MAP.keys(): text = TAG_MAP[text]
    if text in item_types: text = item_types[text]

    if re.search(r"^Token_S\d+$", text, re.MULTILINE): text = 'Event Tokens'

    return text
