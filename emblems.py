from dataclasses import replace
import os
import re
import sys
import traceback
#import json
import argparse
#import collections
from jinja2 import Environment, FileSystemLoader


#import wikitextparser as wtp
import wiki

from data import load_data
from model import Character, Item, Furniture
from classes.Emblem import Emblem
import shared.functions
from shared.MissingTranslations import MissingTranslations

missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")

data = None
args = None
characters = {}
items = {}
emblems = {}



def generate():
    global data, args, characters, items, emblems


    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    # env.globals['len'] = len
    # env.filters['environment_type'] = shared.functions.environment_type
    # env.filters['damage_type'] = shared.functions.damage_type
    # env.filters['armor_type'] = shared.functions.armor_type
    # env.filters['thousands'] = shared.functions.format_thousands
    # env.filters['nl2br'] = shared.functions.nl2br
    # env.filters['nl2p'] = shared.functions.nl2p
    template = env.get_template('./templates/template_emblem.txt')

    existing_files = []
    existing_names = []

    for emblem in emblems.values():
        if emblem.category == 'Potential':
            continue


        wikitext = template.render(emblem=emblem)
        
        name = emblem.name
        if emblem.check_type == 'Favor': 
            name = f"{emblem.name}_({emblem.check_value})"

        if emblem.category == 'Boss': 
            name = f"{emblem.name}_({bossdiff(emblem.rarity)})"

        if emblem.category == 'MultiFloorRaid': 
            name = f"{emblem.name}_({emblem._rarity})"


        if name in existing_names: print(f"WARNING Filename {name} is used more than once")
        existing_names.append(name)

        with open(os.path.join(args['outdir'], f"{name}.txt"), 'w', encoding="utf8") as f:            
            f.write(wikitext)


        if args['wiki'] is not None:
            upload_asset(emblem.icon_path, emblem.icon, existing_files)
            upload_asset(emblem.emblem_icon_path, emblem.emblem_icon, existing_files)
            upload_asset(emblem.emblem_iconbg_path, emblem.emblem_iconbg, existing_files)
            upload_asset(emblem.emblem_bg_path, emblem.emblem_bg, existing_files)

            if not wiki.page_exists(f"Titles/{name}", wikitext):
                print(f'Publishing {f"Titles/{name}"}')
                wiki.publish(f"Titles/{name}", wikitext, f'Title entry')
            

def bossdiff(id):
    return {
        id:'?',
        '0': 'Hard',
        '1': 'Hardcore',
        '2': 'Extreme',
        '3': 'Insane',
    }[id]


def upload_asset(local_path, wiki_name, existing_files):
    global args
    assert(wiki is not None)

    if local_path == '': return False
    if wiki_name == '': return False
    if wiki_name in existing_files: return False

    #print(f"Uploading {local_path} to {wiki_name}")

    full_path = os.path.join(args['assets_dir'], 'Assets', '_MX', 'AddressableAsset', f"{local_path}.png")
    if not os.path.exists(full_path): 
        #print(f"File not found: {full_path}")
        return False
    
    if wiki.page_exists(f"File:{wiki_name}"):
        existing_files.append(wiki_name)
        return False
    
    wiki.upload(os.path.join(args['assets_dir'], 'Assets', '_MX', 'AddressableAsset', f"{local_path}.png"), f"File:{wiki_name}", 'Emblem art asset upload')
    existing_files.append(wiki_name)
    return True


def init_data():
    global args, data, season_data, characters, items, emblems
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    # season_data['jp'] = load_season_data(args['data_primary'])
    # season_data['gl'] = load_season_data(args['data_secondary']) 

    for item in data.items.values():
        try:
            item = Item.from_data(item['Id'], data)
            items[item.id] = item
        except Exception as err:
            print(f'Failed to parse for item {item}: {err}')
            traceback.print_exc()
            continue


    for chardata in data.characters.values():
        if not chardata['IsPlayableCharacter'] or chardata['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(chardata['Id'], data)
            characters[character.id] = character
        except Exception as err:
            print(f'Failed to parse for DevName {chardata["DevName"]}: {err}')
            traceback.print_exc()

        # if args['character_id'] is not None and character['Id'] not in args['character_id']:
        #     continue
    
    
    for emblem_id in data.emblem:
        try:
            emblem = Emblem.from_data(emblem_id, data, characters, missing_etc_localization, missing_localization)
            emblems[emblem.id] = emblem
        except Exception as err:
            print(f'Failed to parse emblem {emblem_id}: {err}')
            traceback.print_exc()




def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-assets_dir',     metavar='DIR', default='C:/Games/datamine/blue_archive/work_240327/', help='Directory with exported assets')
    parser.add_argument('-outdir',          metavar='DIR', default='./out/emblems', help='Output directory')
    
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')
    parser.add_argument('-wiki_section',  metavar='SECTION NAME', help='Name of a page section to be updated')
    
    #parser.add_argument('-character_id', nargs="*", type=int, metavar='ID', help='Id(s) of a characters to export')
    #parser.add_argument('-character_wikiname', nargs="*", type=str, metavar='Wikiname', help='Name(s) of a characters to export')


    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None


    try:
        init_data()
        generate()
    except:
        parser.print_help()
        traceback.print_exc()

    missing_localization.write()
    missing_etc_localization.write()


if __name__ == '__main__':
    main()
