import os
import sys
import argparse
import traceback
from datetime import datetime

from data import load_data, load_season_data
from shared.functions import hashkey, format_datetime
from shared.MissingTranslations import MissingTranslations
from shared.standard_dictionaries import build_standard_dictionaries
from events.common import EventContext, template_env
from events.stages import event_stages, schedule_locations
from events.missions import event_mission_tables, milestone_tables
from events.shops import SHOP_TITLES, parse_shops, shop_tables, box_gacha, card_shop
from events.mode_Field import get_mode_field
from events.mode_Treasure import get_mode_treasure
from events.mode_DreamMaker import get_mode_dreammaker
from events.mode_FortuneGachaShop import get_mode_fortunegachashop
from events.mode_Defense import get_mode_defense
from events.mode_Road import get_mode_road
from events.mode_CCG import get_mode_ccg
from events.mode_DiceRace import get_mode_dicerace
from events.mode_ClueSearch import get_mode_cluesearch
from events.mode_Janken import get_mode_janken

missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_code_localization = MissingTranslations("translation/missing/LocalizeCodeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")

env = template_env()

#An event's season row is its first row of these content types
EVENT_TYPES = ["Stage", "MiniEvent", "SpecialMiniEvent", "MinigameRhythmEvent", "SeasonalEvent"]

EVENT_ITEM_TYPES = ['EventPoint', 'EventToken1', 'EventToken2', 'EventToken3', 'EventToken4']

TEAM_SLOTS = {'Striker': 4, 'Special': 2}

#The sections of the content types, in page order. A new minigame is one more entry.
SECTIONS_BEFORE_MISSIONS = {
    'EventLocation': schedule_locations,
    'DiceRace': get_mode_dicerace,
    'ClueSearch': get_mode_cluesearch,
}
SECTIONS_AFTER_SHOPS = {
    'FortuneGachaShop': get_mode_fortunegachashop,
    'Field': get_mode_field,
    'Treasure': get_mode_treasure,
    'MinigameDreamMaker': get_mode_dreammaker,
    'MiniGameDefense': get_mode_defense,
    'MiniGameRoad': get_mode_road,
    'MiniGameCCG': get_mode_ccg,
    'MinigameJanken': get_mode_janken,
}


def find_season(ctx: EventContext, region: str, event_id: int) -> dict|None:
    """A copy of the event's season row in region's data."""
    seasons = ctx.season_data[region].event_content_season
    return next((dict(seasons[(event_id, x)]) for x in EVENT_TYPES if (event_id, x) in seasons), None)


def title_key(ctx: EventContext, season: dict) -> str:
    """Derive the key of the event's title localization entry. Mini events and seasonal events have none of their own and go by the 
    title of their story replay volume: all mini event stories share one, and all meetups/valentines, another. 
    (in the client, UIService.GetScenarioModeVolumeTitle)"""
    key = f"Event_Title_{season['OriginalEventContentId']}"
    if hashkey(key) in ctx.data.localization: return key
    match season['EventContentType']:
        case 'MiniEvent': return 'Replay_Contents_MiniEvent'  #Aoi
        case 'SeasonalEvent': return 'Event_Title_810_Meetup' #valentines, ctx.data.const_event_common['MeetupScenarioReplayTitleLocalize']
        case _: return key


def localize_season(ctx: EventContext, season: dict):
    """Put the event's localized name, title and description on its season row. An event without a name or a title goes by the other."""
    def lookup(key: str, what: str) -> dict|None:
        localized = ctx.data.localization.get(hashkey(key))
        if localized is None: print(f"Missing {what} {key}")
        elif 'En' not in localized: ctx.missing_localization.add_entry(localized)
        return localized

    name = lookup(season['Name'], 'name')
    title = lookup(title_key(ctx, season), 'title') or name
    name = name or title
    if name is None or title is None: raise ValueError(f"No localized name for event {season['EventContentId']}")

    if name.get('En') != title.get('En'): print(f"Event Name and Title are mismatched, check which is more complete:\n Name :{name.get('En')}\n Title:{title.get('En')}")

    if name.get('EnGlobal') is not None and name.get('En') != name.get('EnGlobal'):
        print(f"Wiki and Global event name translation mismatched:\n Wiki  :{name.get('En')}\n Global:{name.get('EnGlobal')}")

    season['LocalizeName'] = name
    season['LocalizeTitle'] = title
    season['LocalizeDescription'] = lookup(f"Event_Description_{season['OriginalEventContentId']}", 'description')


