import collections
import re
from model_stages import get_currency_rewards, get_equipment_rewards, get_item_rewards, get_character_rewards, get_gacha_rewards, _get_gacha_rewards, _get_gacha_rewards_recursive, get_gacha_prob, _REWARD_TYPES

ignore_item_id = [
        500100, #bundle of one of: Novice Activity Report / Lesser Enhancement Stone / Booster Ticket / (1 random T1 oopart). All story stages seem to have it 
    ]

Reward = collections.namedtuple('Reward', 'name,tag,prob,amount,type')


def get_schedule_rewards(location, data):
    rewards = []
    for reward in _get_schedule_rewards(location, data):
        rewards.append(reward)

    return rewards


def _get_schedule_rewards(location, data):
    for index, reward in enumerate(location['ExtraRewardParcelType']):
        reward = {}
        reward['RewardId'] = location['ExtraRewardParcelId'][index]
        reward['RewardTag'] = 'ExtraReward'
        reward['RewardProb'] = location['ExtraRewardProb'][index]
        reward['RewardAmount'] = location['ExtraRewardAmount'][index]
        reward['RewardParcelType'] = location['ExtraRewardParcelType'][index]

        try:
            yield from _REWARD_TYPES[reward['RewardParcelType']](reward, data)
        except KeyError:
            print(f'Unknown RewardParcelType: {reward["RewardParcelType"]}')



class EventScheduleLocation(object):
    def __init__(self, id, name, order, group_id, localize_id, rank, favor_exp, secretstone_prob, extra_favor_exp, extra_favor_exp_prob, rewards):
        self.id = id
        self.name = name
        self.order = order
        self.group_id = group_id
        self.localize_id = localize_id
        self.rank = rank
        self.favor_exp = favor_exp
        self.secretstone_prob = secretstone_prob
        self.extra_favor_exp = extra_favor_exp
        self.extra_favor_exp = extra_favor_exp
        self.extra_favor_exp_prob = extra_favor_exp_prob
        self.rewards = rewards


    def __repr__ (self):
        return f"EventScheduleLocation:{self.id}"


    @classmethod
    def from_data(cls, location_id, data):
        location = data.event_content_location_reward[location_id]

        name = data.etc_localization[location['LocalizeEtcId']]['NameEn']
        rewards = get_schedule_rewards(location, data)

        return cls(
            location['Id'],
            name,
            location['OrderInGroup'],
            location['ScheduleGroupId'],
            #location['VoiceClipsJp'],
            location['LocalizeEtcId'],
            location['LocationRank'],
            location['FavorExp'],
            location['SecretStoneProb'],
            location['ExtraFavorExp'],
            location['ExtraFavorExpProb'],
            rewards,
        )




