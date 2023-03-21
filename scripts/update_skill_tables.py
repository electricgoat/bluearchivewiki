import argparse
import os
import re
import traceback

import wikitextparser as wtp
from data import load_data
from jinja2 import Environment, FileSystemLoader
from model import Character
from pywikiapi import Site
from util import get_character_page

WIKI_API = 'https://bluearchive.wiki/w/api.php'

args = None
site = None


def colorize(value):
    return re.sub(
        r'\[c]\[([0-9A-Fa-f]{6})]([^\[]*)\[-]\[/c]',
        r'{{SkillValue|\2}}',
        value
    )


def generate():
    global args
    global site
    data = load_data(args['data_primary'],
                     args['data_secondary'], args['translation'])

    env = Environment(loader=FileSystemLoader(
        os.path.join(os.path.dirname(__file__), '..')))
    env.filters['colorize'] = colorize
    template = env.get_template('template_skills.txt')

    done_skipping = False
    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character['Id'], data)
            if character.club == character._club and character.club != 'Veritas':
                print(
                    f' Unknown club name {character.wiki_name} {character.club}')
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue

        if args['resume_from'] is not None and not done_skipping:
            if character.wiki_name == args['resume_from']:
                done_skipping = True
            else:
                continue

        print(f'Processing {character.wiki_name}')

        # Get page from wiki
        page = get_character_page(site, character.wiki_name)
        content_raw = page['revisions'][0]['slots']['main']['content']
        content = wtp.parse(content_raw)

        # First, delete the upgrade materials section
        for section in content.sections:
            if section.title == 'Skill Upgrade Materials':
                del section[:]
                break
        else:
            print(
                f'Did not find skill upgrade materials section for {character.wiki_name}')

        # Then re-render the skill tables
        for section in content.sections:
            if section.title == 'Skills':
                section.contents = template.render(character=character)
                break

        rendered = str(content)
        with open(os.path.join(args['outdir'], f'{character.wiki_name}.txt'), 'w', encoding="utf8") as f:
            f.write(rendered)

        if site is not None:
            wiki_publish(character.wiki_name, rendered)


def wiki_init():
    global site

    try:
        site = Site(WIKI_API)
        site.login(args['wiki'][0], args['wiki'][1])
        print(f'Logged in to wiki, token {site.token()}')

    except Exception as err:
        print(f'Wiki error: {err}')
        traceback.print_exc()


def wiki_publish(page_name, wikitext):
    global args, site

    site(
        action='edit',
        title=page_name,
        text=wikitext,
        summary=f'Updated skill tables for {page_name}',
        token=site.token()
    )


def main():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary', metavar='DIR',
                        help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary', metavar='DIR',
                        help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation', metavar='DIR',
                        help='Additional translations directory')
    parser.add_argument('-outdir', metavar='DIR', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'),
                        help='Publish data to wiki')
    parser.add_argument('-resume_from')

    args = vars(parser.parse_args())
    args['data_primary'] = args['data_primary'] == None and '../ba-data/jp' or args['data_primary']
    args['data_secondary'] = args['data_secondary'] == None and '../ba-data/global' or args['data_secondary']
    args['translation'] = args['translation'] == None and 'translation' or args['translation']
    args['outdir'] = args['outdir'] == None and 'out' or args['outdir']
    print(args)

    if args['wiki'] is not None:
        wiki_init()

    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
