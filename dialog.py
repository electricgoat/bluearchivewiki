from genericpath import exists
import os
import sys
import traceback
import argparse
import json
import re

from jinja2 import Environment, FileSystemLoader
import wikitextparser as wtp

from data import load_data, load_scenario_data
from model import Character
from classes.Dialog import Dialog, Voice
#import shared.functions
import wiki


args = None
data = None
scenario_data = None


force_variant_link = {
    # 20011 : 19009025 #Serika Newyear
}

block_variant_link = {
    20003 : 19009005,
    10003 : 19009006,
    10013 : 19009007,
    10009 : 19009008, #Izumi getting linked Izumi (Swimsuit) event
}



def list_character_variants(character):
    global data
    global force_variant_link, block_variant_link

    character_variation_ids = []
    costume_variation_ids = []
    
    #get event versions of the character
    for character_variant in data.characters.values():
        if character_variant['DevName'].startswith(character.dev_name) or character_variant['DevName'].startswith(character.dev_name.replace('default', 'Event')) or character_variant['DevName'].startswith(character.dev_name.replace('default', 'SpecialOperation')):
            character_variation_ids.append(character_variant['Id'])
            costume_variation_ids.append(data.costumes[character_variant['CostumeGroupId']]['CostumeUniqueId'])

    for character_id in force_variant_link:
        if character.id == character_id: 
            character_variation_ids.append(force_variant_link[character_id])
            costume_variation_ids.append(data.costumes[data.characters[force_variant_link[character_id]]['CostumeGroupId']]['CostumeUniqueId'])
    

    #Not sure how reliable OriginalCharacterId is yet. If it works well, might as well drop all of the above and just go with that data. 
    for line in data.character_dialog_event:
        if line['CostumeUniqueId'] in costume_variation_ids and line['OriginalCharacterId'] not in character_variation_ids:
            print(f"New OriginalCharacterId {line['OriginalCharacterId']} found")
            character_variation_ids.append(line['OriginalCharacterId'])

        if line['OriginalCharacterId'] in character_variation_ids and line['CostumeUniqueId'] not in costume_variation_ids:
            print(f"New CostumeUniqueId {line['CostumeUniqueId']} found")
            costume_variation_ids.append(line['CostumeUniqueId'])


    for character_id in block_variant_link:
        if character.id == character_id: 
            character_variation_ids.remove(block_variant_link[character_id])
            costume_variation_ids.remove(data.costumes[data.characters[block_variant_link[character_id]]['CostumeGroupId']]['CostumeUniqueId'])

    
    print(f"Processing character ids: {character_variation_ids}")
    print(f"Processing costume ids: {costume_variation_ids}")

    return character_variation_ids, costume_variation_ids



