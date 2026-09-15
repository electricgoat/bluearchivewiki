import os
import sys
import traceback
import argparse
import dataclasses
import functools
import re

from jinja2 import Environment, FileSystemLoader

from data import load_data, load_scenario_data
from model import Character
from classes.Dialog import Dialog, Clip
from shared.functions import hashkey
from shared.standard_dictionaries import build_characters
import wiki


args = {}
#data = {}
#scenario_data = {}
characters:dict[int, Character] = {}


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

# Directly appends voicegroup, for use with voicegroups that aren't associated with a playable Character entry: event minigames, summons
force_voice_group_link = {
    10066 : [90001], #Arisu (Maid) : Shooting minigame
    26009 : [90002, 90003], #Yuzu (Maid) : Shooting minigame normal, box
    10094 : [90004], #Momoi (Maid) : Shooting minigame
    10095 : [90005], #Midori (Maid) : Shooting minigame
    20005 : [30000], #Hifumi (Swimsuit) : summon SM005801
    20009 : [30001], #Cherino (Hot Spring) : summon SM0164
    20010 : [40007], #Nodoka (Hot Spring) : summon SM016501 - sm016501_summon_hit is in no voicegroup, so it stays out
    20016 : [30003], #Iroha : summon SM015601
    20034 : [30004], #Akari (New Year) : summon SM019601
    20051 : [40015], #Reisa (Magical) : summon SM032601
    20054 : [30005], #Himari (Battle) : summon SM033201
    26007 : [36001], #Ayane (Swimsuit) : summon SM017601
}

# Shun (Swimsuit) has separate voicepacks depending on combat style; internally combat styles are two mostly-separate characters
combat_styles = [
    {10143 : 'CH0355', 10144 : 'NP0288'}, #Shun (Swimsuit), Shun (Swimsuit) Kid
]

# Clips found in a character's audio directory, or in a voicegroup force_voice_group_link adds, are listed by type: the words their filenames start with past the character code,
# matched case insensitively; clip goes to the first type it matches, unless a dialog line plays it; a clip of no type goes to the Unreferenced table.
STANDARD_LINE_TYPES = [ #the Tactics and growth table
            'Formation', 'Formchange', 'Tactic', 'Battle', 'CommonSkill', 'CommonTSASkill', 'InteractionTSA', 'ExSkill', 'Summon', 'Growup', 'Relationship']

# The tables the Event lines section lists after the event dialog, titled '<event> lines', with the clip types each takes
EVENT_LINE_TABLES = {
    'Extra event':   ['EventLogin', 'EventLobby', 'EventLocation', 'EventMission', 'EventShop', 'CardShop', 'Minigame', 'Carrier'],
    'CCG':           ['Cardgame_Act'],
    'Dice Race':     ['DiceRace'],
    'Versus':        ['Versus'],
    'Concentration': ['Concentration'],
    'Main Story':    ['R89_MainScenario_Battle'], #Himari (Battle) main story battle clips
}

AUDIO_EXTENSION = '.ogg'

# Audio files an archive ships by mistake, left out of every export: '<directory>/<filename>', matched case insensitively
ignored_audio_files = [
    'JP_CH0286/ch0268_formation_select.ogg', #Juri (Part-Timer) archive carries a Misaki (Swimsuit) clip
]

audio_dir_cache:dict[str, dict[str, str]] = {}


def scan_audio_dir(scandir:str) -> dict[str, str]:
    """Index one audio directory, keyed by lowercased filename with the extension stripped.
    
    Game ships differing capitalizations but trats files as case-insensitive.
    """
    global args, audio_dir_cache

    scandir = scandir.strip('/')
    if scandir in audio_dir_cache: return audio_dir_cache[scandir]

    files:dict[str, str] = {}
    fullpath = os.path.join(args['data_audio'], scandir)

    if not os.path.isdir(fullpath):
        print(f"WARNING - audio directory {fullpath} does not exist")
    else:
        for filename in sorted(os.listdir(fullpath), key=lambda x: (x.lower(), x)): #case insensitive, so the two spellings of a clip sort together
            basename, extension = os.path.splitext(filename)
            if extension.lower() != AUDIO_EXTENSION: continue

            if any(f"{scandir.rsplit('/', 1)[-1]}/{filename}".lower() == x.lower() for x in ignored_audio_files):
                print(f"Ignoring {scandir}/{filename}")
                continue

            known = files.get(basename.lower())
            if known is None:
                files[basename.lower()] = f"{scandir}/{basename}"
                continue

            known_basename = known.rsplit('/', 1)[-1]
            keep, drop = (basename, known_basename) if basename.islower() else (known_basename, basename)
            print(f"Duplicate spellings of {scandir}/{basename.lower()}{AUDIO_EXTENSION}, keeping {keep} over {drop}")
            files[basename.lower()] = f"{scandir}/{keep}"

    audio_dir_cache[scandir] = files
    return files


