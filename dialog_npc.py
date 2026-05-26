import os
import sys
import traceback
import argparse

from jinja2 import Environment, FileSystemLoader

from data import load_data, load_scenario_data
from classes.Dialog import Dialog
import wiki



args = {}
data = {}
scenario_data = {}

ARENA_LINE_TYPES = ['ArenaCombatVictory', 'ArenaCombatDefeat', 'ArenaCombatStart']
BATTLEPASS_LINE_TYPES = ['UIBattlePassLogin', 'UIBattlePassLobby', 'UIBattlePassMission', 'UIBattlePass']


def generate_npc_scandir():
    global args, data, scenario_data

    character_wikiname = args['character_wikiname']
    
    # Build lookup tables from voice data with normalized paths (forward slashes, lowercase)
    voice_by_path_lower = {
        x['Path'][0].replace('\\', '/').lower(): x 
        for x in data.voice.values() if len(x['Path'])
    }
    
    # Build lookup by filename only (for case-insensitive matching)
    # voice_by_filename_lower = {
    #     x['Path'][0].rsplit('/', 1)[-1].lower(): x 
    #     for x in data.voice.values() if len(x['Path'])
    # }

    # Build character dialog lookup by voice ID
    character_dialog_by_voice_id = {
        voice_id: item
        for item in data.character_dialog
        for voice_id in item['VoiceId']
    }
    
    # Build battlepass dialog lookup by voice ID
    battlepass_dialog_by_voice_id = {
        voice_id: item
        for item in data.character_dialog_battlepass
        for voice_id in item['VoiceId']
    }
    
    # Build file list from directory
    scandir_path = os.path.join(args['data_audio'], 'Audio', 'VOC_JP', args['scandir'])
    
    if not os.path.exists(scandir_path):
        print(f"ERROR: Directory not found: {scandir_path}")
        return

    file_list = {
        x.split('.')[0]: {
            'localpath': os.path.join('Audio/VOC_JP/', args['scandir'], x),
            'respath': f"Audio/VOC_JP/{args['scandir']}/{x.split('.')[0]}",  # Normalized with forward slashes
            'filename': x.split('.')[0],
            'voice_id': None,
            'is_character_dialog': False,
            'is_battlepass_dialog': False,
            'wikitext_voice_title': x.split('.')[0].split('_', 1)[-1],
            'wikitext_voice_clips': x,
            'localize_jp': '',
            'localize_en': '',
            'dialog_category': None,
        }
        for x in os.listdir(scandir_path)
    }
    
    for name, file in file_list.items():
        # Capitalize line types since actual files tend to be lowercase now
        title = file['wikitext_voice_title']
        clip = file['wikitext_voice_clips']

        types = BATTLEPASS_LINE_TYPES + ARENA_LINE_TYPES
        for index, lowertype in enumerate([x.lower() for x in types]):
            title = title.replace(lowertype, types[index])
            clip = clip.replace(lowertype, types[index])
        file['wikitext_voice_title'] = title
        file['wikitext_voice_clips'] = clip
        
        # Replace filename prefix with character_wikiname in wikitext_voice_clips
        clips_parts = file['wikitext_voice_clips'].split('.', 1)
        clips_base = clips_parts[0]
        clips_ext = f".{clips_parts[1]}" if len(clips_parts) > 1 else ""
        
        if '_' in clips_base:
            clips_suffix = clips_base.split('_', 1)[1]
            file['wikitext_voice_clips'] = f"{character_wikiname}_{clips_suffix}{clips_ext}"
    
    print(f"Found {len(file_list)} files in {args['scandir']}")

    # Match files to voice and dialog data
    unmatched_voice = []
    unmatched_dialog = []
    
    for name, file in file_list.items():
        file['voice_id'] = None
        respath_norm = file['respath'].lower()

        if respath_norm in voice_by_path_lower:
            file['voice_id'] = voice_by_path_lower[respath_norm]['Id']

        if file['voice_id']:
            file['is_character_dialog'] = file['voice_id'] in character_dialog_by_voice_id
            file['is_battlepass_dialog'] = file['voice_id'] in battlepass_dialog_by_voice_id
        
        if file['voice_id'] is None:
            unmatched_voice.append(name)
        if not file['is_character_dialog'] and not file['is_battlepass_dialog']:
            unmatched_dialog.append(name)

    print(f"Matched {len(file_list) - len(unmatched_voice)}/{len(file_list)} entries in Voice")
    print(f"Matched {len(file_list) - len(unmatched_dialog)}/{len(file_list) - len(unmatched_voice)} entries in CharacterDialog/BattlePassDialog")
    
    if unmatched_voice:
        print(f"WARNING - Unmatched voice files (not in Voice data): {unmatched_voice}")
    if unmatched_dialog:
        print(f"WARNING - Unmatched dialog entries (not in CharacterDialog/BattlePass): {unmatched_dialog}")

    # Extract localization data from file matches
    for name, file in file_list.items():
        if not file['voice_id']:
            continue

        voice_id = file['voice_id']
        
        # Try to get localization from character_dialog first
        if voice_id in character_dialog_by_voice_id:
            dialog_entry = character_dialog_by_voice_id[voice_id]
            file['dialog_category'] = dialog_entry.get('DialogCategory', 'CharacterDialog')
            file['localize_jp'] = dialog_entry.get('LocalizeJP', '')
            file['localize_en'] = dialog_entry.get('LocalizeEN', '')
        
        # Try to get localization from battlepass_dialog if not found in character_dialog
        elif voice_id in battlepass_dialog_by_voice_id:
            dialog_entry = battlepass_dialog_by_voice_id[voice_id]
            file['dialog_category'] = dialog_entry.get('DialogCategory', 'BattlePass')
            file['localize_jp'] = dialog_entry.get('LocalizeJP', '')
            file['localize_en'] = dialog_entry.get('LocalizeEN', '')


    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['html'] = Dialog.html
    template = env.get_template('templates/template_npc_dialog.txt')

    with open(os.path.join(args['outdir'], f"npc_{character_wikiname}_dialog.txt"), 'w', encoding="utf8") as f:
        wikitext = template.render(
            character_wikiname=character_wikiname,
            file_list=file_list,
            character_dialog=character_dialog_by_voice_id,
            battlepass_dialog=battlepass_dialog_by_voice_id
        )
        f.write(wikitext)
    
    print(f"Exported NPC dialog to {os.path.join(args['outdir'], f'npc_{character_wikiname}_dialog.txt')}")

    if wiki.site is not None:
        process_files_npc(character_wikiname, file_list)

        wikipath = character_wikiname + '/audio'

        if args['wiki_section'] is not None:
            wiki.update_section(wikipath, args['wiki_section'], wikitext)
        elif not wiki.page_exists(wikipath, wikitext):
            print(f'Publishing {wikipath}')
            wiki.publish(wikipath, wikitext, f'Generated NPC audio page')



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
        


