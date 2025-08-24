import os
import re
from jinja2 import Environment, FileSystemLoader
import copy

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

LOCALIZE_PLACEHOLDER = {'Jp':'Missing Jp localization','En':'Missing En localization'}


def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)


def colorize_flavor_text(text:str):
    if len(text):
        return re.sub(
            r'\[c]\[75b4c0]\[i]([^\[]*)\[/i]\[-]\[/c]',
            r'<p class="flavor-text">\1</p>',
            text
        )
    else: return ''


def colorize_values(text:str):
    if len(text):
        return re.sub(
            r'\[c]([^\[]*)\[/c]',
            r'{{SkillValueWrap|\1}}',
            text
        )
    else: return ''

#{param;DrawCardNum}
def format_param(text:str):
    if len(text):
        return re.sub(
            r'\{param;([^\[]*)\}',
            r'\1', #r'<span class="param">\1</span>',
            text
        )
    else: return ''

#{char;848029}
def format_char(text:str):
    global data, character_data

    if len(text):
        def replace_char(match):
            char_id = int(match.group(1))
            # Try to get the English name from localization using character_data
            try:
                char_name = [x for x in character_data if x['Id']==char_id][0]['Name']
                en_name = data.localization.get(char_name, LOCALIZE_PLACEHOLDER)['En']
                return f'{en_name}'
            except Exception:
                return f'{char_id}'

        return re.sub(
            r'\{char;([^\[]*)\}',
            replace_char,
            text
        )
    else:
        return ''
    

#{skill;8480219} 
def format_skill(text:str):
    global data, skill_data

    if len(text):
        def replace_char(match):
            skill_id = int(match.group(1))
            # Try to get the English name from localization using character_data
            try:
                skill_name = [x for x in skill_data if x['Id']==skill_id][0]['Name']
                en_name = data.localization.get(skill_name, LOCALIZE_PLACEHOLDER)['En']
                return f'{en_name}'
            except Exception:
                return f'{skill_id}'

        return re.sub(
            r'\{skill;([^\[]*)\}',
            replace_char,
            text
        )
    else:
        return ''


#{card;848220}
def format_card(text:str):
    global data, card_data

    if len(text):
        def replace_char(match):
            card_id = int(match.group(1))
            # Try to get the English name from localization using character_data
            try:
                card_name = [x for x in card_data if x['Id']==card_id][0]['Name']
                en_name = data.localization.get(card_name, LOCALIZE_PLACEHOLDER)['En']
                return f'{en_name}'
            except Exception:
                return f'{card_id}'

        return re.sub(
            r'\{card;([^\[]*)\}',
            replace_char,
            text
        )
    else:
        return ''
    

#{tag;Hyakkiyako}
def format_tag(text:str):
    if len(text):
        return re.sub(
            r'\{tag;([^\[]*)\}',
            r'{{SkillValueWrap|#\1}}',
            text
        )
    else: return ''


    

def format_tags(tags:list):
    return " ".join([f"#{x}" for x in tags])


def get_mode_dicerace(season_id: int, ext_data, ext_characters, ext_items, ext_furniture, ext_emblems, ext_missing_localization, ext_missing_code_localization, ext_missing_etc_localization):
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
    env.filters['colorize_values'] = colorize_values
    env.filters['flavor_text'] = colorize_flavor_text
    env.filters['format_tags'] = format_tags
    env.filters['format_param'] = format_param
    env.filters['format_char'] = format_char
    env.filters['format_tag'] = format_tag
    env.filters['format_skill'] = format_skill
    env.filters['format_card'] = format_card


    title = 'Dice Race'
    wikitext = {'title':f"\n=={title}==", 'intro':'', 'lap_rewards':'===Lap Completion Rewards===\n', }

    good = data.goods[data.event_content_dice_race[season_id]['DiceCostGoodsId']]
    dice_cost_wiki_card = wiki_card(good['ConsumeParcelType'][0], good['ConsumeParcelId'][0], quantity = good['ConsumeParcelAmount'][0])  

    nodes = data.event_content_dice_race_node[season_id]

    lap_reward_data = data.event_content_dice_race_total_reward[season_id] #.sort(key=lambda x: x['RequiredLapFinishCount'])
    total_lap_rewards = {}

    for lap_reward in lap_reward_data:
        lap_reward['parcels'] = []
        for i, parcel_id in enumerate(lap_reward['RewardParcelId']):
            parcel = RewardParcel(
                lap_reward['RewardParcelType'][i],
                parcel_id,
                lap_reward['RewardParcelAmount'][i],
                10000,
                None,
                wiki_card=wiki_card,
                data=data
            )
            lap_reward['parcels'].append(parcel)
            if parcel_id not in total_lap_rewards:
                total_lap_rewards[parcel_id] = copy.copy(parcel)
            else:
                total_lap_rewards[parcel_id].amount += parcel.amount


    template = env.get_template('template_dicerace_intro.txt')
    wikitext['intro'] += template.render(season_id=season_id, die_cost = dice_cost_wiki_card, event_info = data.event_content_dice_race[season_id], nodes=nodes)

    template = env.get_template('template_dicerace_lap_rewards.txt')
    wikitext['lap_rewards'] += template.render(lap_reward_data=lap_reward_data, total_rewards=total_lap_rewards)

            
    return '\n'.join(wikitext.values())