def resolve_audio_path(path:str) -> str|None:
    """An extensionless audio path as it is actually spelled on disk, or None if there is no such file."""
    scandir, _, basename = path.rpartition('/')
    return scan_audio_dir(scandir).get(basename.lower())


def in_own_voice(lines:list[Dialog], other_voices:set[str]) -> list[Dialog]:
    """The lines using none of the clips named by other_voices - the codes of a switchable form's other forms."""
    return [line for line in lines if not line.clip_codes & other_voices]


home_directory_cache:dict[str, int|None] = {}


def home_directories() -> dict[str, int|None]:
    """The character each audio directory is home to, keyed by lowercased directory name.

    A character's home directory holds the clips of its default costume's dialog. A directory
    the dialog of several characters uses - the one switchable forms share - is home to none.
    """
    global data, home_directory_cache

    if not home_directory_cache:
        costume_characters = {data.costumes[x['CostumeGroupId']]['CostumeUniqueId']: x['Id'] for x in data.characters.values()
                              if x['IsPlayableCharacter'] and x['ProductionStep'] == 'Release' and x['CostumeGroupId'] in data.costumes}

        directory_characters:dict[str, set[int]] = {}
        for line in data.character_dialog:
            if line['CostumeUniqueId'] not in costume_characters: continue
            for voice_id in line['VoiceId']:
                for path in data.voice.get(voice_id, {}).get('Path', []):
                    directory_characters.setdefault(path.rsplit('/', 2)[-2].lower(), set()).add(costume_characters[line['CostumeUniqueId']])

        for directory, character_ids in directory_characters.items():
            home_directory_cache[directory] = next(iter(character_ids)) if len(character_ids) == 1 else None

    return home_directory_cache


def link_borrowed_clips(character:Character, clips:list[Clip]):
    """Point the clips borrowed from another character's home directory at that character's own files.
    """
    global characters

    for clip in clips:
        owner_id = home_directories().get(clip.directory.lower())
        if owner_id is None or owner_id == character.id or owner_id not in characters: continue

        clip.link_to(characters[owner_id].wiki_name)


def match_line_type(path:str, types:list[str]) -> str|None:
    """The line type a clip filename belongs to, if any.

    Clips are named <character code>_<type>_<index>, with an _S2_ suffix on the ones
    belonging to a character's second form. A type of several words, like Cardgame_Act, is
    matched against as many words of the filename. A file is assigned to the first type it
    matches and no other, so overlapping type names cannot list a clip twice.
    """
    parts = path.rsplit('/', 1)[-1].lower().split('_')
    starts = [1, 2] if 's2' in parts else [1]

    return next((type for type in types for start in starts if type.lower() in '_'.join(parts[start:start + type.count('_') + 1])), None)


event_costume_dir_cache:dict[int, set[str]] = {}


def event_costume_dirs() -> dict[int, set[str]]:
    """The audio directories each event costume's clips live in."""
    global data, event_costume_dir_cache

    if not event_costume_dir_cache:
        for line in data.character_dialog_event:
            for voice_id in line['VoiceId']:
                for path in data.voice.get(voice_id, {}).get('Path', []):
                    event_costume_dir_cache.setdefault(line['CostumeUniqueId'], set()).add(path.rsplit('/', 2)[-2])

    return event_costume_dir_cache


