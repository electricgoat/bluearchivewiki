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
from shared.functions import hashkey
import wiki


args = None
data = None
scenario_data = None


force_variant_link = {
    # 20011 : 19009025 #Serika Newyear
    10029 : 19009251, #Natsu (Band) NPC
}

block_variant_link = {
    10019 : 19009004, #Azusa -> Azusa (Swimsuit)
    20003 : 19009005, #Mashiro -> Mashiro (Swimsuit)
    10003 : 19009006,
    10013 : 19009007,
    10009 : 19009008, #Izumi getting linked Izumi (Swimsuit) event
}

# Directly appends voicegroup, for use with event voicegroups that aren't associated with a Character entry
force_voice_group_link = {
    10066 : [90001], #Arisu (Maid) : Shooting minigame 
    26009 : [90002, 90003], #Yuzu (Maid) : Shooting minigame normal, box
    10094 : [90004], #Momoi (Maid) : Shooting minigame 
    10095 : [90005], #Midori (Maid) : Shooting minigame 
}

STANDARD_LINE_TYPES = [ #those do not have ingame transcriptions
            'Formation', 'Formchange', 'Tactic', 'Battle', 'CommonSkill', 'CommonTSASkill', 'ExSkill', 'Summon', 'Growup', 'Relationship'] 
