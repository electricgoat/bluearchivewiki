import collections
import re
import shared.functions

ignore_item_id = [
        500100, #bundle of one of: Novice Activity Report / Lesser Enhancement Stone / Booster Ticket / (1 random T1 oopart). All story stages seem to have it 
    ]

Reward = collections.namedtuple('Reward', 'name,tag,prob,amount,type')

DIFFICULTY = {'Normal':'Story', 'Hard':'Quest', 'VeryHard':'Challenge'}

def damage_type(text):
    return {
        'Explosion': 'Explosive',
        'Pierce': 'Penetration',
        'Mystic': 'Mystic',
        'Sonic': 'Sonic',
        None: None
    }[text]


def armor_type(text):
    return {
        'LightArmor': 'Light',
        'HeavyArmor': 'Heavy',
        'Unarmed': 'Special',
        'ElasticArmor': 'Elastic',
        None: None
    }[text]



def get_currency_rewards(reward, data):
    currency = data.currencies[reward['RewardId']]
    name_en = 'NameEn' in data.etc_localization[currency['LocalizeEtcId']] and data.etc_localization[currency['LocalizeEtcId']]['NameEn'] or None

    yield Reward(name_en, reward['RewardTag'], reward['RewardProb'] / 100, reward['RewardAmount'], reward['RewardParcelType'])


def get_equipment_rewards(reward, data):
    item = data.equipment[reward['RewardId']]
    name_en = 'NameEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['NameEn'] or None

    yield Reward(name_en, reward['RewardTag'], reward['RewardProb'] / 100, reward['RewardAmount'], reward['RewardParcelType'])


def get_item_rewards(reward, data):
    item = data.items[reward['RewardId']]
    name_en = 'NameEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['NameEn'] or None
    if item['ImmediateUse']:
        print(f"Item {item['Id']} is ImmediateUse through {item['UsingResultParcelType']}")
        if item['UsingResultParcelType'] == 'GachaGroup':
            for reward in _get_gacha_rewards(item['UsingResultId'], reward['RewardProb'] / 100, data, tag = 'Default'):
                yield reward
            return
        else:
            print(f"Do not know to process {item['UsingResultParcelType']}")

    yield Reward(name_en, reward['RewardTag'], reward['RewardProb'] / 100, reward['RewardAmount'], reward['RewardParcelType'])

def get_character_rewards(reward, data):
    #print (f"Character reward {reward}")
    #item = data.characters[reward['RewardId']]
    if reward['RewardId'] in data.translated_characters:
        name_en = data.translated_characters[reward['RewardId']]['PersonalNameEn']
        if data.translated_characters[reward['RewardId']]['VariantNameEn'] is not None: name_en += ' ('+data.translated_characters[reward['RewardId']]['VariantNameEn']+')'
    else:
        name_en = f"Character {reward['RewardId']}"

    yield Reward(name_en, reward['RewardTag'], reward['RewardProb'] / 100, reward['RewardAmount'], reward['RewardParcelType'])


def get_gacha_rewards(stage_reward, data):
    for reward in _get_gacha_rewards(stage_reward['RewardId'], stage_reward['RewardProb'] / 100, data):
        #print (reward)
        yield reward



