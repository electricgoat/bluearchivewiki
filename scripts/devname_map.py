from dataclasses import replace
import os
import re
import sys
import traceback
import json
import argparse



from data import load_data
from model import Character
import shared.functions

args = None

map = {}

def generate():
    global args
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    
    for chardata in data.characters.values():
        # if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
        #     continue

        if data.costumes[chardata['CostumeGroupId']]['SpineResourceName'] == '':
            continue

        try:
            character = Character.from_data(chardata['Id'], data)
            map[character.dev_name.replace('_default','')] = {'firstname': character.personal_name_en, 'lastname': character.family_name_en, 'variant': character.variant}

        except Exception as err:
            print(f'Failed to parse for DevName {chardata["DevName"]}: {err}')
            continue

 

    with open('./translation/devname_map.json', 'w', encoding="utf8") as f:
        f.write(json.dumps(map, sort_keys=False, indent=4))
        f.close()
    
        


def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')

    args = vars(parser.parse_args())
    print(args)

    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
