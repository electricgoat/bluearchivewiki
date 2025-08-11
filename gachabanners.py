from dataclasses import replace
import os
#import re
#import sys
import traceback
import argparse
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

#import wikitextparser as wtp
#import wiki
import shared.functions

from data import load_data, load_season_data
from model import Item, Furniture, Character
#from classes.Gacha import GachaGroup, GachaElement

EXPORT_CAT = ['PickupGacha', 'LimitedGacha', 'FesGacha', 'SelectPickupGacha']
REGION_TIMEZONE = {'jp':'+09', 'gl':'+09'}

args = None
data = {}
characters = {}
regional_data = {'jp':{}, 'gl':{}}
prodnotice_banners = {}


def generate():
    global args, data, regional_data, characters
    global known_rateups

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('templates/template_banner.txt')

    for region in regional_data.keys():
        wikitext = ''
        known_rateups = [] #tracked for rerun detection
        print (f"============ {region.upper()} seasons ============")
        shop_recruit = list(sorted(regional_data[region].shop_recruit.values(), key=lambda item: item['SalePeriodFrom']))
        for banner in shop_recruit:
            if banner['CategoryType'] not in EXPORT_CAT:
                continue

            process_banner(banner, region, known_rateups)
            wikitext += template.render(region=region, entry=banner)

        with open(os.path.join(args['outdir'], f'_banners_{region}.txt'), 'w', encoding="utf8") as f:
            f.write(wikitext)



def process_banner(entry, region, known_rateups):
    global prodnotice_banners
    
    image = ''
    notes = []
    notes_extra = []
    
    opentime = datetime.strptime(entry['SalePeriodFrom'], "%Y-%m-%d %H:%M:%S")
    closetime = datetime.strptime(entry['SalePeriodTo'], "%Y-%m-%d %H:%M:%S")

    rateup_characters = [characters[x].wiki_name for x in entry['InfoCharacterId']]
    if len(rateup_characters)>0 and rateup_characters[0] in known_rateups: notes.append('rerun')
    
    if entry['LinkedRobbyBannerId'] in prodnotice_banners.keys(): image = prodnotice_banners[entry['LinkedRobbyBannerId']]['FileName'][0].rsplit('_',1)[0] + '.png'    

    if entry['CategoryType'] == 'FesGacha': notes.append('Anniversary')
    if entry['CategoryType'] == 'LimitedGacha': notes_extra.append('Limited')

    if entry['CategoryType'] == 'SelectPickupGacha' and entry['SelectAbleGachaGroupId'] > 0:
        select_group = data.gacha_select_pickup_group.get(entry['SelectAbleGachaGroupId'])
        rateup_characters = [characters[entry['CharacterId']].wiki_name for entry in select_group]

    if (opentime > datetime.now()): notes_extra.append('future')
    elif (closetime > datetime.now()): notes_extra.append('current')

    print (f"{str(entry['LinkedRobbyBannerId']).rjust(4, ' ')} {', '.join(rateup_characters).ljust(24, ' ')}: {entry['SalePeriodFrom']} ~ {entry['SalePeriodTo']} {', '.join(notes+notes_extra)}")
    known_rateups.extend(rateup_characters)

    entry['WikiSalePeriodFrom'] = entry['SalePeriodFrom'].replace(' ','T')[:-3] + REGION_TIMEZONE[region]
    entry['WikiSalePeriodTo'] = entry['SalePeriodTo'].replace(' ','T')[:-3] + REGION_TIMEZONE[region]
    entry['RateupCharacters'] = rateup_characters
    entry['Image'] = image 
    entry['Notes'] = notes
    entry['IsLimited'] = entry['CategoryType'] in ['LimitedGacha', 'FesGacha'] and True or False



def init_data():
    global args, data, regional_data, characters
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    regional_data['jp'] = load_season_data(args['data_primary'])
    regional_data['gl'] = load_season_data(args['data_secondary']) 


    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':#  not in ['Release', 'Complete']:
            continue

        try:
            character = Character.from_data(character['Id'], data)
            characters[character.id] = character
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue



def get_prodnotice_data():
    global args
    global prodnotice_banners
    
    prodnotice = shared.functions.load_json_file(args['jp_prodnotice'], 'notice-latest.json')
    prodnotice_banners = 'Banners' in prodnotice and {x['LinkedLobbyBannerId']:x for x in prodnotice['Banners']} or {}



def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-jp_prodnotice',   metavar='DIR', default='../ba-cdn/data_jp/prodnotice', help='Local JP prodnotice directory, optional, used to get banner image name')
    #parser.add_argument('-wiki', nargs=2,   metavar=('LOGIN', 'PASSWORD'), required=True, help='Wiki (bot) login and password')

    args = vars(parser.parse_args())
    print(args)

    # if args['wiki'] != None:
    #     wiki.init(args)
    # else:
    #     args['wiki'] = None


    try:
        init_data()
        get_prodnotice_data()
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
