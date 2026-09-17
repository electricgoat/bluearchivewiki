import os
import json
import argparse
from datetime import datetime, timedelta, timezone

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_season_data
from raid_seasons import RAIDS
import shared.functions


HISTORICAL_DATA_FILE = 'translation/eliminate_raid_seasons.json'
BOSS_GROUPS = ['OpenRaidBossGroup01', 'OpenRaidBossGroup02', 'OpenRaidBossGroup03']
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
JST = timezone(timedelta(hours=9))

SEASON_IGNORE = {
    'jp' : [1],
    'gl' : [1],
}


args = {}
season_data = {'jp':{}, 'gl':{}}
historical_season_data = {'jp':{}, 'gl':{}}


def load_historical_data():
    if not os.path.exists(HISTORICAL_DATA_FILE):
        return
    with open(HISTORICAL_DATA_FILE, 'r', encoding='utf-8') as f:
        stored = json.load(f)
    for region in historical_season_data:
        historical_season_data[region] = {int(k): v for k, v in stored.get(region, {}).items()}


def save_historical_data():
    stored = {region: {str(k): seasons[k] for k in sorted(seasons)} for region, seasons in historical_season_data.items()}
    with open(HISTORICAL_DATA_FILE + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(stored, f, indent=2, ensure_ascii=False)
    os.replace(HISTORICAL_DATA_FILE + '.tmp', HISTORICAL_DATA_FILE)


def parse_date(text):
    return datetime.strptime(text, DATE_FORMAT)


def open_difficulties(group, region):
    return [x['Difficulty'] for x in season_data[region].eliminate_raid_stage[group] if x['IsOpen']]


def live_record(season, region):
    """The season's bosses in the game's order, each with its hardest open difficulty. Only right until the next season of the same boss groups."""
    groups = [season[key] for key in BOSS_GROUPS]
    longest = max((open_difficulties(group, region) for group in groups), key=len)
    return {
        'bosses': [{'group': group, 'difficulty': open_difficulties(group, region)[-1]} for group in groups],
        'challenge_difficulty': 'Torment' if len(longest) == 6 else longest[-1],
    }


def armor(group):
    return shared.functions.armor_type(group.split('_')[-1])


def describe(record):
    return ', '.join(f"{armor(b['group'])} {shared.functions.difficulty_shorthand(b['difficulty'])}" for b in record['bosses'])


def resolve_record(season, region, now):
    """The stored record of a season if it has started, else its game data in the stored boss order, which is recorded."""
    season_id = season['SeasonId']
    history = historical_season_data[region]
    label = f"{region.upper()} season {season_id}"
    started = parse_date(season['SeasonStartData']) <= now
    ended = parse_date(season['SeasonEndData']) <= now
    live = live_record(season, region)
    stored = history.get(season_id)

    if season['ignore']:
        if stored and not started:
            print(f"{label} is ignored, dropping its stored record ({describe(stored)})")
            del history[season_id]
        return live

    live_groups = [b['group'] for b in live['bosses']]
    stored_groups = [b['group'] for b in stored['bosses']] if stored else []
    same_bosses = sorted(stored_groups) == sorted(live_groups)
    if stored and not same_bosses:
        print(f"WARNING - {label} stores bosses {', '.join(stored_groups)}, the game data has {', '.join(live_groups)}")
    elif stored and stored_groups != live_groups:
        print(f"{label} is shown in stored order, the game data's is {', '.join(map(armor, live_groups))}")

    if started and stored:
        return stored
    if started and ended:
        print(f"WARNING - {label} has no stored record, using the current game data, which may have changed since the season")
        return live

    record = live | {'notes': stored.get('notes', '') if stored else ''}
    if same_bosses:
        record['bosses'].sort(key=lambda b: stored_groups.index(b['group']))
    if stored and record != stored:
        print(f"{label} updated from game data: {describe(stored)} / {stored['challenge_difficulty']} -> {describe(record)} / {record['challenge_difficulty']}")
    history[season_id] = record
    return record


def print_season(season, now):
    note = 'future' if parse_date(season['SeasonStartData']) > now else 'current' if parse_date(season['SeasonEndData']) > now else ''
    print (f"{str(season['SeasonId']).rjust(3, ' ')} {str(season['SeasonDisplay']).rjust(3, ' ')}: {season['SeasonStartData']} ~ {season['SeasonEndData']} {season['raid_name'].ljust(40, ' ')} {season['env'].ljust(10, ' ')} {', '.join(season['armor']).ljust(24)} {', '.join(season['difficulty_shorthand']).ljust(16)} {shared.functions.difficulty_shorthand(season['challenge_difficulty'])} {note}")


def generate():
    now = datetime.now(JST).replace(tzinfo=None) # season dates are JST

    for region in ['jp', 'gl']:
        print (f"============ {region.upper()} eliminate raids ============")
        last_season_name = ''
        for season in season_data[region].eliminate_raid_season.values():
            season['ignore'] = season['SeasonId'] in SEASON_IGNORE[region]
            if season['ignore']:
                continue

            boss = season['OpenRaidBossGroup01'].split('_',2)
            if boss[0] not in RAIDS:
                print(f"WARNING - Unknown boss {season['OpenRaidBossGroup01']}, {region} SeasonId {season['SeasonId']} will be ignored")
                season['ignore'] = True
                continue

            start = parse_date(season['SeasonStartData'])
            if (start - now).days > 60:
                print(f"Raid {region} SeasonId {season['SeasonId']} ({RAIDS[boss[0]].environment} | {RAIDS[boss[0]].name}) is too far in the future and will be ignored")
                season['ignore'] = True

            if last_season_name == RAIDS[boss[0]].name and start > now: #jp tends to have a placeholder duplicate a raid set further in the future
                print(f"Raid {region} SeasonId {season['SeasonId']} ({RAIDS[boss[0]].environment} | {RAIDS[boss[0]].name}) is a duplicate of previous entry and will be ignored")
                season['ignore'] = True

            season['raid_name'] = last_season_name = RAIDS[boss[0]].name
            season['env'] = boss[1] if len(boss) > 1 else RAIDS[boss[0]].environment
            season['banner'] = f"EliminateRaid_Banner_{RAIDS[boss[0]].shortname}.png"

            record = resolve_record(season, region, now)
            season['armor'] = [armor(b['group']) for b in record['bosses']]
            season['difficulty_shorthand'] = [shared.functions.difficulty_shorthand(b['difficulty']) for b in record['bosses']]
            season['challenge_difficulty'] = record['challenge_difficulty']

            season_length = parse_date(season['SeasonEndData']) - start
            season['notes'] = record.get('notes') or (f"Non-standard duration of {season_length.days + 1} days" if season_length.days + 1 != 7 else '')

            print_season(season, now)

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['difficulty_shorthand'] = shared.functions.difficulty_shorthand
    template = env.get_template('./raid/template_eliminate_raid_seasons.txt')

    wikitext = template.render(season_data=season_data)

    save_historical_data()

    with open(os.path.join(args['outdir'], 'raids' ,f"eliminate_raid_seasons.txt"), 'w+', encoding="utf8") as f:
        f.write(wikitext)

    if wiki.site != None:
        wiki.update_section('Grand Assault', 'Grand Assault list', wikitext)


def init_data():
    load_historical_data()
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

    init_data()
    generate()


if __name__ == '__main__':
    main()
