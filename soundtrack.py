import os
import json
import traceback
import argparse
import re

import wikitextparser as wtp

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data


args = {}
data = None


def upload_tracks(tracks):
    global args

    known_wiki_pages = set(wiki.page_prefix_list('Track_'))
    print(f"Loaded {len(known_wiki_pages)} cached track file pages from the wiki")

    for track in tracks.values():
        print(f"=== Track {track['Id']} ===")
        localpath = None
        if track.get('Path'): localpath = os.path.join(args['data_audio'], f"{track['Path'][0].lstrip('Audio/')}.ogg")
        if localpath and not os.path.exists(localpath):
            print(f'File not found: {localpath}')
            continue

        complete_name = f"File:{track['WikiFilename']}"
        generic_name = f"File:Track_{track['Id']}.ogg"

        #Rename old file if it had no artist/name listed previously, but now does
        complete_name_exists = complete_name in known_wiki_pages

        if not complete_name_exists:
            generic_name_exists = generic_name in known_wiki_pages
            if generic_name_exists:
                if complete_name != generic_name:
                    wiki.move(generic_name, complete_name, summary='Descriptive track name', noredirect=False)
                    known_wiki_pages.discard(generic_name)
                    known_wiki_pages.add(complete_name)

                    #The generic name is a redirect now, so a Theme_ redirect to it became a double one
                    theme_name = f"File:Theme_{track['Id']:02}.ogg"
                    if wiki.redirect_target(theme_name) == generic_name:
                        wiki.redirect(theme_name, complete_name, summary='Fix double redirect')
            else:
                print (f"Uploading {localpath} as {track['WikiFilename']}")
                wiki.upload(localpath, track['WikiFilename'], 'BGM track upload')
                known_wiki_pages.add(complete_name)


def wiki_file_name(track_id, track_data):
    filename = f"Track_{track_id}"
    
    if 'ArtistEn' in track_data and 'NameEn' in track_data and len(track_data['ArtistEn']) and len(track_data['NameEn']) and not track_data['NameEn'].endswith('BGM'):  
        filename += re.sub(r'<[^>]+>.*?<\/[^>]+>', '', '_'+track_data['ArtistEn']+'_'+track_data['NameEn'])

    return re.sub(r'[:/\\]', '', filename).replace(' ','_') + '.ogg'


# Scavenging the wiki page for existing track data, to avoid overwriting it with blank values 

SCAVENGE_PAGE = 'Music'
SCAVENGE_SECTIONS = ['In-game tracklist']
SCAVENGE_FIELDS = {'Artist': 'ArtistEn', 'ArtistNote': 'ArtistNote', 'Title': 'NameEn'}
BGM_FIELD_ORDER = ['Id', 'ArtistEn', 'ArtistNote', 'ArtistTrack', 'NameEn']


def bgm_json_path():
    global args
    return os.path.join(args['translation'], 'BGM.json')


def read_bgm_translations():
    path = bgm_json_path()

    if not os.path.exists(path):
        print(f'{path} not found, a new one will be created')
        return {}

    with open(path, encoding='utf8') as f:
        return {track['Id']: track for track in json.load(f)['DataList']}


def write_bgm_translations(tracks):
    entries = []

    for track_id in sorted(tracks.keys()):
        entry = {field: tracks[track_id][field] for field in BGM_FIELD_ORDER if field in tracks[track_id]}
        entry.update({field: value for field, value in sorted(tracks[track_id].items()) if field not in entry})
        entries.append(entry)

    with open(bgm_json_path(), 'w', encoding='utf8') as f:
        f.write(json.dumps({'DataList': entries}, sort_keys=False, indent=4, ensure_ascii=False))


def parse_wiki_tracks(wikitext):
    tracks = {}

    for section in wtp.parse(wikitext).sections:
        if section.title is None or section.title.strip() not in SCAVENGE_SECTIONS:
            continue

        for template in section.templates:
            if template.normal_name().strip() != 'Track':
                continue

            arg = template.get_arg('Id')
            if arg is None or not arg.value.strip().lstrip('-').isdigit():
                print(f'Skipping a Track template with no usable Id: {template.string}')
                continue

            track_id = int(arg.value.strip())
            track: dict[str, str|int] = {'Id': track_id}

            for wiki_field, data_field in SCAVENGE_FIELDS.items():
                arg = template.get_arg(wiki_field)
                if arg is not None:
                    track[data_field] = arg.value.strip()

            arg = template.get_arg('ArtistTrack')
            if arg is not None and arg.value.strip().isdigit():
                track['ArtistTrack'] = int(arg.value.strip())

            if track_id in tracks:
                print(f'Track {track_id} is listed more than once on the page, using the last entry')
            tracks[track_id] = track

    return tracks


