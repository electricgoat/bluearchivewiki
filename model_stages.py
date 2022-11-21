import collections
import re

ignore_item_id = [
        500100, #bundle of one of: Novice Activity Report / Lesser Enhancement Stone / Booster Ticket / (1 random T1 oopart). All story stages seem to have it 
    ]

Reward = collections.namedtuple('Reward', 'name,tag,prob,amount,type')

def translate_group_name(text):
    text = re.sub('스테이지용', 'Stage', text)
    text = re.sub('스테이지', 'Stage', text)
    text = re.sub('장비', 'equipment', text)
    text = re.sub('티어', 'Tier', text)
    text = re.sub('박스', 'bundle', text)
    text = re.sub('묶음', 'recursive', text)
    text = re.sub('통합', 'integrated', text)
    text = re.sub('가챠', 'gacha', text)
    text = re.sub('크레딧', 'Credits', text)
    text = re.sub('공통', 'common', text)
    text = re.sub('오파츠', 'OOparts', text)
    text = re.sub('아이템', 'item', text)
    text = re.sub('그룹', 'group', text)
    text = re.sub('하급', 'low-class', text)
    text = re.sub('하드', 'hard', text)
    
    return text



def get_currency_rewards(reward, data):
    currency = data.currencies[reward['RewardId']]
    name_en = 'NameEn' in data.localization[currency['LocalizeEtcId']] and data.localization[currency['LocalizeEtcId']]['NameEn'] or None

    yield Reward(name_en, reward['RewardTag'], reward['RewardProb'] / 100, reward['RewardAmount'], reward['RewardParcelType'])


def get_equipment_rewards(reward, data):
    item = data.equipment[reward['RewardId']]
    name_en = 'NameEn' in data.localization[item['LocalizeEtcId']] and data.localization[item['LocalizeEtcId']]['NameEn'] or None

    yield Reward(name_en, reward['RewardTag'], reward['RewardProb'] / 100, reward['RewardAmount'], reward['RewardParcelType'])


def get_item_rewards(reward, data):
    item = data.items[reward['RewardId']]
    name_en = 'NameEn' in data.localization[item['LocalizeEtcId']] and data.localization[item['LocalizeEtcId']]['NameEn'] or None

    yield Reward(name_en, reward['RewardTag'], reward['RewardProb'] / 100, reward['RewardAmount'], reward['RewardParcelType'])

def get_character_rewards(reward, data):
    #print (f"Character reward {reward}")
    #item = data.characters[reward['RewardId']]
    name_en = reward['RewardId'] in data.translated_characters and data.translated_characters[reward['RewardId']]['PersonalNameEn'] or f"Character {reward['RewardId']}"

    yield Reward(name_en, reward['RewardTag'], reward['RewardProb'] / 100, reward['RewardAmount'], reward['RewardParcelType'])


def get_gacha_rewards(stage_reward, data):
    for reward in _get_gacha_rewards(stage_reward['RewardId'], stage_reward['RewardProb'] / 100, data):
        #print (reward)
        yield reward



def _get_gacha_rewards(group_id, stage_reward_prob, data):
    global ignore_item_id
    verbose = False

    if group_id in ignore_item_id: 
        if verbose: print(f"Ignoring gacha group {group_id}")
        return

    gacha_group = data.gacha_groups[group_id]
    if verbose: print(f"Getting rewards for group_id {group_id}: {translate_group_name(gacha_group['NameKr'])}")
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

        name_en = 'NameEn' in data.localization[item['LocalizeEtcId']] and data.localization[item['LocalizeEtcId']]['NameEn'] or None

        if verbose: print (f'   {name_en}')
        prob = get_gacha_prob(gacha_element, data) * stage_reward_prob / 100
        amount = gacha_element['ParcelAmountMin'] == gacha_element['ParcelAmountMax'] and gacha_element['ParcelAmountMin'] or f"{gacha_element['ParcelAmountMin']}~{gacha_element['ParcelAmountMax']}"


        yield Reward(name_en, 'Other', prob > 5 and round(prob,1) or round(prob,2), amount, gacha_element['ParcelType'])


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
            return f"{{{{ItemCard|{data.localization[data.currencies[stage['StageEnterCostId']]['LocalizeEtcId']]['NameEn']}|quantity={stage['StageEnterCostAmount']}|text=}}}}"
        case 'Item':
            return f"{{{{ItemCard|{data.localization[data.items[stage['StageEnterCostId']]['LocalizeEtcId']]['NameEn']}|quantity={stage['StageEnterCostAmount']}|text=}}}}"
        case _:
            return f"{{{{ItemCard|Unknown Id {stage['StageEnterCostId']}|quantity={stage['StageEnterCostAmount']}|text=}}}}"



class EventStage(object):
    def __init__(self, id, name, season, difficulty, stage_number, stage_display, prev_id, battle_duration, stategy_map, strategy_map_bg, reward_id, topography, rec_level, strategy_environment, ground_id, content_type, rewards, wiki_enter_cost, damage_type, armor_type):
        self.id = id
        self.name = name
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
        self.ground_id = ground_id
        self.content_type = content_type
        self.rewards = rewards
        self.wiki_enter_cost = wiki_enter_cost
        self._damage_type = damage_type
        self._armor_type = armor_type

    def __repr__ (self):
        return f"EventStage:{self.name}"

    @property
    def topography(self):
        return {
            'Street': 'Urban',
            'Indoor': 'Indoors',
            'Outdoor': 'Outdoors'
        }[self._topography]

    @property
    def damage_type(self):
        return {
            'Explosion': 'Explosive',
            'Pierce': 'Penetration',
            'Mystic': 'Mystic',
            None: None
        }[self._damage_type]

    @property
    def armor_type(self):
        return {
            'LightArmor': 'Light',
            'HeavyArmor': 'Heavy',
            'Unarmed': 'Special',
            None: None
        }[self._armor_type]

    
    def wiki_topography(self):
        return '{{Icon|'+str(self.topography)+'|size=24}}<br />'+str(self.topography)


    @classmethod
    def from_data(cls, stage_id, data):
        stage = data.event_content_stages[stage_id]

        rewards = get_event_rewards(stage, data)
        enter_cost =  wiki_enter_cost(stage, data)


        ground = stage['GroundID'] in data.ground and data.ground[stage['GroundID']] or None



        return cls(
            stage['Id'],
            stage['Name'],
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
            stage['GroundID'],
            stage['ContentType'],
            rewards,
            enter_cost,
            (ground != None and ground["EnemyBulletType"] != "Normal") and ground["EnemyBulletType"] or None,
            ground != None and ground["EnemyArmorType"] or None
        )






