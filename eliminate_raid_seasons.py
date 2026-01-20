import collections
import os
import re
import traceback
#import copy
import argparse
import json
from datetime import datetime

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data
from raid_seasons import RAIDS
import shared.functions

HISTORICAL_DATA_FILE = 'translation/eliminate_raid_seasons.json'

SEASON_IGNORE = {
    'jp' : [1],
    'gl' : [1],
}


args = {}
data = {}
season_data = {'jp':{}, 'gl':{}}
historical_season_data = {'jp':{}, 'gl':{}}


def load_historical_data():
    global historical_season_data
    
    if not os.path.exists(HISTORICAL_DATA_FILE):
        return
    
    try:
        with open(HISTORICAL_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            historical_season_data['jp'] = {int(k): v for k, v in data.get('jp', {}).items()}
            historical_season_data['gl'] = {int(k): v for k, v in data.get('gl', {}).items()}
        #print(f"Loaded historical data for {len(historical_season_data['jp'])} JP and {len(historical_season_data['gl'])} GL seasons")
    except Exception as e:
        print(f"Error loading historical data: {e}")


def save_historical_data():
    try:
        data = {
            'jp': {str(k): v for k, v in historical_season_data['jp'].items()},
            'gl': {str(k): v for k, v in historical_season_data['gl'].items()}
        }
        with open(HISTORICAL_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # jp_count = len(historical_season_data['jp'])
        # gl_count = len(historical_season_data['gl'])
        # print(f"Saved historical data for {jp_count} JP and {gl_count} GL seasons to {HISTORICAL_DATA_FILE}")
        # if jp_count > 0:
        #     print(f"  JP seasons: {sorted(historical_season_data['jp'].keys())}")
        # if gl_count > 0:
        #     print(f"  GL seasons: {sorted(historical_season_data['gl'].keys())}")
    except Exception as e:
        print(f"Error saving historical data: {e}")
        import traceback
        traceback.print_exc()


def get_season_historical_data(season_id, region):
    if season_id in historical_season_data[region]:
        return historical_season_data[region][season_id]
    return None


def record_season_data(season_id, region, armor_types, difficulties, challenge_difficulty, notes=''):
    now = datetime.now()
    season = season_data[region].eliminate_raid_season.get(season_id)
    
    if season:
        start_time = datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S")
        if start_time >= now:
            # Store bosses as list of [armor, difficulty] pairs
            bosses = [[armor_types[i], difficulties[i]] for i in range(len(armor_types))]
            
            # Preserve existing notes if present, otherwise use current notes
            existing_notes = historical_season_data[region].get(season_id, {}).get('notes', '')
            final_notes = existing_notes if existing_notes else notes
            
            historical_season_data[region][season_id] = {
                'bosses': bosses,
                'challenge_difficulty': challenge_difficulty,
                'notes': final_notes
            }
            #print(f"  Recorded {region} season {season_id} to historical data")


def apply_historical_overrides(season, season_id, region, boss_data, boss_groups, difficulties_range):
    hist_data = get_season_historical_data(season_id, region)
    
    if hist_data:
        # Apply armor and difficulty overrides from historical data
        if 'bosses' in hist_data:
            for i in range(len(boss_groups)):
                if i < len(hist_data['bosses']):
                    season['armor'][i] = hist_data['bosses'][i][0]
                    season['difficulty'][i] = hist_data['bosses'][i][1]
        # Apply challenge difficulty override if present
        if 'challenge_difficulty' in hist_data:
            season['challenge_difficulty'] = hist_data['challenge_difficulty']
        # Apply notes override if present
        if hist_data.get('notes'):
            season['notes'] = hist_data['notes']
        return True
    
    return False


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
            season_length = datetime.strptime(season['SeasonEndData'], "%Y-%m-%d %H:%M:%S") - datetime.strptime(season['SeasonStartData'], "%Y-%m-%d %H:%M:%S")
            if (season_length.days + 1) != 7: 
                season['notes'] += f"Non-standard duration of {season_length.days + 1} days"

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
            
            # Apply historical data overrides
            apply_historical_overrides(season, season['SeasonId'], region, boss_data, boss_groups, difficulties_range)

            season['difficulty_shorthand'] = [shared.functions.difficulty_shorthand(x) for x in season['difficulty']]
            
            # Record this season to historical data if it's current or future
            record_season_data(season['SeasonId'], region, season['armor'], season['difficulty'], season['challenge_difficulty'], season['notes'])
            
            print_season(season)

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['difficulty_shorthand'] = shared.functions.difficulty_shorthand
    template = env.get_template('./raid/template_eliminate_raid_seasons.txt')

    wikitext = template.render(season_data=season_data)
    
    save_historical_data()

    with open(os.path.join(args['outdir'], 'raids' ,f"eliminate_raid_seasons.txt"), 'w+', encoding="utf8") as f:
        f.write(wikitext)

    if wiki.site != None:
        wiki.update_section('Grand Assault', 'Grand Assault list', wikitext)



def init_data():
    global args, data, season_data
    
    load_historical_data()
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
