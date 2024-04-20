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
import shared.functions


args = None
data = None
season_data = {'jp':None, 'gl':None}

SEASON_IGNORE = {
    'jp' : [],
    'gl' : [],
}

SEASON_NOTES = {
    'jp' : {
    },
    'gl' : {
    }
}


def get_raid_boss_data(group):
    global args, data, season_data

    boss_data = {}

    boss_data['stage'] = data.multi_floor_raid_stage[group]
    for stage in boss_data['stage']:
        #print (f"RaidCharacterId: {stage['RaidCharacterId']} {stage['RaidBossGroup']} {stage['Difficulty']}")
        stage['ground'] = data.ground[stage['GroundId']]
        stage['character'] = data.characters[stage['RaidCharacterId']]
        stage['characters_stats'] = data.characters_stats[stage['RaidCharacterId']]
    
    return boss_data



def generate():
    global args, data, season_data
    last_season_name = ''

    for region in ['jp', 'gl']:
        for season in season_data[region].multi_floor_raid_season.values():
            boss = [season['OpenRaidBossGroupId']]

            if season['SeasonId'] in SEASON_IGNORE[region]:
                #print(f"Flagged to ignore {region} season {season['SeasonId']}")
                season['ignore'] = True
                continue

            if boss[0] not in RAIDS:
                print(f"Unknown boss {boss[0]}")
                continue

            if ((datetime.strptime(season['SeasonStartDate'], "%Y-%m-%d %H:%M:%S") - datetime.now()).days > 14):
                print(f"Raid {region} SeasonId {season['SeasonId']} ({RAIDS[boss[0]].environment} | {RAIDS[boss[0]].name}) is too far in the future and will be ignored")
                season['ignore'] = True
                continue

            if (last_season_name == RAIDS[boss[0]].name and (datetime.strptime(season['SeasonStartDate'], "%Y-%m-%d %H:%M:%S") > datetime.now())):
                print(f"Raid {region} SeasonId {season['SeasonId']} ({RAIDS[boss[0]].environment} | {RAIDS[boss[0]].name}) is a duplicate of previous entry and will be ignored")
                season['ignore'] = True
                #continue

            season['raid_name'] = RAIDS[boss[0]].name
            last_season_name = season['raid_name'] #jp tends to have a placeholder duplicate a raid set further in the future

            if (len(boss)>1):
                season['env'] = boss[1]
            else:
                season['env'] = RAIDS[boss[0]].environment

            season['banner'] = f"MultiFloorRaid_Banner_{RAIDS[boss[0]].shortname.replace(' ','_')}.png"

            season['notes'] = ''
            if season['SeasonId'] in SEASON_NOTES[region]: season['notes'] += SEASON_NOTES[region][season['SeasonId']]
            # season_length = datetime.strptime(season['SeasonEndDate'], "%Y-%m-%d %H:%M:%S") - datetime.strptime(season['SeasonStartDate'], "%Y-%m-%d %H:%M:%S")
            # if (season_length.days + 1) != 7: 
            #     season['notes'] += f"{len(season['notes'])>0 and '; n' or 'N'}on-standard duration of {season_length.days + 1} days"

            boss_data = {}

            boss_data['OpenRaidBossGroupId']= get_raid_boss_data(season['OpenRaidBossGroupId'])

            for stage in boss_data['OpenRaidBossGroupId']['stage']: 
                if stage['Difficulty'] == 'Torment' and stage['IsOpen']:
                    #print(f"{region} {season['SeasonId']}({season['SeasonDisplay']}) TOR stage is {stage['Id']} {stage['Difficulty']} {stage['character']['ArmorType']}")
                    season['challenge'] = stage['character']['ArmorType']
                    break



    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    template = env.get_template('./raid/template_multifloor_raid_seasons.txt')

    wikitext = template.render(season_data=season_data)
    

    with open(os.path.join(args['outdir'], 'raids' ,f"multifloor_raid_seasons.txt"), 'w+', encoding="utf8") as f:
        f.write(wikitext)

    if wiki.site != None:
        wiki.update_section('Limit Break Raid', 'Limit Break Raid list', wikitext)



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
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