def _get_gacha_rewards(group_id, stage_reward_prob, data, tag='Other'):
    global ignore_item_id
    verbose = False

    if group_id in ignore_item_id: 
        if verbose: print(f"Ignoring gacha group {group_id}")
        return

    gacha_group = data.gacha_groups[group_id]
    if verbose: print(f"Getting rewards for group_id {group_id}: {shared.functions.translate_package_name(gacha_group['NameKr'])}")
    if gacha_group['IsRecursive']:
        if verbose: print (f'This is a recursive group')
        yield from _get_gacha_rewards_recursive(group_id, stage_reward_prob, data)
        return

    for gacha_element in data.gacha_elements[group_id]:
        #print (gacha_element)
        type_ = gacha_element['ParcelType']
        if type_ == 'Currency':
            item = data.currencies[gacha_element['ParcelID']]
        elif type_ == 'Equipment':
            item = data.equipment[gacha_element['ParcelID']]
        elif type_ == 'Item':
            item = data.items[gacha_element['ParcelID']]
        #There is no support for Character rewards here but they are never in gachagroups

        name_en = 'NameEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['NameEn'] or None

        if verbose: print (f'   {name_en}')
        prob = get_gacha_prob(gacha_element, data) * stage_reward_prob / 100
        amount = gacha_element['ParcelAmountMin'] == gacha_element['ParcelAmountMax'] and gacha_element['ParcelAmountMin'] or f"{gacha_element['ParcelAmountMin']}~{gacha_element['ParcelAmountMax']}"

        yield Reward(name_en, tag, prob > 5 and round(prob,1) or round(prob,2), amount, gacha_element['ParcelType'])


def _get_gacha_rewards_recursive(group_id, stage_reward_prob, data):
    for gacha_element in data.gacha_elements_recursive[group_id]:
        #print (f"Getting reward group {gacha_element['ParcelID']} for recursive element {gacha_element}")
        yield from _get_gacha_rewards(gacha_element['ParcelID'], stage_reward_prob, data)


def get_gacha_prob(gacha_element, data):
    #print (f"Current GachaGroupID is {gacha_element['GachaGroupID']}")
    #print (f"Current Prob is {gacha_element['Prob']}")
    total_prob = 0

    for element in data.gacha_elements[gacha_element['GachaGroupID']]:
        total_prob += element['Prob']
    #print (f"Total prob is {total_prob}")

    return gacha_element['Prob'] / total_prob * 100



_REWARD_TYPES = {
    'Currency': get_currency_rewards,
    'Equipment': get_equipment_rewards,
    'Item': get_item_rewards,
    'GachaGroup': get_gacha_rewards,
    'Character': get_character_rewards
}



def get_rewards(campaign_stage, data):
    rewards = collections.defaultdict(list)
    for reward in _get_rewards(campaign_stage, data):
        #print(reward)
        rewards[reward.tag].append(reward)

    return dict(rewards)


def _get_rewards(campaign_stage, data):
    rewards = data.campaign_stage_rewards[campaign_stage['CampaignRewardId']]
    for reward in rewards:
        reward_type = reward['StageRewardParcelType']
        #print (reward_type)
        try:
            yield from _REWARD_TYPES[reward_type](reward, data)
        except KeyError:
            print(f'Unknown StageRewardParcelType: {reward_type}')



def get_event_rewards(stage, data):
    rewards = collections.defaultdict(list)
    for reward in _get_event_rewards(stage, data):
        #print(reward)
        rewards[reward.tag].append(reward)

    return dict(rewards)


def _get_event_rewards(stage, data):
    rewards = data.event_content_stage_rewards[stage['EventContentStageRewardId']]
    for reward in rewards:
        reward_type = reward['RewardParcelType']
        #print (reward_type)
        try:
            yield from _REWARD_TYPES[reward_type](reward, data)
        except KeyError:
            print(f'Unknown RewardParcelType: {reward_type}')




def wiki_enter_cost(stage, data):       
    match stage['StageEnterCostType']:
        case 'None':
            return ''
        case 'Currency':
            return f"{{{{ItemCard|{data.etc_localization[data.currencies[stage['StageEnterCostId']]['LocalizeEtcId']]['NameEn']}|quantity={stage['StageEnterCostAmount']}|text=}}}}"
        case 'Item':
            return f"{{{{ItemCard|{data.etc_localization[data.items[stage['StageEnterCostId']]['LocalizeEtcId']]['NameEn']}|quantity={stage['StageEnterCostAmount']}|text=}}}}"
        case _:
            return f"{{{{ItemCard|Unknown Id {stage['StageEnterCostId']}|quantity={stage['StageEnterCostAmount']}|text=}}}}"



