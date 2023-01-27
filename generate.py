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

    #weapon_data = {}
    #weapon_data['DataList'] = []
    #
    #def save_weapons_translation(weapon_data):
    #    f = open('Weapons.json', "w", encoding='utf8' )
    #    f.write(json.dumps(weapon_data, sort_keys=False, indent=4, ensure_ascii=False))
    #    f.close()
    #    return True

    # total_characters = 0
    # total_momotalks = 0
    # total_jims=0

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character['Id'], data)
            if character.club == character._club and character.club != 'Veritas': print(f' Unknown club name {character.name_translated} {character.club}')
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue
        
        with open(os.path.join(args['outdir'], f'{character.name_translated}.txt'), 'w', encoding="utf8") as f:
            wikitext = template.render(character=character)
            
            f.write(wikitext)
            if wiki.site != None:
                update_template(character.name_translated, args['wiki_template'], wikitext)

        
    #     total_characters += 1
    #     for reward in character.momotalk.levels:
    #         total_momotalks += 1
    #         for index,parcel in enumerate(reward['RewardParcelType']):
    #             if parcel == 'Currency' and reward['RewardParcelId'][index] == 3:
    #                 total_jims += reward['RewardAmount'][index]

    # print(f"Total playable characters: {total_characters}")
    # print(f"Total momotalks: {total_momotalks}")
    # print(f"Total pyroxene rewards: {total_jims}")



        
        #weapon_data['DataList'].append({'Id':character.id, 'NameJP': character.profile.weapon_name, 'NameEN': character.profile.weapon_name_translated, 'DescriptionJP': character.profile.weapon_desc, 'DescriptionEN': character.profile.weapon_desc_translated})

    #save_weapons_translation(weapon_data)



def update_template(page_name, template_name, wikitext):
    template_new = None
    template_old = None

    text = wiki.site('parse', page=page_name, prop='wikitext')
    print (f"Updating wiki page {text['parse']['title']}")

    wikitext_old = wtp.parse(text['parse']['wikitext'])
    for template in wikitext_old.templates:
        if template.name.strip() == template_name: 
            template_old = str(template)
            #print (f'Old template text is {template_old}')

    wikitext_new = wtp.parse(wikitext)
    for template in wikitext_new.templates:
        if template.name.strip() == template_name: 
            template_new = str(template)
            #print (f'New template text is {template_new}')

    if template_new == template_old:
        print (f'No changes in {template_name} for {page_name}')
    else:
        wiki_publish(page_name, text['parse']['wikitext'].replace(template_old, template_new))



def wiki_publish(page_name, wikitext):
    global args

    #with open(os.path.join(args['outdir'], f'{page_name}_wikiupdate.txt'), 'w', encoding="utf8") as f:    
    #    f.write(wikitext)
    wiki.site(
        action='edit',
        title=page_name,
        text=wikitext,
        summary=f'Updated template {args["wiki_template"]} data',
        token=wiki.site.token()
    )



def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary', metavar='DIR', help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary', metavar='DIR', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation', metavar='DIR', help='Additional translations directory')
    parser.add_argument('-outdir', metavar='DIR', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')
    parser.add_argument('-wiki_template', metavar='TEMPLATE NAME', help='Name of a template whose data will be updated')

    args = vars(parser.parse_args())
    args['data_primary'] = args['data_primary'] == None and '../ba-data/jp' or args['data_primary']
    args['data_secondary'] = args['data_secondary'] == None and '../ba-data/global' or args['data_secondary']
    args['translation'] = args['translation'] == None and 'translation' or args['translation']
    args['outdir'] = args['outdir'] == None and 'out' or args['outdir']
    print(args)

    if args['wiki'] != None and args['wiki_template'] != None and len(args['wiki_template'])>0:
        wiki.init(args)
    else:
        args['wiki'] = None
        args['wiki_template'] = None


    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