def event_dates(season_jp: dict, season_gl: dict|None) -> str:
    template = env.get_template('template_event_dates.txt')

    wikitext = '\n==Schedule==\n' + template.render(title='Japanese Version', server='JP', season=dated(season_jp, season_jp))
    if season_gl is not None: wikitext += template.render(title='Global Version', server='GL', season=dated(season_gl, season_jp))

    return wikitext


def dated(season: dict, localized: dict) -> dict:
    """The season with its times as the wiki writes them, and the localized texts of localized, the JP season, which the GL one shows too."""
    return season | {x: format_datetime(season[x]) for x in ['EventContentOpenTime', 'EventContentCloseTime', 'ExtensionTime']} \
                  | {x: localized[x] for x in ['LocalizeName', 'LocalizeTitle', 'LocalizeDescription']}


def main_event_rows(season: dict, table: dict, what: str) -> list[dict]:
    """The rows of table for the event, or for its main event if it is a sub-event."""
    if season['MainEventId'] != 0:
        print(f"This is a sub-event, using {what} data from MainEventId {season['MainEventId']}")
        return table.get(season['MainEventId'], [])

    if season['EventContentId'] not in table: print(f"Warning - no {what} data found!")
    return table.get(season['EventContentId'], [])


def bonus_units(ctx: EventContext, season: dict) -> str:
    """The characters that raise the drops of each event item, by bonus rate."""
    bonuses = main_event_rows(season, ctx.data.event_content_character_bonus, 'bonus character')

    bonus_characters = {x: [] for x in EVENT_ITEM_TYPES}
    for item, characters in bonus_characters.items():
        for row in bonuses:
            if item not in row['EventContentItemType']: continue

            character = ctx.characters.get(row['CharacterId'])
            characters.append({
                'CharacterId': row['CharacterId'],
                'Name': character.wiki_name if character is not None else str(row['CharacterId']),
                'Class': character.combat_class if character is not None else 'Striker',
                'BonusPercentage': int(row['BonusPercentage'][row['EventContentItemType'].index(item)]/100),
            })

    bonus_values = {item: sorted({x['BonusPercentage'] for x in characters}, reverse=True) for item, characters in bonus_characters.items()}
    max_bonus = {item: max_bonus_rate(characters) for item, characters in bonus_characters.items()}

    event_currencies = {x: {} for x in EVENT_ITEM_TYPES}
    for currency in main_event_rows(season, ctx.data.event_content_currency, 'event currencies'):
        event_currencies[currency['EventContentItemType']] = {'ItemUniqueId': currency['ItemUniqueId'], 'Name': ctx.items[currency['ItemUniqueId']].name_en}

    template = env.get_template('template_event_bonus_characters.txt')
    return "==Details==\n{{EventStorySection}}\n" + template.render(bonus_characters=bonus_characters, bonus_values=bonus_values, max_bonus=max_bonus, event_currencies=event_currencies)


def max_bonus_rate(characters: list[dict]) -> int:
    """The bonus of the best team for an event item: every slot of TEAM_SLOTS takes the highest bonus left of its class."""
    return sum(sum(sorted((x['BonusPercentage'] for x in characters if x['Class'] == combat_class), reverse=True)[:slots])
               for combat_class, slots in TEAM_SLOTS.items())