EVENT_STANDARD_LINE_TYPES = [ 'EventLocation', 'EventMission', 'Minigame', 'MiniGame' ] 


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
    


    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    #env.filters['colorize'] = shared.functions.colorize
    env.filters['html'] = Dialog.html
    template = env.get_template('templates/template_dialog.txt')


    for character in data.characters.values():
        normal_lines = []
        event_lines = []
        memorial_lines = []

        standard_lines = [] 

        if character['Id'] == 10099: #Hoshino (Battle) Attacker form
            continue

        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        if args['character_id'] is not None and character['Id'] not in args['character_id']:
            continue

        try:
            character = Character.from_data(character['Id'], data)
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue
        
        if args['character_wikiname'] is not None and character.wiki_name not in args['character_wikiname']:
            continue

        if (args['scavenge']):
            scavenge(character)
            continue

        print (f"===== [{character.id}] {character.wiki_name} =====")
        
        character_variation_ids, costume_variation_ids = list_character_variants(character)
    
        
        normal_lines = get_dialog_lines(character, data.character_dialog, character.costume['CostumeUniqueId'])

        #extract character audio folder/codename from normal lines data
        #this isn't pretty but deriving it from character.model_prefab_name has proven unreliable
        character_code = normal_lines[0].voice[0].path[0].rsplit('/')[-2].replace('JP_','')
        files_scandir = normal_lines[0].voice[0].path[0].rsplit('/',1)[0] + '/'

        memorial_lines = get_memorial_lines(character, data.character_dialog, files_scandir, character_code)

        
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
            if len(memorial_unlock)==0 and (os.path.exists(os.path.join(args['data_audio'], files_scandir, f"{character_code}_MemorialLobby_0.ogg")) or os.path.exists(os.path.join(args['data_audio'], files_scandir, f"{character_code}_MemorialLobby_0.ogg".lower()))):
                line['CharacterId'] = character.id
                line['CostumeUniqueId'] = character.costume['CostumeUniqueId']
                line['DialogCategory'] = 'UILobbySpecial'
                line['GroupId'] = 0
                line['LocalizeJP'] = ''
                line['LocalizeEN'] = ''
                line['VoiceId'] = []

                memorial_unlock.append(line)

            memorial_lines = get_memorial_lines(character, memorial_unlock, files_scandir, character_code) + memorial_lines

      

        for id in costume_variation_ids:
            #lines_list = []
            lines_list = get_dialog_lines(character, data.character_dialog_event, id)
            if len(lines_list)>0: event_lines.extend(lines_list)
        print(f"Total event lines: {len(event_lines)}")



        
        sl = []
        file_list = [os.path.join(files_scandir, x.split('.')[0]) for x in os.listdir(os.path.join(args['data_audio'], files_scandir))]
        append_files = [
            item 
            for voice_group in force_voice_group_link.get(character.id, []) 
            for sublist in data.character_voice[voice_group] 
            for item in sublist['Path']
        ]

        # for x in [data.costumes[x]['ModelPrefabName'] for x in character_variation_ids if x in data.costumes]:
        #     append_scandir = f"Audio/VOC_JP/JP_{x}/"
        #     if append_scandir != files_scandir and os.path.exists(os.path.join(args['data_audio'], append_scandir)):
        #         print(f"Additionally gathering files from {append_scandir}")
        #         append_files += [os.path.join(files_scandir, x.split('.')[0]) for x in os.listdir(os.path.join(args['data_audio'], append_scandir))]

        for type in (STANDARD_LINE_TYPES + EVENT_STANDARD_LINE_TYPES):
            #print(f"Gathering {type}-type standard lines")
            sl = [x for x in file_list+append_files if type.lower() in x.rsplit('/')[-1].split('_')[1].lower() or ('_s2_' in x.lower() and type.lower() in x.rsplit('/')[-1].split('_')[2].lower())]

            if sl: print (f'Found {len(sl)} {type}-type standard lines') 
            standard_lines += get_standard_lines(character, sl, type, maindir=character_code)
        #dump_missing_standard_translations(character, standard_lines)




        all_used_files = []
        for x in normal_lines: all_used_files += x.used_files
        for x in memorial_lines: all_used_files += x.used_files 
        for x in event_lines: all_used_files += x.used_files
        for x in standard_lines: all_used_files += x.used_files 

        unused_files = set([x.rsplit('/')[-1].lower() for x in file_list+append_files]).difference(set([x.lower() for x in all_used_files]))
        if len(unused_files): print(f"WARNING - unused files: {unused_files}")

        missing_files = set([x.lower() for x in all_used_files]).difference(set([x.rsplit('/')[-1].lower() for x in file_list+append_files]))
        if len(missing_files): print(f"WARNING - missing files: {missing_files}")
        


        if wiki.site != None: page_list = wiki.page_list(f"File:{character.wiki_name}")
        else: page_list = []
        #print(f"Existing pages list: {page_list}")

        
        for line in normal_lines:
            process_files(character, line, page_list)

        for line in memorial_lines:
            process_files(character, line, page_list)

        for line in event_lines:
            process_files(character, line, page_list)

        for line in standard_lines:
            process_files(character, line, page_list)

        
        missing_sl_jp_count = len([x for x in standard_lines if x.wiki_localization_jp==''])
        missing_sl_en_count = len([x for x in standard_lines if x.wiki_localization_en==''])
        print (f"Missing standard lines text counts JP: {missing_sl_jp_count}, EN: {missing_sl_en_count}")


        with open(os.path.join(args['outdir'], f'{character.wiki_name}_dialog.txt'), 'w', encoding="utf8") as f:
            wikitext = template.render(
                character=character, 
                lines=normal_lines, 
                event_lines=event_lines, 
                memorial_lines=memorial_lines, 
                standard_lines=[x for x in standard_lines if x.dialog_category in STANDARD_LINE_TYPES],
                event_standard_lines=[x for x in standard_lines if x.dialog_category in EVENT_STANDARD_LINE_TYPES],
                missing_sl_jp_count=missing_sl_jp_count,
                missing_sl_en_count=missing_sl_en_count,
                )
            f.write(wikitext)
            
        
        if wiki.site != None:
            wikipath = character.wiki_name + '/audio'

            if args['wiki_section'] != None:
                #print(f"Updating section {args['wiki_section']} of {wikipath}")
                wiki.update_section(wikipath, args['wiki_section'], wikitext)
            elif not wiki.page_exists(wikipath, wikitext):
                print(f'Publishing {wikipath}')
                wiki.publish(wikipath, wikitext, f'Generated character audio page')



