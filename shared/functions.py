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
    if len(text): return text.replace('\n\n','<br>').replace('\n','<br>')
    else: return ''


def nl2p(text:str):
    if len(text): 
        return '<p>' + text.replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>'
    else: return ''


def environment_type(environment):
    return {
        environment: environment,
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


def difficulty_shorthand(type):
    return {
        type: type,
        'Normal':   'N',
        'Hard':     'H',
        'VeryHard': 'VH',
        'Hardcore': 'HC',
        'Extreme':  'EXT',
        'Insane':   'INS',
        'Torment':  'TOR',
        'Lunatic':  'LUN'
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
        #'Field':'Outdoor',
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

            if items[id].icon == "Item_Icon_RecruitTicket_Normal_10" and items[id].expiration_datetime != "":
                #print(f'Replacing timed ticket item Id {id}, expiration {items[id].expiration_datetime} with permanent ticket')
                name = items[6999].name_en

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



def replace_units(text):
    
    #text = re.sub('1回', 'once', text)
    #text = re.sub('2回', 'twice', text)
    #text = re.sub('3回', 'three times', text)
    text = re.sub('回', '', text)
    text = re.sub('つ', '', text)
    text = re.sub('\]1秒\[', ']1 second[', text)
    text = re.sub('秒', ' seconds', text)
    text = re.sub('個', '', text)
    text = re.sub('発分', ' hits', text)
    return text


def replace_statnames(stat_list):
    list_out = []
    if type(stat_list) == str: stat_list = [stat_list] 
    
    for item in stat_list:
        item = re.sub('OppressionPower', 'CC Strength', item)
        item = re.sub('OppressionResist', 'CC Resistance', item)        
        
        item = re.sub('_Base', '', item)
        item = re.sub('Power', '', item)
        item = re.sub('Max', '', item)
        item = re.sub('Point', '', item)
        item = re.sub('Rate', '', item)
        item = re.sub('Normal', '', item)
        item = re.sub('Heal', 'Healing', item)
        item = re.sub('Speed', ' Speed', item)
        item = re.sub('Damage', ' Damage', item)

        list_out.append(item)     
    #return([re.sub('_Base', '', item) for item in stat_list])
    return (list_out)

def statcalc_replace_statname(stat_name):
    return {
            'AttackPower': 'attack',
            'DefensePower': 'defense',
            'HealPower': 'healing',
            'MaxHP': 'hp',

            'CriticalDamageRate': 'crit_damage',
            'CriticalPoint': 'crit_rate',
            'AccuracyPoint': 'accuracy',
            'DodgePoint': 'evasion',
            'OppressionPower': 'cc_str',
            '': 'cc_res',
            '': 'crit_res',
            '': 'critdamage_res',
            'HealEffectivenessRate': 'healing_inc',
            'StabilityPoint': 'stability',
            'NormalAttackSpeed': '',
            'BlockRate': '',
            'MoveSpeed': 'move_speed',
            'DefensePenetration': '',
            'MaxBulletCount': '',
            'ExtendBuffDuration':'',
            'ExtendDebuffDuration':'',
            'EnhanceExplosionRate':'',
            'EnhancePierceRate':'',
            'EnhanceMysticRate':'',
            'WeaponRange':'weapon_range'
        }[stat_name]


def format_ms_duration(ms:int):
    return f"{ms // 60000}:{(ms // 1000) % 60:02}"


def format_datetime (datetime:str):
    return f"{datetime.replace(' ','T')[:-3]}+09"


def deduplicate_dict_values(datatables):
    deduplicated_datatables = {}
    previous_key = None
    previous_value = None
    start_key = None

    for key, value in datatables.items():
        if previous_value is not None and value == previous_value:
            if start_key is None:
                start_key = previous_key
            merged_key = f"{start_key.split('~')[0]}~{key}"
            previous_key = merged_key
        else:
            if start_key is not None:
                deduplicated_datatables[previous_key] = previous_value
                start_key = None
            else:
                if previous_key is not None:
                    deduplicated_datatables[previous_key] = previous_value
            previous_key = key
        previous_value = value


    deduplicated_datatables[previous_key] = previous_value

    return deduplicated_datatables