def scavenge():
    global args
    assert wiki.site != None, 'Scavenging requires wiki access, provide -wiki LOGIN PASSWORD'

    print(f'Scavenging track data from https://bluearchive.wiki/wiki/{SCAVENGE_PAGE}')
    text = wiki.site('parse', page=SCAVENGE_PAGE, prop='wikitext')
    wiki_tracks = parse_wiki_tracks(text['parse']['wikitext'])
    print(f"Parsed {len(wiki_tracks)} Track templates from section(s) {', '.join(SCAVENGE_SECTIONS)}")

    tracks = read_bgm_translations()
    added = []
    updated = []
    kept = []
    unchanged = 0
    skipped = 0

    for track_id, wiki_track in sorted(wiki_tracks.items()):
        is_new = track_id not in tracks

        if is_new:
            if not any(wiki_track.get(field, '') for field in SCAVENGE_FIELDS.values()):
                #a track with no translations on the wiki either, nothing worth storing
                skipped += 1
                continue
            tracks[track_id] = {'Id': track_id, 'ArtistEn': '', 'ArtistTrack': 0, 'NameEn': ''}
            added.append(track_id)

        track = tracks[track_id]
        changes = []

        for field in list(SCAVENGE_FIELDS.values()) + ['ArtistTrack']:
            if field not in wiki_track:
                continue

            new_value = wiki_track[field]
            old_value = track.get(field, 0 if field == 'ArtistTrack' else '')

            if new_value == old_value:
                continue
            if new_value == '':
                #the page is generated from this very file, so a blank there is missing data and not a deletion
                kept.append((track_id, field, old_value))
                continue

            track[field] = new_value
            changes.append((field, old_value, new_value))

        if is_new:
            continue
        elif changes:
            updated.append((track_id, changes))
        else:
            unchanged += 1

    print(f'\n===== Scavenge digest =====')
    print(f'{len(wiki_tracks)} tracks on the wiki page, {len(tracks)} in {bgm_json_path()}')

    if added:
        print(f'\nAdded {len(added)} track(s):')
        for track_id in added:
            print(f"  + [{track_id}] {tracks[track_id].get('ArtistEn', '')} - {tracks[track_id].get('NameEn', '')}")

    if updated:
        print(f'\nUpdated {len(updated)} track(s):')
        for track_id, changes in updated:
            for field, old_value, new_value in changes:
                print(f"  ~ [{track_id}] {field}: '{old_value}' -> '{new_value}'")

    if kept:
        print(f'\nBlank on the wiki, local value kept in {len(kept)} case(s):')
        for track_id, field, old_value in kept:
            print(f"  = [{track_id}] {field}: '{old_value}'")

    missing = sorted(set(tracks.keys()) - set(wiki_tracks.keys()))
    if missing:
        print(f'\nNot listed on the wiki page, left as is - {len(missing)} track(s): {missing}')

    print(f'\nUnchanged: {unchanged}, blank on both sides and skipped: {skipped}')

    if added or updated:
        write_bgm_translations(tracks)
        print(f'Updated {bgm_json_path()}')
    else:
        print(f'No changes, {bgm_json_path()} left untouched')

# End of Scavenging section 


def generate():
    global args, data
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    #Memory lobbies tracklist
    memolobby_tracklist = sorted(set([x['BGMId'] for x in data.memory_lobby.values()]))

    # Filter tracks with ID under 999 or those explicitly used in memorylobbies  
    filtered_data = {
        track_id: {
            **track_data,
            'WikiFilename': wiki_file_name(track_id, track_data)
        }
        for track_id, track_data in sorted(data.bgm.items())
        if track_id < 999 or track_id in memolobby_tracklist
    }

    if wiki.site != None:
        upload_tracks(filtered_data)


    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('templates/template_soundtrack.txt')

    wikitext = template.render(filtered_data=filtered_data)

    with open(os.path.join(args['outdir'], f"_soundtrack.txt"), 'w+', encoding="utf8") as f:
        f.write(wikitext)

    if wiki.site != None:
        wiki.update_section('Music', 'In-game tracklist', wikitext)



def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-data_audio',      metavar='DIR', help='Audio files directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Upload files and publish generated wikitext to wiki')
    parser.add_argument('-scavenge',        action='store_true', help=f'Parse existing track data from the wiki {SCAVENGE_PAGE} page into translation/BGM.json')

    args = vars(parser.parse_args())
    print(args)

    if not args['scavenge'] and args['data_audio'] == None:
        parser.error('-data_audio is required to publish files')

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    try:
        if args['scavenge']:
            scavenge()
        else:
            generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
