import collections
import os
#import re
import traceback
import argparse

from enum import IntFlag, auto
from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data
from model import Item, Furniture, FurnitureGroup, Character
from shared.functions import translate_package_name
from event import Card, wiki_itemcard
import shared.functions

ignore_item_id = [
    500100, #bundle of one of: Novice Activity Report / Lesser Enhancement Stone / Booster Ticket / (1 random T1 oopart). All story stages seem to have it     
]

noopen_item_id = [
    100013, #R52 False Sanctuary Alliance Operation Event - Equipment Random Box
]

args = None
data = None
season_data = {'jp':None, 'gl':None}


characters, items, furniture = {},{},{}

class Card(IntFlag):
    PROBABILITY = auto()
    #PROBABILITY_AUTO = auto()
    QUANTITY = auto()
    QUANTITY_AUTO = auto()

STAGE_DIFFICULTY = {'A': 'Normal',
                    'B': 'Hard',
                    'C': 'VeryHard',
                    'D': 'Hardcore',
                    'E': 'Extreme',
                    'F': 'Insane',
                    'G': 'Torment',
                    'None': 'Decisive Battle'
                }

Reward = collections.namedtuple('Reward', 'name,tag,prob,amount,type')
GachaGroup = collections.namedtuple('GachaGroup', 'name,tag,droprate,items')
Droprate = collections.namedtuple('Droprate', 'prob,amount')


def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, **params)


#DEPRECATED
def wiki_itemformat(reward, *params):
    #print ("WARNING - wiki_itemformat function is deprecated, switch to wiki_card")
    if (type(reward).__name__ == 'Reward'):
        return wiki_itemcard(reward, *params)
    elif (type(reward).__name__ == 'GachaGroup'):   
        wikitext = ''
        wikitext += '<div class="itemgroup tag"><span class="tag' + ((len(reward.items)<3 and len(reward.droprate)>2) and ' condensed' or '') + '">' + ", ".join([f"{droprate.amount}×{'%g' % droprate.prob}%" for droprate in reward.droprate]) + '</span>'

        for item in reward.items:
             wikitext += wiki_itemcard(item, *params)
        wikitext += '</div>'
        return wikitext



def get_currency_rewards(reward, data):
    currency = data.currencies[reward['ClearStageRewardParcelUniqueID']]
    name_en = 'NameEn' in data.etc_localization[currency['LocalizeEtcId']] and data.etc_localization[currency['LocalizeEtcId']]['NameEn'] or None

    yield Reward(name_en, 'Other', reward['ClearStageRewardProb'] / 100, reward['ClearStageRewardAmount'], reward['ClearStageRewardParcelType'])


def get_equipment_rewards(reward, data):
    item = data.equipment[reward['ClearStageRewardParcelUniqueID']]
    name_en = 'NameEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['NameEn'] or None

    yield Reward(name_en, 'Other', reward['ClearStageRewardProb'] / 100, reward['ClearStageRewardAmount'], reward['ClearStageRewardParcelType'])


def get_item_rewards(reward, data):
    global ignore_item_id

    item = data.items[reward['ClearStageRewardParcelUniqueID']]

    if item['Id'] in ignore_item_id: 
        print(f"Ignoring item {item['Id']}, listed in ignore_item_id")
        return

    if reward['ClearStageRewardProb'] == 0: 
        #print(f"Ignoring item {item['Id']}, drop probability is {reward['ClearStageRewardProb']}")
        return

    name_en = 'NameEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['NameEn'] or None
    if item['ImmediateUse'] and item['Id'] not in noopen_item_id:
        print(f"Item {item['Id']} is ImmediateUse through {item['UsingResultParcelType']}")
        if item['UsingResultParcelType'] == 'GachaGroup':
            for reward in _get_gacha_rewards(item['UsingResultId'], reward['ClearStageRewardProb'] / 100, data, tag = 'Default'):
                yield reward
            return
        else:
            print(f"Do not know to process {item['UsingResultParcelType']}")

    yield Reward(name_en, 'Other', reward['ClearStageRewardProb'] / 100, reward['ClearStageRewardAmount'], reward['ClearStageRewardParcelType'])

def get_character_rewards(reward, data):
    #print (f"Character reward {reward}")
    #item = data.characters[reward['ClearStageRewardParcelUniqueID']]
    name_en = reward['ClearStageRewardParcelUniqueID'] in data.translated_characters and data.translated_characters[reward['ClearStageRewardParcelUniqueID']]['PersonalNameEn'] or f"Character {reward['ClearStageRewardParcelUniqueID']}"

    yield Reward(name_en, 'Other', reward['ClearStageRewardProb'] / 100, reward['ClearStageRewardAmount'], reward['ClearStageRewardParcelType'])


