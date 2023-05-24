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

args = None

def colorize(value):
    return re.sub(
        r'\[c]\[([0-9A-Fa-f]{6})]([^\[]*)\[-]\[/c]',
        r'{{SkillValue|\2}}',
        value
    )


def generate():
    global args
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['colorize'] = colorize
    template = env.get_template('template.txt')

    # total_characters = 0
    # total_momotalks = 0
    # total_jims=0

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character['Id'], data)
            #if character.club == character._club and character.club != 'Veritas': print(f' Unknown club name {character.wiki_name} {character.club}')
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue
        
        with open(os.path.join(args['outdir'], f'{character.wiki_name}.txt'), 'w', encoding="utf8") as f:
            wikitext = template.render(character=character)
            
            f.write(wikitext)
            
        if wiki.site != None and args['wiki_template'] != None:
            wiki.update_template(character.wiki_name, args['wiki_template'], wikitext)
        elif wiki.site != None and args['wiki_section'] != None:
            wiki.update_section(character.wiki_name, args['wiki_section'], wikitext)

        
    #     total_characters += 1
    #     for reward in character.momotalk.levels:
    #         total_momotalks += 1
    #         if reward['FavorRank'] > 9:
    #             print(f"{character.wiki_name} has a reward at FavorRank {reward['FavorRank']}")
    #         for index,parcel in enumerate(reward['RewardParcelType']):
    #             if parcel == 'Currency' and reward['RewardParcelId'][index] == 3:
    #                 total_jims += reward['RewardAmount'][index]

    # print(f"Total playable characters: {total_characters}")
    # print(f"Total momotalks: {total_momotalks}")
    # print(f"Total pyroxene rewards: {total_jims}")



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

    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None and (args['wiki_template'] != None or args['wiki_section'] != None):
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
