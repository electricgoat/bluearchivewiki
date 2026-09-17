import os
import re
import json
import traceback
import argparse
import textwrap


import wiki

from data import load_data
from model import Character


#Region subdirectory of the cards directory -> filename infix
REGIONS = {
    'en': 'En',
    'jp': 'Jp',
}

#Sprite devname maps that double as the NPC roster, same pair npc_portrait_upload.py and gallery.py read
NPC_DEVNAME_MAPS = ['./translation/devname_map.json', './translation/devname_map_aux.json']

UPLOAD_COMMENT = 'Character introduction card upload'
UPLOAD_COMMENT_NPC = 'NPC introduction card upload'

data = {}
args = {}
characters = {}
npcs = {}




def get_character_data():
    global data, characters

    for character_data in data.characters.values():
        if not character_data['IsPlayableCharacter'] or character_data['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character_data['Id'], data)
            characters[character.wiki_name] = character
        except Exception as err:
            print(f'Failed to parse for DevName {character_data["DevName"]}: {err}')
            traceback.print_exc()

    return characters




#NPCs have no game data entry, so their names come from the sprite devname maps the same way gallery.py builds them
def get_npc_data():
    global characters, npcs

    devname_map = {}
    for path in NPC_DEVNAME_MAPS:
        with open(path, encoding="utf8") as f:
            devname_map.update(json.load(f))

    for devname, npc in devname_map.items():
        wiki_name = npc['firstname'] + (npc['variant'] and f" ({npc['variant']})" or '')

        #a name claimed by a playable character is not an NPC one
        if wiki_name in characters:
            continue

        npcs[wiki_name] = {
            'wiki_name': wiki_name,
            'wiki_name_base': npc['firstname'],
            'devname': devname,
        }

    return npcs




def load_cards(region):
    global args

    index_path = os.path.join(args['cards_dir'], region, 'index.json')

    with open(index_path, encoding="utf8") as f:
        index = json.load(f)

    print(f"Loaded {len(index['cards'])} {region} cards from {index_path}")
    return index['cards']




#ba-introcards names its files after Character.wiki_name; the same name is rebuilt here from the card metadata
def card_wiki_name(card):
    reference = card['reference']

    if reference['wiki_name_override']:
        return reference['wiki_name_override']

    if not reference['firstname']:
        return None

    out = reference['firstname']
    if reference['variant']: out += ' '+f"({reference['variant']})"
    return out




def process_card(region, card, known_wiki_pages=None):
    global args, characters, npcs

    source_file = card['image']['file']
    source_path = os.path.join(args['cards_dir'], region, source_file)

    wiki_name = card_wiki_name(card)
    if wiki_name == None:
        print(f"Skipping {region}/{source_file} - card is not resolved to a character ({card['tweet']['url']})")
        return

    character = characters.get(wiki_name)
    npc = npcs.get(wiki_name)
    if character != None:
        wiki_name = character.wiki_name
        wiki_name_base = character.wiki_name_base
    elif npc != None:
        wiki_name = npc['wiki_name']
        wiki_name_base = npc['wiki_name_base']
    else:
        wiki_name_base = card['reference']['wiki_name_override'] or card['reference']['firstname']
        print(f"WARNING - {wiki_name} is neither a playable character nor a known NPC, using card metadata as is")

    if args['character_wikiname'] is not None and wiki_name not in args['character_wikiname']:
        return

    #A character introduced more than once keeps the plain name for the first card and is numbered after that
    match = re.fullmatch(re.escape(wiki_name.replace(' ','_'))+r'(_\d+)?(\.\w+)', source_file)
    if match == None:
        print(f"WARNING - skipping {region}/{source_file}, filename does not match wiki name {wiki_name}")
        return

    filename = f"Card_{REGIONS[region]}_{wiki_name.replace(' ','_')}{match.group(1) or ''}{match.group(2)}"
    wikipath = f"File:{filename}"

    wikitext = ''
    if card['tweet']['url']:
        wikitext += f"Retrieved from {card['tweet']['url']}\n\n"

    wikitext += textwrap.dedent("""\
                            [[Category:Character introduction cards]]
                            [[Category:"""+ wiki_name_base +""" images]]
                            """)

    if not os.path.exists(source_path):
        print(f"WARNING - source file {source_path} is listed in the index but missing")
        return

    if wiki.site != None:
        if known_wiki_pages is not None and wikipath in known_wiki_pages:
            print(f"Skipping {filename} - already in cached category members")
            return

        if not wiki.page_exists(wikipath):
            print (f"Uploading {filename}")
            wiki.upload(source_path, filename, npc != None and UPLOAD_COMMENT_NPC or UPLOAD_COMMENT, wikitext)
        # elif not wiki.page_exists(wikipath, wikitext):
        #     print(f'Updating {wikipath}')
        #     wiki.publish(wikipath, wikitext, UPLOAD_COMMENT)
    else:
        print(f"{source_file.ljust(30)} -> {filename}")




def generate():
    global data, args

    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    get_character_data()
    get_npc_data()

    known_wiki_pages = set()
    if wiki.site != None:
        known_wiki_pages = set(wiki.category_members('Character introduction cards'))
        print(f"Loaded {len(known_wiki_pages)} cached wiki pages from the category")

    for region in args['region']:
        for card in load_cards(region):
            process_card(region, card, known_wiki_pages)




def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-cards_dir',       metavar='DIR', default='../ba-introcards/cards', help='Directory with ba-introcards output')

    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')

    parser.add_argument('-region', nargs="*", type=str, metavar='REGION', choices=REGIONS.keys(), default=list(REGIONS.keys()), help='Card region(s) to export')
    #parser.add_argument('-character_id', nargs="*", type=int, metavar='ID', help='Id(s) of a characters to export')
    parser.add_argument('-character_wikiname', nargs="*", type=str, metavar='Wikiname', help='Name(s) of a characters to export')


    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    if args['character_wikiname']:
        args['character_wikiname'] = [name.replace('_',' ').strip() for name in args['character_wikiname']]

    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