def generate():
    global args
    global data, scenario_data
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    scenario_data = load_scenario_data(args['data_primary'], args['data_secondary'], args['translation'])

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    #env.filters['colorize'] = shared.functions.colorize
    env.filters['html'] = Dialog.html
    template = env.get_template('template_dialog.txt')


    for character in data.characters.values():      
        lines = []
        event_lines = []
        memorial_lines = []

        standard_lines = [] 
        standard_line_types = [ #those do not have ingame transcriptions
            'Formation', 'Tactic', 'Battle', 'CommonSkill', 'CommonTSASkill', 'ExSkill', 'Summon', 'Growup', 'Relationship' ] 



        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        if (args['character_id'] != None) and (character['Id'] != int(args['character_id'])):
            continue

        try:
            character = Character.from_data(character['Id'], data)
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue
        
        if args['character_wikiname'] is not None and character.wiki_name not in args['character_wikiname']:
            continue

        print (f"===== [{character.id}] {character.wiki_name} =====")

        character.model_prefab_name = character.model_prefab_name.replace('_Original','').replace('_','')
        files_scandir = f"Audio/VOC_JP/JP_{character.model_prefab_name}/"
        
        character_variation_ids, costume_variation_ids = list_character_variants(character)
    

        
        lines = get_dialog_lines(character, data.character_dialog , character.costume['CostumeUniqueId'])

        memorial_lines = get_memorial_lines(character, data.character_dialog)
        
        # Memorial lobby unlock text from affection level script
        memorial_unlock = []
        first_memolobby_line = memorial_lines[0].localize_jp.replace('\n','')
        #print(f"FIRST MEMOLOBBY LINE {first_memolobby_line}")

        favor_rewards = [x for x in data.favor_rewards.values() if x['CharacterId'] == character.id and 'MemoryLobby' in x['RewardParcelType'] ]
        if favor_rewards: 
            sdf = [x for x in scenario_data.scenario_script if x['GroupId'] == favor_rewards[0]['ScenarioSriptGroupId'] and x['TextJp']]
            for line in sdf:                  
                if re.sub(r"\[ruby=\w+\]|\[/ruby]|\[wa:\d+\]", "", line['TextJp'], 0).replace('\n','').find(first_memolobby_line) > -1 or first_memolobby_line.find(re.sub(r"\[ruby=\w+\]|\[/ruby]|\[wa:\d+\]", "", line['TextJp'], 0).replace('\n','').replace('— ','').replace('― ','')) > -1: 
                    break
                if line['TextJp'] and line['TextJp'].startswith('―'): 
                    line['CharacterId'] = character.id
                    line['CostumeUniqueId'] = character.costume['CostumeUniqueId']
                    line['DialogCategory'] = 'UILobbySpecial'
                    line['GroupId'] = 0 
                    line['LocalizeJP'] = re.sub(r"\[.*?\]", "", line['TextJp'].replace('― ',''), 0)
                    line['LocalizeEN'] = re.sub(r"\[.*?\]", "", line['TextEn'].replace('— ','').replace('― ',''), 0)
                    line['VoiceId'] = []
                    
                    memorial_unlock.append(line)
            
            #Guess memorial lobby unlock audio if it had no text
            if len(memorial_unlock)==0 and os.path.exists(os.path.join(args['data_audio'], files_scandir, f"{character.model_prefab_name}_MemorialLobby_0.ogg")):
                line['CharacterId'] = character.id
                line['CostumeUniqueId'] = character.costume['CostumeUniqueId']
                line['DialogCategory'] = 'UILobbySpecial'
                line['GroupId'] = 0
                line['LocalizeJP'] = ''
                line['LocalizeEN'] = ''
                line['VoiceId'] = []

                memorial_unlock.append(line)

            memorial_lines = get_memorial_lines(character, memorial_unlock) + memorial_lines

      

        for id in costume_variation_ids:
            #lines_list = []
            lines_list = get_dialog_lines(character, data.character_dialog_event, id)
            if len(lines_list)>0: event_lines.extend(lines_list)
        print(f"Total event lines: {len(event_lines)}")



        if wiki.site != None: page_list = wiki.page_list(f"File:{character.wiki_name}")
        else: page_list = []
        #print(f"Existing pages list: {page_list}")

            
        
        sl = []
        file_list = os.listdir(os.path.join(args['data_audio'], files_scandir))
        for type in standard_line_types:
            #print(f"Gathering {type}-type standard lines")
            sl += [os.path.join(files_scandir, x.split('.')[0]) for x in file_list if type in x.split('_')[1]]
        standard_lines = get_standard_lines(character, sl, data.character_dialog_standard)

        #dump_missing_standard_translations(character, standard_lines)




        all_used_files = []
        for x in lines: all_used_files += x.used_files
        for x in memorial_lines: all_used_files += x.used_files 
        for x in event_lines: all_used_files += x.used_files
        for x in standard_lines: all_used_files += x.used_files 

        unused_files = list(set(all_used_files).symmetric_difference(set([x.split('.')[0] for x in file_list])))
        if len(unused_files): print(f"WARNING - unused files: {unused_files}")

        
        for line in lines:
            process_files(character, line, page_list)

        for line in memorial_lines:
            process_files(character, line, page_list)

        for line in event_lines:
            process_files(character, line, page_list)

        for line in standard_lines:
            process_files(character, line, page_list)



        with open(os.path.join(args['outdir'], f'{character.wiki_name}_dialog.txt'), 'w', encoding="utf8") as f:
            wikitext = template.render(character=character, lines=lines, event_lines=event_lines, memorial_lines=memorial_lines, standard_lines=standard_lines)
            f.write(wikitext)
            
        
        if wiki.site != None:
            wikipath = character.wiki_name + '/audio'

            if args['wiki_section'] != None:
                #print(f"Updating section {args['wiki_section']} of {wikipath}")
                wiki.update_section(wikipath, args['wiki_section'], wikitext)
            elif not wiki.page_exists(wikipath, wikitext):
                print(f'Publishing {wikipath}')
                wiki.publish(wikipath, wikitext, f'Generated character audio page')



