from dataclasses import replace
import os
import re
import sys
import traceback
import json
import argparse
import collections


#import wikitextparser as wtp
import wiki

from data import load_data, load_scenario_data
from model import Character, Furniture
# import shared.functions
# from shared.CompareImages import compare_images

Interaction = collections.namedtuple(
    'Interaction',
    ['characters', 'filename', 'furniture']
)

data = None
scenario_data = None
args = {}
characters = {}
devname_map = None



      

def enforce_naming(local_path, file_wikiname, move_from, scope='image'):
    global args 

    #localpath = os.path.join(args['data_assets'], local_name)
    if not os.path.exists(local_path):
        print(f'ERROR - Local file not found: {local_path}')
        return False
    
    new_name_exists = wiki.page_exists(f"File:{file_wikiname}")
    if new_name_exists and not args['force_upload']:
        return True

    rename = '' 
    for old_name in move_from:
        old_name_exists = wiki.page_exists(f"File:{old_name}")
        if old_name_exists: 
            rename = old_name
            break
            
    
    if not new_name_exists and old_name_exists:
        print(f"Enforcing consistent {scope} file naming")
        wiki.move(f"File:{rename}", f"File:{file_wikiname}", summary = f"Enforcing consistent {scope} file naming")
    
    if not new_name_exists or args['force_upload']:
        print (f"!!! Uploading {local_path} as {file_wikiname}")
        wiki.upload(local_path, file_wikiname, f"{scope} image")
    


def generate():
    global data, scenario_data, args, characters
    global devname_map

    portrait_catalog =  [x for x in os.listdir(os.path.join(args['data_assets'], 'Assets/_MX/AddressableAsset/UIs/01_Common/01_Character')) if x.endswith('.png')]
    portrait_catalog_lc = [x.casefold() for x in portrait_catalog]

    scenario_character_portrait_by_sprite = {x['SpinePrefabName'].rsplit('/')[-1].replace('CharacterSpine_', '').lower():{'portrait': x['SmallPortrait'].rsplit('/')[-1]} for x in scenario_data.scenario_character_name.values()}

    for sprname, char in devname_map.items():
        npc_wikiname =  char['firstname'] + (char['variant'] and f" ({char['variant']})" or '')
        if args['character_wikiname'] is not None and npc_wikiname not in args['character_wikiname']:
            continue
        
        if 'portrait' in args['type']:
            file_sourcename = None
            file_wikiname = f"Portrait_{npc_wikiname.replace(' ', '_')}.png"
            sourcenames = {f"Student_Portrait_{sprname}.png", f"NPC_Portrait_{sprname}.png"}
            if sprname.lower() in scenario_character_portrait_by_sprite: sourcenames.add(f"{scenario_character_portrait_by_sprite[sprname.lower()]['portrait']}.png")

            for sourcename in sourcenames:
                if sourcename.casefold() in portrait_catalog_lc: file_sourcename = sourcename
            if not file_sourcename:
                print(f"No portrait found for {sprname}")
                continue

            move_from = [file_sourcename, f"Portrait_{sprname}.png"]
            enforce_naming(os.path.join(args['data_assets'], 'Assets/_MX/AddressableAsset/UIs/01_Common/01_Character', file_sourcename), file_wikiname, move_from, 'portrait')

        if 'portrait_small' in args['type']:
            file_sourcename = None
            file_wikiname = f"Portrait_{npc_wikiname.replace(' ', '_')}_Small.png"
            sourcenames = {f"Student_Portrait_{sprname}_Small.png", f"NPC_Portrait_{sprname}_Small.png"}

            for sourcename in sourcenames:
                if sourcename.casefold() in portrait_catalog_lc: file_sourcename = sourcename
            if not file_sourcename:
                print(f"No small portrait found for {sprname}")
                continue

            move_from = [file_sourcename, f"Portrait_{sprname}_Small.png"]
            enforce_naming(os.path.join(args['data_assets'], 'Assets/_MX/AddressableAsset/UIs/01_Common/01_Character', file_sourcename), file_wikiname, move_from, 'portrait')







    
def load_json_file(path: str, file: str):
    return json.loads(load_file(path, file))


def load_file(path: str, file: str):
    if os.path.exists(os.path.join(path, file)):
        with open(os.path.join(path, file), encoding="utf8") as f:
            data = f.read()
            f.close()
        return data
    else: return "{}"


def init_data():
    global args, data, scenario_data
    global characters
    global devname_map
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    scenario_data = load_scenario_data(args['data_primary'], args['data_secondary'], args['translation'])
    

    # season_data['jp'] = load_season_data(args['data_primary'])
    # season_data['gl'] = load_season_data(args['data_secondary']) 

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character['Id'], data)
            characters[character.id] = character
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()

    devname_map = load_json_file('./translation', 'devname_map.json') | load_json_file('./translation', 'devname_map_aux.json')
  



def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-data_assets',     metavar='DIR', required=True, help='Directory with art assets')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')
    
    #parser.add_argument('-character_id', nargs="*", type=int, metavar='ID', help='Id(s) of a characters to export')
    parser.add_argument('-character_wikiname', nargs="*", type=str, metavar='Wikiname', help='Name(s) of a characters to export')
    parser.add_argument('-type', nargs="*", type=str, required=True, metavar='Asset type', help='Type of images to upload')
    parser.add_argument('-force_upload',  action='store_true', help='Try reuploading images even if one already exists.')


    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    if args['character_wikiname']:
        args['character_wikiname'] = [name.replace('_', ' ').strip() for name in args['character_wikiname']]

    try:
        init_data()
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