def generate_scandir():
    global args
    global data, scenario_data

    voice_by_path = {
        path: item
        for item in data.voice.values()
        for path in item["Path"]
    }

    character_dialog_by_voice_id = {
        voice_id:item
        for item in data.character_dialog
        for voice_id in item['VoiceId']
    }
    
    character_wikiname = args['character_wikiname'][0]

    file_list = {
        x.split('.')[0]: {
            'localpath':    os.path.join('Audio/VOC_JP/', args['scandir']+'/', x),
            'respath':      os.path.join('Audio/VOC_JP/', args['scandir']+'/', x.split('.')[0]) ,
            'voice_id': None,
            'is_character_dialog': False,
            'wikitext_voice_title': x.split('.')[0].split('_',1)[-1],
            'wikitext_voice_clips': x
        }
        for x in os.listdir(os.path.join(args['data_audio'], 'Audio', 'VOC_JP',  args['scandir']))
    }
    print(f"Found {len(file_list)} files")


    unmatched_voice = []
    unmatched_dialog = []
    for name, file in file_list.items():
        file['voice_id'] = file['respath'] in voice_by_path and voice_by_path[file['respath']]['Id'] or None
        file['is_character_dialog'] =  file['voice_id'] and file['voice_id'] in character_dialog_by_voice_id

        if file['voice_id'] is None: unmatched_voice.append(name)
        if not file['is_character_dialog']: unmatched_dialog.append(name)
    print(f"Matched {len(file_list)-len(unmatched_voice)}/{len(file_list)} entries in Voice")
    print(f"Matched {len(file_list)-len(unmatched_dialog)}/{len(file_list)-len(unmatched_voice)} entries in CharacterDialog")


    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['html'] = Dialog.html
    template = env.get_template('templates/template_npc_dialog.txt')

    with open(os.path.join(args['outdir'], f"npc_{character_wikiname}_dialog.txt"), 'w', encoding="utf8") as f:
        wikitext = template.render(
            character_wikiname=character_wikiname, 
            file_list=file_list, 
            character_dialog = character_dialog_by_voice_id
            )
        f.write(wikitext)
        

    if wiki.site != None:
        process_files_npc(character_wikiname, file_list)

        wikipath = character_wikiname + '/audio'

        if args['wiki_section'] != None:
            #print(f"Updating section {args['wiki_section']} of {wikipath}")
            wiki.update_section(wikipath, args['wiki_section'], wikitext)
        elif not wiki.page_exists(wikipath, wikitext):
            print(f'Publishing {wikipath}')
            wiki.publish(wikipath, wikitext, f'Generated NPC audio page')