def scavenge():
    global args

    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    #scenario_data = load_scenario_data(args['data_primary'], args['data_secondary'], args['translation'])

    for character in data.characters.values():      
        lines = []
        standard_lines = [] 

        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        if (args['character_id'] != None) and (character['Id'] != int(args['character_id'])):
            continue

        try:
            character = Character.from_data(character['Id'], data)
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue

        if args['character_wikiname'] is not None and character.wiki_name not in args['character_wikiname']:
            continue


        print (f'Scavenging standard lines for {character.wiki_name}')
        if wiki.site != None:
            parsed_section = None
            wikipath = character.wiki_name + '/audio'
                    
            text = wiki.site('parse', page=wikipath, prop='wikitext')
            text_parsed = wtp.parse(text['parse']['wikitext'])
            
            for section in text_parsed.sections:
                if section.title == 'Tactics and growth':
                    parsed_section = section

            lines = [x for x in parsed_section.tables[0].data() if re.search(r"\[\[File:(.+)\.ogg\]\]", x[1]) is not None]
            for line in lines:
                clip_name = f"{character.wiki_name.replace(' ', '_')}_{line[0]}"
                line_jp = line[2].replace('</p><p>','\n').replace('<p>','').replace('</p>','').replace('<br>','\n') if line[2] is not None else ''
                line_en = line[3].replace('</p><p>','\n').replace('<p>','').replace('</p>','').replace('<br>','\n') if line[3] is not None else ''

                standard_lines.append({"CharacterId":character.id, "DialogCategory":"Standard", "VoiceClip": clip_name, "LocalizeJP":line_jp, "LocalizeEN":line_en})

            if standard_lines: write_file(args['translation'] + '/audio/standard_' + character.wiki_name.replace(' ', '_') + '.json', standard_lines)



def get_standard_lines(character, files, dialog_data):
    lines = []

    for file in files:
        dialog = Dialog.construct_standard(character, dialog_data, file)
        lines.append(dialog)
    
    return lines



def get_memorial_lines(character, dialog_data):
    global data
    lines:list[Dialog] = []
    known_paths = [] #VoiceExcelTable contains duplicates
    
    for index, line in enumerate(dialog_data):
        if line['CharacterId'] == character.id and line['DialogCategory'] == 'UILobbySpecial':
            add_voice = []

            
            speculated_path = f"Audio/VOC_JP/JP_{character.model_prefab_name}/{character.model_prefab_name}_MemorialLobby_{line['GroupId']}"
            #print(f"speculated path {speculated_path}")
            for voice in data.voice_spine.values():
                for path in voice['Path']:
                    if speculated_path in path and path not in known_paths:
                        known_paths.append(path)
                        add_voice.append(voice)

            dialog = Dialog.from_data(character.wiki_name, data.voice_spine, line, add_voice)

            #merge followup lines instead of generating new ones
            if len(lines) == 0: lines.append(dialog)
            else:
                prev_dialog = lines[-1]
                if dialog.group_id == prev_dialog.group_id and dialog.display_order > prev_dialog.display_order:
                    prev_dialog.followup.append(dialog)
                else:
                    lines.append(dialog)
    
    return lines



def get_dialog_lines(character, dialog_data, costume_id):
    global data
    lines:list[Dialog] = []
    known_list = []

    for line in dialog_data:
        if line['DialogCategory'] == 'UILobbySpecial':
            #memorial lobby line
            continue

        if line['CostumeUniqueId'] != costume_id:
            #print(f"Skipping a line, wrong costume id")
            continue
        

        #Deduplicate lines
        is_duplicate = False
        for known_line in known_list:
            if known_line['LocalizeJP'] == line['LocalizeJP'] and len(known_line['VoiceId'])==1 and len(line['VoiceId'])==1:
                is_duplicate = True
                break
            if len(known_line['VoiceId'])==1 and len(line['VoiceId'])==1 and known_line['VoiceId'] == line['VoiceId']:
                print(f"Duplicate line with VoiceId {line['VoiceId']}")
                is_duplicate = True
                break
        
        if is_duplicate:
            #print(f"Skipped duplicate line {line}")
            continue


        known_list.append(line)
        dialog = Dialog.from_data(character.wiki_name, data.voice, line)
        
        #merge followup lines instead of generating new ones
        if len(lines) == 0: lines.append(dialog)
        else:
            prev_dialog = lines[-1]
            if dialog.voice_id == [] and dialog.group_id == prev_dialog.group_id and dialog.display_order > prev_dialog.display_order:
                prev_dialog.followup.append(dialog)
            elif dialog.voice_id != []:
                lines.append(dialog)
        

    print(f"Gathered {len(lines)} dialog lines for costume id {costume_id}")
    return lines



