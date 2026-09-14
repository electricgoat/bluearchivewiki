from dataclasses import replace
import os
import re
import sys
import traceback
import json
import argparse

from jinja2 import Environment, FileSystemLoader

import wikitextparser as wtp
import wiki

from data import load_data
from model import Character
import shared.functions
from shared.MissingTranslations import MissingTranslations

missing_skill_localization = MissingTranslations("translation/missing/LocalizeSkillExcelTable.json")

DEVNAME_MAP = 'translation/devname_map.json'
DEVNAME_MAP_AUX = 'translation/devname_map_aux.json'

args = {}


def generate():
    global args
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['colorize'] = shared.functions.colorize
    template = env.get_template('templates/page_character.txt')

    devname_entries = {}

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        if args['character_id'] is not None and character['Id'] not in args['character_id']:
            continue

        try:
            character = Character.from_data(character['Id'], data, missing_skill_localization)
            #if character.club == character._club and character.club != 'Veritas': print(f' Unknown club name {character.wiki_name} {character.club}')
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue

        devname_entries[devname_key(character.dev_name)] = {
            #consumers build wiki names as firstname + (variant), so a variantless wiki name override has to go into firstname
            'firstname': character.personal_name_en if character.variant else character.wiki_name_base,
            'lastname': character.family_name_en,
            'variant': character.variant
        }

        fragment_sources = "FragmentSources" in data.translated_characters[character.id] and "\n"+data.translated_characters[character.id]["FragmentSources"] or None
        with open(os.path.join(args['outdir'], f'{character.wiki_name}.txt'), 'w', encoding="utf8") as f:
            wikitext = template.render(character=character, fragment_sources = fragment_sources)
            
            f.write(wikitext)
            
        if wiki.site != None and args['wiki_template'] != None:
            wiki.update_template(character.wiki_name, args['wiki_template'], wikitext)
        elif wiki.site != None and args['wiki_section'] != None:
            wiki.update_section(character.wiki_name, args['wiki_section'], wikitext)
        elif wiki.site != None and args['wiki_section_number'] != None:
            wiki.update_section_number(character.wiki_name, args['wiki_section_number'], wikitext)
        elif wiki.site != None and not wiki.page_exists(character.wiki_name, wikitext):
            print(f"Publishing {character.wiki_name}")
            wiki.publish(character.wiki_name, wikitext, "Updated character page")

    update_devname_maps(data, devname_entries)


def devname_key(dev_name):
    return dev_name.replace('_default', '')


def update_devname_maps(data, devname_entries, path_map=DEVNAME_MAP, path_aux=DEVNAME_MAP_AUX):
    """Keeps playable characters in devname_map and everything else (NPCs) in devname_map_aux"""
    with open(path_map, encoding="utf8") as f:
        devname_map = json.load(f)
    with open(path_aux, encoding="utf8") as f:
        devname_map_aux = json.load(f)

    #checked against the full character list so characters skipped by -character_id or failing to parse are not offloaded
    playable = {devname_key(x['DevName']) for x in data.characters.values() if x['IsPlayableCharacter'] and x['ProductionStep'] == 'Release'}

    #playable characters that ended up in the aux map are moved back
    for devname in [x for x in devname_map_aux if x in playable]:
        devname_map.setdefault(devname, devname_map_aux.pop(devname))

    devname_map.update(devname_entries)

    offloaded = [x for x in devname_map if x not in playable]
    for devname in offloaded:
        #aux takes priority wherever both maps are merged, so an existing aux entry is kept
        devname_map_aux.setdefault(devname, devname_map.pop(devname))

    if offloaded: print(f"Moved {len(offloaded)} NPC entries to {path_aux}: {', '.join(offloaded)}")

    for path, content in [(path_map, devname_map), (path_aux, devname_map_aux)]:
        with open(path, 'w', encoding="utf8") as f:
            json.dump(content, f, indent=4)


def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')
    parser.add_argument('-wiki_template', metavar='TEMPLATE NAME', help='Name of a template whose data will be updated')
    parser.add_argument('-wiki_section',  metavar='SECTION NAME', help='Name of a page section to be updated')
    parser.add_argument('-wiki_section_number', type=int,  metavar='SECTION NUMBER', help='Sequential number of a page section to be updated, use with caution')
    parser.add_argument('-character_id', nargs="*", type=int, metavar='ID', help='Id(s) of a characters to export')

    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None: #and (args['wiki_template'] != None or args['wiki_section'] != None or args['wiki_section_number'] != None):
        wiki.init(args)
    # else:
    #     args['wiki'] = None


    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()

    missing_skill_localization.write()


if __name__ == '__main__':
    main()