def scavenge(character):
    global args, data
    assert(wiki.site != None)
    SCRAPE_SECTIONS = ['Tactics and growth', 'Extra event lines']

    CVGROUPS = ['CommonSkill', 'CommonSkill_2', 'ExSkill_1', 'ExSkill_2', 'ExSkill_3', 'ExSkill_4', 'ExSkill_5', 'ExSkill_6', 'ExSkill_Level_1', 'ExSkill_Level_2', 'ExSkill_Level_3', 'ExSkill_Level_4', 'ExSkill_Level_5', 'ExSkill_Level_6', 'ExSkill_Level_7', 'ExSkill_Level_8', 'ExSkill_Level_9', 'ExSkill_Level_10', 'ExSkill_Level_11', 'ExSkill_Level_12', 'Growup_1', 'Growup_2', 'Growup_3', 'Growup_4', 'Relationship_Up_1', 'Relationship_Up_2', 'Relationship_Up_3', 'Relationship_Up_4', 'Formation_In_1', 'Formation_In_2', 'Formation_Select', 'Tactic_In_1', 'Tactic_In_2', 'Tactic_Victory_1', 'Tactic_Victory_2', 'Battle_Buffed_1', 'Battle_Covered_1', 'Battle_Defense_1', 'Battle_In_1', 'Battle_In_2', 'Battle_Move_1', 'Battle_Move_2', 'Battle_Recovery_1',  'Battle_TacticalAction_1', 'Battle_Victory_1', 'Battle_Victory_2', 'Battle_Victory_3', 'Formchange', #localized in subtitles
    'Tactic_Defeat_1', 'Tactic_Defeat_2', 'Battle_BuffSelf_1', 'Battle_Damage_1', 'Battle_Damage_2', 'Battle_Damage_3', 'Battle_Damage_4','Battle_Damage_5', 'Battle_Damage_6', 'Battle_Retire', 'Battle_Shout_1', 'Battle_Shout_2', 'Battle_Shout_3', 'Battle_Shout_4', 'Battle_Shout_5', 'Battle_Shout_6', 'Battle_TSA_1', 'Battle_TSA_2', 'Battle_Supply', 'Battle_Entrance_1', 'Battle_Entrance_2', 'Battle_Entrance_3', 'CommonTSASkill'] #unlocalized


    print (f'Scavenging standard lines for [{character.id}] {character.wiki_name}')

    character_voice_group = character.costume['CharacterVoiceGroupId']
    
    parsed_section = None
    standard_lines =[]
    wikipath = character.wiki_name + '/audio'
            
    text = wiki.site('parse', page=wikipath, prop='wikitext')
    text_parsed = wtp.parse(text['parse']['wikitext'])
    
    for section in text_parsed.sections:
        if section.title in SCRAPE_SECTIONS:
            parsed_section = section
            lines = [x for x in parsed_section.tables[0].data() if re.search(r"\[\[File:(.+)\.ogg\]\]", x[1]) is not None]
            for line in lines:
                clip_name = f"{character.wiki_name.replace(' ', '_')}_{line[0]}"
                category = line[0].replace(character.wiki_name+'_','').split('_',1)[0] or "Standard"
                line_jp = line[2].replace('</p><p>','\n').replace('<p>','').replace('</p>','').replace('<br>','\n') if line[2] is not None else ''
                line_en = line[3].replace('</p><p>','\n').replace('<p>','').replace('</p>','').replace('<br>','\n') if line[3] is not None else ''


                cvgroup = 'CVGroup_'+line[0]
                if line[0].startswith('S2_'): cvgroup  = 'CVGroup_'+line[0].replace('S2_', 'Formchange2_')
                if line[0] not in CVGROUPS: 
                    if not line[0].startswith('MiniGame') and not line[0].startswith('Minigame') and not line[0].startswith('Event'): print(f"{line[0]} is not in the known cvgroups list, verify it's correct")
                    cvgroup = None
                

                standard_lines.append({
                    "CharacterId":character.id, 
                    "CharacterVoiceGroupId":character_voice_group, 
                    "LocalizeCVGroup":cvgroup,
                    "DialogCategory":category, 
                    "VoiceClip": clip_name, 
                    "LocalizeJP":line_jp, 
                    "LocalizeEN":line_en
                    })

    if standard_lines: write_file(args['translation'] + '/audio/standard_' + character.wiki_name.replace(' ', '_') + '.json', standard_lines)



