import os
import traceback
import argparse

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data


args = None
data = None


def upload_tracks(tracks):
    global args 

    for track in tracks.values():
        print(f"=== Track {track['Id']} ===")

        localpath = os.path.join(args['data_audio'], f"{track['Path'].lstrip('Audio/')}.ogg")
        if not os.path.exists(localpath):
            print(f'File not found: {localpath}')
            continue

        #Rename old file if it had no artist/name listed previously, but now does
        generic_name_exists = wiki.page_exists(f"File:Track_{track['Id']}.ogg")
        complete_name_exists = wiki.page_exists(f"File:{track['WikiFilename']}")
        if generic_name_exists:
            if f"File:{track['WikiFilename']}" != f"File:Track_{track['Id']}.ogg" and not complete_name_exists:
                wiki.move(f"File:Track_{track['Id']}.ogg", f"File:{track['WikiFilename']}")
        elif not complete_name_exists:
            print (f"Uploading {localpath} as {track['WikiFilename']}")
            wiki.upload(localpath, track['WikiFilename'], 'BGM track upload')



def generate():
    global args, data
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    #Memory lobbies tracklist
    memolobby_tracklist = sorted(set([x['BGMId'] for x in data.memory_lobby.values()]))

    # Filter tracks with ID under 999 or those explicitly used in memorylobbies
    def has_info(track_data):
        return True if 'ArtistEn' in track_data and 'NameEn' in track_data and len(track_data['ArtistEn']) and len(track_data['NameEn']) else False
        
    filtered_data = {
        track_id: {
            **track_data,
            'WikiFilename': f"Track_{track_id}{'_'+track_data['ArtistEn'] if has_info(track_data) else ''}{'_'+track_data['NameEn'] if has_info(track_data) else ''}.ogg"
        }
        for track_id, track_data in data.bgm.items()
        if track_id < 999 or track_id in memolobby_tracklist
    }

    if wiki.site != None:
        upload_tracks(filtered_data)


    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('./template_soundtrack.txt')

    wikitext = template.render(filtered_data=filtered_data)

    with open(os.path.join(args['outdir'], f"soundtrack.txt"), 'w+', encoding="utf8") as f:
        f.write(wikitext)

    if wiki.site != None:
        wiki.update_section('Music', 'Tracklist', wikitext)



def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-data_audio',      metavar='DIR', required=True, help='Audio files directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Upload files and publish generated wikitext to wiki')

    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
