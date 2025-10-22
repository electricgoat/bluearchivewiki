from dataclasses import replace
import os
import re
import sys
import traceback
#import json
import argparse

#from jinja2 import Environment, FileSystemLoader

import wikitextparser as wtp
import wiki

from data import load_data
from model import Character

args = {}




def generate():
    global args
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])


    for character in data.characters.values():
        if (args['character_id'] != None) and (character['Id'] != int(args['character_id'])):
            continue
        
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character['Id'], data)
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue
        
        print(f"\n=== {character.wiki_name} ===")
        
        #character collection portrait
        local_path = os.path.join(args['data_assets'] ,'Assets/_MX/AddressableAsset', f"{character.costume['CollectionTexturePath']}.png" )
        if (os.path.exists(local_path)):
            image_internal = local_path.rsplit('/',1)[-1]
            image_target = f"{character.wiki_name.replace(' ', '_')}.png"
            copy_wikinamed(local_path, image_target)
            enforce_naming(local_path, image_internal, image_target, 'character portrait')
        else:
            print(f"WARNING: Character {character.wiki_name} collection portrait not found at {local_path}")

        #character portrait
        local_path = os.path.join(args['data_assets'] ,'Assets/_MX/AddressableAsset', f"{character.costume['TextureDir']}.png" )
        if (os.path.exists(local_path)):
            image_internal = local_path.rsplit('/',1)[-1]
            image_target = f"Portrait_{character.wiki_name.replace(' ', '_')}.png"
            copy_wikinamed(local_path, image_target)
            enforce_naming(local_path, image_internal, image_target, 'character portrait', "[[Category:Student portraits]]")
        else:
            print(f"WARNING: Character {character.wiki_name} portrait not found at {local_path}")

        #character portrait small
        local_path = os.path.join(args['data_assets'] ,'Assets/_MX/AddressableAsset', f"{character.costume['TextureDir']}_Small.png")
        if (os.path.exists(local_path)):
            image_internal = local_path.rsplit('/',1)[-1]
            image_target = f"Portrait_{character.wiki_name.replace(' ', '_')}_Small.png"
            copy_wikinamed(local_path, image_target)
            enforce_naming(local_path, image_internal, image_target, 'character small portrait', "[[Category:Student portraits]]")
        else:
            print(f"WARNING: Character {character.wiki_name} small portrait not found at {local_path}")

        #Memorial lobby image
        local_path = os.path.join(args['data_assets'] ,'Assets/_MX/AddressableAsset/UIs/01_Common/08_Lobbyillust', f"{character.memory_lobby.image}.png")
        if (os.path.exists(local_path)):
            image_internal = f"{character.memory_lobby.image}.png"
            image_target = f"Lobbyillust_{character.wiki_name.replace(' ', '_')}.png"
            copy_wikinamed(local_path, image_target)
            enforce_naming(local_path, image_internal, image_target, 'character memorial lobby')
        else:
            print(f"WARNING: Character {character.wiki_name} memorial lobby image not found at {local_path}")

        #Memorial lobby image small
        local_path = os.path.join(args['data_assets'] ,'Assets/_MX/AddressableAsset/UIs/01_Common/08_Lobbyillust', f"{character.memory_lobby.image}_Small.png")
        if (os.path.exists(local_path)):
            image_internal = f"{character.memory_lobby.image}_Small.png"
            image_target = f"Lobbyillust_{character.wiki_name.replace(' ', '_')}_Small.png"
            copy_wikinamed(local_path, image_target)
            enforce_naming(local_path, image_internal, image_target, 'character memorial lobby small')
        else:
            print(f"WARNING: Character {character.wiki_name} memorial lobby small image not found at {local_path}")

        #Weapon
        local_path = os.path.join(args['data_assets'] ,f"Assets/_MX/AddressableAsset/UIs/01_Common/04_Weapon/Weapon_Icon_{character.weapon.image_path}.png")
        if (os.path.exists(local_path)):
            image_internal = f"Weapon_Icon_{character.weapon.image_path}.png"
            image_target = f"Weapon_Icon_{character.wiki_name.replace(' ', '_')}.png"
            copy_wikinamed(local_path, image_target)
            enforce_naming(local_path, image_internal, image_target, 'character unique weapon')
        else:
            print(f"WARNING: Character {character.wiki_name} unique weapon image not found at {local_path}")

        #Emblem portrait
        local_path = os.path.join(args['data_assets'] ,'Assets/_MX/AddressableAsset/UIs/01_Common/43_Emblem', f"Emblem_Icon_Favor_{character.dev_name}.png")
        if (os.path.exists(local_path)):
            image_internal = f"Emblem_Icon_Favor_{character.dev_name}.png"
            image_target = f"Emblem_Icon_Favor_{character.wiki_name.replace(' ', '_')}.png"
            copy_wikinamed(local_path, image_target)
            enforce_naming(local_path, image_internal, image_target, 'character emblem icon')
        else:
            print(f"WARNING: Character {character.wiki_name} emblem icon not found at {local_path}")



def copy_wikinamed(local_path, wikiname):
    global args
    target_path = os.path.join(args['data_assets'], 'wikinamed', wikiname )
    if not os.path.exists(target_path):
        os.makedirs(os.path.join(args['data_assets'], 'wikinamed'), exist_ok=True)
        os.link(local_path, target_path) #hardlinks
        

def enforce_naming(local_path, old_name, new_name, scope='image', text=''):
    global args 

    #localpath = os.path.join(args['data_assets'], local_name)
    if not os.path.exists(local_path):
        print(f'ERROR - Local file not found: {local_path}')
        return False
    
    old_name_exists = wiki.page_exists(f"File:{old_name}")
    new_name_exists = wiki.page_exists(f"File:{new_name}")
    if not new_name_exists and old_name_exists:
        print(f"Enforcing consistent {scope} file naming")
        wiki.move(f"File:{old_name}", f"File:{new_name}", summary = f"Enforcing consistent {scope} file naming")
    elif not new_name_exists or args['force_upload']:
        print (f"!!! Uploading {local_path} as {new_name}")
        wiki.upload(local_path, new_name, f"{scope} image", text)
        


def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-data_assets',     metavar='DIR', required=True, help='Directory with art assets')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2,   metavar=('LOGIN', 'PASSWORD'), required=True, help='Wiki (bot) login and password')
    parser.add_argument('-character_id',    metavar='ID', help='Id of a single character to export')
    parser.add_argument('-force_upload',  action='store_true', help='Try reuploading images even if one already exists.')

    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None


    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
