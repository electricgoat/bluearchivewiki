import os
import re
import sys
import traceback
import argparse

import wiki


args = None


def process():
    global args

    for path in os.listdir(args['upload_dir']):
        print (f"Processing {path}")
        if os.path.isfile(os.path.join(args['upload_dir'], path)) and wiki.site != None:
            with open(os.path.join(args['upload_dir'], path), encoding="utf8") as f:
                wiki.upload(os.path.join(args['upload_dir'], path), path)




def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('upload_dir', metavar='DIR', help='Directory to upload files from')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')

    args = vars(parser.parse_args())
    args['upload_dir'] = args['upload_dir'] == None and '../ba-data/jp' or args['upload_dir']
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None


    try:
        process()
    except:
        parser.print_help()
        traceback.print_exc()



if __name__ == '__main__':
    main()