def get_standard_lines(character, files, dialog_category, maindir=None) -> list[Dialog]:
    global data
    dialog_data = data.character_dialog_standard
    lines = []

    operator_by_voiceid = {x['VoiceId'][0]:x for x in data.operator.values() if len(x['VoiceId'])}
    #voice_by_path = {x['Path'][0]:x for x in data.voice.values() if len(x['Path'])}
    voice_by_path_lower = {x['Path'][0].lower():x for x in data.voice.values() if len(x['Path'])}
    
    character_dialog_by_voiceid = {x['VoiceId'][0]:x for x in data.character_dialog if len(x['VoiceId'])}
    character_dialog_event_by_voiceid = {x['VoiceId'][0]:x for x in data.character_dialog_event if len(x['VoiceId'])}

    character_voice_group = character.costume['CharacterVoiceGroupId']
    character_voice = data.character_voice[character_voice_group]
    character_voice_by_path = {x['Path'][0]:x for x in character_voice if len(x['Path'])}
    character_voice_by_filename_lower = {x['Path'][0].rsplit("/", 1)[-1].lower():x for x in character_voice if len(x['Path'])}
    character_voice_subtitle_by_cvgroup = {x['LocalizeCVGroup']:x for x in data.character_voice_subtitle if x['CharacterVoiceGroupId']==character_voice_group}
    
    
    for file in files:
        file_prefix = ''
        
        #Attempt to get proper filename capitalization from the character_voice data
        filename_base = file.rsplit("/", 1)[-1]
        if filename_base in character_voice_by_filename_lower:
            filename_base = character_voice_by_filename_lower[filename_base]['Path'][0].rsplit("/", 1)[-1]
        else:
            #or capitalize the name by substituting types and capitalizing words
            types = STANDARD_LINE_TYPES + EVENT_STANDARD_LINE_TYPES 
            for index, lowertype in enumerate([x.lower() for x in types]):
                filename_base = filename_base.replace(lowertype, types[index])

            filename_base = re.sub(r"_(\w)", lambda x: f"_{x.group(1).upper()}", filename_base)
        
        
        file_wikititle = character.wiki_name.replace(' ', '_') + '_' + filename_base.split('_',1)[-1]
        
        if maindir is not None and maindir.lower() != file.rsplit("/", 1)[-1].split('_',1)[0].lower(): 
            #print(f"This is not a maindir {maindir} file: {file}")
            file_prefix = filename_base.split('_',1)[0]
            file_wikititle = character.wiki_name.replace(' ', '_') + '_' + filename_base


        voice_id = None
        if file.lower() in voice_by_path_lower: voice_id = voice_by_path_lower[file.lower()]['Id']

        if voice_id and voice_id in character_dialog_by_voiceid:
            #print(f"Skipping voice id {voice_id} as standard line candidate - present in character_dialog")
            continue

        if voice_id and voice_id in character_dialog_event_by_voiceid:
            #print(f"Skipping voice id {voice_id} as standard line candidate - present in character_dialog_event")
            continue


        # Get localization data from character_voice_subtitle
        if file in character_voice_by_path and character_voice_by_path[file]['LocalizeCVGroup'] in character_voice_subtitle_by_cvgroup:
            #print(f"File {file} is CharacterVoiceUniqueId {character_voice_by_path[file]['CharacterVoiceUniqueId']}, CVGroup {character_voice_by_path[file]['LocalizeCVGroup']}")
            subtitle_data = character_voice_subtitle_by_cvgroup[character_voice_by_path[file]['LocalizeCVGroup']]
            if file_wikititle not in dialog_data: dialog_data[file_wikititle] = {}

            dialog_data[file_wikititle]['LocalizeCVGroup'] = dialog_data[file_wikititle].get('LocalizeCVGroup', subtitle_data['LocalizeCVGroup'])
            #dialog_data[file_wikititle]['LocalizeKR'] = dialog_data[file_wikititle]['LocalizeKR'] or subtitle_data.get('LocalizeKR', '')
            dialog_data[file_wikititle]['LocalizeJP'] = subtitle_data.get('LocalizeJP', False) or dialog_data[file_wikititle].get('LocalizeJP') #prioritize ingame subtitle data over wiki transcriptions
            dialog_data[file_wikititle]['LocalizeEN'] = subtitle_data.get('LocalizeEN', False) or dialog_data[file_wikititle].get('LocalizeEN')


        # Inject localization data linked through operator lines
        if voice_id and voice_id in operator_by_voiceid:
            operator_line = operator_by_voiceid[voice_id]
            localize_key = hashkey(operator_line['TextLocalizeKey'])
            if localize_key in data.localization:
                if file_wikititle not in dialog_data:
                    dialog_data[file_wikititle] = {'LocalizeKR': data.localization[localize_key].get('Kr'),
                                                    'LocalizeJP': data.localization[localize_key].get('Jp'), 
                                                    'LocalizeEN': data.localization[localize_key].get('En')}
                else:
                    #dialog_data[file_wikititle]['LocalizeKR'] = dialog_data[file_wikititle]['LocalizeKR'] or data.localization[localize_key].get('Kr')
                    dialog_data[file_wikititle]['LocalizeJP'] = dialog_data[file_wikititle]['LocalizeJP'] or data.localization[localize_key].get('Jp')
                    dialog_data[file_wikititle]['LocalizeEN'] = dialog_data[file_wikititle]['LocalizeEN'] or data.localization[localize_key].get('En')


        dialog = Dialog.construct_standard(character, dialog_data, file, filename_base.split('_',1)[-1], file_prefix, dialog_category = dialog_category)
        lines.append(dialog)
    
    return lines