def process_files(character, dialog:Dialog, page_list:list):
    page_list_lower = [x.lower() for x in page_list]

    for line in dialog.voice:
        for index, filepath in enumerate(line.path):
            if not os.path.exists(os.path.join(args['data_audio'], f"{filepath}.ogg")):
                print(f"Local file not found at {os.path.join(args['data_audio'], f'{filepath}.ogg')}")
                continue
        
            if f"File:{line.wiki_voice_clips[index]}.ogg" in page_list: 
                print(f"File:{line.wiki_voice_clips[index]}.ogg is already in known pages list")
                continue

            if f"File:{line.wiki_voice_clips[index]}.ogg".lower() in page_list_lower:
                i = page_list_lower.index(f"File:{line.wiki_voice_clips[index]}.ogg".lower())
                print(f"File:{line.wiki_voice_clips[index]}.ogg is in known pages list, but capitalized as {page_list[i]}")
                if wiki.site != None:
                    wiki.move(page_list[i], f"File:{line.wiki_voice_clips[index]}.ogg", 'Name capitalization changed', noredirect=False)
                       
            
            if wiki.site != None:
                print (f"Uploading {filepath}.ogg → {line.wiki_voice_clips[index]}.ogg")
                wiki.upload(os.path.join(args['data_audio'], f"{filepath}.ogg"), 
                            f"{line.wiki_voice_clips[index]}.ogg", 
                            'Character dialog upload', 
                            f"[[Category:Character dialog]]\r\n[[Category:{character.wiki_name} dialog]]")



def dump_missing_standard_translations(character:Character, lines:list[Voice]):
    data = []
    for line in lines:
        if line.localize_en != '': continue

        data.append({
            "CharacterId": character.id,
            "DialogCategory": "Standard",
            "VoiceClip": line.voice[0].wiki_voice_clips[0],
            "Path": line.voice[0].path[0],
            "LocalizeKR": line.localize_kr,
            "LocalizeJP": line.localize_jp,
            "LocalizeEN": line.localize_en
        })
    
    if len(data)>0:
        f = open(args['translation'] + '/missing/' + f"standard_{character.wiki_name}.json".replace(' ', '_'), "w", encoding='utf8' )
        f.write(json.dumps({'DataList':data}, sort_keys=False, indent=4, ensure_ascii=False)+"\n")
        f.close()



def write_file(file, items):
    data = {}
    data['DataList'] = []
    for item in items: 
        data['DataList'].append(item)

    f = open(os.path.join(file), 'w', encoding="utf8")
    f.write(json.dumps(data, sort_keys=False, indent=4, ensure_ascii=False)+"\n")
    f.close()
    return True



def main():
    global args
    global data, scenario_data

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-data_audio',      metavar='DIR', required=True, help='Audio files directory')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-character_id',    metavar='ID', help='Id of a single character to export')
    parser.add_argument('-character_wikiname', nargs="*", type=str, metavar='Wikiname', help='Name(s) of a characters to export')
    parser.add_argument('-wiki', nargs=2,   metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki')
    parser.add_argument('-wiki_section',    metavar='SECTION NAME', help='Name of a page section to be updated')
    parser.add_argument('-upload_files',    action='store_false', help='Check if audio file is already on the wiki and upload it if not')
    parser.add_argument('-scavenge',        action='store_true', help='Parse existing standard line transcriptions from the wikidata')

    args = vars(parser.parse_args())
    args['character_id'] = args['character_id'] == None and '' or args['character_id']
    args['data_audio'] = args['data_audio'] == None and None or args['data_audio']
    print(args)

    if args['wiki'] != None:
        wiki.init(args)

    if args['character_wikiname']:
        args['character_wikiname'] = [x.replace('_',' ').strip() for x in args['character_wikiname']]

    try:
        if (args['scavenge']): scavenge()
        else: generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
