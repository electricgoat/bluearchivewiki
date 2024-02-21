from dataclasses import replace
import os
#import re
#import sys
import traceback
#import json
import argparse
from itertools import permutations
import textwrap

import wiki

from data import load_data
from model import Character
from classes.Furniture import Furniture, FurnitureInteraction


data = None
args = None
characters = {}
furniture: dict[int:Furniture] = {}
furniture_interactions: dict[str:FurnitureInteraction] = {}


def upload_files(export_galleries):
    assert wiki.site != None
    global args

    for gallery in export_galleries:
        page_list = wiki.page_list(f"File:{gallery.character_wikiname}")
        #print(page_list)
        wiki_categories = ["Character sprites", f"{gallery.variant_origin} images"]
        wiki_text = "\n".join([f"[[Category:{x}]]" for x in wiki_categories])

        comment = f"Sprite for {gallery.character_wikiname}"
    
        for file in [x for x in gallery.files if f"File:{x}" not in page_list]:
            print (f"Uploading {file}")
            path = os.path.join(args['gallery_dir'], gallery.dirname, file)
            #print(f"Path {path}")
            wiki.upload(path, file, comment, wiki_text)





def generate():
    global data, args
    global characters
    global furniture
    global furniture_interactions

    video_catalog =  [x for x in os.listdir(args['gallery_dir']) if x.endswith('.webm')]
    processed_files = []

    for furn in furniture.values():
        speculated_filenames = []
        
        if not furn.interaction_all:
            continue

        if args['furniture'] is not None and furn.name_en not in args['furniture']:
            continue

        print(f"===== {furn.name_en} =====")
        charnames_req = []
        charnames_add = []
        charnames_make = []
        charnames_only = []

        interaction_types = {
            'req': charnames_req,
            'add': charnames_add,
            'make': charnames_make,
            'only': charnames_only,
        }

        for interaction_type, interaction_list in interaction_types.items():
            if getattr(furn, f'interaction_{interaction_type}'):
                for interaction in getattr(furn, f'interaction_{interaction_type}').values():
                    print(f"    {interaction_type} [{interaction.character_state}] {characters[interaction.character_id].wiki_name}")
                    interaction_list.append(characters[interaction.character_id].wiki_name)

        charnames_all = charnames_req + charnames_add + charnames_make + charnames_only
        if args['character_wikiname'] is not None and not set(charnames_all).intersection(args['character_wikiname']):
            continue


        if charnames_only:
            speculated_filenames.extend(charnames_only)
        if charnames_make:
            speculated_filenames.extend(['_'.join(combo) for r in range(1, len(charnames_make)+1) for combo in permutations(charnames_make, r)])
        if charnames_req:
            reqnames = ['_'.join(combo) for combo in permutations(charnames_req)]
            speculated_filenames.extend(reqnames)
            if charnames_add:
                speculated_filenames.extend([f"{reqname}_{'_'.join(combo)}" for reqname in reqnames for r in range(1, len(charnames_add)+1) for combo in permutations(charnames_add, r)])

        speculated_filenames = [element.replace(' ', '_') for element in speculated_filenames]
        print(f"Checking filenames: {speculated_filenames}")


        found_files = []

        for vc in video_catalog:
            vc_name = vc[0:vc.rfind('interact')-1]
            if vc_name in speculated_filenames: found_files.append(vc)

        print(f"Found {len(found_files)} files: {found_files}")

        for file in found_files:
            wikitext = textwrap.dedent("""\
                                    {{Media
                                    | Type = Interaction
                                    | Collection =
                                    | Student = """+ ", ".join([x for x in set(charnames_all) if x.replace(' ','_') in file])+"""
                                    | Furniture = Cafe/"""+ furn.name_en.replace(' ','_') +"""
                                    | Notes = 
                                    }}
                                    [[Category:Character videos]]
                                    """)

            if file in processed_files:
                print(f"WARNING - file {file} is getting processed again")

            else:
                with open(os.path.join(args['outdir'], file+'.txt'), 'w', encoding="utf8") as f:           
                    f.write(wikitext)
                processed_files.append(file)

                if args['wiki'] != None: file_upload(wikitext, file)
        
    print(f"Leftover files: {set(video_catalog).difference(processed_files)}")



def file_upload(wikitext, file):
    wikipath = f"File:{file}"

    if not wiki.page_exists(wikipath):
        print (f"Uploading {file}")
        wiki.upload(os.path.join(args['gallery_dir'], file), file, 'Interaction video upload', wikitext)



def init_data():
    global args, data
    global characters
    global furniture
    global furniture_interactions
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    # season_data['jp'] = load_season_data(args['data_primary'])
    # season_data['gl'] = load_season_data(args['data_secondary']) 

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character['Id'], data)
            characters[character.id] = character
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
  
    for line in data.furniture.values():
        try:
            item = Furniture.from_data(line['Id'], data)
            furniture[item.id] = item
        except Exception as err:
            print(f'Failed to parse for furniture item {line}: {err}')
            traceback.print_exc()
            continue



def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-gallery_dir',     metavar='DIR', default='D:/Video_capture/upload_cafe_interact', help='Directory with video files')
    parser.add_argument('-outdir',          metavar='DIR', default='./out/video', help='Output directory')
    
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')
    parser.add_argument('-wiki_section',  metavar='SECTION NAME', help='Name of a page section to be updated')
    
    #parser.add_argument('-character_id', nargs="*", type=int, metavar='ID', help='Id(s) of a characters to export')
    parser.add_argument('-character_wikiname', nargs="*", type=str, metavar='Wikiname', help='Name(s) of a characters to export')
    parser.add_argument('-furniture', nargs="*", type=str, metavar='Name', help='Name(s) of furniture pieces to export')


    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    if args['character_wikiname']:
        for name in args['character_wikiname']: name = name.replace('_',' ').strip()

    try:
        init_data()
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
