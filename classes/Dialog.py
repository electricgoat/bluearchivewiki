from model import Character
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

    def __repr__(self):
        return str(self.__dict__)
    

    @property
    def wiki_localization_kr(self):
        text = [self.localize_kr]
        for x in self.followup:
            text.append(x.localize_kr)
        return '\n\n'.join(text)
    
    @property
    def wiki_localization_jp(self):
        text = [self.localize_jp]
        for x in self.followup:
            text.append(x.localize_jp)
        return '\n\n'.join(text)
    
    @property
    def wiki_localization_en(self):
        text = [self.localize_en]
        for x in self.followup:
            text.append(x.localize_en)
        return '\n\n'.join(text)


    @property
    def wikitext_voice_title(self):
        titles = []
        for voice in self.voice: 
            if len(voice.titles) and voice.titles[0].startswith('MemorialLobby_'): return re.sub(r"(_\d{1})_\d{1}", "\\g<1>", self.voice[0].titles[0], 0, re.MULTILINE)
            titles += [x for x in voice.titles]       
        return '<br>'.join(titles)

    @property
    def wikitext_voice_clips(self):
        clips = []
        for voice in self.voice: 
            clips += [f"[[File:{x}.ogg]]" for x in voice.wiki_voice_clips]
        return '<br>'.join(clips)
    

    @property
    def used_files(self):
        list = []
        for v in self.voice:
            for filepath in v.path: list.append(filepath[filepath.rfind('/')+1:])
        return list
    

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
    def construct_standard(cls, character:Character, localization, file, file_wikititle=None, file_prefix='', production_step='Release', dialog_category = 'Standard'):
        voice = Voice.from_data({'Path':[file]}, character.wiki_name, file_prefix, [file_wikititle])

        return cls(
            character_id = character.id,
            character_costume_id = character.costume['CostumeUniqueId'],
            display_order = 0,
            production_step = production_step,
            dialog_category = dialog_category,
            dialog_condition = "",
            anniversary = "None",
            start_date = "",
            end_date = "",
            group_id = 900,
            localize_kr = voice.wiki_voice_clips[0] in localization and localization[voice.wiki_voice_clips[0]].get('LocalizeKR', '') or '',
            localize_jp = voice.wiki_voice_clips[0] in localization and localization[voice.wiki_voice_clips[0]].get('LocalizeJP', '') or '', 
            localize_en = voice.wiki_voice_clips[0] in localization and localization[voice.wiki_voice_clips[0]].get('LocalizeEN', '') or '',
            localize_cvgroup = voice.wiki_voice_clips[0] in localization and localization[voice.wiki_voice_clips[0]].get('LocalizeCVGroup','') or '',
            voice_id = [],
            unlock_favor_rank = 0,
            unlock_equip_weapon = False,

            voice = [voice],
            character_wiki_name = character.wiki_name,
        )
    

    @staticmethod
    def html(string:str) -> str:
        return len(string.replace('\n',''))>0 and '<p>' + string.replace("\n\n",'</p><p>').replace("\n",'<br>').strip() + '</p>' or ''
    


class Voice(object):
    def __init__(self, id:int, unique_id:int, nation:list[str], path:list[str], titles:list[str], wiki_voice_clips:list[str]):
        self.id = id
        self.unique_id = unique_id
        self.nation = nation
        self.path = path
        self.titles = titles
        self.wiki_voice_clips = wiki_voice_clips


    def __repr__(self):
        return str(self.__dict__)
    
    
    @classmethod
    def from_data(cls, data, character_wiki_name, file_prefix='', preset_titles:list|None = None):
        titles = []

        if preset_titles:
            titles = preset_titles
        else:
            for filepath in data['Path']:
                titles.append(filepath[filepath.rfind('/'):].split('_', 1)[1])

        wiki_voice_clips = []
        for title in titles:
            wiki_voice_clips.append(f"{character_wiki_name.replace(' ','_')}_{file_prefix != '' and file_prefix+'_' or ''}{title}")

        return cls(
            id = data.get('Id', 0),
            unique_id = data.get('UniqueId', 0),
            nation = data.get('Nation', ['All']),
            path = data['Path'],
            #volume = 'Volume' in data and data['Volume'] or 1,
            titles = titles,
            wiki_voice_clips = wiki_voice_clips,
        )