def get_gacha_rewards(stage_reward, data):
    gacha_group = GachaGroup('Gacha Group', 'GachaGroup', [Droprate(stage_reward['ClearStageRewardProb'] / 100, stage_reward['ClearStageRewardAmount'])],[])

    for reward in _get_gacha_rewards(stage_reward['ClearStageRewardParcelUniqueID'], 100, data):
        #yield reward
        gacha_group.items.append(reward)
    yield gacha_group



def _get_gacha_rewards(group_id, stage_reward_prob, data, tag='Other'):
    global ignore_item_id
    verbose = False

    if group_id in ignore_item_id: 
        if verbose: print(f"Ignoring gacha group {group_id}")
        return

    gacha_group = data.gacha_groups[group_id]
    if verbose: print(f"Getting rewards for group_id {group_id}: {translate_package_name(gacha_group['NameKr'])}")
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
    total_prob = 0

    for element in data.gacha_elements[gacha_element['GachaGroupID']]:
        total_prob += element['Prob']


    return gacha_element['Prob'] / total_prob * 100



_REWARD_TYPES = {
    'Currency': get_currency_rewards,
    'Equipment': get_equipment_rewards,
    'Item': get_item_rewards,
    'GachaGroup': get_gacha_rewards,
    'Character': get_character_rewards
}



def get_world_raid_reward(reward_id: int):
    global data

    rewards = collections.defaultdict(list)
    for reward in _get_world_raid_reward(reward_id):

        if (type(reward).__name__ == 'GachaGroup'):
            for index, existing_reward in enumerate(rewards[reward.tag]):
                if type(existing_reward).__name__ == 'GachaGroup' and reward.items == existing_reward.items:
                    #print(f'Duplicate found for {reward}')
                    rewards[reward.tag][index] = GachaGroup('Gacha Group (collapsed)', existing_reward.tag, existing_reward.droprate + reward.droprate, existing_reward.items)
                    reward = None
                    break
            
            if reward != None: rewards[reward.tag].append(reward)

        else:
            rewards[reward.tag].append(reward)

    return dict(rewards)


def _get_world_raid_reward(reward_id: int):
    global data

    if reward_id not in data.world_raid_stage_reward:
        print(f"Reward group {reward_id} data not found in world_raid_stage_reward")
        return

    rewards = data.world_raid_stage_reward[reward_id]
    for reward in rewards:
        reward_type = reward['ClearStageRewardParcelType']
        #print (reward_type)
        try:
            yield from _REWARD_TYPES[reward_type](reward, data)
        except KeyError:
            print(f'Unknown ClearStageRewardParcelType: {reward_type}')



def get_event_rewards(stage, data, reward_group_param = 'RaidRewardGroupId'):
    rewards = collections.defaultdict(list)
    for reward in _get_event_rewards(stage, data, reward_group_param):

        if (type(reward).__name__ == 'GachaGroup'):
            for index, existing_reward in enumerate(rewards[reward.tag]):
                if type(existing_reward).__name__ == 'GachaGroup' and reward.items == existing_reward.items:
                    #print(f'Duplicate found for {reward}')
                    rewards[reward.tag][index] = GachaGroup('Gacha Group (collapsed)', existing_reward.tag, existing_reward.droprate + reward.droprate, existing_reward.items)
                    reward = None
                    break
            
            if reward != None: rewards[reward.tag].append(reward)

        else:
            rewards[reward.tag].append(reward)

    return dict(rewards)


def _get_event_rewards(stage, data, reward_group_param):
    if stage[reward_group_param] not in data.world_raid_stage_reward:
        print(f"Reward group {stage[reward_group_param]} data not found in world_raid_stage_reward")
        return

    rewards = data.world_raid_stage_reward[stage[reward_group_param]]
    for reward in rewards:
        reward_type = reward['ClearStageRewardParcelType']
        #print (reward_type)
        try:
            yield from _REWARD_TYPES[reward_type](reward, data)
        except KeyError:
            print(f'Unknown ClearStageRewardParcelType: {reward_type}')



