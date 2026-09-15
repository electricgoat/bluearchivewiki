from model import Character
from shared.glossary import CLIP_TITLE_WORDS
import re


class Dialog(object):
    def __init__(self, character_id:int, character_costume_id:int, display_order:int, production_step:str, dialog_category:str, dialog_condition:str, anniversary:str, start_date:str, end_date:str, group_id:int, localize_kr:str, localize_jp:str, localize_en:str, localize_cvgroup:str, voice_id:list[int], unlock_favor_rank:int, unlock_equip_weapon:bool, voice:list, character_wiki_name:str):
        self.character_id = character_id
        self.character_costume_id = character_costume_id
        self.display_order = display_order
        self.production_step = production_step
        self.dialog_category = dialog_category
        self.dialog_condition = dialog_condition
        self.anniversary = anniversary
        self.start_date = start_date
        self.end_date = end_date
        self.group_id = group_id
        self.localize_kr = localize_kr
        self.localize_jp = localize_jp
        self.localize_en = localize_en
        self.localize_cvgroup = localize_cvgroup
        self.voice_id:list = voice_id
        self.unlock_favor_rank:int = unlock_favor_rank
        self.unlock_equip_weapon:bool = unlock_equip_weapon

        self.voice:list[Voice] = voice
        self.character_wiki_name = character_wiki_name
        self.followup:list[Dialog] = []
        self.aux_jp:str|None = None     #the text translation/audio has for the line, shown in place of the game data's - see dialog_scrape.py
        self.aux_en:str|None = None

    def __repr__(self):
        return str(self.__dict__)


    @staticmethod
    def join_localization(*text:str) -> str:
        return '\n\n'.join(x for x in text if x and x.strip())


    @property
    def wiki_localization_kr(self):
        return Dialog.join_localization(self.localize_kr, *[x.localize_kr for x in self.followup])

    @property
    def wiki_localization_jp(self):
        return self.aux_jp if self.aux_jp is not None else Dialog.join_localization(self.localize_jp, *[x.localize_jp for x in self.followup])

    @property
    def wiki_localization_en(self):
        return self.aux_en if self.aux_en is not None else Dialog.join_localization(self.localize_en, *[x.localize_en for x in self.followup])


    @property
    def clips(self) -> list['Clip']:
        """The clips the line plays, across its voices. Those of the continuation rows merged into it aren't included."""
        return [clip for voice in self.voice for clip in voice.clips]

    @property
    def paths(self) -> set[str]:
        """The line's clip paths, lowercased.

        Full paths rather than filenames, so clips that share a filename across two
        directories - which happens whenever an event borrows another character's - stay
        distinct.
        """
        return {clip.path.lower() for clip in self.clips}

    @staticmethod
    def clips_of(lines:list['Dialog']) -> list['Clip']:
        """The clips of all the given lines."""
        return [clip for line in lines for clip in line.clips]

    @staticmethod
    def paths_of(lines:list['Dialog']) -> set[str]:
        """The clip paths of all the given lines, lowercased."""
        return set().union(*(line.paths for line in lines))

    @property
    def clip_codes(self) -> set[str]:
        """The character codes of the line's clips - which voice it speaks in."""
        return {clip.code for clip in self.clips}

    @property
    def used_files(self) -> list[str]:
        return [clip.filename for clip in self.clips]

    @property
    def aux_key(self) -> str|None:
        """What translation/audio keeps the line's text under: its first clip's path, lowercased. A line without clips has none."""
        return self.clips[0].path.lower() if self.clips else None


    @property
    def duplicate_key(self) -> tuple:
        """What makes two table rows the same line.

        The tables repeat an event's dialog once per rerun, at times under other VoiceIds of the same clips, so a
        voiced row is the clips it plays. Rows that only share their text are different lines - a character can
        say "……。" in several of them. A continuation row has no clips of its own, and is its text within its group.
        """
        return ('clips', frozenset(self.paths)) if self.clips else ('continuation', self.localize_jp, self.group_id)

    def continues(self, line:'Dialog') -> bool:
        """Whether this row carries on the given line: the same group, further along it."""
        return self.group_id == line.group_id and self.display_order > line.display_order

    def add_to(self, lines:list['Dialog'], voiced_followups:bool = False):
        """Add the row to a list of lines, merged into the last line if it continues that one.

        In dialog tables only a row with no voice of its own continues a line, and such a row that continues
        nothing is dropped. With voiced_followups, as in the memorial lobby tables, any row can continue a line.
        """
        if not lines: lines.append(self)
        elif (voiced_followups or not self.voice) and self.continues(lines[-1]): lines[-1].followup.append(self)
        elif voiced_followups or self.voice: lines.append(self)


    @property
    def wikitext_voice_title(self):
        titles = []
        for voice in self.voice:
            if voice.clips and voice.clips[0].title.startswith('MemorialLobby_'): return re.sub(r"(_\d{1})_\d{1}", "\\g<1>", self.voice[0].clips[0].title, 0, re.MULTILINE)
            titles += [clip.title for clip in voice.clips]
        return '<br>'.join(titles)

    @property
    def wikitext_voice_clips(self):
        return '<br>'.join(clip.wikitext for clip in self.clips)


    @classmethod
    def from_data(cls, character_wiki_name, voice_data, line, add_voice:list = None):
        voice = []
        for voice_id in line['VoiceId']:
            voice.append(Voice.from_data(voice_data[voice_id], character_wiki_name))

        if add_voice:
            for voiceline_data in add_voice:
                #print(f"Adding extra voice data: {voiceline_data}")
                voice.append(Voice.from_data(voiceline_data, character_wiki_name))

        #Some characters have title drop spelled out, some don't. Default to neutral game name if there's nothing.
        if line['DialogCategory'] == 'UITitle':
            if not line['LocalizeJP']: line['LocalizeJP'] = 'ブルーアーカイブ'
            if not line['LocalizeEN']: line['LocalizeEN'] = 'Blue Archive'

        return cls(
            character_id = line.get('CharacterId', 0),
            character_costume_id = line['CostumeUniqueId'],
            display_order = line.get('DisplayOrder', 0),
            production_step = line.get('ProductionStep', 'Release'),
            dialog_category = line['DialogCategory'],
            dialog_condition = line.get('DialogCondition', ''),
            anniversary = line.get('Anniversary', "None"),
            start_date = line.get('StartDate', ''),
            end_date = line.get('EndDate', ''),
            group_id = line['GroupId'],
            localize_kr = line.get('LocalizeKR', ''),
            localize_jp = line.get('LocalizeJP', ''),
            localize_en = line.get('LocalizeEN', ''),
            localize_cvgroup = '',
            voice_id = line['VoiceId'],
            unlock_favor_rank = line.get('UnlockFavorRank', 0),
            unlock_equip_weapon = line.get('UnlockEquipWeapon', False),

            voice = voice,
            character_wiki_name = character_wiki_name,
        )


    @classmethod
    def construct_standard(cls, character:Character, file, prefix='', localize_jp='', localize_en='', dialog_category = 'Standard'):
        """A line for a clip found on disk."""
        return cls(
            character_id = character.id,
            character_costume_id = character.costume['CostumeUniqueId'],
            display_order = 0,
            production_step = 'Release',
            dialog_category = dialog_category,
            dialog_condition = "",
            anniversary = "None",
            start_date = "",
            end_date = "",
            group_id = 900,
            localize_kr = '',
            localize_jp = localize_jp,
            localize_en = localize_en,
            localize_cvgroup = '',
            voice_id = [],
            unlock_favor_rank = 0,
            unlock_equip_weapon = False,

            voice = [Voice.from_data({'Path':[file]}, character.wiki_name, prefix)],
            character_wiki_name = character.wiki_name,
        )


    @staticmethod
    def html(string:str) -> str:
        return len(string.replace('\n',''))>0 and '<p>' + string.replace("\n\n",'</p><p>').replace("\n",'<br>').strip() + '</p>' or ''



