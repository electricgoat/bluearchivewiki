import collections
import os
import re
import traceback
import copy
import argparse
from datetime import datetime

from enum import IntFlag, auto
from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data
from model import Item, Furniture, FurnitureGroup, Character
from model_stages import EventStage
from model_event_schedule import EventScheduleLocation
from events.mission_desc import mission_desc


args = None
data = None
season_data = {'jp':None, 'gl':None}

characters = {}
items = {}
furniture = {}

stages = {}
missions = {}
hexamaps = {}

total_rewards = {}
total_milestone_rewards = {}


class Card(IntFlag):
    PROBABILITY = auto()
    #PROBABILITY_AUTO = auto()
    QUANTITY = auto()
    QUANTITY_AUTO = auto()

DIFFICULTY = {'Normal':'Story', 'Hard':'Quest', 'VeryHard':'Challenge'}


def parse_stages(season_id):
    global args, data, hexamaps
    stages = []

    for stage in data.event_content_stages.values():
        if stage['EventContentId'] != season_id:
            continue
        stage = EventStage.from_data(stage['Id'], data)
        stages.append(stage)
                
        if stage.content_type == 'EventContentMainStage':
            hexamaps[f"{DIFFICULTY[stage.difficulty]} {stage.stage_number}"] = {'name':f"{DIFFICULTY[stage.difficulty]} {stage.stage_number}", 'filename':f"{stage.name}.png"}

    return stages


def parse_schedule_locations(location_groups):
    global args, data
    
    locations = []

    for location in data.event_content_location_reward.values():
        if location['ScheduleGroupId'] not in location_groups:
            continue
    
        location = EventScheduleLocation.from_data(location['Id'], data)
        locations.append(location)

    return locations
    

def wiki_itemcard(reward, *params):
    card_type = reward.type != 'Character' and 'ItemCard' or 'CharacterCard'

    if Card.PROBABILITY in params: probability = f'|probability={reward.prob:g}'
    else: probability = ''

    if Card.QUANTITY_AUTO in params: quantity = reward.amount>1 and '|quantity='+str(reward.amount) or ''
    elif Card.QUANTITY in params: quantity = '|quantity='+str(reward.amount)
    else: quantity = ''

    return '{{'+card_type+'|'+(reward.name != None and reward.name or 'Unknown')+quantity+probability+'|text=|60px|block}}'


#TODO replace wiki_itemcard with this one
def wiki_card(type, id, **params ):
    global data, items, furniture
    wikitext_params = ''

    match type:
        case 'Item':
            card_type = 'ItemCard'
            name = items[id].name_en
        case 'Equipment':
            card_type = 'ItemCard'
            name = data.etc_localization[data.equipment[id]['LocalizeEtcId']]['NameEn']
        case 'Currency':
            card_type = 'ItemCard'
            name = data.etc_localization[data.currencies[id]['LocalizeEtcId']]['NameEn']
        case 'Character':
            card_type = 'CharacterCard'
            name = characters[id].wiki_name
        case 'Furniture':
            card_type = 'FurnitureCard'
            name = furniture[id].name_en
        case _:
            print(f'Unrecognized item type {type}')
    
    if 'probability' in params:
        wikitext_params += f"|probability={params['probability']:g}"

    if 'quantity' in params and params['quantity'] != None:
        wikitext_params += f"|quantity={params['quantity']}"

    if 'text' in params:
        text = params['text'] != None and params['text'] or ''
        wikitext_params += f"|text={text}"

    if 'size' in params:
        wikitext_params += f"|{params['size']}"

    if 'block' in params:
        wikitext_params += f"|block"

    if name == None: print (f"Unknown {type} item {id}")
    return '{{'+card_type+'|'+(name != None and name.replace('"', '\\"') or f'{type}_{id}')+wikitext_params+'}}'