class EventStage(object):
    def __init__(self, id, name, name_en, season, difficulty, stage_number, stage_display, prev_id, battle_duration, stategy_map, strategy_map_bg, reward_id, topography, rec_level, strategy_environment, grounds, content_type, rewards, wiki_enter_cost, damage_types, armor_types):
        self.id = id
        self.name = name
        self.name_en = name_en
        self.season = season
        self.difficulty = difficulty
        self.stage_number = stage_number
        self.stage_display = stage_display
        self.prev_id = prev_id
        self.battle_duration = battle_duration
        #self.enter_cost_type = enter_cost_type
        #self.enter_cost_id = enter_cost_id
        #self.enter_cost_amount = enter_cost_amount
        self.stategy_map = stategy_map
        self.strategy_map_bg = strategy_map_bg
        self.reward_id = reward_id
        self._topography = topography
        self.rec_level = rec_level
        self.strategy_environment = strategy_environment
        self.grounds = grounds
        self.content_type = content_type
        self.rewards = rewards
        self.wiki_enter_cost = wiki_enter_cost
        self.damage_types = damage_types
        self.armor_types = armor_types

    def __repr__ (self):
        return f"EventStage:{self.name}"

    @property
    def topography(self):
        return {
            'Street': 'Urban',
            'Indoor': 'Indoors',
            'Outdoor': 'Outdoors'
        }[self._topography]

    
    def wiki_topography(self):
        return '{{Icon|'+str(self.topography)+'|size=24}}<br />'+str(self.topography)


    @classmethod
    def from_data(cls, stage_id, data):
        grounds = []
        stage = data.event_content_stages[stage_id]

        rewards = get_event_rewards(stage, data)
        enter_cost =  wiki_enter_cost(stage, data)

        name_en = f"{DIFFICULTY[stage['StageDifficulty']]} {stage['StageNumber']}"

        devname_characters = {x['DevName']:{'Id':x['Id'], 'BulletType':x['BulletType'],'ArmorType':x['ArmorType']} for x in data.characters.values()}
        spawn_templates = dict()

        if stage['GroundID'] > 0 and stage['GroundID'] in data.ground: 
            grounds.append(data.ground[stage['GroundID']])
        else:
            for entity in data.strategymaps[stage['StrategyMap'][12:]]['hexaUnitList']:
                grounds.append(data.ground[entity['Id']])

        for ground in grounds:
            stagefile = data.stages[ground['StageFileName'][0]]

            for template in json_find_key(stagefile, 'SpawnTemplateId'):
                if template != '' and template in devname_characters and template not in spawn_templates:
                    spawn_templates[template] = devname_characters[template]     


        return cls(
            stage['Id'],
            stage['Name'],
            name_en,
            stage['EventContentId'],
            stage['StageDifficulty'],
            stage['StageNumber'],
            stage['StageDisplay'],
            stage['PrevStageId'],
            stage['BattleDuration'],
            #stage['StageEnterCostType'],
            #stage['StageEnterCostId'],
            #stage['StageEnterCostAmount'],
            stage['StrategyMap'],
            stage['StrategyMapBG'],
            stage['EventContentStageRewardId'],
            stage['StageTopography'],
            stage['RecommandLevel'],
            stage['StrategyEnvironment'] == "None" and None or stage['StrategyEnvironment'],
            grounds,
            stage['ContentType'],
            rewards,
            enter_cost,
            # set([damage_type(x['EnemyBulletType']) for x in grounds if x['EnemyBulletType'] != "Normal" ]),
            # set([armor_type(x['EnemyArmorType']) for x in grounds])
            set(sorted([damage_type(x['BulletType']) for x in spawn_templates.values() if x['BulletType'] != "Normal" ])),
            set(sorted([armor_type(x['ArmorType']) for x in spawn_templates.values()]))
        )



def json_find_key(json_input, lookup_key):
    if isinstance(json_input, dict):
        for k, v in json_input.items():
            if k == lookup_key:
                yield v
            else:
                yield from json_find_key(v, lookup_key)
    elif isinstance(json_input, list):
        for item in json_input:
            yield from json_find_key(item, lookup_key)
