import re
import os
import json
from xxhash import xxh32_intdigest

def colorize(text:str):
    if len(text):
        return re.sub(
            r'\[c]\[([0-9A-Fa-f]{6})]([^\[]*)\[-]\[/c]',
            r'{{SkillValue|\2}}',
            text
        )
    else: return ''

def nl2br(text:str):
    if len(text): return text.replace('\n','<br>')
    else: return ''


def nl2p(text:str):
    if len(text): 
        return '<p>' + text.replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>'
    else: return ''


def environment_type(environment):
    return {
        'Street': 'Urban',
        'Outdoor': 'Outdoors',
        'Indoor': 'Indoors'
    }[environment]


def damage_type(type):
    return {
        type: type,
        'Explosion': 'Explosive',
        'Pierce': 'Penetration',
        #'Mystic': 'Mystic',
        #'Sonic': 'Sonic'
    }[type]


def armor_type(type):
    return {
        type: type,
        'LightArmor': 'Light',
        'HeavyArmor': 'Heavy',
        'Unarmed': 'Special',
        'ElasticArmor': 'Elastic'
    }[type]





def format_thousands(number):
    return "{:,}".format(number).replace(',',' ') #hate this, but seems to be the most practcal locale-independent way


def item_sort_order(item):
    sort_value = item['parcel_id']
    match item['parcel_type']:
        case 'Item':
            sort_value += 200000
        case 'Equipment':
            sort_value += 100000
        case 'Currency':
            sort_value += 3000000
        case 'Character':
            sort_value += 900000
        case 'Furniture':
            sort_value += 800000
        case _:
            pass
    
    
    match item['parcel_id']:
        case 23: #eligma
            sort_value += 2200000
        case 7 | 9 | 70 | 71: #raid coins
            sort_value += 2100000
        case _:
            pass

    #print(f"{item} {translate_package_name(item['parcel_name'])} is sort index {sort_value}")
    return sort_value


def replace_glossary(item:str = None):
    glossary = {
        'Field':'Outdoor',
        'Valkyrie Police School':'Valkyrie Police Academy',
        'Cherenka':'Cheryonka',
        '※ This item will disappear if not used by 14:00 on 8/19/2021.':'',
        'Total Assault': 'Raid',
        'Grand Assault': 'Elimination Raid',
        'Used for Exclusive Weapon Growth':'Used to enhance Unique Weapons',
        'Relationship Rank': 'Affection rank',
        'Exclusive Weapon': 'Unique Weapon',
        'Unique Item': 'Unique Gear',
        'Remedial Knights': 'Rescue Knights',
    }
    for search, replace in glossary.items():
        if item != None:
            item = re.sub(search, replace, item)
    return item