event_clip_costume_cache:dict[str, int] = {}
event_costume_rows_cache:dict[int, list[dict]] = {}
event_costume_lines_cache:dict[int, list[Dialog]] = {}


def event_clip_line(character:Character, path:str) -> Dialog|None:
    """The event dialog line that plays a clip, continuation rows included, if any does.

    An event can borrow a clip that no dialog of the character it belongs to plays. That character lists
    the clip as a standard line, and the event line is where its transcription is.
    """
    global data, event_clip_costume_cache, event_costume_rows_cache, event_costume_lines_cache

    if not event_costume_rows_cache:
        for line in data.character_dialog_event:
            event_costume_rows_cache.setdefault(line['CostumeUniqueId'], []).append(line)
            for voice_id in line['VoiceId']:
                for voice_path in data.voice.get(voice_id, {}).get('Path', []):
                    event_clip_costume_cache.setdefault(voice_path.lower(), line['CostumeUniqueId'])

    costume_id = event_clip_costume_cache.get(path.lower())
    if costume_id is None: return None

    #built the way a page lists the costume's event lines, so the text matches theirs
    if costume_id not in event_costume_lines_cache:
        event_costume_lines_cache[costume_id] = get_dialog_lines(character, event_costume_rows_cache[costume_id], costume_id)

    return next((line for line in event_costume_lines_cache[costume_id] if path.lower() in line.paths), None)


def disk_clip_prefix(file:str, maindir:str|None) -> str:
    """The code a clip found on disk keeps in its wiki name: its own, where that isn't maindir."""
    return Clip.code_of(file) if maindir is not None and maindir.upper() != Clip.code_of(file) else ''


@functools.cache
def voice_by_path() -> dict[str, dict]:
    """Voice table entries by lowercased path; where the table lists a path twice, the later entry."""
    return {x['Path'][0].lower(): x for x in data.voice.values() if x['Path']}


@functools.cache
def first_voice_ids(table:str) -> set[int]:
    """The first VoiceId of every row of a dialog table - 'character_dialog' or 'character_dialog_event'."""
    return {row['VoiceId'][0] for row in getattr(data, table) if row['VoiceId']}


@functools.cache
def operator_by_voice_id() -> dict[int, dict]:
    return {x['VoiceId'][0]: x for x in data.operator.values() if x['VoiceId']}


@functools.cache
def ccg_dialog_by_voice_id() -> dict[int, dict]:
    """Card game dialog by the voice it plays; where several rows play one voice, the first."""
    return {x['Voice']: x for x in reversed(data.minigame_ccg_open_dialog)}


@functools.cache
def voice_subtitles(voice_group_id:int) -> dict[str, dict]:
    """The subtitle of each clip of a character voice group that has one, keyed by lowercased path."""
    subtitles = {x['LocalizeCVGroup']: x for x in data.character_voice_subtitle if x['CharacterVoiceGroupId'] == voice_group_id}
    voices = {x['Path'][0].lower(): x for x in data.character_voice[voice_group_id] if x['Path']}
    return {path: subtitles[voice['LocalizeCVGroup']] for path, voice in voices.items() if voice['LocalizeCVGroup'] in subtitles}


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
    #A group event tags every member's rows with one OriginalCharacterId - the group's first member - so the id can only suggest a costume. 
    #A suggestion is taken up when the costume's clips sit in a directory this character's own dialog already uses; otherwise a group event puts all of its members' lines on each member's page.
    skipped_costume_ids = set()
    costume_dirs = event_costume_dirs()
    own_dirs = {path.rsplit('/', 2)[-2]
                for line in data.character_dialog if line['CostumeUniqueId'] == character.costume['CostumeUniqueId']
                for voice_id in line['VoiceId'] for path in data.voice.get(voice_id, {}).get('Path', [])}

    for line in data.character_dialog_event:
        if line['CostumeUniqueId'] in costume_variation_ids and line['OriginalCharacterId'] not in character_variation_ids:
            print(f"New OriginalCharacterId {line['OriginalCharacterId']} found")
            character_variation_ids.append(line['OriginalCharacterId'])

        if line['OriginalCharacterId'] in character_variation_ids and line['CostumeUniqueId'] not in costume_variation_ids:
            #a costume with no clips of its own carries text only, and is taken on the id alone
            line_dirs = costume_dirs.get(line['CostumeUniqueId'])
            if own_dirs and line_dirs and line_dirs.isdisjoint(own_dirs):
                if line['CostumeUniqueId'] not in skipped_costume_ids:
                    skipped_costume_ids.add(line['CostumeUniqueId'])
                    print(f"Skipping CostumeUniqueId {line['CostumeUniqueId']} - {sorted(line_dirs)} is not this character's audio")
                continue

            print(f"New CostumeUniqueId {line['CostumeUniqueId']} found")
            costume_variation_ids.append(line['CostumeUniqueId'])


    for character_id in block_variant_link:
        if character.id == character_id: 
            character_variation_ids.remove(block_variant_link[character_id])
            costume_variation_ids.remove(data.costumes[data.characters[block_variant_link[character_id]]['CostumeGroupId']]['CostumeUniqueId'])

    
    print(f"Processing character ids: {character_variation_ids}")
    print(f"Processing costume ids: {costume_variation_ids}")

    return character_variation_ids, costume_variation_ids