def init_data():
    global args, data, scenario_data
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    scenario_data = load_scenario_data(args['data_primary'], args['data_secondary'], args['translation'])


def main():
    global args, data, scenario_data

    parser = argparse.ArgumentParser(
        description='Files-first export of NPC dialog'
        )

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-data_audio',      metavar='DIR', required=True, help='Audio files directory')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-character_id', type=int, required=True, metavar='ID', help='Id of a character to export')
    parser.add_argument('-character_wikiname', type=str, required=True, metavar='Wikiname', help='Wiki name for the NPC')
    parser.add_argument('-scandir',         type=str, metavar='DIR', required=True, help='Audio subdirectory to scan (e.g., JP_NPC0001)')
    parser.add_argument('-wiki',            nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki')
    parser.add_argument('-wiki_section',    metavar='SECTION NAME', help='Name of a page section to be updated')
    parser.add_argument('-update_files',    action='store_true', help='Check audio file wikitext and update it')
    parser.add_argument('-force_upload',    action='store_true', help='Try reuploading files even if one already exists.')

    args = vars(parser.parse_args())
    
    print("Arguments:", args)

    if args['wiki'] is not None:
        wiki.init(args)

    try:
        init_data()
        generate_npc_scandir()
    except Exception as e:
        parser.print_help()
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