def generate(ctx: EventContext, event_id: int, outdir: str):
    season = find_season(ctx, 'jp', event_id)
    if season is None: raise ValueError(f"JP season {event_id} data not found. Is this a new event type?")

    season_gl = find_season(ctx, 'gl', event_id)
    if season_gl is None: print(f"GL season {event_id} data not found. Is this event not on global yet?")

    localize_season(ctx, season)

    content_types = [type for (id, type) in ctx.season_data['jp'].event_content_season if id == event_id]
    print(f"Event {event_id} content types: {content_types}")
    shops = parse_shops(ctx, event_id) if 'Shop' in content_types or 'MiniShop' in content_types else []

    wikitext = env.get_template('template_event_header.txt').render(season=season)
    wikitext += event_dates(season, season_gl)
    wikitext += bonus_units(ctx, season)
    if 'Stage' in content_types: wikitext += event_stages(ctx, event_id)
    wikitext += ''.join(section(ctx, event_id) for type, section in SECTIONS_BEFORE_MISSIONS.items() if type in content_types)

    wikitext += '\n=Mission Details & Rewards=\n' + event_mission_tables(ctx, event_id, 'Mission' in content_types)
    wikitext += ''.join(shop_tables(shops, title) for type, title in SHOP_TITLES.items() if type in content_types)
    if 'BoxGacha' in content_types: wikitext += box_gacha(ctx, event_id)
    wikitext += milestone_tables(ctx, event_id)
    if 'CardShop' in content_types: wikitext += card_shop(ctx, event_id, shops)
    wikitext += ''.join(section(ctx, event_id) for type, section in SECTIONS_AFTER_SHOPS.items() if type in content_types)
    wikitext += env.get_template('template_event_footer.txt').render(season=season)

    with open(os.path.join(outdir, 'events', f"event_{event_id}.txt"), 'w', encoding="utf8") as f:
        f.write(wikitext)


def init(args: dict) -> EventContext:
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    return EventContext(
        data = data,
        season_data = {'jp': load_season_data(args['data_primary']), 'gl': load_season_data(args['data_secondary'])},
        **build_standard_dictionaries(data, missing_localization, missing_etc_localization)._asdict(),
        missing_localization = missing_localization,
        missing_code_localization = missing_code_localization,
        missing_etc_localization = missing_etc_localization,
    )


def list_seasons(ctx: EventContext):
    for region in ['jp', 'gl']:
        print(f"============ {region.upper()} seasons ============")
        print_seasons(ctx, region)


def print_seasons(ctx: EventContext, region: str):
    seasons = {}
    now = datetime.now() #does not account for timezone

    for season in ctx.season_data[region].event_content_season.values():
        if season['EventContentId'] in seasons: continue

        localized = ctx.data.localization.get(hashkey(season['Name'])) or ctx.data.localization.get(hashkey(title_key(ctx, season)), {})
        name = localized.get('En') or localized.get('Jp', '')

        seasons[season['EventContentId']] = {'Name': name, 'EventContentOpenTime': season['EventContentOpenTime'], 'EventContentCloseTime': season['EventContentCloseTime']}

    for id, season in seasons.items():
        opentime = datetime.strptime(season['EventContentOpenTime'], "%Y-%m-%d %H:%M:%S")
        closetime = datetime.strptime(season['EventContentCloseTime'], "%Y-%m-%d %H:%M:%S")
        note = 'future' if opentime > now else 'current' if closetime > now else ''

        print(f"{str(id).rjust(6, ' ')}: {season['EventContentOpenTime']} ~ {season['EventContentCloseTime']} {note.ljust(8)} {season['Name']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('event_season',     metavar='event_season', nargs='*', type=int, help='Event season(s) to export, none to list the seasons')
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')

    args = vars(parser.parse_args())
    print(args)

    ctx = init(args)
    if not args['event_season']: list_seasons(ctx)

    failed = []
    for event_id in args['event_season']:
        try:
            generate(ctx, event_id, args['outdir'])
        except Exception:
            traceback.print_exc()
            failed.append(event_id)

    missing_localization.write()
    missing_code_localization.write()
    missing_etc_localization.write()

    if failed: sys.exit(f"Failed to export events {failed}")


if __name__ == '__main__':
    main()
