from dataclasses import replace
import os
import re
import sys
import traceback
#import json
import argparse

from jinja2 import Environment, FileSystemLoader

import wikitextparser as wtp
import wiki
import shared.functions

from data import load_data, load_season_data
from model import Item, Character
from classes.Stage import WeekDungeonStage
from classes.Furniture import Furniture, FurnitureGroup
from classes.Gacha import GachaGroup, GachaElement
from classes.RewardParcel import RewardParcel
from classes.Emblem import Emblem
from shared.MissingTranslations import MissingTranslations

missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_code_localization = MissingTranslations("translation/missing/LocalizeCodeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")

DUNGEON_TYPES = {
    "Blood": "Ruined Munitions Factory",
    "ChaserA": "Overpass",
    "ChaserB": "Desert Railroad",
    "ChaserC": "Classroom",
    "FindGift": "Slumpia Square",
}

args = None
data = None

characters = {}
items = {}
furniture = {}
emblems = {}

season_data = {'jp':None, 'gl':None}



def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)


def generate():
    global args, data, season_data, items
    
    week_dungeon_types = set()
    for weekday in data.week_dungeon_open_schedule.values():
        week_dungeon_types.update(weekday['Open'])
    print(sorted(week_dungeon_types))

    
    stages = {}
    for dungeon_type in week_dungeon_types:
        stages[dungeon_type] = []

        for stage in data.week_dungeon.values():
            if stage['WeekDungeonType'] != dungeon_type:
                continue
            stage = WeekDungeonStage.from_data(stage['StageId'], data, wiki_card=wiki_card)
            stages[dungeon_type].append(stage)



    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    template = env.get_template('templates/template_week_dungeon.txt')

    for dungeon_type in week_dungeon_types:
        wikitext = template.render(stages=stages[dungeon_type], dungeon_type=DUNGEON_TYPES.get(dungeon_type, dungeon_type) )
        with open(os.path.join(args['outdir'], 'week_dungeon', f'{dungeon_type}.txt'), 'w', encoding="utf8") as f:
            f.write(wikitext)
            f.close()




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



def main():
    global args
    global missing_localization, missing_code_localization, missing_etc_localization

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')


    args = vars(parser.parse_args())
    print(args)


    try:
        init_data()
        generate()

        missing_localization.write()
        missing_code_localization.write()
        missing_etc_localization.write()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
