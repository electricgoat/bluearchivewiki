import os
from jinja2 import Environment, FileSystemLoader

import shared.functions
from classes.RewardParcel import RewardParcel

missing_localization = None
missing_code_localization = None
missing_etc_localization = None

data = {}
characters = {}
items = {}
furniture = {}
emblems = {}


def parse_rounds(season_id):
    global data
    global missing_localization, missing_etc_localization
    rounds = []

    roadpuzzle_rewards = {x['UniqueId']:x for x in data.minigame_roadpuzzle_reward[season_id]}
    for reward in roadpuzzle_rewards.values():
        reward['reward_parcels'] = []
        for i, parcel_id in enumerate(reward['RewardParcelId']):
            parcel_type = reward['RewardParcelType'][i]
            parcel_amount = reward['RewardParcelAmount'][i]
            
            parcel = RewardParcel(parcel_type, parcel_id, parcel_amount, 10000, wiki_card=wiki_card)
            reward['reward_parcels'].append(parcel)




    for round in data.minigame_roadpuzzle_roadround:
        if round['EventContentId'] != season_id:
            continue

        # This is all wrong, figure out AdditionalRewardID 

        # ar_shop = {x['Id']:x for x in data.event_content_shop[season_id]}
        # additional_rewards = []

        # for i, ar_id in enumerate(round['AdditionalRewardID']):
        #     ar_shop_item = ar_shop[ar_id]
        #     goods = [data.goods[x] for x in ar_shop_item['GoodsId']]
        #     reward_quantity = round['AdditionalRewardAmount'][i]
        #     for j, good in enumerate(goods):
        #         additional_rewards.append(wiki_card(good['ParcelType'][0], good['ParcelId'][0], quantity = good['ParcelAmount'][0] > 1 and  good['ParcelAmount'][0] or None, size='48px', block=True, text='')) 
        # print(additional_rewards)


        round['rewards'] = roadpuzzle_rewards[round['RoundReward']] #minigame_roadpuzzle_reward
        round['wiki_additional_rewards'] = [] #additional_rewards 
        rounds.append(round)
                
    return rounds



def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)


def get_mode_road(season_id: int, ext_data, ext_characters, ext_items, ext_furniture, ext_emblems, ext_missing_localization, ext_missing_code_localization, ext_missing_etc_localization):
    global data, characters, items, furniture, emblems
    global missing_localization, missing_code_localization, missing_etc_localization
    data = ext_data
    characters = ext_characters
    items = ext_items
    furniture = ext_furniture
    emblems = ext_emblems
    missing_localization = ext_missing_localization
    missing_code_localization = ext_missing_code_localization
    missing_etc_localization = ext_missing_etc_localization

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.globals['len'] = len
    
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['nl2br'] = shared.functions.nl2br
    env.filters['nl2p'] = shared.functions.nl2p


    title = 'Road Puzzle Minigame'
    wikitext = {'title':f"=={title}==", 'intro':'', 'rounds':'', 'maps':''}


    # template = env.get_template('template_roadpuzzle_intro.txt')
    # wikitext['intro'] = template.render(name=title, defense_info = data.minigame_defense_info[season_id])
    #print(wikitext['intro'])


    rounds = parse_rounds(season_id)

    template = env.get_template('template_event_road_rounds.txt')
    wikitext['rounds'] = template.render(rounds=rounds)

    maps = data.minigame_roadpuzzle_map[season_id]



            
    return '\n'.join(wikitext.values())
