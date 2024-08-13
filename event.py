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
from model import Item, Character
#from classes.model_stages import EventStage
from classes.model_event_schedule import EventScheduleLocation
from classes.Stage import EventStage
from classes.Furniture import Furniture, FurnitureGroup
from classes.Emblem import Emblem
from events.mission_desc import mission_desc
from events.mode_Field import *
from events.mode_Treasure import get_mode_treasure
from events.mode_DreamMaker import get_mode_dreammaker
from events.mode_FortuneGachaShop import get_mode_fortunegachashop
from events.mode_Defense import get_mode_defense
from shared.functions import hashkey
from shared.MissingTranslations import MissingTranslations

missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_code_localization = MissingTranslations("translation/missing/LocalizeCodeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")


args = None
data = None
season_data = {'jp':None, 'gl':None}

characters = {}
items = {}
furniture = {}
emblems = {}

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


def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)


def parse_stages(season_id):
    global args, data, hexamaps
    global missing_localization, missing_etc_localization
    stages = []

    for stage in data.event_content_stages.values():
        if stage['EventContentId'] != season_id:
            continue
        stage = EventStage.from_data(stage['Id'], data, wiki_card=wiki_card, missing_localization=missing_localization, missing_etc_localization=missing_etc_localization)
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
    #
    #Deprecated
    #Use shared.functions wiki_card
    #
    card_type = reward.type != 'Character' and 'ItemCard' or 'CharacterCard'

    if Card.PROBABILITY in params: probability = f'|probability={reward.prob:g}'
    else: probability = ''

    if Card.QUANTITY_AUTO in params: quantity = reward.amount>1 and '|quantity='+str(reward.amount) or ''
    elif Card.QUANTITY in params: quantity = '|quantity='+str(reward.amount)
    else: quantity = ''

    return '{{'+card_type+'|'+(reward.name != None and reward.name or 'Unknown')+quantity+probability+'|text=|60px|block}}'



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
    global data, characters, items, furniture, emblems

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
    elif mission['MissionRewardParcelType'][index] == 'Emblem':
        mission['RewardItemNames'].append(emblems[mission['MissionRewardParcelId'][index]].name)
        mission['RewardItemCards'].append('{{TitleCard|'+emblems[mission['MissionRewardParcelId'][index]].name+'}}')
    else:
        mission['RewardItemNames'].append("UNKNOWN REWARD TYPE")
        print (f"Unknown reward parcel type {mission['MissionRewardParcelType'][index]}")

    return






def total_reward_card(item):
    global data, character, items, furniture, emblems
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
    elif item['Type'] == 'Emblem':
        item['Name'] = (emblems[item['Id']].name)
        item['Card'] = ('{{TitleCard|'+emblems[item['Id']].name+'|'+(icon_size[0] if item['IsCompletionReward'] else icon_size[1])+'|block|text=}}')
    else:
        item['Name'] = ("UNKNOWN REWARD TYPE")
        print (f"Unknown reward parcel type {item['Type']}")

    return




