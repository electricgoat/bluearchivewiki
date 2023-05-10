from genericpath import exists
import os
import sys
import traceback
import argparse
import json
import copy
import re

from jinja2 import Environment, FileSystemLoader
import wikitextparser as wtp

from data import load_data, load_scenario_data
from model import Character
from generate import colorize
import wiki



args = None


force_variant_link = {
    20011 : 19009025 #Serika Newyear
}

block_variant_link = {
    20003 : 19009005,
    10003 : 19009006,
    10013 : 19009007,
    10009 : 19009008

}





def generate():
    global args
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    scenario_data = load_scenario_data(args['data_primary'], args['data_secondary'], args['translation'])

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['colorize'] = colorize
    template = env.get_template('template_dialog.txt')


    for character in data.characters.values():      
        lines = []
        event_lines = []
        memorial_lines = []

        standard_lines = [] 
        standard_line_types = [ #those do not have ingame transcriptions
            'Formation', 'Tactic', 'Battle', 'CommonSkill', 'CommonTSASkill', 'ExSkill', 'Summon', 'Growup', 'Relationship' ] 

        character_variation_ids = []

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

        character.model_prefab_name = character.model_prefab_name.replace('_Original','').replace('_','')
        
        #get event versions of the character
        for character_variant in data.characters.values():
            if character_variant['DevName'].startswith(character.dev_name) or character_variant['DevName'].startswith(character.dev_name.replace('default', 'Event')) or character_variant['DevName'].startswith(character.dev_name.replace('default', 'SpecialOperation')):
                character_variation_ids.append(character_variant['Id'])

        for character_id in force_variant_link:
            if character.id == character_id: character_variation_ids.append(force_variant_link[character_id])
        for character_id in block_variant_link:
            if character.id == character_id: character_variation_ids.remove(block_variant_link[character_id])
        #print(f"Processing character ids: {character_variation_ids}")


        #dump missing translations
        missing_tl = [x for x in data.character_dialog if x['CharacterId']==character.id and x['LocalizeEN'] == '' and x['LocalizeJP'] != '']
        if len(missing_tl)>1 : 
            print(f"Missing {character.wiki_name} translations: {len(missing_tl)}")
            save_missing_translations('dialog_'+character.wiki_name.replace(' ', '_'), missing_tl)

        missing_tl = [x for x in data.character_dialog_event if x['CharacterId'] in character_variation_ids and x['LocalizeEN'] == '' and x['LocalizeJP'] != '']
        if len(missing_tl)>1 : 
            print(f"Missing {character.wiki_name} event translations: {len(missing_tl)}")
            save_missing_translations('event_dialog_'+character.wiki_name.replace(' ', '_'), missing_tl)
        


        #Memorial lobby unlock text from affection level script
        memorial_unlock = []
        first_memolobby_line = [x for x in data.character_dialog if x['CharacterId'] == character.id and x['DialogCategory'] == 'UILobbySpecial' and x['LocalizeJP'] != '']
        if first_memolobby_line: first_memolobby_line = first_memolobby_line[0]['LocalizeJP'].replace('\n','')
        #print(f"FIRST LINE {first_memolobby_line}")

        if exists(f"{args['data_audio']}/JP_{character.model_prefab_name}/{character.model_prefab_name}_MemorialLobby_0.ogg") or exists(f"{args['data_audio']}/JP_{character.model_prefab_name}/{character.model_prefab_name}_MemorialLobby_0_1.ogg"):
            favor_rewards = [x for x in data.favor_rewards.values() if x['CharacterId'] == character.id and 'MemoryLobby' in x['RewardParcelType'] ]
            if favor_rewards: 
                sdf = [x for x in scenario_data.scenario_script_favor if x['GroupId'] == favor_rewards[0]['ScenarioSriptGroupId'] and x['TextJp']]
                for line in sdf:                  
                    if re.sub(r"\[ruby=\w+\]|\[/ruby]|\[wa:\d+\]", "", line['TextJp'], 0).replace('\n','').find(first_memolobby_line) > -1 or first_memolobby_line.find(re.sub(r"\[ruby=\w+\]|\[/ruby]|\[wa:\d+\]", "", line['TextJp'], 0).replace('\n','').replace('— ','').replace('― ','')) > -1: 
                        break
                    if line['TextJp'] and line['TextJp'].startswith('―'): 
                        line['CharacterId'] = character.id
                        line['DialogCategory'] = 'UILobbySpecial'
                        line['GroupId'] = 0
                        line['LocalizeJP'] = re.sub(r"\[ruby=\w+\]|\[/ruby]|\[wa:\d+\]", "", line['TextJp'].replace('― ',''), 0)
                        line['LocalizeEN'] = re.sub(r"\[ruby=\w+\]|\[/ruby]|\[wa:\d+\]", "", line['TextEn'].replace('— ','').replace('― ',''), 0)
                        line['VoiceClipsJp'] = []
                        
                        memorial_unlock.append(line)
                memorial_lines += get_memorial_lines(character, memorial_unlock, 0)


        lines = get_dialog_lines(character, data.character_dialog)


        memorial_lines += get_memorial_lines(character, data.character_dialog)


        for id in character_variation_ids:
            lines_list = []
            character_variant = copy.copy(character)
            character_variant.id = id
            lines_list = get_dialog_lines(character_variant, data.character_dialog_event)
            if len(lines_list)>0: event_lines.extend(lines_list)
            

        #deduplicate event rerun lines
        for line in [x for x in event_lines if x['EventID']>10000]:
            line_copy = line.copy()
            line_copy['EventID'] -= 10000
            if line_copy in event_lines:
                event_lines.remove(line)
            # else:
            #     print(line)
            


        if wiki.site != None: page_list = wiki.page_list(f"File:{character.wiki_name}")
        else: page_list = []

        for line in lines:
            process_file(character, line, page_list)

        for line in event_lines:
            process_file(character, line, page_list)


        ml = []
        #Guess memorial lobby unlock audio if it had no text
        if (exists(f"{args['data_audio']}/JP_{character.model_prefab_name}/{character.model_prefab_name}_MemorialLobby_0.ogg") or exists(f"{args['data_audio']}/JP_{character.model_prefab_name}/{character.model_prefab_name}_MemorialLobby_0_1.ogg")) and not memorial_unlock:
                #print(f'Found memorial lobby unlock audio for {character.wiki_name}, but no text')
                ml.append(process_file(character, {'CharacterId': character.id, 'ProductionStep': 'Release', 'DialogCategory': 'UILobbySpecial', 'DialogCondition': 'Idle', 'Anniversary': 'None', 'StartDate': '', 'EndDate': '', 'GroupId': 0, 'DialogType': 'Talk', 'ActionName': '', 'Duration': 0, 'AnimationName': 'Talk_00_M', 'LocalizeKR': '', 'LocalizeJP': '', 'VoiceClipsKr': [], 'VoiceClipsJp': [], 'LocalizeEN': ""}, page_list))

        for line in memorial_lines:
            ml.append(process_file(character, line, page_list))
        memorial_lines = [x for x in ml if x['WikiVoiceClip'] != [] or x['LocalizeJP'] != '']
            
        
        sl = []
        file_list = os.listdir(args['data_audio'] != None and f"{args['data_audio']}/JP_{character.model_prefab_name}/" or [])
        for type in standard_line_types:
            #print(f"Gathering {type}-type standard lines")
            sl += [x for x in file_list if type in x.split('_')[1]]

        standard_lines = get_standard_lines(character, sl, data.character_dialog_standard)
        for line in standard_lines:
            if f"File:{line['WikiName']}" not in page_list and wiki.site != None:
                print (f"Uploading {line['WikiName']}")
                wiki.upload(f"{args['data_audio']}/JP_{character.model_prefab_name}/{line['Filename']}", line['WikiName'], 'Character audio upload')


        with open(os.path.join(args['outdir'], f'{character.wiki_name}_dialog.txt'), 'w', encoding="utf8") as f:
            wikitext = template.render(character=character,lines=lines,event_lines=event_lines,memorial_lines=memorial_lines,standard_lines=standard_lines)
            f.write(wikitext)
            

        if wiki.site != None:
            wikipath = character.wiki_name + '/audio'

            if not wiki.page_exists(wikipath, wikitext):
                print(f'Publishing {wikipath}')
                
                wiki.site(
                action='edit',
                title=wikipath,
                text=wikitext,
                summary=f'Generated character audio page',
                token=wiki.site.token()
                )

            


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

                standard_lines.append({"CharacterId":character.id, "DialogCategory":"Standard", "VoiceClip": clip_name, "LocalizeJP":line[2].replace('</p><p>','\n').replace('<p>','').replace('</p>','').replace('<br>','\n'), "LocalizeEN":line[3].replace('</p><p>','\n').replace('<p>','').replace('</p>','').replace('<br>','\n')})

            if standard_lines: write_file(args['translation'] + '/audio/standard_' + character.wiki_name.replace(' ', '_') + '.json', standard_lines)



