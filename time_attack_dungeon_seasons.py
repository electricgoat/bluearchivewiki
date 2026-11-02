import os
import traceback
import argparse
from datetime import datetime

import wiki

from data import load_data, load_season_data

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


args = {}

season_data = {}
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")


def dungeon_type_name(type):
    return {
        type: type,
        'Shooting':     'Shooting',
        'Defense':      'Defense',
        'Destruction':  'Assault',
        'Escort':       'Escort',
    }[type]


def geas_icons(geas):
    return ' '.join(f"[[File:{x.split('/')[-1]}.png|50px]]" for x in geas['GeasIconPath'])



def print_season(season, note: str = ''):
    now = datetime.now() #does not account for timezone

    opentime = datetime.strptime(season['StartDate'], "%Y-%m-%d %H:%M:%S")
    closetime = datetime.strptime(season['EndDate'], "%Y-%m-%d %H:%M:%S")

    if (opentime > now): note += 'future'
    elif (closetime > now): note += 'current'

    print (f"{str(season['Id']).rjust(3, ' ')}: {season['StartDate']} ~ {season['EndDate']} {season['type'].ljust(12, ' ')} {note}")



def prepare_seasons(seasons, region, data):
    """Marks up the rows of a region's TimeAttackDungeonSeasonManageExcelTable for the season list, and returns the listed ones,
    each with its number among the listed exercises of its type"""
    last_season_type = None
    listed = []

    for season in seasons:
        dungeon_type = data.time_attack_dungeon[season['DungeonId']]['TimeAttackDungeonType']
        season['type'] = dungeon_type_name(dungeon_type)
        season['geas'] = [data.time_attack_dungeon_geas[x] for x in season['DifficultyGeas']]
        season['ignore'] = season['Id'] in SEASON_IGNORE[region]

        if ((datetime.strptime(season['StartDate'], "%Y-%m-%d %H:%M:%S") - datetime.now()).days > 28):
            print(f"TimeAttackDungeon {region} Id {season['Id']} ({dungeon_type}) is too far in the future and will be ignored")
            season['ignore'] = True

        if (last_season_type == dungeon_type and (datetime.strptime(season['StartDate'], "%Y-%m-%d %H:%M:%S") > datetime.now())):
            print(f"TimeAttackDungeon {region} Id {season['Id']} ({dungeon_type}) is a duplicate of previous entry and will be ignored")
            season['ignore'] = True

        print_season(season, note = season['ignore'] and 'ignored ' or '')
        last_season_type = dungeon_type

        if not season['ignore']:
            season['number'] = 1 + sum(x['type'] == season['type'] for x in listed)
            listed.append(season)

    return listed



def generate():
    global args, data, season_data

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
        print (f"============ {region.upper()} TimeAttackDungeon ============")
        wikitext_seasons = ''.join("{{" + f"Event | Server = {region.upper()} | Category = Joint Firepower Exercise | NameEN = {season['type']} Exercise | StartDate = {shared.functions.format_datetime(season['StartDate'])} | EndDate = {shared.functions.format_datetime(season['EndDate'])} | Notes = {geas_icons(season['geas'][-1])}" + " }}\n\n"
                                   for season in prepare_seasons(season_data[region].time_attack_dungeon_season, region, data))

        with open(os.path.join(args['outdir'], 'events' ,f"time_attack_dungeon_seasons_{region}.txt"), 'w+', encoding="utf8") as f:
            f.write(wikitext_seasons)

        if wiki.site != None:
            wiki.publish(SEASON_PAGE[region], wikitext_seasons, 'Updated TimeAttackDungeon schedule')
 


def init_data():
    global args, data, season_data
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    season_data['jp'] = load_season_data(args['data_primary'])
    season_data['gl'] = load_season_data(args['data_secondary'])


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
        missing_etc_localization.write()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()