def translate_package_name(text):
    glossary = {
        '가챠' : 'Gacha',
        '제조' : 'Crafting',
        '튜토리얼' : 'Tutorial',
        '선별' : 'Selection',
        '레거시' : 'Legacy',
        '시즌용' : 'Seasonal',
        '더미' : 'Dummy',
        '학생모집(스즈미)' : 'Student recruitment (Suzumi)',
        '재료' : 'Ingredient',
        '스킬' : 'Skill',
        '책' : 'Book',
        '장비' : 'Equipment',
        '티어' : 'Tier',
        '박스' : 'Bundle',
        '묶음' : 'Recursive',
        '통합' : 'Integrated',
        '크레딧' : 'Credits',
        '오파츠' : 'OOparts',
        '아이템' : 'item',
        '그룹' : 'Group',
        '하급' : 'Novice',
        '중급' : 'Normal',
        '상급' : 'Advanced',
        '최상급' : 'Superior',
        '하드' : 'Hard',
        '공통' : 'Common',
        '강화석' : 'Lesser',
        '일반' : 'Normal',
        '엘리그마' : 'Eligma',
        '스킬북' : 'Skill book',
        'EX스킬' : 'EXskill',
        '강화석' : 'Enhancement stone',
        '마모된' : 'Worn-out',
        '활동' : 'Activity',
        '만드라고라' : 'Mandragora',
        '비의서' : 'Secret tech notes',
        '선물' : 'Gift',
        '타입' : 'Type',
        '조각' : 'Piece',
        '스테이지' : 'Stage',
        '스테이지' : 'For stage',
        '가챠그룹' : 'GachaGroup',
        '호드' : 'Horde',
        '비나' : 'Binah',
        '헤세드' : 'Chesed',
        '시로쿠로' : 'Shirokuro',

        '복각' : 'Rerun',
        '아비도스' : 'Abydos',
        '드랍' : 'Drop',

    }


    words = text.replace('_',' ').split()
    words = [glossary.get(x, x) for x in words]

    text = ' '.join(words)

    text = re.sub('번째', 'th', text)
    text = re.sub('게헨', 'Gehenna', text)
    text = re.sub('레드', 'RW', text)
    text = re.sub('산해', 'Shanhai', text)
    text = re.sub('백귀', 'Hyakki', text)
    text = re.sub('아비', 'Abydos', text)
    text = re.sub('트리', 'Trinity', text)
    text = re.sub('밀레', 'Millenium', text)
    text = re.sub('아리', 'Arius', text)
    text = re.sub('발키', 'Valk', text)
    
    return text


def wiki_card(type: str, id: int, data:dict|None, characters:dict|None, items:dict|None, furniture:dict|None, emblems:dict|None, **params):
    wikitext_params = ''

    match type:
        case 'Item':
            assert data is not None, "ItemCard card is called for, but no items dict has been "
            card_type = 'ItemCard'
            name = items[id].name_en
        case 'Equipment':
            assert data is not None, "Equipment ItemCard card is called for, but no data dict has been "
            card_type = 'ItemCard'
            name = data.etc_localization[data.equipment[id]['LocalizeEtcId']]['NameEn']
        case 'Currency':
            assert data is not None, "Currency ItemCard card is called for, but no data dict has been "
            card_type = 'ItemCard'
            name = data.etc_localization[data.currencies[id]['LocalizeEtcId']]['NameEn']
        case 'Character':
            assert characters is not None, "Character card is called for, but no characters dict has been provided"
            card_type = 'CharacterCard'
            name = characters[id].wiki_name
        case 'Furniture':
            assert furniture is not None, "Furniture card is called for, but no furniture dict has been provided"
            card_type = 'FurnitureCard'
            name = furniture[id].name_en
        case 'Emblem':
            assert emblems is not None, "Emblem card is called for, but no emblems dict has been provided"
            card_type = 'TitleCard'
            name = emblems[id].name
        case _:
            card_type = 'ItemCard'
            name = None
            print(f'Unrecognized item type {type}')
    
    if 'probability' in params and params['probability'] != None:
        wikitext_params += f"|probability={params['probability']:g}"

    if 'quantity' in params and params['quantity'] != None:
        wikitext_params += f"|quantity={params['quantity']}"

    if 'text' in params:
        text = params['text'] != None and params['text'] or ''
        wikitext_params += f"|text={text}"

    if 'size' in params:
        wikitext_params += f"|{params['size']}"

    if 'block' in params and params['block']:
        wikitext_params += f"|block"

    if name == None: print (f"Unknown {type} item {id}")
    return '{{'+card_type+'|'+(name != None and name.replace('"', '\\"') or f'{type}_{id}')+wikitext_params+'}}'


def hashkey(text:str)->int:
    return xxh32_intdigest(text)


def load_json_file(path: str, file: str):
    return json.loads(load_file(path, file))


def load_file(path: str, file: str):
    if os.path.exists(os.path.join(path, file)):
        with open(os.path.join(path, file), encoding="utf8") as f:
            data = f.read()
            f.close()
        return data
    else: return "{}"