def generate():
    global args, data, stages, missions, season_data
    global characters, items, furniture
    global total_rewards, total_milestone_rewards
    global missing_localization, missing_code_localization

    season = None
    season_gl = None

    for eventmode in ["Stage", "MiniEvent" ,"MinigameRhythmEvent"]:
        if (args['event_season'], eventmode) in season_data['jp'].event_content_season:
            season_jp = season_data['jp'].event_content_season[(args['event_season'], eventmode)]
            season = season_jp#TODO work directly with season_jp or _gl

            break
    if season is None: exit(f"JP season {args['event_season']} data not found. Is this a new event type?")
    
    for eventmode in ["Stage", "MiniEvent" ,"MinigameRhythmEvent"]:
        if (args['event_season'], eventmode) in season_data['gl'].event_content_season:
            season_gl = season_data['gl'].event_content_season[(args['event_season'], eventmode)]
            break
    if season_gl is None: print(f"GL season {args['event_season']} data not found. Is this event not on global yet?")


    localize_key = hashkey(season['Name'])
    if localize_key in data.localization: 
        season['LocalizeName'] = data.localization[localize_key]
        if 'En' not in data.localization[localize_key]: missing_localization.add_entry(data.localization[localize_key])
    else: 
        print(f"Missing localize key {localize_key}")
        if localize_key == 2954736197: season['LocalizeName'] = data.localization[1435341545] #mini event fix, TODO figure out how its key is derived
        elif localize_key == 1202895593: season['LocalizeName'] = data.localization[2677397330] #1st collab event

    localize_title_key = hashkey(f"Event_Title_{season['OriginalEventContentId']}")
    if localize_title_key in data.localization: 
        season['LocalizeTitle'] = data.localization[localize_title_key]
        if 'En' not in data.localization[localize_title_key]: missing_localization.add_entry(data.localization[localize_title_key])
    else: 
        print(f"Missing localize_title key {localize_title_key}")
        if localize_title_key == 4164572829: season['LocalizeTitle'] = data.localization[1011309388] #mini event fix, TODO figure out how its key is derived   

    if season['LocalizeName'].get('En') != season['LocalizeTitle'].get('En'): print(f"Event Name and Title are mismatched, check which is more complete:\n Name :{season['LocalizeName'].get('En')}\n Title:{season['LocalizeTitle'].get('En')}")

    localize_description_key =  hashkey(f"Event_Description_{season['OriginalEventContentId']}")
    if localize_description_key in data.localization: 
        season['LocalizeDescription'] = data.localization[localize_description_key]
        if 'En' not in data.localization[localize_description_key]: missing_localization.add_entry(data.localization[localize_description_key])
    else: 
        season['LocalizeDescription'] = None
        print(f"Missing localize_description key {localize_description_key}")


    content_types = [x['EventContentType'] for x in data.event_content_seasons.values() if x['EventContentId'] == args['event_season']]
    print(f"Event {args['event_season']} content types: {content_types}")

    if season['MainEventId'] != 0:
        print(f"This is a sub-event, using bonus character data from MainEventId {season['MainEventId']}")
        bc = data.event_content_character_bonus.get(season['MainEventId'], [])
    elif season['EventContentId'] in data.event_content_character_bonus:
        bc = data.event_content_character_bonus.get(season['EventContentId'], [])
    else:
        print('Warning - no bonus character data found!')
        bc = []
    
    bonus_characters = {x: [] for x in ['EventPoint', 'EventToken1', 'EventToken2', 'EventToken3', 'EventToken4']}
    for item in bonus_characters:  
        for character in bc:
            if item in character['EventContentItemType']:
                try:
                    bonus_characters[item].append({'CharacterId':character['CharacterId'], 'Name':characters[character['CharacterId']].wiki_name, 'Class':characters[character['CharacterId']].combat_class, 'BonusPercentage':int(character['BonusPercentage'][character['EventContentItemType'].index(item)]/100)})
                except KeyError as err:
                    bonus_characters[item].append({'CharacterId':character['CharacterId'], 'Name':str(character['CharacterId']), 'Class':'Striker', 'BonusPercentage':int(character['BonusPercentage'][character['EventContentItemType'].index(item)]/100)})
    #print (bonus_characters)

    bonus_values = {x: [] for x in ['EventPoint', 'EventToken1', 'EventToken2', 'EventToken3', 'EventToken4']}
    for item in bonus_characters:
        for character in bonus_characters[item]:
            bonus_values[item].append(character['BonusPercentage'])
        bonus_values[item] = list(set(bonus_values[item]))
        bonus_values[item].sort(reverse=True)
    #print(len(bonus_values['EventToken2']))


    if season['MainEventId'] != 0:
        print(f"This is a sub-event, using currencies data from MainEventId {season['MainEventId']}")
        cy = data.event_content_currency.get(season['MainEventId'], [])
    elif season['EventContentId'] in data.event_content_currency:
        cy = data.event_content_currency.get(season['EventContentId'], [])
    else:
        print('Warning - no event currencies data found!')
        cy = []

    event_currencies = {x: [] for x in ['EventPoint', 'EventToken1', 'EventToken2', 'EventToken3', 'EventToken4']}
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

    # env.filters['damage_type'] = shared.functions.damage_type
    # env.filters['armor_type'] = shared.functions.armor_type
    # env.filters['thousands'] = shared.functions.format_thousands
    env.filters['nl2br'] = shared.functions.nl2br
    # env.filters['nl2p'] = shared.functions.nl2p
    env.filters['replace_glossary'] = shared.functions.replace_glossary
   
    
    #STAGES
    wikitext_stages = ''

    if (args['event_season'], "Stage") in data.event_content_seasons:
        difficulty_names = {'Normal':'Story','Hard':'Quest','VeryHard':'Challenge', 'VeryHard_Ex': 'Extra Challenge'}
        stage_reward_types = {x: [] for x in difficulty_names.keys()}

        for stage in stages:
            for reward_tag in stage.rewards.keys():
                if reward_tag not in stage_reward_types[stage.difficulty] and len([x.wikitext_items() for x in stage.rewards[reward_tag] if len(x.wikitext_items())])>0:
                    stage_reward_types[stage.difficulty].append(reward_tag)
    
        template = env.get_template('events/template_event_stages.txt')
        for difficulty in stage_reward_types:
            stages_filtered = [x for x in stages if x.difficulty == difficulty]
            if len(stages_filtered): wikitext_stages += template.render(stage_type=difficulty_names[difficulty], stages=stages_filtered, reward_types=stage_reward_types[difficulty], rewardcols = len(stage_reward_types[difficulty]), Card=Card)


    #FIELD
    wikitext_field = ''
    if (args['event_season'], "Field") in data.event_content_seasons:
        wikitext_field = "=Field Mission=\n" + get_mode_field(args['event_season'], data, characters, items, furniture, emblems, missing_localization, missing_code_localization)

    #TREASURE
    wikitext_treasure = ''
    if (args['event_season'], "Treasure") in data.event_content_seasons:
        wikitext_treasure = get_mode_treasure(args['event_season'], data, characters, items, furniture, emblems, missing_localization, missing_code_localization)

    #DREAMMAKER
    wikitext_dreammaker = ''
    if (args['event_season'], "MinigameDreamMaker") in data.event_content_seasons:
        wikitext_dreammaker = get_mode_dreammaker(args['event_season'], data, characters, items, furniture, emblems, missing_localization, missing_code_localization, missing_etc_localization)

    #TOWER DEFENSE
    wikitext_defense = ''
    if (args['event_season'], "MiniGameDefense") in data.event_content_seasons:
        wikitext_defense = get_mode_defense(args['event_season'], data, characters, items, furniture, emblems, missing_localization, missing_code_localization, missing_etc_localization)


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
            if shop['CostParcelType'][0] == 'Item':
                shop['wiki_currency_name'] = items[shop['CostParcelId'][0]].name_en
            elif shop['CostParcelType'][0] == 'Currency':
                shop['wiki_currency_name'] = data.etc_localization[data.currencies[shop['CostParcelId'][0]]['LocalizeEtcId']]['NameEn']
            else:
                print(f"Unknown shop currency type for {shop}")

            shop['wiki_currency'] = f"{{{{ItemCard|{shop['wiki_currency_name']}}}}}" 
            shop['wiki_title'] = f"{{{{ItemCard|{shop['wiki_currency_name']}|48px}}}}"
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
        wikitext_fortunegacha = get_mode_fortunegachashop(args['event_season'], data, characters, items, furniture, emblems, missing_localization, missing_code_localization)


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


    template = env.get_template('events/template_event_header.txt')
    wikitext_header = template.render(season=season)

    season_jp['EventContentOpenTime'] = season_jp['EventContentOpenTime'].replace(' ','T')[:-3]+'+09'
    season_jp['EventContentCloseTime'] = season_jp['EventContentCloseTime'].replace(' ','T')[:-3]+'+09'
    season_jp['EventContentOpenTime'] = season_jp['EventContentOpenTime'].replace(' ','T')[:-3]+'+09'
    season_jp['ExtensionTime'] = season_jp['ExtensionTime'].replace(' ','T')[:-3]+'+09'
    season_jp['LocalizeName'] = season['LocalizeName']
    season_jp['LocalizeTitle'] = season['LocalizeTitle']
    season_jp['LocalizeDescription'] = season['LocalizeDescription']
    template = env.get_template('events/template_event_dates.txt')
    wikitext_event_dates = '\n==Schedule==\n' + template.render(title='Japanese Version', server='JP', season=season_jp)

    if season_gl is not None:
        season_gl['EventContentOpenTime'] = season_gl['EventContentOpenTime'].replace(' ','T')[:-3]+'+09'
        season_gl['EventContentCloseTime'] = season_gl['EventContentCloseTime'].replace(' ','T')[:-3]+'+09'
        season_gl['EventContentOpenTime'] = season_gl['EventContentOpenTime'].replace(' ','T')[:-3]+'+09'
        season_gl['ExtensionTime'] = season_gl['ExtensionTime'].replace(' ','T')[:-3]+'+09'
        season_gl['LocalizeName'] = season['LocalizeName']
        season_gl['LocalizeTitle'] = season['LocalizeTitle']
        season_gl['LocalizeDescription'] = season['LocalizeDescription']
        #template = env.get_template('events/template_event.txt')
        wikitext_event_dates += template.render(title='Global Version', server='GL', season=season_gl)



    template = env.get_template('events/template_event_bonus_characters.txt')
    wikitext_bonus_characters = '==Details==\n' + template.render(bonus_characters=bonus_characters, bonus_values=bonus_values, event_currencies=event_currencies)

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
    
    wikitext = wikitext_header + wikitext_event_dates + wikitext_bonus_characters + wikitext_stages + wikitext_hexamaps
    wikitext += wikitext_schedule_locations
    wikitext += '\n=Mission Details & Rewards=\n' + wikitext_missions + wikitext_shops + wikitext_boxgacha + wikitext_milestones + wikitext_cardshop+ wikitext_fortunegacha + wikitext_field + wikitext_treasure + wikitext_dreammaker + wikitext_defense + wikitext_footer


    with open(os.path.join(args['outdir'], 'events' ,f"event_{season['EventContentId']}.txt"), 'w', encoding="utf8") as f:
        f.write(wikitext)