def get_standard_lines(character, files, dialog_data):
    lines = []

    for file in files:
        line = {}
        line['Filename'] = file
        line['VoiceClip'] = file[0:file.index('.')]
        line['WikiName'] = f"{character.wiki_name.replace(' ', '_') + '_' + file.split('_', 1)[1]}"
        line['Title'] = line['VoiceClip'].split('_', 1)[1]

        if line['WikiName'].split('.')[0] in dialog_data:
            line.update(dialog_data[line['WikiName'].split('.')[0]])
        
        if 'LocalizeJP' not in line or line['LocalizeJP'] == None: line['LocalizeJP'] = ''
        if 'LocalizeEN' not in line or line['LocalizeEN'] == None: line['LocalizeEN'] = ''
        
        line['LocalizeJP'] = len(line['LocalizeJP'])>0 and '<p>' + line['LocalizeJP'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>' or ''
        line['LocalizeEN'] = len(line['LocalizeEN'])>0 and '<p>' + line['LocalizeEN'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>' or ''

        lines.append(line)
    
    return lines



def get_memorial_lines(character, dialog_data, processing_group = 1):
    lines = []
    
    for index, line in enumerate(dialog_data):
        if line['CharacterId'] == character.id and line['DialogCategory'] == 'UILobbySpecial' and line['GroupId'] == processing_group:
            processing_group +=1
            
            line = merge_followup(index, dialog_data)
        
            if 'LocalizeEN' not in line or line['LocalizeEN'] == None: line['LocalizeEN'] = ''
            
            line['LocalizeJP'] = len(line['LocalizeJP'])>0 and '<p>' + line['LocalizeJP'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>' or ''
            line['LocalizeEN'] = len(line['LocalizeEN'])>0 and '<p>' + line['LocalizeEN'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>' or ''

            lines.append(line)

    return lines



def get_dialog_lines(character, dialog_data):
    lines = []

    for index, line in enumerate(dialog_data):
        if line['CharacterId'] == character.id and line['VoiceClipsJp'] != [] and line['DialogCategory'] != 'UILobbySpecial' :
            line = merge_followup(index, dialog_data)

            if line['VoiceClipsJp']: 
                line['VoiceClipsJp'][0] = line['VoiceClipsJp'][0].replace('__','_').replace('Memoriallobby', 'MemorialLobby')
                line['Title'] = line['VoiceClipsJp'][0].split('_', 1)[1]

                line['WikiVoiceClip'] = []
                line['WikiVoiceClip'].append(character.wiki_name.replace(' ', '_') + '_' + line['Title'])
            
            if 'LocalizeEN' not in line or line['LocalizeEN'] == None: line['LocalizeEN'] = ''

            line['LocalizeJP'] = len(line['LocalizeJP'])>0 and '<p>' + line['LocalizeJP'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>' or ''
            line['LocalizeEN'] = len(line['LocalizeEN'])>0 and '<p>' + line['LocalizeEN'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>' or ''

            #Some characters have title drop spelled out, some don't. Default to neutral game name if there's nothing.
            if line['Title'] == 'Title':
                if not line['LocalizeJP']: line['LocalizeJP'] = 'ブルーアーカイブ'
                if not line['LocalizeEN']: line['LocalizeEN'] = 'Blue Archive' 

            #this varies arbitrarily for event reruns, so it's easier to ignore
            if 'DialogConditionDetailValue' in line: line.pop('DialogConditionDetailValue')

            #remove duplicate second lobby lines
            if line['DialogCategory'] == 'UILobby2': 
                lines_copy = copy.deepcopy(lines)
                for x in lines_copy: 
                     x.pop('GroupId')

                line_copy = line.copy()
                line_copy['DialogCategory'] = 'UILobby'
                line_copy['AnimationName'] = line_copy['AnimationName'].replace('S2_','')
                line_copy.pop('GroupId')
                
                if line_copy not in lines_copy: 
                    lines.append(line)
            else: lines.append(line)

    return lines



def merge_followup(index, dialog_data):
    current = dialog_data[index]
    try: next = dialog_data[index+1]
    except IndexError: 
        return current
    
    if current['CharacterId'] == next['CharacterId'] and current['GroupId'] == next['GroupId'] and current['DialogCategory'] == next['DialogCategory'] and next['VoiceClipsJp'] == []:
        next = merge_followup(index + 1, dialog_data)
        if 'LocalizeEN' not in current or current['LocalizeEN'] == None: current['LocalizeEN'] = ''
        if 'LocalizeEN' not in next or next['LocalizeEN'] == None: next['LocalizeEN'] = ''
        current['LocalizeJP'] += '\n\n' + next['LocalizeJP']
        current['LocalizeEN'] += ( len(current['LocalizeEN'])>0 and '\n\n' or '' ) + next['LocalizeEN']
        #print(f'Merged followup at index {index}')
   
    return current
    


def process_file(character, line, page_list):
    if (line['VoiceClipsJp'] and not exists(f"{args['data_audio']}/JP_{character.model_prefab_name}/{line['VoiceClipsJp'][0]}.ogg")) or line['DialogCategory'] == 'UILobbySpecial':

        #fix script error for oCherino title line
        if line['CharacterId']==20009 and line['DialogCategory'] == 'UITitle': line['VoiceClipsJp'][0] = 'CH0164_Title'

        partial_file_path = f"{args['data_audio']}/JP_{character.model_prefab_name}/"
        partial_file_name = line['VoiceClipsJp'] and f"{line['VoiceClipsJp'][0]}" or f"{character.model_prefab_name}_MemorialLobby_{line['GroupId']}"
        
        line['VoiceClipsJp'] = []
        line['WikiVoiceClip'] = []

        if exists(f"{partial_file_path}{partial_file_name}.ogg"): 
            line['VoiceClipsJp'].append(f"{partial_file_name}")
            line['WikiVoiceClip'].append(character.wiki_name.replace(' ', '_') + '_' + f"{partial_file_name.split('_', 1)[1]}")

        i=0
        while exists(f"{partial_file_path}{partial_file_name}_{i+1}.ogg"):
            line['VoiceClipsJp'].append(f"{partial_file_name}_{i+1}")
            line['WikiVoiceClip'].append(character.wiki_name.replace(' ', '_') + '_' + f"{partial_file_name.split('_', 1)[1]}_{i+1}")
            #print(f"Added {partial_file_path}{partial_file_name}_{i+1}.ogg partial voiceline to the list")
            i += 1

        if 'Title' not in line and line['VoiceClipsJp']: line['Title'] = line['VoiceClipsJp'][0].split('_', 1)[1]
        elif 'Title' not in line: line['Title'] = ''
        line['Title'] = re.sub(r"(_\d{1})_\d{1}", "\\g<1>", line['Title'], 0, re.MULTILINE)


    if wiki.site != None:
        for index, wiki_voice_clip in enumerate(line['WikiVoiceClip']):
            if f"File:{wiki_voice_clip}.ogg" not in page_list: 
                print (f"Uploading {wiki_voice_clip}.ogg")
                wiki.upload(f"{args['data_audio']}/JP_{character.model_prefab_name}/{line['VoiceClipsJp'][index]}.ogg", f"{wiki_voice_clip}.ogg")

    return line



def save_missing_translations(name, data):
    global args
    lines = []

    for line in data:
        lines.append({'CharacterId': line['CharacterId'], 'DialogCategory': line['DialogCategory'], 'DialogCondition': line['DialogCondition'], 'GroupId': line['GroupId'], 'LocalizeKR': line['LocalizeKR'], 'LocalizeJP': line['LocalizeJP'], 'LocalizeEN': '', 'VoiceClipsJp': line['VoiceClipsJp']})

    f = open(args['translation'] + '/missing/' + name + '.json', "w", encoding='utf8' )
    f.write(json.dumps({'DataList':lines}, sort_keys=False, indent=4, ensure_ascii=False)+"\n")
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
    parser.add_argument('-wiki', nargs=2,   metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki')
    parser.add_argument('-upload_files',    action='store_false', help='Check if audio file is already on the wiki and upload it if not')
    parser.add_argument('-scavenge',        action='store_true', help='Parse existing standard line transcriptions from the wikidata')

    args = vars(parser.parse_args())
    args['character_id'] = args['character_id'] == None and '' or args['character_id']
    args['data_audio'] = args['data_audio'] == None and None or args['data_audio']
    print(args)

    if args['wiki'] != None:
        wiki.init(args)


    try:
        if (args['scavenge']): scavenge()
        else: generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
