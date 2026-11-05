from shared.glossary import CLUBS
from classes.ScenarioMode import ScenarioMode


class Profile(object):
    def __init__(self, family_name_jp, family_name_ruby_jp, personal_name_jp, personal_name_ruby_jp, family_name_en, personal_name_en, family_name_reading_en, personal_name_reading_en, club, school_year, age, birthday, height, hobbies, designer, illustrator, lobby_illustrator, voice, introduction_jp, introduction_en, weapon_name, weapon_desc, weapon_name_translated, weapon_desc_translated, release_date_jp, release_date_gl, change_story):
        self.family_name_jp = family_name_jp
        self.family_name_ruby_jp = family_name_ruby_jp
        self.personal_name_jp = personal_name_jp
        self.personal_name_ruby_jp = personal_name_ruby_jp
        self.family_name_en = family_name_en
        self.personal_name_en = personal_name_en
        self.family_name_reading_en = family_name_reading_en
        self.personal_name_reading_en = personal_name_reading_en
        self._club = club
        self.school_year = school_year
        self.age = age
        self._birthday = birthday
        self.height = height
        self.hobbies = hobbies
        self.designer = designer
        self.illustrator = illustrator
        self.lobby_illustrator = lobby_illustrator
        self.voice = voice
        self.introduction_jp = introduction_jp
        self.introduction_en = introduction_en
        self.weapon_name = weapon_name
        self.weapon_desc = weapon_desc
        self.weapon_name_translated = weapon_name_translated
        self.weapon_desc_translated = weapon_desc_translated
        self.release_date_jp = release_date_jp
        self.release_date_gl = release_date_gl
        self.change_story = change_story

    @property
    def birthday(self):
        if self._birthday is None: return ''
        if len(self._birthday) < 2: return self._birthday
        month, day = self._birthday.split('/')
        month = [
            'January',
            'February',
            'March',
            'April',
            'May',
            'June',
            'July',
            'August',
            'September',
            'October',
            'November',
            'December'
        ][int(month) - 1]
        return f'{month} {day}'
    
    @property
    def full_name(self):
        return f'{self.family_name_jp} {self.personal_name_jp}'
    
    @property
    def reading(self):
        return f'{self.family_name_ruby_jp} {self.personal_name_jp}'
    
    @property
    def club(self):
        return CLUBS[self._club] if self._club in CLUBS else self._club

    @classmethod
    def from_data(cls, character_id, data):
        localization = data.translated_characters[character_id]
        change = data.characters_profile_change.get(character_id)
        profile_id = change['ChangeCharacterID'] if change else character_id
        if profile_id not in data.translated_characters:
            print(f"WARNING - changed profile {profile_id} of {localization['PersonalNameEn']} ({character_id}) has no translation, the original profile is used")
            profile_id = character_id

        original = data.characters_localization.get(character_id, {})
        profile = data.characters_localization.get(profile_id, {})
        profile_localization = localization | data.translated_characters[profile_id]

        field_list = ['FamilyName', 'PersonalName', 'CharacterAge', 'CharHeight', 'DesignerName', 'IllustratorName', 'LobbyIllustratorName', 'Voice', 'Hobby', 'ProfileIntroduction', 'WeaponName', 'WeaponDesc' ]
        localized_strings = {}
        for f in field_list:
            #the profile screen shows the changed profile, the weapon screen the character's own
            jp, en = (original, localization) if f.startswith('Weapon') else (profile, profile_localization)
            localized_strings[f] = en[f+'En'] if f+'En' in en and en[f+'En'] is not None else jp.get(f+'Jp', '')

        release_date_jp = localization.get('ReleaseDateJp') or ''
        release_date_gl = localization.get('ReleaseDateGl') or ''

        if profile.get('DesignerNameJp', "") not in localized_strings['DesignerName'] or profile.get('IllustratorNameJp', "") not in localized_strings['IllustratorName']:
            print (f"Possible mistranslation {localization['PersonalNameEn'].ljust(10)}: {(profile.get('DesignerNameJp')+'/'+localized_strings['DesignerName']).ljust(45)} {profile.get('IllustratorNameJp')}/{localized_strings['IllustratorName']}")

        #translator = Translator()
        #
        #weapon_name_translated = translator.translate(profile['WeaponNameJp'], dest='en', src='ja').text
        #weapon_desc_translated = translator.translate(profile['WeaponDescJp'], dest='en', src='ja').text
        #print(weapon_name_translated)
        #weapon_name_translated = None
        #weapon_desc_translated = None

        return cls(
            profile.get("FamilyNameJp"),
            profile.get("FamilyNameRubyJp"),
            profile.get("PersonalNameJp"),
            profile.get("PersonalNameRubyJp"),    
            localized_strings['FamilyName'],
            localized_strings['PersonalName'],
            profile_localization.get('FamilyNameReadingEn') or localized_strings['FamilyName'],
            profile_localization.get('PersonalNameReadingEn') or localized_strings['PersonalName'],
            profile.get('Club'),
            profile.get('SchoolYearJp'),        
            localized_strings['CharacterAge'].replace('歳',''),
            profile.get('BirthDay'),
            localized_strings['CharHeight'],
            localized_strings['Hobby'],
            localized_strings['DesignerName'],
            localized_strings['IllustratorName'],
            localized_strings['LobbyIllustratorName'],
            localized_strings['Voice'],
            '<p>' + profile.get('ProfileIntroductionJp', "").replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            '<p>' + localized_strings['ProfileIntroduction'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            original.get('WeaponNameJp'),
            '<p>' + original.get('WeaponDescJp', "").replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            localized_strings['WeaponName'],
            '<p>' + localized_strings['WeaponDesc'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            release_date_jp,
            release_date_gl,
            change and ScenarioMode.from_data(change['ScenarioModeId'], data),
        )