def selected_characters() -> list[Character]:
    """The characters a run covers: every playable, released one but Hoshino (Battle)'s Attacker form, narrowed down by -character_id and -character_wikiname."""
    global args, characters

    return [character for character in characters.values() if character.id != 10099 #Hoshino (Battle) Attacker form
            and (args['character_id'] is None or character.id in args['character_id'])
            and (args['character_wikiname'] is None or character.wiki_name in args['character_wikiname'])]


def generate():
    global args

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    #env.filters['colorize'] = shared.functions.colorize
    env.filters['html'] = Dialog.html
    template = env.get_template('templates/template_dialog.txt')
    

    failed = []
    for character in selected_characters():
        try:
            export_character(character, template)
        except Exception as err:
            print(f"ERROR - export of [{character.id}] {character.wiki_name} failed: {err}")
            traceback.print_exc()
            failed.append(f"[{character.id}] {character.wiki_name}")

    if failed: print(f"ERROR - {len(failed)} characters failed to export: {', '.join(failed)}")
    return failed



@dataclasses.dataclass
class AudioPage:
    """The lines of a character's audio page, by table, and the audio files they were picked from."""
    lines: list[Dialog]
    memorial_lines: list[Dialog]
    event_lines: list[Dialog]
    event_tables: dict[str, list[Dialog]]   #the lines of each EVENT_LINE_TABLES table, empty ones too
    tactics_lines: list[Dialog]
    unreferenced_lines: list[Dialog]        #the clips of the audio directory no line plays and no type takes
    candidate_files: list[str]

    @property
    def standard_lines(self) -> list[Dialog]:
        """The lines of the clips found in the audio directory rather than through the dialog tables, in page order."""
        return [line for table in self.event_tables.values() for line in table] + self.tactics_lines

    @property
    def all_lines(self) -> list[Dialog]:
        """Every line, in page order."""
        return self.lines + self.memorial_lines + self.event_lines + self.standard_lines + self.unreferenced_lines



