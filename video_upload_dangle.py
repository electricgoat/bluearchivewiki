from dataclasses import replace
import os
import re
import sys
import traceback
#import json
import argparse
import collections
import textwrap


#import wikitextparser as wtp
import wiki

from data import load_data
from model import Character, Furniture
import shared.functions
from shared.CompareImages import compare_images

Interaction = collections.namedtuple(
    'Interaction',
    ['characters', 'filename', 'furniture']
)

data = None
args = None
map_wikiname_id = {}
videos = []




def get_character_data():
    global data, map_wikiname_id
    characters = []

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character['Id'], data)
            map_wikiname_id[character.wiki_name] = character.id
            characters.append(character)
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()

        # if args['character_id'] is not None and character['Id'] not in args['character_id']:
        #     continue
    
    return characters
    




def generate():
    global data, args, map_wikiname_id
    assert wiki is not None

    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    characters = get_character_data()



    for character in characters:
        if args['character_wikiname'] is not None and character.wiki_name not in args['character_wikiname']:
            continue

        wikitext = textwrap.dedent("""\
                                {{Media
                                | Type = Dangle
                                | Collection =
                                | Student = """+ character.wiki_name+"""
                                | Notes = 
                                }}
                                [[Category:Character videos]]
                                """)

        filename = f"{character.wiki_name.replace(' ','_')}_dangle.webm"
        wikipath = f"File:{character.wiki_name.replace(' ','_')}_dangle.webm"       

        if wiki.site != None:  
            if wiki.page_exists(wikipath):
                print(f'Updating {wikipath}')
                wiki.publish(wikipath, wikitext, f'Adding cargo entries for dangle video')
            elif os.path.exists(os.path.join(args['gallery_dir'], filename)):
                print (f"Uploading {filename}")
                wiki.upload(os.path.join(args['gallery_dir'], filename), filename, 'Dangle video upload', wikitext)





def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-gallery_dir',     metavar='DIR', default='D:/Video_capture/upload', help='Directory with video file')
    parser.add_argument('-outdir',          metavar='DIR', default='./out/video', help='Output directory')
    
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')
    parser.add_argument('-wiki_section',  metavar='SECTION NAME', help='Name of a page section to be updated')
    
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
