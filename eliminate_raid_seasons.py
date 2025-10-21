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


args = {}
data = {}
season_data = {'jp':{}, 'gl':{}}

SEASON_IGNORE = {
    'jp' : [1],
    'gl' : [1],
}

SEASON_NOTES = {
    'jp' : {
        2:'Beta version',
        3:'Beta version',
        5:'Torment difficulty no longer based on original defense type',
        13:'No longer requires all 3 clears for ranking rewards',
        30:'Torment difficulty now present on two defense types',
    },
    'gl' : {
        2:'Beta version',
        3:'Beta version',
        5:'Torment difficulty no longer based on original defense type',
        13:'No longer requires all 3 clears for ranking rewards',
        30:'Torment difficulty now present on two defense types',
    }
}

# Override per-season TOR armor type, this data has been altered in the client retroactively
SEASON_CHALLENGE_DEF = {
    'jp' : {
        2:'HeavyArmor',
        4:'Unarmed',
        5:'HeavyArmor',
        6:'Unarmed',
        10:'LightArmor',
        11:'Unarmed',
        12:'HeavyArmor',
        13:'Unarmed',
        15:'HeavyArmor',
        19:'Unarmed',
        20:'HeavyArmor',
    },
    'gl' : {
        2:'HeavyArmor',
        4:'Unarmed',
        5:'HeavyArmor',
        6:'Unarmed',
        10:'LightArmor',
        11:'Unarmed',
        12:'HeavyArmor',
        13:'Unarmed',
        15:'HeavyArmor',
        19:'Unarmed',
        20:'HeavyArmor',
    }
}


def get_raid_boss_data(group, region = 'jp'):
    global args, data, season_data

    boss_data = {}

    boss_data['stage'] = season_data[region].eliminate_raid_stage[group]
    boss_data['armor'] = None
    for stage in boss_data['stage']:
        #print (f"RaidCharacterId: {stage['RaidCharacterId']} {stage['RaidBossGroup']} {stage['Difficulty']}")
        stage['ground'] = data.ground[stage['GroundId']]
        stage['character'] = data.characters[stage['RaidCharacterId']]
        stage['characters_stats'] = data.characters_stats[stage['RaidCharacterId']]
        if not boss_data['armor']: boss_data['armor'] = stage['RaidBossGroup'].split('_')[-1]
        
    return boss_data


def print_season(season, note: str = ''):
    now = datetime.now() #does not account for timezone

    opentime = datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S")
    closetime = datetime.strptime(season['SeasonEndData'], "%Y-%m-%d %H:%M:%S")

    if (opentime > now): note += 'future'
    elif (closetime > now): note += 'current'

    print (f"{str(season['SeasonId']).rjust(3, ' ')} {str(season['SeasonDisplay']).rjust(3, ' ')}: {season['SeasonStartData']} ~ {season['SeasonEndData']} {season['raid_name'].ljust(40, ' ')} {season['env'].ljust(10, ' ')} {', '.join(season['armor']).ljust(24)} {', '.join([shared.functions.difficulty_shorthand(x) for x in season['difficulty']]).ljust(16)} {shared.functions.difficulty_shorthand(season['challenge_difficulty'])} {note}")


def generate():
    global args, data, season_data
    last_season_name = ''
    boss_groups = ['OpenRaidBossGroup01', 'OpenRaidBossGroup02', 'OpenRaidBossGroup03']

    for region in ['jp', 'gl']:
        print (f"============ {region.upper()} eliminate raids ============")
        for season in season_data[region].eliminate_raid_season.values():
            boss = season['OpenRaidBossGroup01'].split('_',2)
            season['armor'] = []
            season['difficulty'] = []

            if season['SeasonId'] in SEASON_IGNORE[region]:
                #print(f"Flagged to ignore {region} season {season['SeasonId']}")
                season['ignore'] = True
                continue

            if boss[0] not in RAIDS:
                print(f"Unknown boss {season['OpenRaidBossGroup01']}")
                continue

            if ((datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S") - datetime.now()).days > 60):
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
                season['env'] = boss[1]
            else:
                season['env'] = RAIDS[boss[0]].environment

            season['banner'] = f"EliminateRaid_Banner_{RAIDS[boss[0]].shortname}.png"

            season['notes'] = ''
            if season['SeasonId'] in SEASON_NOTES[region]: season['notes'] += SEASON_NOTES[region][season['SeasonId']]
            season_length = datetime.strptime(season['SeasonEndData'], "%Y-%m-%d %H:%M:%S") - datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S")
            if (season_length.days + 1) != 7: 
                season['notes'] += f"{len(season['notes'])>0 and '; n' or 'N'}on-standard duration of {season_length.days + 1} days"

            boss_data = {}
            difficulties_range = []
            for group in boss_groups:
                boss_data[group]= get_raid_boss_data(season[group], region)

                season['armor'].append(shared.functions.armor_type(boss_data[group]['armor']))

                stage_difficulties = [x['Difficulty'] for x in boss_data[group]['stage'] if x['IsOpen']]
                if len(stage_difficulties) > len(difficulties_range): difficulties_range = stage_difficulties
                season['difficulty'].append(stage_difficulties[-1])
            
            if len(difficulties_range) == 6: difficulties_range.append('Torment')
            season['challenge_difficulty'] = difficulties_range[-1]
            
            if season['SeasonId'] in SEASON_CHALLENGE_DEF[region]:
                #print(f"Overriding {region} season {season['SeasonId']} challenge armor to {SEASON_CHALLENGE_DEF[region][season['SeasonId']]}")
                for i, group in enumerate(boss_groups):
                    if boss_data[group]['armor'] == SEASON_CHALLENGE_DEF[region][season['SeasonId']]: 
                        season['difficulty'][i] = season['challenge_difficulty']
                    else:
                        season['difficulty'][i] = difficulties_range[-2]

            season['difficulty_shorthand'] = [shared.functions.difficulty_shorthand(x) for x in season['difficulty']]
            print_season(season)

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['difficulty_shorthand'] = shared.functions.difficulty_shorthand
    template = env.get_template('./raid/template_eliminate_raid_seasons.txt')

    wikitext = template.render(season_data=season_data)
    

    with open(os.path.join(args['outdir'], 'raids' ,f"eliminate_raid_seasons.txt"), 'w+', encoding="utf8") as f:
        f.write(wikitext)

    if wiki.site != None:
        wiki.update_section('Grand Assault', 'Grand Assault list', wikitext)



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
