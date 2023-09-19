import re

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


def translate_package_name(text):
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
    text = re.sub('하급', 'novice', text)
    text = re.sub('하드', 'hard', text)

    text = re.sub('강화석', 'lesser', text)
    text = re.sub('일반', 'normal', text)
    text = re.sub('엘리그마', 'eligma', text)
    text = re.sub('강화석', 'enhancement stone', text)
    text = re.sub('마모된', 'worn-out', text)
    text = re.sub('활동', 'activity', text)
    text = re.sub('만드라고라', 'Mandragora', text)
    text = re.sub('비의서', 'secret tech notes', text)
    text = re.sub('조각', 'piece', text)
    
    return text


def wiki_card(type: str, id: int, data:dict|None, characters:dict|None, items:dict|None, furniture:dict|None, **params):
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

    if 'block' in params and params['block']:
        wikitext_params += f"|block"

    if name == None: print (f"Unknown {type} item {id}")
    return '{{'+card_type+'|'+(name != None and name.replace('"', '\\"') or f'{type}_{id}')+wikitext_params+'}}'
