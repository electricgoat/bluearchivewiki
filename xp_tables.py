from dataclasses import replace
import os
import re
import sys
import traceback
import argparse

from jinja2 import Environment, FileSystemLoader

import wikitextparser as wtp
import wiki

from data import load_json

args = None
data = {}

def init_data(data_path):
    global data
    data['account_levels'] = load_json(data_path, 'AccountLevelExcelTable.json')
    data['character_levels'] = load_json(data_path, 'CharacterLevelExcelTable.json')
    data['weapon_levels'] = load_json(data_path, 'CharacterWeaponLevelExcelTable.json')
    #data['gear_levels'] = load_json(data_path, 'CharacterGearLevelExcelTable.json') #it's 0 for both levels
    data['favor_levels'] = load_json(data_path, 'FavorLevelExcelTable.json')
    data['equipment_levels'] = load_json(data_path, 'EquipmentLevelExcelTable.json')



def generate_basic_table(dataset: str):
    global data, args

    total_xp=0
    for level in data[f'{dataset}_levels']:
        if dataset == 'favor': level['Exp'] = level['ExpType'][0]

        level['TotalExp']=total_xp
        total_xp += level['Exp']

    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'xp_tables')))
    template = env.get_template(f'template_{dataset}.txt')

    with open(os.path.join(args['outdir'], f'xp_table_{dataset}.txt'), 'w', encoding="utf8") as f:
        wikitext = template.render(levels=data[f'{dataset}_levels'])
        f.write(wikitext)



def generate_equipment_table(dataset: str):
    global data, args

    total_xp = [0, 0, 0, 0, 0, 0, 0, 0]
    for level in data[f'{dataset}_levels']:
        level['TotalExp'] = total_xp
        total_xp = [x + y for x, y in zip(total_xp, level['TierLevelExp'])]    

    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'xp_tables')), extensions=['jinja2.ext.loopcontrols'])
    template = env.get_template(f'template_{dataset}.txt')

    with open(os.path.join(args['outdir'], f'xp_table_{dataset}.txt'), 'w', encoding="utf8") as f:
        wikitext = template.render(levels=data[f'{dataset}_levels'])
        f.write(wikitext)




def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary', metavar='DIR', default='../ba-data/jp', help='Fullest (JP) game version data')
    parser.add_argument('-outdir',       metavar='DIR', default='out', help='Output directory')

    args = vars(parser.parse_args())
    print(args)

    try:
        init_data(args['data_primary'])
        generate_basic_table('account')
        generate_basic_table('character')
        generate_basic_table('weapon')
        generate_basic_table('favor')
        generate_equipment_table('equipment')
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