def parse_missions(season_id):
    global args, data, missions
    missions = copy.copy(data.event_content_mission)
    missing_descriptions = []
    global total_rewards
 
    for mission in data.event_content_mission.values():
        if mission['EventContentId'] != season_id:
            missions.pop(mission['Id'])
            continue
        
        mission_desc(mission, data, missing_descriptions, items=items, furniture=furniture)

        mission['RewardItemNames'] = []
        mission['RewardItemCards'] = []
    
        for index, _ in enumerate(mission['MissionRewardParcelType']):
            mission_reward_parcels(mission, index)
            
            if mission['Category'] == "EventAchievement":
                if mission['MissionRewardParcelId'][index] not in total_rewards:
                    total_rewards[mission['MissionRewardParcelId'][index]] = {}
                    total_rewards[mission['MissionRewardParcelId'][index]]['Id'] = mission['MissionRewardParcelId'][index]
                    total_rewards[mission['MissionRewardParcelId'][index]]['Amount'] = mission['MissionRewardAmount'][index]
                    total_rewards[mission['MissionRewardParcelId'][index]]['Type'] = mission['MissionRewardParcelType'][index]
                    total_rewards[mission['MissionRewardParcelId'][index]]['IsCompletionReward'] = False
                else:
                    total_rewards[mission['MissionRewardParcelId'][index]]['Amount'] += mission['MissionRewardAmount'][index]
                # if mission['TabNumber'] == 0:
                #     total_rewards[mission['MissionRewardParcelId'][index]]['IsCompletionReward'] = True   
        
    for item in total_rewards.values():
        total_reward_card(item)

    return missions


def parse_milestone_rewards(season_id):
    global args, data
    global total_milestone_rewards

    milestones = [x for x in data.event_content_stage_total_rewards.values() if x['EventContentId'] == season_id]

    for mission in milestones:        
        mission['DescriptionEn'] = f"Event Points: {mission['RequiredEventItemAmount']}"

        mission['RewardItemNames'] = []
        mission['RewardItemCards'] = []
    
        for index, _ in enumerate(mission['RewardParcelType']):
            mission['MissionRewardParcelType'] = mission['RewardParcelType']
            mission['MissionRewardParcelId'] = mission['RewardParcelId']
            mission['MissionRewardAmount'] = mission['RewardParcelAmount']

            mission_reward_parcels(mission, index)  

            if (mission['RewardParcelType'][index], mission['RewardParcelId'][index]) not in total_milestone_rewards:
                total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])] = {}
                total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])]['Id'] = mission['RewardParcelId'][index]
                total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])]['Amount'] = mission['RewardParcelAmount'][index]
                total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])]['Type'] = mission['RewardParcelType'][index]
                total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])]['IsCompletionReward'] = False
            else:
                total_milestone_rewards[(mission['RewardParcelType'][index], mission['RewardParcelId'][index])]['Amount'] += mission['RewardParcelAmount'][index]
  
    for item in total_milestone_rewards.values():
        total_reward_card(item)

    return milestones


