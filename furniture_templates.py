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
from classes.Furniture import Furniture, FurnitureGroup
import shared.functions
from shared.MissingTranslations import MissingTranslations

missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_code_localization = MissingTranslations("translation/missing/LocalizeCodeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")
args = {}
data = None
furniture = {}

PAGE_NAME = 'Cafe Presets'

def generate():
    global args, data, furniture
    global missing_etc_localization

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['colorize'] = shared.functions.colorize
    template = env.get_template('templates/template_furniture_template.txt', None)

    wikitext = ''

    for furniture_template in data.furniture_template.values():
        title = data.etc_localization.get(furniture_template['FunitureTemplateTitle'])
        if title is not None and not title.get('NameEn'):
            missing_etc_localization.add_entry(title)

        template_elements = data.furniture_template_element[furniture_template['FurnitureTemplateId']]
        #{'furniture_id':0, 'count':0, 'order':[]}
        template_itemlist = {}
        template_item_count = 0
        for element in template_elements:
            template_item_count += 1
            if element['FurnitureId'] not in template_itemlist:
                template_itemlist[element['FurnitureId']] = {'furniture_id': element['FurnitureId'], 'count': 1, 'order': [element['Order']]}
            else:
                template_itemlist[element['FurnitureId']]['count'] += 1
                template_itemlist[element['FurnitureId']]['order'].append(element['Order'])
        template_elements = list(template_itemlist.values())
        template_elements.sort(key=lambda x: x['furniture_id'], reverse=False)  

        print(f"Processing template {furniture_template['FurnitureTemplateId']} - {title.get('NameEn', 'Unknown')} with {len(template_elements)} elements")
        wikitext += template.render(furniture_template=furniture_template, title = title, template_elements=template_elements, furniture=furniture, template_item_count=template_item_count)


    template = env.get_template('templates/page_cafe_presets.txt', None)
    wikitext = template.render(layouts=wikitext)

    with open(os.path.join(args['outdir'], 'furniture_templates.txt'), 'w', encoding="utf8") as f:
        f.write(wikitext)
        
    if wiki.site != None:
        for furniture_template in data.furniture_template.values():
            image_path = furniture_template.get('ImagePath', None)
            local_path = os.path.join(args['assets_dir'], 'Assets', '_MX', 'AddressableAsset', f"{image_path}.png")
            if image_path and os.path.exists(local_path):
                wiki_name = f"FurnitureTemplate_{str(furniture_template['FurnitureTemplateId']).zfill(2)}.png"
                upload_asset(local_path, wiki_name, message = 'Furniture template render upload')

    if wiki.site != None and not wiki.page_exists(PAGE_NAME, wikitext):
        print(f"Publishing {PAGE_NAME}")
        wiki.publish(PAGE_NAME, wikitext, f"Updated {PAGE_NAME} page")





def upload_asset(local_path, wiki_name, existing_files = [], message = 'Asset upload'):
    global args
    assert(wiki is not None)

    if local_path == '': return False
    if wiki_name == '': return False
    if wiki_name in existing_files: return False

    print(f"Uploading {local_path} to {wiki_name}")

    if not os.path.exists(local_path): 
        print(f"File not found: {local_path}")
        return False
    
    if wiki.page_exists(f"File:{wiki_name}"):
        existing_files.append(wiki_name)
        return False
    
    wiki.upload(local_path, f"File:{wiki_name}", message)
    existing_files.append(wiki_name)
    return True



def init_data():
    global args, data, furniture #, season_data, characters, items, , emblems
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    # season_data['jp'] = load_season_data(args['data_primary'])
    # season_data['gl'] = load_season_data(args['data_secondary']) 

    # for character in data.characters.values():
    #     if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':#  not in ['Release', 'Complete']:
    #         continue

    #     try:
    #         character = Character.from_data(character['Id'], data)
    #         characters[character.id] = character
    #     except Exception as err:
    #         print(f'Failed to parse for DevName {character["DevName"]}: {err}')
    #         traceback.print_exc()
    #         continue

    # for item in data.items.values():
    #     try:
    #         item = Item.from_data(item['Id'], data)
    #         items[item.id] = item
    #     except Exception as err:
    #         print(f'Failed to parse for item {item}: {err}')
    #         traceback.print_exc()
    #         continue

    for item in data.furniture.values():
        try:
            item = Furniture.from_data(item['Id'], data)
            furniture[item.id] = item
        except Exception as err:
            print(f'Failed to parse for furniture {item}: {err}')
            traceback.print_exc()
            continue

    # for emblem_id in data.emblem:
    #     try:
    #         emblem = Emblem.from_data(emblem_id, data, characters, missing_etc_localization, missing_localization)
    #         emblems[emblem.id] = emblem
    #     except Exception as err:
    #         print(f'Failed to parse emblem {emblem_id}: {err}')
    #         traceback.print_exc()



def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')
    parser.add_argument('-assets_dir',     metavar='DIR', default='C:/blue_archive_data/datamine/blue_archive/ui_textures', help='Directory with exported assets')

    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None: 
        wiki.init(args)


    try:
        init_data()
        generate()
    except:
        parser.print_help()
        traceback.print_exc()

    missing_localization.write()
    missing_code_localization.write()
    missing_etc_localization.write()



if __name__ == '__main__':
    main()