def collect_page(character:Character) -> AudioPage|None:
    """The lines of a character's audio page as the game data has them, before translation/audio text goes over theirs. None if the character has no dialog."""
    global args
    global data, scenario_data

    normal_lines = []
    event_lines = []
    memorial_lines = []

    print (f"===== [{character.id}] {character.wiki_name} =====")

    character_variation_ids, costume_variation_ids = list_character_variants(character)


    #every switchable form's lobby lines sit under the first form's costume, so each form reads all of the forms' dialog and keeps what is spoken in its own voice
    forms = next((x for x in combat_styles if character.id in x), {})
    other_voices = {code for form_id, code in forms.items() if form_id != character.id}
    costume_ids = [data.costumes[data.characters[x]['CostumeGroupId']]['CostumeUniqueId'] for x in forms] or [character.costume['CostumeUniqueId']]

    normal_lines = in_own_voice([line for costume_id in costume_ids for line in get_dialog_lines(character, data.character_dialog, costume_id)], other_voices)
    if not normal_lines:
        print(f"WARNING - no normal lines found, skipping character")
        return None

    #extract character audio folder/codename from normal lines data
    #this isn't pretty but deriving it from character.model_prefab_name has proven unreliable
    character_code = normal_lines[0].clips[0].path.rsplit('/')[-2].replace('JP_','')
    files_scandir = normal_lines[0].clips[0].path.rsplit('/',1)[0] + '/'
    character_code = forms.get(character.id, character_code) #forms sharing a directory tell their clips apart by code

    memorial_lines = get_memorial_lines(character, data.character_dialog, files_scandir, character_code)


    # Memorial lobby unlock text from affection level script
    memorial_unlock = []
    first_memolobby_line = memorial_lines[0].localize_jp.replace('\n','') if memorial_lines else ''
    #print(f"FIRST MEMOLOBBY LINE {first_memolobby_line}")

    favor_rewards = [x for x in data.favor_rewards.values() if x['CharacterId'] == character.id and 'MemoryLobby' in x['RewardParcelType'] ]
    if favor_rewards: 
        #the scrape stops at the first memorial lobby line, so there is nothing to scrape without one
        sdf = [x for x in scenario_data.scenario_script if x['GroupId'] == favor_rewards[0]['ScenarioSriptGroupId'] and x['TextJp']] if memorial_lines else []
        for line in sdf:
            if re.sub(r"\[ruby=\w+\]|\[/ruby]|\[wa:\d+\]", "", line['TextJp']).replace('\n','').find(first_memolobby_line) > -1 or first_memolobby_line.find(re.sub(r"\[ruby=\w+\]|\[/ruby]|\[wa:\d+\]", "", line['TextJp']).replace('\n','').replace('— ','').replace('― ','')) > -1:
                break
            if line['TextJp'] and line['TextJp'].startswith('―'):
                #a copy, as the scenario rows have to stay as loaded for the page to be collected again
                memorial_unlock.append(line | {
                    'CharacterId': character.id,
                    'CostumeUniqueId': character.costume['CostumeUniqueId'],
                    'DialogCategory': 'UILobbySpecial',
                    'GroupId': 0,
                    'LocalizeJP': re.sub(r"\[.*?\]", "", line['TextJp'].replace('― ',''), count=0),
                    'LocalizeEN': re.sub(r"\[.*?\]", "", line['TextEn'].replace('— ','').replace('― ',''), count=0),
                    'VoiceId': [],
                })

        #Guess memorial lobby unlock audio if it had no text
        if len(memorial_unlock)==0 and resolve_audio_path(f"{files_scandir}{character_code}_MemorialLobby_0") is not None:
            memorial_unlock.append({
                'CharacterId': character.id,
                'CostumeUniqueId': character.costume['CostumeUniqueId'],
                'DialogCategory': 'UILobbySpecial',
                'GroupId': 0,
                'LocalizeJP': '',
                'LocalizeEN': '',
                'VoiceId': [],
            })

        memorial_lines = get_memorial_lines(character, memorial_unlock, files_scandir, character_code) + memorial_lines



    #the event tables reuse clips the base costume already has, and across costume variants
    event_line_files = Dialog.paths_of(normal_lines + memorial_lines)
    for id in costume_variation_ids:
        for line in in_own_voice(get_dialog_lines(character, data.character_dialog_event, id), other_voices):
            line_files = line.paths
            if line_files and line_files & event_line_files: continue #costume variants and the base costume share clips
            event_line_files |= line_files
            event_lines.append(line)
    print(f"Total event lines: {len(event_lines)}")




    # Every clip in the character's own directory
    candidate_files = [x for x in scan_audio_dir(files_scandir).values() if Clip.code_of(x) not in other_voices]
    for voice_group in force_voice_group_link.get(character.id, []):
        for voice_line in data.character_voice[voice_group]:
            for path in voice_line['Path']:
                resolved = resolve_audio_path(path)
                if resolved is None: print(f"WARNING - voice group {voice_group} file {path} is missing from the audio directory")
                elif resolved not in candidate_files: candidate_files.append(resolved)

    # A clip backing a line that was already emitted is not a candidate for another section 
    used_paths = Dialog.paths_of(normal_lines + memorial_lines + event_lines)


    #the other clips go to the first table taking their type
    line_types = STANDARD_LINE_TYPES + [type for types in EVENT_LINE_TABLES.values() for type in types]
    file_types = {path: match_line_type(path, line_types) for path in candidate_files if path.lower() not in used_paths}

    def table_lines(types:list[str]) -> list[Dialog]:
        lines = []
        for type in types:
            files = [path for path, file_type in file_types.items() if file_type == type]
            if not files: continue
            print(f'Found {len(files)} {type}-type lines')
            lines += get_standard_lines(character, files, type, maindir=character_code)
        return lines

    tactics_lines = table_lines(STANDARD_LINE_TYPES)
    event_tables = {name: table_lines(types) for name, types in EVENT_LINE_TABLES.items()}
    unreferenced_files = [path for path, file_type in file_types.items() if file_type is None]
    if unreferenced_files: print(f'Found {len(unreferenced_files)} unreferenced files')
    unreferenced_lines = get_standard_lines(character, unreferenced_files, 'Unreferenced', maindir=character_code)

    page = AudioPage(normal_lines, memorial_lines, event_lines, event_tables, tactics_lines, unreferenced_lines, candidate_files)

    clips = Dialog.clips_of(page.all_lines)
    for clip in clips: clip.file = resolve_audio_path(clip.path)
    link_borrowed_clips(character, clips)

    return page