def get_memorial_lines(character, dialog_data, files_scandir, character_code) -> list[Dialog]:
    global data
    lines:list[Dialog] = []
    known_paths = [] #VoiceExcelTable contains duplicates
    
    for index, line in enumerate(dialog_data):
        if line['CharacterId'] == character.id and line['DialogCategory'] == 'UILobbySpecial':
            add_voice = []

            
            speculated_path = f"{files_scandir}{character_code}_MemorialLobby_{line['GroupId']}"
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



def get_dialog_lines(character, dialog_data, costume_id) -> list[Dialog]:
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
                print(f"Deduplicated line with VoiceId {line['VoiceId']}")
                is_duplicate = True
                break
        
        if is_duplicate:
            #print(f"Skipped duplicate line {line}")
            continue

        
        known_list.append(line)
        dialog = Dialog.from_data(character.wiki_name, data.voice, line, line['AddVoice'] if 'AddVoice' in line else None)
        
        #merge followup lines instead of generating new ones
        if len(lines) == 0: lines.append(dialog)
        else:
            prev_dialog = lines[-1]
            if dialog.voice == [] and dialog.group_id == prev_dialog.group_id and dialog.display_order > prev_dialog.display_order:
                prev_dialog.followup.append(dialog)
            elif dialog.voice != []:
                lines.append(dialog)
        

    #print(f"Gathered {len(lines)} dialog lines for costume id {costume_id}")
    return lines



def process_files(character, dialog:Dialog, page_list:list):
    global args

    if wiki.site == None: return
    page_list_lower = [x.lower() for x in page_list]

    for line in dialog.voice:
        for index, filepath in enumerate(line.path):
            wikiname = f"File:{line.wiki_voice_clips[index]}.ogg"
            wikitext = f"[[Category:Character dialog]]\r\n[[Category:{character.wiki_name} dialog]]"

            localfilename = None
            if os.path.exists(os.path.join(args['data_audio'], f"{filepath}.ogg")): localfilename = f"{filepath}.ogg"
            elif os.path.exists(os.path.join(args['data_audio'], f"{filepath.lower()}.ogg")): localfilename = f"{filepath.lower()}.ogg"
            if localfilename is None:
                print(f"Local file not found at {os.path.join(args['data_audio'], f'{filepath}.ogg')}")
                continue
            
            if wikiname in page_list: 
                print(f"File:{line.wiki_voice_clips[index]}.ogg is already in known pages list")
                if args['force_upload']:
                    wiki.upload(os.path.join(args['data_audio'], localfilename), 
                        f"{line.wiki_voice_clips[index]}.ogg", 
                        'Character dialog upload', 
                        wikitext)
                if args['update_files'] and not wiki.page_exists(wikiname, wikitext): 
                    wiki.publish(wikiname, wikitext, 'Updated audio categories')
                    print('... updated file categories.')
                continue

            if wikiname.lower() in page_list_lower:
                i = page_list_lower.index(wikiname.lower())
                print(f"File:{line.wiki_voice_clips[index]}.ogg is in known pages list, but capitalized as {page_list[i]}")
                wiki.move(page_list[i], wikiname, 'Name capitalization changed', noredirect=False)
                #no continue here because we will try and upload the new file on the chance it's data changed
            
            
            print (f"Uploading {localfilename} → {line.wiki_voice_clips[index]}.ogg")
            wiki.upload(os.path.join(args['data_audio'], localfilename), 
                        f"{line.wiki_voice_clips[index]}.ogg", 
                        'Character dialog upload', 
                        wikitext)
            