class Voice(object):
    def __init__(self, id:int, unique_id:int, nation:list[str], clips:list['Clip']):
        self.id = id
        self.unique_id = unique_id
        self.nation = nation
        self.clips = clips


    def __repr__(self):
        return str(self.__dict__)


    @classmethod
    def from_data(cls, data, character_wiki_name, file_prefix=''):
        return cls(
            id = data.get('Id', 0),
            unique_id = data.get('UniqueId', 0),
            nation = data.get('Nation', ['All']),
            #volume = 'Volume' in data and data['Volume'] or 1,
            clips = [Clip(path, character_wiki_name, file_prefix) for path in data['Path']],
        )



class Clip(object):
    """One audio file a line plays, and the wiki file it is published as."""
    glossary = {word.lower(): word for word in CLIP_TITLE_WORDS}

    def __init__(self, path:str, character_wiki_name:str, prefix:str = ''):
        self.path = path                    #extensionless, as the line's data gives it - or as on disk, for a clip found in a directory
        self.title = Clip.title_of(path)    #the filename past its character code, spelled by the glossary
        self.wiki_name = Clip.name_for(character_wiki_name, self.title, prefix) #wiki file name, without the File: namespace and extension
        self.owner:str|None = None          #wiki name of the character the clip is borrowed from
        self.file:str|None = None           #extensionless path as spelled on disk, once looked up; None if the file is missing


    def __repr__(self):
        return str(self.__dict__)


    @staticmethod
    def title_of(path:str) -> str:
        """A clip's title: its filename past the character code, each word capitalized as CLIP_TITLE_WORDS in shared/glossary.py has it.

        The game capitalizes clip filenames inconsistently, and the filesystem ignores case, so a path's spelling
        can't be relied on. A word the glossary lacks keeps the spelling the path gives it.
        """
        return '_'.join(Clip.glossary.get(word.lower(), word) for word in path.rsplit('/', 1)[-1].split('_')[1:])

    @staticmethod
    def unknown_words(title:str) -> list[str]:
        """The words of a title the glossary lacks. Numbers aren't words."""
        return [word for word in title.split('_') if word and not word.isdigit() and word.lower() not in Clip.glossary]

    @staticmethod
    def name_for(character_wiki_name:str, title:str, prefix:str = '') -> str:
        """The wiki file name of a character's clip, without the File: namespace and extension.

        prefix is the code of a clip that isn't named by the character's own code, and stays in its name.
        """
        return f"{character_wiki_name.replace(' ', '_')}_{prefix + '_' if prefix else ''}{title}"

    @staticmethod
    def code_of(path:str) -> str:
        """The character code a clip filename starts with, uppercased."""
        return path.rsplit('/', 1)[-1].split('_', 1)[0].upper()

    @property
    def code(self) -> str:
        return Clip.code_of(self.path)

    @property
    def directory(self) -> str:
        """The audio directory the clip sits in."""
        return self.path.rsplit('/', 2)[-2]

    @property
    def filename(self) -> str:
        return self.path.rsplit('/', 1)[-1]


    def link_to(self, owner:str):
        """Point the clip at the file its owner publishes it as, rather than a copy under the borrowing character's name."""
        self.wiki_name = Clip.name_for(owner, self.title)
        self.owner = owner

    @property
    def wikitext(self) -> str:
        note = f'<ref name="{self.owner} voice clip" group="note">This line uses a [[{self.owner}]] voice clip.</ref>' if self.owner else ''
        return f"[[File:{self.wiki_name}.ogg]]{note}"