def init_data():
    global args, data, season_data, characters, items, furniture, emblems
    
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
            print(f'Failed to parse for furniture {item}: {err}')
            traceback.print_exc()
            continue

    for emblem_id in data.emblem:
        try:
            emblem = Emblem.from_data(emblem_id, data, characters, missing_etc_localization, missing_localization)
            emblems[emblem.id] = emblem
        except Exception as err:
            print(f'Failed to parse emblem {emblem_id}: {err}')
            traceback.print_exc()

   


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
            event_name = ''
            localize_key = hashkey(evencontent['Name'])
            if localize_key in data.localization: 
                event_name = 'En' in data.localization[localize_key] and data.localization[localize_key]['En'] or data.localization[localize_key]['Jp']

            seasons[evencontent['EventContentId']] = {'Name': event_name, 'EventContentOpenTime': evencontent['EventContentOpenTime'], 'EventContentCloseTime': evencontent['EventContentCloseTime']} 
            #print (data.localize_code[hashkey(evencontent['Name'])])

    for season in seasons:
        note = ''
        opentime = datetime.strptime(seasons[season]['EventContentOpenTime'], "%Y-%m-%d %H:%M:%S")
        closetime = datetime.strptime(seasons[season]['EventContentCloseTime'], "%Y-%m-%d %H:%M:%S")

        if (opentime > now): note = 'future'
        elif (closetime > now): note = 'current'

        print (f"{str(season).rjust(6, ' ')}: {seasons[season]['EventContentOpenTime']} ~ {seasons[season]['EventContentCloseTime']} {note.ljust(8)} {seasons[season]['Name']}")


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

        missing_localization.write()
        missing_code_localization.write()
        missing_etc_localization.write()

    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
