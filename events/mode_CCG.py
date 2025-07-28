import os
import re
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

LOCALIZE_PLACEHOLDER = {'Jp':'Missing Jp localization','En':'Missing En localization'}

def parse_cards(season_id):
    global data
    global missing_localization, missing_etc_localization
    global character_data, card_data, skill_data

    character_data = data.minigame_ccg_character.values()
    for card in character_data:
        if card['Name'] in data.localization: 
            card['Localization'] = data.localization[card['Name']]
            if 'En' not in data.localization[card['Name']]: missing_localization.add_entry(data.localization[card['Name']])
    
    card_data = data.minigame_ccg_card.values()
    for card in card_data:
        if card['Name'] in data.localization: 
            card['Localization'] = data.localization[card['Name']]
            if 'En' not in data.localization[card['Name']]: missing_localization.add_entry(data.localization[card['Name']])

    skill_data = data.minigame_ccg_skill.values()
    for skill in skill_data:

        skill['LocalizeName'] = data.localization.get(skill['Name'], None)
        if 'En' not in data.localization[skill['Name']]: missing_localization.add_entry(data.localization[skill['Name']])

        skill['LocalizeDescription'] = data.localization.get(skill['Description'], None)
        if skill['Description'] != 0 and skill['Description'] in data.localization and 'En' not in data.localization[skill['Description']]: 
            missing_localization.add_entry(data.localization[skill['Description']])

                
    return character_data, card_data, skill_data



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


def get_mode_ccg(season_id: int, ext_data, ext_characters, ext_items, ext_furniture, ext_emblems, ext_missing_localization, ext_missing_code_localization, ext_missing_etc_localization):
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


    title = 'Collectible Card Game'
    wikitext = {'title':f"=={title}==", 'intro':'', 'strikers':'===Striker Characters===\n', 'specials':'===Special Characters===\n', 'enemy_strikers':'===Enemy Striker Characters===\n', 'enemy_specials':'===Enemy Special Characters===\n', 'cards':'===Playable Cards===\n'}

    ICON_MAP = {
        'Equipment' : 'Gear',
        'Spell' : 'Event',
        'Zone' : 'Location',
    }
    


    character_data, card_data, skill_data = parse_cards(season_id)


    template = env.get_template('template_ccg_characters.txt')
    wikitext['strikers'] += template.render(cards=[x for x in character_data if x['Type'] == 'Striker' and not x['ImagePath'].rsplit('/',1)[-1].startswith('Enemy')], skills={x['Id']:x for x in skill_data}, icon_map=ICON_MAP, localization = data.localization, localize_placeholder = LOCALIZE_PLACEHOLDER)

    wikitext['specials'] += template.render(cards=[x for x in character_data if x['Type'] != 'Striker' and not x['ImagePath'].rsplit('/',1)[-1].startswith('Enemy')], skills={x['Id']:x for x in skill_data}, icon_map=ICON_MAP, localization = data.localization, localize_placeholder = LOCALIZE_PLACEHOLDER)

    wikitext['enemy_strikers'] += template.render(cards=[x for x in character_data if x['Type'] == 'Striker' and x['ImagePath'].rsplit('/',1)[-1].startswith('Enemy')], skills={x['Id']:x for x in skill_data}, icon_map=ICON_MAP, localization = data.localization, localize_placeholder = LOCALIZE_PLACEHOLDER)

    wikitext['enemy_specials'] += template.render(cards=[x for x in character_data if x['Type'] != 'Striker' and x['ImagePath'].rsplit('/',1)[-1].startswith('Enemy')], skills={x['Id']:x for x in skill_data}, icon_map=ICON_MAP, localization = data.localization, localize_placeholder = LOCALIZE_PLACEHOLDER)


    template = env.get_template('template_ccg_cards.txt')
    wikitext['cards'] += template.render(cards=card_data, skills={x['Id']:x for x in skill_data}, icon_map=ICON_MAP, localization = data.localization, localize_placeholder = LOCALIZE_PLACEHOLDER)

    



            
    return '\n'.join(wikitext.values())
