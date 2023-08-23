import os
import traceback
import json
import argparse

from pywikiapi import Site
import wikitextparser as wtp


WIKI_API = 'https://bluearchive.wiki/w/api.php'

args = None


def load_file(file, key='CharacterId'):
    with open(file,encoding="utf8") as f:
        data = json.load(f)

    return {item[key]: item for item in data['DataList']}


def write_file(file, strategy_list):
    data = {}
    data['DataList'] = []
    for item in strategy_list.values(): 
        data['DataList'].append(item)

    f = open(os.path.join(file), 'w', encoding="utf8")
    f.write(json.dumps(data, sort_keys=False, indent=2, ensure_ascii=False))
    f.close()
    return True


def scavenge():
    global args

    page_list = []
    character_list = load_file(args['load_file'])

    try:
        site = Site(WIKI_API)
    except Exception as err:
        print(f'Wiki error: {err}')
        traceback.print_exc()


    for r in site.query(list='categorymembers', cmtitle='Category:Characters', cmtype='page'):
        for page in r['categorymembers']:
            page_list.append(page)
    #print(page_list)

    for page in page_list:
        text = site('parse', page=page['title'], prop='wikitext')
        print (f"\n{text['parse']['title']}")

        text_parsed = wtp.parse(text['parse']['wikitext'])
        parsed_character = text_parsed.templates[0]
        parsed_background = text_parsed.templates[1]
        print(parsed_character.arguments[0].value.strip())
        
        wiki_data = {}

        for argument in parsed_character.arguments:
            wiki_data[argument.name.strip()] = argument.value.replace('\n','').strip()

        wiki_data['FamilyNameEn'] = wiki_data['JPReading'][:wiki_data['JPReading'].index(' ')]
        
        id = int(wiki_data['Id'])
        if id in character_list:
            #print(f"Found existing entry for {character_list[id]['PersonalNameEn']} in the file") 

            map_fields = {
                'HobbiesEn':'Hobbies',
                'Illust':'Illust',
                'VoiceEn':'Voice',
                'FamilyNameEn':'FamilyNameEn',
                'ReleaseDateJp':'ReleaseDate'
            }
            for key, value in map_fields.items():
                #print (f"Checking {key}")
                if key not in character_list[id] or character_list[id][key] == None:
                    print (f"Added {key} for {character_list[id]['PersonalNameEn']}")
                    character_list[id][key] = wiki_data[value]

            if ('ProfileIntroductionEn' not in character_list[id] or character_list[id]['ProfileIntroductionEn'] == None) and len(parsed_background.arguments[0].value) > 0 :
                print (f"Added character background for {character_list[id]['PersonalNameEn']}")
                character_list[id]['ProfileIntroductionEn'] = parsed_background.arguments[0].value.strip()

    
    if len(character_list):
         write_file(args['write_file'], character_list)
         print(f"Saved data for {len(character_list)} characters to {args['write_file']}")


def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('-load_file', metavar='PATH_TO_JSON_FILE', help='Existing file to load character translations from')
    parser.add_argument('-write_file', metavar='PATH_TO_JSON_FILE', help='File to write data to')
    
    args = vars(parser.parse_args())
    args['load_file'] = args['load_file'] == None and 'translation/CharProfile.json' or args['load_file']
    args['write_file'] = args['write_file'] == None and 'translation/CharProfile_scavenged.json' or args['write_file']
    print(args)

    try:
        scavenge()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
