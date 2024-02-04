# import collections
# import re
from shared.functions import armor_type, damage_type, environment_type
from classes.RewardParcel import RewardParcel

ignore_item_id = [
        500100, #bundle of one of: Novice Activity Report / Lesser Enhancement Stone / Booster Ticket / (1 random T1 oopart). All story stages seem to have it 
    ]

DIFFICULTY = {'Normal':'Story', 'Hard':'Quest', 'VeryHard':'Challenge', 'VeryHard_Ex': 'Extra Challenge'}


class Stage(object):
    def __init__(self, id, name, name_en, season, difficulty, stage_number, stage_display, prev_id, battle_duration, stategy_map, strategy_map_bg, reward_id, topography, rec_level, strategy_environment, grounds, content_type, rewards, wiki_enter_cost, damage_types, armor_types, stage_hint):
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
        self.stage_hint = stage_hint

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
            



class EventStage(Stage):
    
    @classmethod
    def get_rewards(cls, stage, data, wiki_card = None):
        reward_parcels = []
        rewards = {}

        reward_parcels = data.event_content_stage_reward[stage['EventContentStageRewardId']]

        for parcel in [x for x in reward_parcels if x['RewardProb']>0]:
            reward = RewardParcel(parcel['RewardParcelType'], 
                                  parcel['RewardId'], 
                                  [parcel['RewardAmount']], 
                                  [parcel['RewardProb']],
                                  parcel['RewardTag'],
                                  data=data,
                                  wiki_card=wiki_card
                                  ) 

            if reward.parcel_id in rewards and reward.tag == rewards[reward.parcel_id].tag:
                rewards[reward.parcel_id].add_drop(reward.amount, reward.parcel_prob)
            else:
                rewards[reward.parcel_id] = reward

        return dict(rewards)


    @classmethod
    def from_data(cls, stage_id, data):
        grounds = []
        stage = data.event_content_stages[stage_id]

        rewards = cls.get_rewards(stage, data)
        enter_cost =  cls.wiki_enter_cost(stage, data)

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

        stage_hint = ''
        if stage['StageHint'] > 0 and stage['StageHint'] in data.etc_localization:
            stage_hint = data.etc_localization[stage['StageHint']]['DescriptionEn'] if 'DescriptionEn' in data.etc_localization[stage['StageHint']] else data.etc_localization[stage['StageHint']]['DescriptionJp']


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
            set(sorted([armor_type(x['ArmorType']) for x in spawn_templates.values()])),
            stage_hint
        )
    


class FieldStage(Stage):

    @classmethod
    def get_rewards(cls, stage, data, wiki_card = None):
        reward_parcels = []
        rewards = {}

        reward_parcels = data.field_content_stage_reward[stage['Id']]

        for parcel in [x for x in reward_parcels if x['RewardProb']>0]:
            reward = RewardParcel(parcel['RewardParcelType'], 
                                  parcel['RewardId'], 
                                  [parcel['RewardAmount']], 
                                  [parcel['RewardProb']],
                                  parcel['RewardTag'],
                                  data=data,
                                  wiki_card=wiki_card
                                  ) 

            if reward.parcel_id in rewards and reward.tag == rewards[reward.parcel_id].tag:
                rewards[reward.parcel_id].add_drop(reward.amount, reward.parcel_prob)
            else:
                rewards[reward.parcel_id] = reward

        return dict(rewards)


    @classmethod
    def from_data(cls, stage_id, data, wiki_card = None):
        grounds = []
        stage = data.field_content_stage[stage_id]

        rewards = cls.get_rewards(stage, data, wiki_card)
        enter_cost =  cls.wiki_enter_cost(stage, data)

        #print(f"Stage {stage['Name']} localization key {shared.functions.hashkey(stage['Name'])}")

        name_en = f"{DIFFICULTY[stage['StageDifficulty']]} {int(stage['Name'][-2:])}"
        #name_en = data.localization[shared.functions.hashkey(stage['Name'])].get('En') or data.localization[shared.functions.hashkey(stage['Name'])].get('Jp','Unknown')

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
            stage['SeasonId'],
            stage['StageDifficulty'],
            stage['AreaId'],
            stage['AreaId'],
            0,
            stage['BattleDuration'],
            #stage['StageEnterCostType'],
            #stage['StageEnterCostId'],
            #stage['StageEnterCostAmount'],
            "",
            "",
            stage['Id'],
            stage['StageTopography'],
            stage['RecommandLevel'],
            None,
            grounds,
            "FieldContentBattleStage",
            rewards,
            enter_cost,
            # set([damage_type(x['EnemyBulletType']) for x in grounds if x['EnemyBulletType'] != "Normal" ]),
            # set([armor_type(x['EnemyArmorType']) for x in grounds])
            set(sorted([damage_type(x['BulletType']) for x in spawn_templates.values() if x['BulletType'] != "Normal" ])),
            set(sorted([armor_type(x['ArmorType']) for x in spawn_templates.values()])),
            stage_hint = '',
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
