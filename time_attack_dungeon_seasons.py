import collections
import os
import re
import traceback
import argparse
from datetime import datetime

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data
# from model import Item, Character
# from classes.Furniture import Furniture
# from classes.Emblem import Emblem

import shared.functions
from shared.MissingTranslations import MissingTranslations

SEASON_PAGE = {
    'jp': 'Events/Joint Firing Drill',
    'gl': 'Events/Joint Firing Drill (Global)',
}

SEASON_IGNORE = {
    'jp' : [1,2,3],
    'gl' : [],
}


args = None

data = None
characters = {}
items = {}
furniture = {}
emblems = {}

season_data = {'jp':None, 'gl':None}
missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_skill_localization = MissingTranslations("translation/missing/LocalizeSkillExcelTable.json")
missing_code_localization = MissingTranslations("translation/missing/LocalizeCodeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")


def dungeon_type_name(type):
    return {
        type: type,
        'Shooting':     'Shooting',
        'Defense':      'Defense',
        'Destruction':  'Assault',
        'Escort':       'Escort',
    }[type]


def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)



def print_season(season, dungeon, note: str = ''):
    now = datetime.now() #does not account for timezone

    opentime = datetime.strptime(season['StartDate'], "%Y-%m-%d %H:%M:%S")
    closetime = datetime.strptime(season['EndDate'], "%Y-%m-%d %H:%M:%S")

    if (opentime > now): note += 'future'
    elif (closetime > now): note += 'current'

    print (f"{str(season['Id']).rjust(3, ' ')}: {season['StartDate']} ~ {season['EndDate']} {dungeon_type_name(dungeon['TimeAttackDungeonType']).ljust(12, ' ')} {note}")


def generate():
    global args, data, season_data
    global missing_code_localization

    # boss_groups = ['OpenRaidBossGroup']
    # boss_data = {}

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['ms_duration'] = shared.functions.format_ms_duration
    env.filters['colorize'] = shared.functions.colorize
    env.filters['nl2br'] = shared.functions.nl2br
    

    geas_localize_etc_ids = [id 
                             for x in data.time_attack_dungeon_geas.values() 
                             for id in x['GeasLocalizeEtcKey']
                             ]
    for id in list(set(geas_localize_etc_ids)):
        if id not in data.etc_localization:
            print(f"Missing etc_localization for geas {id}")
        elif data.etc_localization[id].get('NameEn', "") == "":
            missing_etc_localization.add_entry(data.etc_localization[id])


    for region in ['jp', 'gl']:
        last_season_type = None
        wikitext_seasons = ''

        print (f"============ {region.upper()} TimeAttackDungeon ============")
        for season in season_data[region].time_attack_dungeon_season:
            season['ignore'] = False
            id = season['Id']
            dungeon = data.time_attack_dungeon[season['DungeonId']] 
            geas = [data.time_attack_dungeon_geas[x] for x in season['DifficultyGeas']]

            
            if season['Id'] in SEASON_IGNORE[region]:
                #print(f"Flagged to ignore {region} season {season['Id']}")
                season['ignore'] = True
                #continue

            if ((datetime.strptime(season['StartDate'], "%Y-%m-%d %H:%M:%S") - datetime.now()).days > 28):
                print(f"TimeAttackDungeon {region} Id {season['Id']} ({dungeon['TimeAttackDungeonType']}) is too far in the future and will be ignored")
                season['ignore'] = True
                #continue

            if (last_season_type == dungeon['TimeAttackDungeonType'] and (datetime.strptime(season['StartDate'], "%Y-%m-%d %H:%M:%S") > datetime.now())):
                print(f"TimeAttackDungeon {region} Id {season['Id']} ({dungeon['TimeAttackDungeonType']}) is a duplicate of previous entry and will be ignored")
                season['ignore'] = True
                #continue

            print_season(season, dungeon, note = season['ignore'] and 'ignored ' or '')

            last_season_type = dungeon['TimeAttackDungeonType']


            geas_icons = [x.split('/')[-1] for x in geas[-1]['GeasIconPath']]
            wiki_geas_icos = [f"[[File:{x}.png|50px]]" for x in geas_icons]

            if not season['ignore']: wikitext_seasons += "{{" + f"Event | Server = {region.upper()} | Category = Joint Firepower Exercise | NameEN = {dungeon_type_name(dungeon['TimeAttackDungeonType'])} Exercise | Start_date = {shared.functions.format_datetime(season['StartDate'])} | End_date = {shared.functions.format_datetime(season['EndDate'])} | Notes = {' '.join(wiki_geas_icos)}" + " }}\n\n"


        with open(os.path.join(args['outdir'], 'events' ,f"time_attack_dungeon_seasons_{region}.txt"), 'w+', encoding="utf8") as f:
            f.write(wikitext_seasons)

        if wiki.site != None:
            wiki.publish(SEASON_PAGE[region], wikitext_seasons, 'Updated TimeAttackDungeon schedule')
 


def init_data():
    global args, data, season_data
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    season_data['jp'] = load_season_data(args['data_primary'])
    season_data['gl'] = load_season_data(args['data_secondary'])

    # for character in data.characters.values():
    #     if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':#  not in ['Release', 'Complete']:
    #         continue

    #     try:
    #         character = Character.from_data(character['Id'], data)
    #         characters[character.id] = character
    #     except Exception as err:
    #         print(f'Failed to parse for DevName {character["DevName"]}: {err}')
    #         traceback.print_exc()
    #         continue

    # for item in data.items.values():
    #     try:
    #         item = Item.from_data(item['Id'], data)
    #         items[item.id] = item
    #     except Exception as err:
    #         print(f'Failed to parse for item {item}: {err}')
    #         traceback.print_exc()
    #         continue

    # for item in data.furniture.values():
    #     try:
    #         item = Furniture.from_data(item['Id'], data)
    #         furniture[item.id] = item
    #     except Exception as err:
    #         print(f'Failed to parse for furniture {item}: {err}')
    #         traceback.print_exc()
    #         continue

    # for emblem_id in data.emblem:
    #     try:
    #         emblem = Emblem.from_data(emblem_id, data, characters, missing_etc_localization, missing_localization)
    #         emblems[emblem.id] = emblem
    #     except Exception as err:
    #         print(f'Failed to parse emblem {emblem_id}: {err}')
    #         traceback.print_exc()
   

def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')

    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    try:
        init_data()
        generate()
        missing_localization.write()
        missing_skill_localization.write()
        missing_code_localization.write()
        missing_etc_localization.write()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()

