import os
import re
import traceback
import argparse
import collections
import textwrap


import wiki

from data import load_data
from model import Character


# The wiki Type is what {{Media}} accepts; see the cargo declaration in Template:Media
VideoType = collections.namedtuple(
    'VideoType',
    ['dirname', 'suffix', 'media_type', 'comment']
)

VIDEO_TYPES = {
    'dangle':           VideoType('upload_dangle',        'dangle',         'Dangle',  'Dangle video upload'),
    'formation_idle':   VideoType('upload_formation_idle','formation_idle', 'Idle',    'Formation idle video upload'),
    'cafe_headpat':     VideoType('upload_cafe_headpat',  'headpat',        'Headpat', 'Headpat video upload'),
}


data = {}
args = {}
map_wikiname_id = {}


def get_character_data():
    global data, map_wikiname_id
    characters = []

    for character_data in data.characters.values():
        if not character_data['IsPlayableCharacter'] or character_data['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character_data['Id'], data)
            map_wikiname_id[character.wiki_name] = character.id
            characters.append(character)
        except Exception as err:
            print(f'Failed to parse for DevName {character_data["DevName"]}: {err}')
            traceback.print_exc()

    return characters



def scan_gallery(gallery_dir, suffix):
    catalog = collections.defaultdict(list)

    if not os.path.isdir(gallery_dir):
        print(f'Directory {gallery_dir} does not exist, skipping')
        return catalog

    pattern = re.compile(rf'^(?P<name>.+)_{re.escape(suffix)}(?:_(?P<part>\d+))?$')

    for filename in sorted(os.listdir(gallery_dir)):
        if not filename.endswith('.webm'):
            continue

        wiki_filename = filename.replace(' ', '_')
        if wiki_filename != filename:
            print(f'NOTE - {filename} will be uploaded as {wiki_filename}')

        match = pattern.match(wiki_filename[:-len('.webm')])

        if not match:
            print(f'WARNING - unrecognised filename {filename} in {gallery_dir}')
            continue

        catalog[match.group('name')].append((wiki_filename, os.path.join(gallery_dir, filename)))

    return catalog



def generate():
    global data, args, map_wikiname_id
    assert wiki is not None

    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    characters = get_character_data()

    for type_name in args['video_type']:
        video_type = VIDEO_TYPES[type_name]
        gallery_dir = os.path.join(args['gallery_root'], video_type.dirname)

        print(f'===== {type_name} ({gallery_dir}) =====')
        catalog = scan_gallery(gallery_dir, video_type.suffix)
        matched_names = set()

        for character in characters:
            if args['character_wikiname'] is not None and character.wiki_name not in args['character_wikiname']:
                continue

            name = character.wiki_name.replace(' ', '_')
            files = catalog.get(name)

            if files:
                matched_names.add(name)
            else:
                # No local capture - still visit the expected page so an already
                # uploaded file gets its cargo entry refreshed.
                files = [(f'{name}_{video_type.suffix}.webm', None)]

            wikitext = textwrap.dedent("""\
                                    {{Media
                                    | Type = """+ video_type.media_type+"""
                                    | Collection =
                                    | Student = """+ character.wiki_name+"""
                                    | Notes = 
                                    }}
                                    [[Category:Character videos]]
                                    """)

            for wiki_filename, path in files:
                wikipath = f'File:{wiki_filename}'

                if wiki.site is None:
                    continue

                if wiki.page_exists(wikipath):
                    print(f'Updating {wikipath}')
                    wiki.publish(wikipath, wikitext, f'Adding cargo entries for {type_name} video')
                elif path is not None:
                    print(f'Uploading {wiki_filename}')
                    wiki.upload(path, wiki_filename, video_type.comment, wikitext)

        leftovers = set(catalog.keys()).difference(matched_names)
        if leftovers and args['character_wikiname'] is None:
            print(f'Files not matched to a character: {sorted(leftovers)}')



def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-gallery_root',    metavar='DIR', default='C:/Video_capture', help='Directory containing the per-type video directories')
    parser.add_argument('-outdir',          metavar='DIR', default='./out/video', help='Output directory')

    parser.add_argument('-video_type', nargs="*", type=str, metavar='TYPE', choices=list(VIDEO_TYPES), default=['dangle'], help=f'Type(s) of video to upload: {", ".join(VIDEO_TYPES)}')

    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')
    #parser.add_argument('-wiki_section',  metavar='SECTION NAME', help='Name of a page section to be updated')

    #parser.add_argument('-character_id', nargs="*", type=int, metavar='ID', help='Id(s) of a characters to export')
    parser.add_argument('-character_wikiname', nargs="*", type=str, metavar='Wikiname', help='Name(s) of a characters to export')


    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None: # and (args['wiki_template'] != None or args['wiki_section'] != None or args['wiki_section_number'] != None):
        wiki.init(args)
    else:
        args['wiki'] = None

    if args['character_wikiname']:
        for name in args['character_wikiname']: name = name.replace('_',' ').strip()

    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