def mission_reward_parcels(mission, index):
    global data, items, furniture

    if mission['MissionRewardParcelType'][index] == 'Item':
        mission['RewardItemNames'].append(items[mission['MissionRewardParcelId'][index]].name_en )
        mission['RewardItemCards'].append('{{ItemCard|'+items[mission['MissionRewardParcelId'][index]].name_en+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
        #print(data.items[mission['MissionRewardParcelId'][index]].name_en)
    elif mission['MissionRewardParcelType'][index] == 'Furniture':
        mission['RewardItemNames'].append(furniture[mission['MissionRewardParcelId'][index]].name_en )
        mission['RewardItemCards'].append('{{FurnitureCard|'+furniture[mission['MissionRewardParcelId'][index]].name_en+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
        #print(data.furniture[mission['MissionRewardParcelId'][index]].name_en)
    elif mission['MissionRewardParcelType'][index] == 'Equipment':
        mission['RewardItemNames'].append(data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
        mission['RewardItemCards'].append('{{ItemCard|'+data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn']+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
        #print(data.etc_localization[ data.equipment[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
    elif mission['MissionRewardParcelType'][index] == 'Currency':
        mission['RewardItemNames'].append(data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
        mission['RewardItemCards'].append('{{ItemCard|'+data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn']+'|quantity='+str(mission['MissionRewardAmount'][index])+'}}')
        #print(data.etc_localization[ data.currencies[mission['MissionRewardParcelId'][index]]['LocalizeEtcId']]['NameEn'])
    else:
        mission['RewardItemNames'].append("UNKNOWN REWARD TYPE")
        print (f"Unknown reward parcel type {mission['MissionRewardParcelType'][index]}")

    return






def total_reward_card(item):
    global data, items, furniture
    icon_size = ['80px','60px']

    if item['Type'] == 'Item':
        item['Name'] = (items[item['Id']].name_en )
        item['Card'] = ('{{ItemCard|'+items[item['Id']].name_en+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
        item['Tags'] = items[item['Id']].tags
    elif item['Type'] == 'Furniture':
        item['Name'] = (furniture[item['Id']].name_en )
        item['Card'] = ('{{FurnitureCard|'+furniture[item['Id']].name_en+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
    elif item['Type'] == 'Equipment':
        item['Name'] = (data.etc_localization[data.equipment[item['Id']]['LocalizeEtcId']]['NameEn'])
        item['Card'] = ('{{ItemCard|'+data.etc_localization[ data.equipment[item['Id']]['LocalizeEtcId']]['NameEn']+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
    elif item['Type'] == 'Currency':
        item['Name'] = (data.etc_localization[data.currencies[item['Id']]['LocalizeEtcId']]['NameEn'])
        item['Card'] = ('{{ItemCard|'+data.etc_localization[ data.currencies[item['Id']]['LocalizeEtcId']]['NameEn']+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|quantity='+str(item['Amount'])+'|text=}}')
    else:
        item['Name'] = ("UNKNOWN REWARD TYPE")
        print (f"Unknown reward parcel type {item['Type']}")

    return




def generate():
    global args, data, stages, missions
    global characters, items, furniture
    global total_rewards, total_milestone_rewards

    if (args['event_season'], "Stage") in data.event_content_seasons:
        season = data.event_content_seasons[(args['event_season'], "Stage")]
    elif (args['event_season'], "MiniEvent") in data.event_content_seasons:
        season = data.event_content_seasons[(args['event_season'], "MiniEvent")]
    else:
        exit(f"Season {args['event_season']} data not found. Is this a new event type?")
    
    content_types = [x['EventContentType'] for x in data.event_content_seasons.values() if x['EventContentId'] == args['event_season']]
    print(f"Event {args['event_season']} content types: {content_types}")

    if season['MainEventId'] != 0:
        print(f"This is a sub-event, using bonus character data from MainEventId {season['MainEventId']}")
        bc = data.event_content_character_bonus[season['MainEventId']]
    elif season['EventContentId'] in data.event_content_character_bonus:
        bc = data.event_content_character_bonus[season['EventContentId']]
    else:
        print('Warning - no bonus character data found!')
        bc = []
    
    bonus_characters = {x: [] for x in ['EventPoint', 'EventToken1', 'EventToken2', 'EventToken3']}
    for item in bonus_characters:  
        for character in bc:
            if item in character['EventContentItemType']:
                try:
                    bonus_characters[item].append({'CharacterId':character['CharacterId'], 'Name':characters[character['CharacterId']].wiki_name, 'Class':characters[character['CharacterId']].combat_class, 'BonusPercentage':int(character['BonusPercentage'][character['EventContentItemType'].index(item)]/100)})
                except KeyError as err:
                    bonus_characters[item].append({'CharacterId':character['CharacterId'], 'Name':str(character['CharacterId']), 'Class':'Striker', 'BonusPercentage':int(character['BonusPercentage'][character['EventContentItemType'].index(item)]/100)})
    #print (bonus_characters)

    bonus_values = {x: [] for x in ['EventPoint', 'EventToken1', 'EventToken2', 'EventToken3']}
    for item in bonus_characters:
        for character in bonus_characters[item]:
            bonus_values[item].append(character['BonusPercentage'])
        bonus_values[item] = list(set(bonus_values[item]))
        bonus_values[item].sort(reverse=True)
    #print(len(bonus_values['EventToken2']))


    if season['MainEventId'] != 0:
        print(f"This is a sub-event, using currencies data from MainEventId {season['MainEventId']}")
        cy = data.event_content_currency[season['MainEventId']]
    elif season['EventContentId'] in data.event_content_currency:
        cy = data.event_content_currency[season['EventContentId']]
    else:
        print('Warning - no event currencies data found!')
        cy = []

    event_currencies = {x: [] for x in ['EventPoint', 'EventToken1', 'EventToken2', 'EventToken3']}
    for currency in cy:
        event_currencies[currency['EventContentItemType']] = {'ItemUniqueId': currency['ItemUniqueId'], 'Name':items[currency['ItemUniqueId']].name_en} 
    #print(event_currencies)


    if (args['event_season'], "Stage") in data.event_content_seasons:
        stages = parse_stages(data.event_content_seasons[(args['event_season'], "Stage")]['EventContentId'])

    if (args['event_season'], "Mission") in data.event_content_seasons:
        missions = parse_missions(data.event_content_seasons[(args['event_season'], "Mission")]['EventContentId'])

    #Pt milestone rewards
    milestones = parse_milestone_rewards(args['event_season'])


    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.globals['wiki_itemcard'] = wiki_itemcard
    env.globals['len'] = len
   
    
    #STAGES
    wikitext_stages = ''
    difficulty_names = {'Normal':'Story','Hard':'Quest','VeryHard':'Challenge'}
    if (args['event_season'], "Stage") in data.event_content_seasons:

        stage_reward_types = {x: [] for x in ['Normal', 'Hard', 'VeryHard']}

        for stage in stages:
            for reward_tag in stage.rewards:
                if reward_tag not in stage_reward_types[stage.difficulty]:
                    stage_reward_types[stage.difficulty].append(reward_tag)
    
        for difficulty in stage_reward_types:
            template = env.get_template('events/template_event_stages.txt')
            wikitext_stages += template.render(stage_type=difficulty_names[difficulty], stages=[x for x in stages if x.difficulty == difficulty], reward_types=stage_reward_types[difficulty], rewardcols = len(stage_reward_types[difficulty]), Card=Card)


    #SCHEDULE
    wikitext_schedule_locations = ''
    if (args['event_season'], "EventLocation") in data.event_content_seasons:
        wikitext_schedule_locations = '=Schedule Locations=\n'
        location_groups = [x['RewardGroupId'] for x in data.event_content_zone.values() if x['LocationId'] == args['event_season']]
        schedule_locations = parse_schedule_locations(location_groups)

        for schedule_group in location_groups:
            locations = [x for x in schedule_locations if x.group_id == schedule_group]
            template = env.get_template('events/template_schedule.txt')
            wikitext_schedule_locations += template.render(location_name=locations[0].name, locations=locations, Card=Card)


    #SHOPS
    wikitext_shops = ''
    if (args['event_season'], "Shop") in data.event_content_seasons:
        shops = {}
        wikitext_shops = '==Exchange Shop==\n<div style="display: flex; flex-flow: row wrap; align-items: flex-start; gap: 4px;">\n'
        template = env.get_template('events/template_shop.txt')

        for shop in data.event_content_shop_info[args['event_season']]:
            shop = shop
            shop['wiki_currency'] = f"{{{{ItemCard|{items[shop['CostParcelId'][0]].name_en}}}}}"
            shop['wiki_title'] = f"{{{{ItemCard|{items[shop['CostParcelId'][0]].name_en}|48px}}}}"
            shop['total_cost'] = 0
            shop['shop_content'] = [x for x in data.event_content_shop[args['event_season']] if x['CategoryType'] == shop['CategoryType']]

            for shop_item in shop['shop_content']:
                good = data.goods[shop_item['GoodsId'][0]]
                reward_quantity=good['ParcelAmount'][0]
                shop_item['wiki_card'] = wiki_card(good['ParcelType'][0], good['ParcelId'][0], quantity = reward_quantity > 1 and reward_quantity or None  )
                shop_item['cost'] = good['ConsumeParcelAmount'][0]
                shop_item['stock'] = shop_item['PurchaseCountLimit']>0 and shop_item['PurchaseCountLimit'] or '∞'
                shop_item['subtotal'] = shop_item['PurchaseCountLimit']>0 and shop_item['cost']*shop_item['PurchaseCountLimit'] or ''

                if shop_item['PurchaseCountLimit']>0: shop['total_cost'] += shop_item['subtotal']

            shops[shop['CategoryType']] = shop
            wikitext_shops += template.render(shop=shop)
        wikitext_shops += '</div>\n'


    #BOXGACHA
    wikitext_boxgacha = ''
    if (args['event_season'], "BoxGacha") in data.event_content_seasons:
        wikitext_boxgacha = '==Supply Box==\n<tabber>\n'
        template = env.get_template('events/template_boxgacha.txt')

        box_gacha = data.event_content_box_gacha_manage[args['event_season']]
        for box in box_gacha:
            box['wiki_title'] = f"Box {box['Round']}{box['IsLoop']==True and '+' or ''}"
            
            box['Items'] = [{'GroupId': x['GroupId'], 'GroupElementAmount': x['GroupElementAmount'], 'IsPrize': x['IsPrize'], 'GoodsId': x['GoodsId'], 'DisplayOrder': x['DisplayOrder']} for x in data.event_content_box_gacha_shop[args['event_season']] if x['Round'] == box['Round']]

            first_good = data.goods[box['Items'][0]['GoodsId'][0]]
            box['wiki_price'] = wiki_card(first_good['ConsumeParcelType'][0], first_good['ConsumeParcelId'][0], quantity = first_good['ConsumeParcelAmount'][0] )
            box['total_stock'] = 0
            box['total_price'] = 0
            box['is_duplicate'] = False
            
            for box_item in box['Items']:
                good = data.goods[box_item['GoodsId'][0]]
                reward_quantity=good['ParcelAmount'][0]
                box_item['wiki_card'] = wiki_card(good['ParcelType'][0], good['ParcelId'][0], quantity = reward_quantity > 1 and reward_quantity or None )
                box['total_stock'] += box_item['GroupElementAmount']

            box['total_price'] = box['total_stock'] * first_good['ConsumeParcelAmount'][0]

            
        #Deduplicate boxes with matching contents
        for index, box in enumerate(box_gacha):
            if index < 2:
                continue

            for i in range(0, index):
                if box['Items'] == box_gacha[i]['Items']:
                    box['is_duplicate'] = True
                    box_gacha[i]['wiki_title'] += f"/{box['Round']}"


        for box in box_gacha:
            if box['is_duplicate'] == False: wikitext_boxgacha += template.render(box=box)
        
        wikitext_boxgacha = wikitext_boxgacha.rstrip('|-|\n') + '</tabber>\n'


    #OMIKUJI / FORTUNE SLIPS
    wikitext_fortunegacha = ''
    if (args['event_season'], "FortuneGachaShop") in data.event_content_seasons:
        template = env.get_template('events/template_fortunegacha.txt')

        fortune_gacha = data.event_content_fortune_gacha_shop[args['event_season']]
        fortune_tiers = {
            5:{'wiki_title':'Great Blessing (大吉)',    'total_prob' : 0, 'total_modifier': 0, 'total_mod_limit': 0, 'wiki_items': []},
            4:{'wiki_title':'Blessing (吉)',            'total_prob' : 0, 'total_modifier': 0, 'total_mod_limit': 0, 'wiki_items': []},
            3:{'wiki_title':'Modest Blessing (中吉)',   'total_prob' : 0, 'total_modifier': 0, 'total_mod_limit': 0, 'wiki_items': []},
            2:{'wiki_title':'Small Blessing (小吉)',    'total_prob' : 0, 'total_modifier': 0, 'total_mod_limit': 0, 'wiki_items': []},
            1:{'wiki_title':'Future Blessing (末吉)',   'total_prob' : 0, 'total_modifier': 0, 'total_mod_limit': 0, 'wiki_items': []},
            0:{'wiki_title':'Misfortune (凶)',          'total_prob' : 0, 'total_modifier': 0, 'total_mod_limit': 0, 'wiki_items': []},
        }
        for tier in range(0,6):
        
            for box in fortune_gacha:
                if box['Grade'] != tier:
                    continue
               
                fortune_tiers[tier]['total_prob'] += box['Prob']
                fortune_tiers[tier]['total_modifier'] += box['ProbModifyValue']
                fortune_tiers[tier]['total_mod_limit'] += box['ProbModifyLimit']

                if 'RewardParcelType' not in fortune_tiers[tier]: fortune_tiers[tier]['RewardParcelType'] = box['RewardParcelType']
                elif fortune_tiers[tier]['RewardParcelType'] != box['RewardParcelType']: print(f'Mismatched RewardParcelType data within FortuneGacha tier {tier}')

                if 'RewardParcelId' not in fortune_tiers[tier]: fortune_tiers[tier]['RewardParcelId'] = box['RewardParcelId']
                elif fortune_tiers[tier]['RewardParcelId'] != box['RewardParcelId']: print(f'Mismatched RewardParcelId data within FortuneGacha tier {tier}')

                if 'RewardParcelAmount' not in fortune_tiers[tier]: fortune_tiers[tier]['RewardParcelAmount'] = box['RewardParcelAmount']
                elif fortune_tiers[tier]['RewardParcelAmount'] != box['RewardParcelAmount']: print(f'Mismatched RewardParcelAmount data within FortuneGacha tier {tier}')
            
            for index,type in enumerate(fortune_tiers[tier]['RewardParcelType']):
                wiki_card_text = wiki_card(type, fortune_tiers[tier]['RewardParcelId'][index], quantity = fortune_tiers[tier]['RewardParcelAmount'][index], text = None, size = '60px', block = True )
                fortune_tiers[tier]['wiki_items'].append(wiki_card_text)

            #print(fortune_tiers[tier])
        cost_good = data.goods[fortune_gacha[0]['CostGoodsId']]
        wiki_price = wiki_card('Item', cost_good['ConsumeParcelId'][0], quantity = cost_good['ConsumeParcelAmount'][0])

        wikitext_fortunegacha += template.render(fortune_tiers=fortune_tiers.values(), wiki_price = wiki_price)


    #CARDSHOP (4-card draw store) 
    wikitext_cardshop = ''
    if (args['event_season'], "CardShop") in data.event_content_seasons:
        template = env.get_template('events/template_cardshop.txt')

        cardshop_data = {}
        card_groups = data.event_content_card
        card_shop = data.event_content_card_shop[args['event_season']]
        card_tiers = sorted(set([x['Rarity'] for x in card_shop]), key=lambda x: ('SSR', 'SR', 'R', 'N').index(x))
        #print(f"CardShop card tiers are: {card_tiers}")

        #Expectation is that RefreshGroups are [1, 2, 3, 4], with 1~3 being complete duplicates and 4 being the SR+ rarity one.
        refresh_groups = sorted(set([x['RefreshGroup'] for x in card_shop]))
        #print(f"CardShop RefreshGroups are: {refresh_groups}")

        card_set = [x for x in card_shop if x['RefreshGroup'] == 1]
        for index, card in enumerate(card_set):
            #This mess is to deal with IconPath strings being lowercase while actual resouce names are capitalized
            card['image'] = '_'.join(word.upper() if word.lower() in ['sr', 'ssr'] else word.capitalize() for word in re.split(r'[_ ]', card_groups[card["CardGroupId"]]['IconPath'].rsplit('/', 1)[-1]))
            card['wiki_image_rowspan'] = 1

            card['LocalizeEtcId'] = card_groups[card["CardGroupId"]]['LocalizeEtcId']
            card['name'] = data.etc_localization[card['LocalizeEtcId']]['NameJp'].capitalize()
            card['wiki_items'] = []
            
            while card['CardGroupId'] == card_set[index-1]['CardGroupId']:
                card['image'] = None
                card_set[index-1]['wiki_image_rowspan'] += 1
                index -= 1
            

            for index,type in enumerate(card['RewardParcelType']):
                wiki_card_text = wiki_card(type, card['RewardParcelId'][index], quantity = card['RewardParcelAmount'][index], text = None, size = '60px', block = True )
                card['wiki_items'].append(wiki_card_text)


        for tier in card_tiers:
            cardshop_data[tier] = {'total_prob':0, 'total_ProbWeight1':0}
        for card in card_set:
            cardshop_data[card['Rarity']]['total_prob'] += card['Prob']
            cardshop_data[card['Rarity']]['total_ProbWeight1'] += card['ProbWeight1'] #unused?
            
                
        cost_good = data.goods[card_set[0]['CostGoodsId']]
        wiki_price = wiki_card('Item', cost_good['ConsumeParcelId'][0], quantity = cost_good['ConsumeParcelAmount'][0])


        wikitext_cardshop += template.render(card_set=card_set, cardshop_data=cardshop_data, card_tiers=card_tiers, wiki_price=wiki_price, shop_currency= shops['EventContent_2']['wiki_currency'] )




    season['EventContentOpenTime'] = season['EventContentOpenTime'].replace(' ','T')[:-3]+'+09'
    season['EventContentCloseTime'] = season['EventContentCloseTime'].replace(' ','T')[:-3]+'+09'
    season['EventContentOpenTime'] = season['EventContentOpenTime'].replace(' ','T')[:-3]+'+09'
    season['ExtensionTime'] = season['ExtensionTime'].replace(' ','T')[:-3]+'+09'
    template = env.get_template('events/template_event.txt')
    wikitext_event = template.render(season=season)

    template = env.get_template('events/template_event_bonus_characters.txt')
    wikitext_bonus_characters = template.render(bonus_characters=bonus_characters, bonus_values=bonus_values, event_currencies=event_currencies)

    template = env.get_template('events/template_event_missions.txt')
    wikitext_missions = template.render(season=season, missions=missions.values(), total_rewards=dict(sorted(total_rewards.items())).values())

    template = env.get_template('events/template_event_hexamaps.txt')
    wikitext_hexamaps = template.render(hexamaps=hexamaps.values())

    wikitext_milestones = ''
    if milestones:
        template = env.get_template('events/template_event_milestones.txt')
        wikitext_milestones = template.render(milestones=milestones, total_rewards=dict(sorted(total_milestone_rewards.items())).values())

    template = env.get_template('events/template_event_footer.txt')
    wikitext_footer = template.render(season=season)
    
    wikitext = wikitext_event + wikitext_bonus_characters + wikitext_stages + wikitext_hexamaps
    wikitext += wikitext_schedule_locations
    wikitext += '\n=Mission Details & Rewards=\n' + wikitext_missions + wikitext_shops + wikitext_boxgacha + wikitext_milestones + wikitext_cardshop+ wikitext_fortunegacha + wikitext_footer


    with open(os.path.join(args['outdir'], 'events' ,f"event_{season['EventContentId']}.txt"), 'w', encoding="utf8") as f:
        f.write(wikitext)



def init_data():
    global args, data, season_data, characters, items, furniture
    
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
   


def list_seasons():
    print ("============ JP seasons ============")
    print_seasons('jp')
    print ("============ GL seasons ============")
    print_seasons('gl')


def print_seasons(region: str):
    seasons = {}
    now = datetime.now() #does not account for timezone

    for evencontent in season_data[region].event_content_season.values():
        if evencontent['EventContentId'] not in seasons: 
            seasons[evencontent['EventContentId']] = {'EventContentOpenTime': evencontent['EventContentOpenTime'], 'EventContentCloseTime': evencontent['EventContentCloseTime']} 

    for season in seasons:
        note = ''
        opentime = datetime.strptime(seasons[season]['EventContentOpenTime'], "%Y-%m-%d %H:%M:%S")
        closetime = datetime.strptime(seasons[season]['EventContentCloseTime'], "%Y-%m-%d %H:%M:%S")

        if (opentime > now): note = 'future'
        elif (closetime > now): note = 'current'

        print (f"{str(season).rjust(6, ' ')}: {seasons[season]['EventContentOpenTime']} ~ {seasons[season]['EventContentCloseTime']} {note}")


def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('event_season',     metavar='event_season', nargs='?', default=None, help='Event season to export')
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')

    args = vars(parser.parse_args())
    print(args)

    try:
        init_data()

        if args['event_season'] is not None:
            args['event_season'] = int(args['event_season'])
            generate()
        else:
            list_seasons()

    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
