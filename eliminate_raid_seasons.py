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
from raid_seasons import RAIDS


args = None
data = None
season_data = {'jp':None, 'gl':None}

SEASON_IGNORE = {
    'jp' : [1],
    'gl' : [],
}

SEASON_NOTES = {
    'jp' : {
        2:'Beta version',
        3:'Beta version',
    },
    'gl' : {

    }
}


def environment_type(environment):
    return {
        'Street': 'Urban',
        'Outdoor': 'Outdoors',
        'Indoor': 'Indoors'
    }[environment]


def generate():
    global args, data, season_data

    for region in ['jp']:
        for season in season_data[region].eliminate_raid_season.values():
            boss = season['OpenRaidBossGroup01'].split('_',2)

            if season['SeasonId'] in SEASON_IGNORE[region]:
                #print(f"Flagged to ignore {region} season {season['SeasonId']}")
                season['ignore'] = True
                continue

            if boss[0] not in RAIDS:
                print(f"Unknown boss {season['OpenRaidBossGroup01']}")
                continue

            if ((datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S") - datetime.now()).days > 7):
                print(f"Raid {region} SeasonId {season['SeasonId']} ({RAIDS[boss[0]].environment} | {RAIDS[boss[0]].name}) is too far in the future and will be ignored")
                season['ignore'] = True
                continue

            season['raid_name'] = RAIDS[boss[0]].name

            if (len(boss)>1):
                season['env'] = environment_type(boss[1])
            else:
                season['env'] = RAIDS[boss[0]].environment

            season['banner'] = f"EliminateRaid_Banner_{RAIDS[boss[0]].shortname}.png"

            season['notes'] = ''
            if season['SeasonId'] in SEASON_NOTES[region]: season['notes'] += SEASON_NOTES[region][season['SeasonId']]
            season_length = datetime.strptime(season['SeasonEndData'], "%Y-%m-%d %H:%M:%S") - datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S")
            if (season_length.days + 1) != 7: 
                season['notes'] += f"{len(season['notes'])>0 and '; n' or 'N'}on-standard duration of {season_length.days + 1} days"


    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('./raid/template_eliminate_raid_seasons.txt')

    wikitext = template.render(season_data=season_data)
    

    with open(os.path.join(args['outdir'], 'raids' ,f"eliminate_raid_seasons.txt"), 'w+', encoding="utf8") as f:
        f.write(wikitext)

    if wiki.site != None:
        wiki.update_section('Elimination Raid', 'Elimination Raid list', wikitext)



def init_data():
    global args, data, season_data
    
    season_data['jp'] = load_season_data(args['data_primary'])
    #season_data['gl'] = load_season_data(args['data_secondary'])
   

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