def get_raid_boss_data(group):
    global args, data, season_data

    boss_data = {}

    boss_data['stage'] = data.world_raid_stage[group]
    for stage in boss_data['stage']:
        #print (f"RaidCharacterId: {stage['RaidCharacterId']} {stage['RaidBossGroup']} {stage['Difficulty']}")
        stage['ground'] = data.ground[stage['GroundId']]
        stage['character'] = data.characters[stage['RaidCharacterId']]
        stage['characters_stats'] = data.characters_stats[stage['RaidCharacterId']]
        stage['Difficulty'] = STAGE_DIFFICULTY[stage['WorldRaidDifficulty']]


    boss_data['name'] = data.etc_localization[data.characters[boss_data['stage'][0]['RaidCharacterId']]['LocalizeEtcId']]['NameEn']

    boss_data['PortraitPath'] = boss_data['stage'][0]['PortraitPath']
    boss_data['BGPath'] = boss_data['stage'][0]['BGPath']

    boss_data['portrait'] = boss_data['PortraitPath'].rsplit('/',1)[-1]
    boss_data['portrait_bg'] = boss_data['BGPath'].rsplit('/',1)[-1]

    print( boss_data['name'] )


    
    return boss_data



def generate():
    global args, data
    global characters, items, furniture

    #boss_groups = ['OpenRaidBossGroupId']
    boss_data = {}

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.globals['wiki_itemformat'] = wiki_itemformat
    env.globals['len'] = len
    
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands


    region = 'jp'
    #season = season_data[region].world_raid_season[args['season_id']]
    for season in season_data[region].world_raid_season.values():
        print (f"Working on season {season['SeasonId']}")
        wikitext = "\n==Boss Info==\n"

        
        for group in season['OpenRaidBossGroupId']:          
            boss_data[group]= get_raid_boss_data(group)

            clear_rewards = get_world_raid_reward(data.world_raid_boss_group[group]['WorldBossClearRewardGroupId'])
            clear_rewards = 'Other' in clear_rewards and clear_rewards['Other'] or []

            template = env.get_template('./raid/template_world_raid_boss_info.txt')
            wikitext += template.render(boss_data=boss_data[group], raid_group_data=data.world_raid_boss_group[group], clear_rewards = clear_rewards, Card=Card)

            template = env.get_template('./raid/template_raid_boss.txt')
            wikitext += "\n===Stats===\n"+ template.render(season_data=season, boss_data=boss_data[group])


            stages = boss_data[group]['stage']
            print(f"Found {len(stages)} stages for boss group {group}.")
            template = env.get_template('./raid/template_world_raid_rewards.txt')
            
            wikitext_rewards = []

            for stage in stages:
                stage_rewards = get_event_rewards(stage, data, 'RaidRewardGroupId')
                battle_end_rewards = get_event_rewards(stage, data, 'RaidBattleEndRewardGroupId')

                battle_end_rewards= 'Other' in battle_end_rewards and battle_end_rewards['Other'] or []

                wikitext_rewards.append(stage['Difficulty'] + '=' + template.render(stage=stage, battle_end_rewards=battle_end_rewards, rewards=stage_rewards, Card=Card))
            
            wikitext += "\n===Rewards===\n" + '<tabber>' + '|-|'.join(wikitext_rewards) + '</tabber>' + "\n\n"

        with open(os.path.join(args['outdir'], 'raids' ,f"world_raid_{season['SeasonId']}.txt"), 'w', encoding="utf8") as f:
            f.write(wikitext)




def init_data():
    global args, data, characters, items, furniture, season_data
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    season_data['jp'] = load_season_data(args['data_primary'])
    season_data['gl'] = load_season_data(args['data_secondary'])
   

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':#  not in ['Release', 'Complete']:
            continue

        try:
            character = Character.from_data(character['Id'], data)
            characters[character.id] = character
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue

    for item in data.items.values():
        try:
            item = Item.from_data(item['Id'], data)
            items[item.id] = item
        except Exception as err:
            print(f'Failed to parse for item {item}: {err}')
            traceback.print_exc()
            continue

    for item in data.furniture.values():
        try:
            item = Furniture.from_data(item['Id'], data)
            furniture[item.id] = item
        except Exception as err:
            print(f'Failed to parse for item {item}: {err}')
            traceback.print_exc()
            continue




def main():
    global args

    parser = argparse.ArgumentParser()

    #parser.add_argument('season_id',        metavar='SeasonId', help='World raid stage id')
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')

    args = vars(parser.parse_args())
    #args['season_id'] = int(args['season_id'])

    print(args)

    try:
        init_data()
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