def apply_dialog_aux(character:Character, lines:list[Dialog]):
    """Show the text translation/audio has for the character's lines in place of the game data's - see dialog_scrape.py."""
    global data

    aux = data.character_dialog_aux.get(character.id, {})
    for line in lines:
        record = aux.get(line.aux_key)
        if record is not None: line.aux_jp, line.aux_en = record.get('LocalizeJP'), record.get('LocalizeEN')

    keys = {line.aux_key for line in lines}
    unused = sorted(record['VoiceClip'] for key, record in aux.items() if key not in keys)
    if unused: print(f"WARNING - translation/audio has text for clips that start no line of the page: {unused}")



def export_character(character:Character, template):
    """Build one character's audio page, upload its clips and publish the page."""
    global args

    page = collect_page(character)
    if page is None: return
    if not args['noaux']: apply_dialog_aux(character, page.all_lines)
    clips = Dialog.clips_of(page.all_lines)

    #clips in the character's own directory that no line picked up
    unused_files = {x.rsplit('/')[-1].lower() for x in page.candidate_files}.difference({x.lower() for line in page.all_lines for x in line.used_files})
    if unused_files: print(f"WARNING - unused files: {sorted(unused_files)}")

    #looked up per directory, so a line borrowing another character's clip isn't reported as missing
    missing_files = sorted({clip.path for clip in clips if clip.file is None})
    if missing_files: print(f"WARNING - missing files: {missing_files}")

    #Wiki clip names have to map one to one onto audio files: a name built from two
    #different clips uploads one over the other, and a clip listed twice is a duplicate row.
    clip_sources = {}
    for clip in clips:
        clip_sources.setdefault(clip.wiki_name, []).append(clip.path.lower())

    colliding_clips = {name: sorted(set(paths)) for name, paths in clip_sources.items() if len(set(paths)) > 1}
    if colliding_clips: print(f"WARNING - wiki clip names still built from more than one audio file: {colliding_clips}")

    repeated_clips = sorted(name for name, paths in clip_sources.items() if len(paths) > len(set(paths)))
    if repeated_clips: print(f"WARNING - clips listed more than once: {repeated_clips}")

    #clip titles are spelled by the glossary, see Clip.title_of
    unknown_words = {word: clip.wiki_name for clip in clips for word in Clip.unknown_words(clip.title)}
    if unknown_words: print(f"WARNING - clip title words missing from CLIP_TITLE_WORDS in shared/glossary.py: {unknown_words}")



    if wiki.site != None:
        page_list = wiki.page_list(f"File:{character.wiki_name}")
    else: page_list = []
    #print(f"Existing pages list: {page_list}")


    for line in page.all_lines:
        process_files(character, line, page_list)


    missing_sl_jp_count = len([x for x in page.standard_lines if x.wiki_localization_jp==''])
    missing_sl_en_count = len([x for x in page.standard_lines if x.wiki_localization_en==''])
    print (f"Missing standard lines text counts JP: {missing_sl_jp_count}, EN: {missing_sl_en_count}")


    with open(os.path.join(args['outdir'], f'{character.wiki_name}_dialog.txt'), 'w', encoding="utf8") as f:
        wikitext = template.render(
            character=character, 
            lines=page.lines,
            event_lines=page.event_lines,
            memorial_lines=page.memorial_lines,
            tactics_lines=page.tactics_lines,
            event_tables=[(name, lines) for name, lines in page.event_tables.items() if lines],
            unreferenced_lines=page.unreferenced_lines,
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


def get_standard_lines(character, files, dialog_category, maindir=None) -> list[Dialog]:
    """The lines of clips found in the audio directory, all of one type - see match_line_type."""
    global data
    subtitles = {} #the character's own voice group's, over those of the voice groups force_voice_group_link adds
    for voice_group_id in force_voice_group_link.get(character.id, []) + [character.costume['CharacterVoiceGroupId']]:
        subtitles |= voice_subtitles(voice_group_id)
    lines = []

    for file in files:
        voice_id = voice_by_path().get(file.lower(), {}).get('Id')
        if voice_id and voice_id in first_voice_ids('character_dialog'): continue #listed with the character's dialog

        # The game's subtitles for the clip, else the text of the operator line or card game dialog playing it, else that of an event line borrowing it
        subtitle = subtitles.get(file.lower(), {})
        localize_jp, localize_en = subtitle.get('LocalizeJP') or '', subtitle.get('LocalizeEN') or ''

        operator = operator_by_voice_id().get(voice_id) if voice_id else None
        if operator is not None and hashkey(operator['TextLocalizeKey']) in data.localization:
            text = data.localization[hashkey(operator['TextLocalizeKey'])]
            localize_jp, localize_en = localize_jp or text.get('Jp') or '', localize_en or text.get('En') or ''

        card_game_dialog = ccg_dialog_by_voice_id().get(voice_id) if voice_id else None
        if card_game_dialog is not None and card_game_dialog['Dialog'] in data.localization:
            text = data.localization[card_game_dialog['Dialog']]
            localize_jp, localize_en = localize_jp or text.get('Jp') or '', localize_en or text.get('En') or ''

        if not localize_jp or not localize_en:
            event_line = event_clip_line(character, file)
            if event_line is not None:
                localize_jp, localize_en = localize_jp or event_line.wiki_localization_jp, localize_en or event_line.wiki_localization_en

        lines.append(Dialog.construct_standard(character, file, disk_clip_prefix(file, maindir), localize_jp, localize_en, dialog_category = dialog_category))

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

            #merge followup lines instead of generating new ones - voiced ones too, within a memorial lobby scene
            dialog.add_to(lines, voiced_followups=True)
    
    return lines



def get_dialog_lines(character, dialog_data, costume_id) -> list[Dialog]:
    global data
    lines:list[Dialog] = []
    kept:dict[tuple, Dialog] = {} #the line kept for each duplicate key

    for line in dialog_data:
        if line['DialogCategory'] == 'UILobbySpecial':
            #memorial lobby line
            continue

        if line['CostumeUniqueId'] != costume_id:
            #print(f"Skipping a line, wrong costume id")
            continue
        

        dialog = Dialog.from_data(character.wiki_name, data.voice, line, line['AddVoice'] if 'AddVoice' in line else None)

        #Deduplicate lines - the tables repeat an event's dialog once per rerun, see Dialog.duplicate_key
        key = dialog.duplicate_key
        if key in kept:
            #a rerun repeats a line word for word, so only a repeat with other text is worth reporting
            if dialog.clips and kept[key].localize_jp != dialog.localize_jp: print(f"Deduplicated line with VoiceId {line['VoiceId']} - its text differs from the line kept")
            continue
        kept[key] = dialog

        #merge followup lines instead of generating new ones
        dialog.add_to(lines)
        

    #print(f"Gathered {len(lines)} dialog lines for costume id {costume_id}")
    return lines



def process_files(character, dialog:Dialog, page_list:list):
    global args

    if wiki.site == None: return
    page_list_lower = [x.lower() for x in page_list]

    for clip in dialog.clips:
        if clip.owner is not None:
            print(f"File:{clip.wiki_name}.ogg is a {clip.owner} clip, uploaded with their dialog")
            continue

        wikiname = f"File:{clip.wiki_name}.ogg"#.replace("Seia_(Swimsuit)", "Seia_(Swimsuit)_GL").replace("Seia (Swimsuit)", "Seia (Swimsuit) GL")
        wikitext = f"[[Category:Character dialog]]\r\n[[Category:{character.wiki_name} dialog]]"#.replace("Seia_(Swimsuit)", "Seia_(Swimsuit)_GL").replace("Seia (Swimsuit)", "Seia (Swimsuit) GL")

        if clip.file is None:
            print(f"Local file not found at {os.path.join(args['data_audio'], f'{clip.path}{AUDIO_EXTENSION}')}")
            continue
        localfilename = clip.file + AUDIO_EXTENSION

        if wikiname in page_list:
            print(f"File:{clip.wiki_name}.ogg is already in known pages list")
            if args['force_upload']:
                wiki.upload(os.path.join(args['data_audio'], localfilename),
                    f"{clip.wiki_name}.ogg",
                    'Character dialog upload',
                    wikitext)
            if args['update_files'] and not wiki.page_exists(wikiname, wikitext):
                wiki.publish(wikiname, wikitext, 'Updated audio categories')
                print('... updated file categories.')
            continue

        if wikiname.lower() in page_list_lower:
            i = page_list_lower.index(wikiname.lower())
            print(f"File:{clip.wiki_name}.ogg is in known pages list, but capitalized as {page_list[i]}")
            wiki.move(page_list[i], wikiname, 'Name capitalization changed', noredirect=False)
            #no continue here because we will try and upload the new file on the chance it's data changed

        print (f"Uploading {localfilename} → {wikiname}")
        wiki.upload(os.path.join(args['data_audio'], localfilename),
                    wikiname,
                    'Character dialog upload',
                    wikitext)


def init_data():
    global args, data, scenario_data, characters
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    scenario_data = load_scenario_data(args['data_primary'], args['data_secondary'], args['translation'])
    characters = build_characters(data)


def argument_parser() -> argparse.ArgumentParser:
    """The arguments dialog.py and dialog_scrape.py share."""
    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-data_audio',      metavar='DIR', required=True, help='Audio files directory')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-character_id',    nargs="*", type=int, metavar='ID', help='Id(s) of a characters to export')
    parser.add_argument('-character_wikiname', nargs="*", type=str, metavar='Wikiname', help='Name(s) of a characters to export')
    parser.add_argument('-wiki', nargs=2,   metavar=('LOGIN', 'PASSWORD'), help='Log in to the wiki - to publish data, for dialog.py')

    return parser


def init(parsed_args:dict):
    """Take the parsed arguments, log in to the wiki if asked to, and load the data."""
    global args

    args = parsed_args
    print(args)

    if args['wiki'] != None:
        wiki.init(args)

    if args['character_wikiname']:
        args['character_wikiname'] = [x.replace('_',' ').strip() for x in args['character_wikiname']]

    init_data()


def main():
    parser = argument_parser()
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki_section',    metavar='SECTION NAME', help='Name of a page section to be updated')
    parser.add_argument('-update_files',    action='store_true', help='Check audio file wikitext and update it')
    parser.add_argument('-force_upload',    action='store_true', help='Try reuploading files even if one already exists.')
    parser.add_argument('-noaux',           action='store_true', help='Skip the aux translations, for debugging: dialog_scrape.py compares this to published pages to detect overwrites')

    parsed_args = vars(parser.parse_args())
    #pages published without the translation/audio text would lose it on the wiki - and in translation/audio, with the next dialog_scrape.py run
    if parsed_args['noaux'] and parsed_args['wiki']: parser.error("-noaux can't be combined with -wiki")

    init(parsed_args)
    if generate(): sys.exit(1)


if __name__ == '__main__':
    main()
