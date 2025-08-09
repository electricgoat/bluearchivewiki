from dataclasses import replace
import os
import re
import sys
import traceback
#import json
import argparse

from jinja2 import Environment, FileSystemLoader

import wikitextparser as wtp
import wiki

from data import load_data
from model import Character
import shared.functions
from shared.MissingTranslations import MissingTranslations

missing_skill_localization = MissingTranslations("translation/missing/LocalizeSkillExcelTable.json")

args = {}


def generate():
    global args
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['colorize'] = shared.functions.colorize
    template = env.get_template('templates/page_character.txt')


    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        if args['character_id'] is not None and character['Id'] not in args['character_id']:
            continue

        if character['Id'] == 10099: #Hoshio (Battle) Attacker form
            continue

        try:
            character = Character.from_data(character['Id'], data, missing_skill_localization)
            #if character.club == character._club and character.club != 'Veritas': print(f' Unknown club name {character.wiki_name} {character.club}')
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue
        
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