def process_files_npc(character_wikiname:str, file_list:dict):
    global args

    if wiki.site == None: return

    page_list = wiki.page_list(f"File:{character_wikiname}")
    page_list_lower = [x.lower() for x in page_list]

    for file, line in file_list.items():
        wikiname = f"File:{line['wikitext_voice_clips']}"
        wikitext = f"[[Category:NPC dialog]]\r\n[[Category:{character_wikiname} dialog]]"

        localfilename = None
        if os.path.exists(os.path.join(args['data_audio'], line['localpath'])): localfilename = line['localpath']
        elif os.path.exists(os.path.join(args['data_audio'], line['localpath'].lower())): localfilename = line['localpath'].lower()
        if localfilename is None:
            print(f"Local file not found at {os.path.join(args['data_audio'], line['localpath'])}")
            continue
        
        if wikiname in page_list: 
            print(f"{wikiname} is already in known pages list")
            if args['update_files'] and not wiki.page_exists(wikiname, wikitext): 
                wiki.publish(wikiname, wikitext, 'Updated audio categories')
                print('... updated file categories.')
            continue

        if wikiname.lower() in page_list_lower:
            i = page_list_lower.index(wikiname.lower())
            print(f"{wikiname} is in known pages list, but capitalized as {page_list[i]}")
            wiki.move(page_list[i], wikiname, 'Name capitalization changed', noredirect=False)
            #no continue here because we will try and upload the new file on the chance its data changed
        
        
        print (f"Uploading {localfilename} → {line['wikitext_voice_clips']}")
        wiki.upload(os.path.join(args['data_audio'], localfilename), 
                    line['wikitext_voice_clips'], 
                    'NPC dialog upload', 
                    wikitext)



def dump_missing_standard_translations(character:Character, lines:list[Dialog]):
    data = []
    for line in lines:
        if len(line.localize_en): continue

        data.append({
            "CharacterId": character.id,
            "DialogCategory": "Standard",
            "VoiceClip": line.voice[0].wiki_voice_clips[0],
            "Path": line.voice[0].path[0],
            #"LocalizeKR": line.localize_kr,
            "LocalizeJP": line.localize_jp,
            "LocalizeEN": line.localize_en
        })
    
    if len(data)>0: write_file(os.path.join(args['translation'], 'missing', f"standard_{character.wiki_name.replace(' ', '_')}.json"), data)



def write_file(file, data):
    f = open(file, 'w', encoding="utf8")
    f.write(json.dumps({'DataList':data}, sort_keys=False, indent=4, ensure_ascii=False)+"\n")
    f.close()
    return True



def init_data():
    global args, data, scenario_data
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    scenario_data = load_scenario_data(args['data_primary'], args['data_secondary'], args['translation'])


def main():
    global args
    global data, scenario_data

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-data_audio',      metavar='DIR', required=True, help='Audio files directory')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-character_id', nargs="*", type=int, metavar='ID', help='Id(s) of a characters to export')
    parser.add_argument('-character_wikiname', nargs="*", type=str, metavar='Wikiname', help='Name(s) of a characters to export')
    parser.add_argument('-scandir', nargs='?', default=None, type=str, metavar='DIR', help='Skip character export logic; try to match files within specified directory directly')
    parser.add_argument('-wiki', nargs=2,   metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki')
    parser.add_argument('-wiki_section',    metavar='SECTION NAME', help='Name of a page section to be updated')
    parser.add_argument('-update_files',    action='store_true', help='Check audio file wikitext and update it')
    parser.add_argument('-force_upload',  action='store_true', help='Try reuploading files even if one already exists.')
    parser.add_argument('-scavenge',        action='store_true', help='Parse existing standard line transcriptions from the wikidata')

    args = vars(parser.parse_args())
    args['data_audio'] = args['data_audio'] == None and None or args['data_audio']
    print(args)

    if args['wiki'] != None:
        wiki.init(args)

    if args['character_wikiname']:
        args['character_wikiname'] = [x.replace('_',' ').strip() for x in args['character_wikiname']]

    try:
        init_data()

        if  args['scandir'] is None:
            generate()
        elif args['character_wikiname'] is None:
            print(f"character_wikiname needs to be specified when using -scandir")
        else:
            generate_scandir()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
