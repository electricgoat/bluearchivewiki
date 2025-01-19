import collections
import os
import re
import traceback
#import copy
import argparse
from datetime import datetime

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data


args = None
data = None
season_data = {'jp':None, 'gl':None}

Raid = collections.namedtuple('Raid', 'name, shortname, environment') #Store default environment so we don't have to look at actual boss info
RAIDS = {
    'Binah':            Raid('Decagrammaton: Binah', 'Binah', 'Outdoors'),
    'Chesed':           Raid('Decagrammaton: Chesed', 'Chesed', 'Indoors'),
    'ShiroKuro':        Raid('Slumpia: ShiroKuro', 'ShiroKuro', 'Urban'),
    'Hieronymus':       Raid('Communio Sanctorum: Hieronymus', 'Hieronymus', 'Indoors'),
    'Perorozilla':      Raid('The Library of Lore: Perorodzilla', 'Perorodzilla', 'Indoors'),
    'Kaitenger':        Raid('Kaitenger: KAITEN FX Mk.0', 'Kaitenger', 'Outdoors'),
    'HOD':              Raid('Decagrammaton: Hod', 'Hod', 'Urban'),
    'Goz':              Raid('Slumpia: Goz', 'Goz', 'Indoors'),
    'EN0005':           Raid('Communio Sanctorum: Gregorius', 'Gregorius', 'Indoors'),
    'HoverCraft':       Raid('Wakamo: Hovercraft', 'Hovercraft', 'Outdoors'),
    'EN0006':           Raid('One Hundred Ghost Tales: Myouki Kurokage', 'Kurokage', 'Urban'),
    'EN0008':           Raid('Celestial Pantheon: The Fury of Set', 'The Fury of Set', 'Outdoors'),
    'EN0009':           Raid('Decagrammaton: Chokmah', 'Chokmah', 'Outdoors'),
}

SEASON_IGNORE = {
    'jp' : [1,2],
    'gl' : [1],
}

SEASON_NOTES = {
    'jp' : {
        3:'Beta version, no ranking rewards',
        4:'No ranking rewards',
        5:'Introduction of the Ranking System and corresponding rewards based on rank',
        9:'Introduction of Extreme Difficulty',
        11:'Emergency raid 1',
        14:'Ability to set and borrow Raid Supports in the player\'s Club added',
        18:'Emergency raid 2',
        23:'Emergency raid 3',
        29:'Introduction of Insane Difficulty',
        51:'Introduction of Torment Difficulty',
        69:'Reward Insurance system added',
        78:'Introduction of Lunatic Difficulty',
    },
    'gl' : {
        2:'Beta version, no ranking rewards',
        7:'Introduction of Extreme Difficulty',
        24:'Introduction of Insane Difficulty',
        46:'Introduction of Torment Difficulty',
    }
}


def environment_type(environment):
    return {
        'Street': 'Urban',
        'Outdoor': 'Outdoors',
        'Indoor': 'Indoors'
    }[environment]



def print_season(season, note: str = ''):
    now = datetime.now() #does not account for timezone

    opentime = datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S")
    closetime = datetime.strptime(season['SeasonEndData'], "%Y-%m-%d %H:%M:%S")

    if (opentime > now): note += 'future'
    elif (closetime > now): note += 'current'

    print (f"{str(season['SeasonId']).rjust(3, ' ')} {str(season['SeasonDisplay']).rjust(3, ' ')}: {season['SeasonStartData']} ~ {season['SeasonEndData']} {season['raid_name'].ljust(36, ' ')} {season['env'].ljust(10, ' ')} {note}")



def generate():
    global args, data, season_data
    last_season_name = ''

    for region in ['jp', 'gl']:
        print (f"============ {region.upper()} raids ============")
        for season in season_data[region].raid_season.values():
            boss = season['OpenRaidBossGroup'][0].split('_',1)

            if season['SeasonId'] in SEASON_IGNORE[region]:
                #print(f"Flagged to ignore {region} season {season['SeasonId']}")
                season['ignore'] = True
                continue

            if boss[0] not in RAIDS:
                print(f"Unknown boss {season['OpenRaidBossGroup']}")
                continue

            if ((datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S") - datetime.now()).days > 28):
                print(f"Raid {region} SeasonId {season['SeasonId']} ({RAIDS[boss[0]].environment} | {RAIDS[boss[0]].name}) is too far in the future and will be ignored")
                season['ignore'] = True
                #continue

            if (last_season_name == RAIDS[boss[0]].name and (datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S") > datetime.now())):
                print(f"Raid {region} SeasonId {season['SeasonId']} ({RAIDS[boss[0]].environment} | {RAIDS[boss[0]].name}) is a duplicate of previous entry and will be ignored")
                season['ignore'] = True
                #continue


            season['raid_name'] = RAIDS[boss[0]].name
            last_season_name = season['raid_name'] #jp tends to have a placeholder duplicate a raid set further in the future

            if (len(boss)>1):
                season['env'] = environment_type(boss[1])
            else:
                season['env'] = RAIDS[boss[0]].environment

            season['banner'] = f"Raid_Banner_{RAIDS[boss[0]].shortname}.png"

            season['notes'] = ''
            if season['SeasonId'] in SEASON_NOTES[region]: season['notes'] += SEASON_NOTES[region][season['SeasonId']]
            season_length = datetime.strptime(season['SeasonEndData'], "%Y-%m-%d %H:%M:%S") - datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S")
            if (season_length.days + 1) != 7: 
                season['notes'] += f"{len(season['notes'])>0 and '; n' or 'N'}on-standard duration of {season_length.days + 1} days"

            print_season(season)


    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('./raid/template_raid_seasons.txt')

    wikitext = template.render(season_data=season_data)
    

    with open(os.path.join(args['outdir'], 'raids' ,f"raid_seasons.txt"), 'w+', encoding="utf8") as f:
        f.write(wikitext)

    if wiki.site != None:
        wiki.update_section('Total Assault', 'Raid list', wikitext)



def init_data():
    global args, data, season_data
    
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
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
