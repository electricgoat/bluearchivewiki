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

from data import load_generic
from model import Character

args = None
data = None

def init_data(data_path):
    global data
    data = load_generic(data_path, 'AccountLevelExcelTable.json')


def generate():
    global data

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('template_xp_table.txt')

    with open(os.path.join(args['outdir'], 'xp_table.txt'), 'w', encoding="utf8") as f:
        wikitext = template.render(levels=data.values())
        
        f.write(wikitext)




def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')

    args = vars(parser.parse_args())
    print(args)

    try:
        init_data(args['data_primary'])
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
