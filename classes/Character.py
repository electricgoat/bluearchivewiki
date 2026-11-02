from shared.glossary import CLUBS, SCHOOLS
from classes.Profile import Profile
from classes.Skill import Skill
from classes.Stats import Stats
from classes.Weapon import Weapon
from classes.Gear import Gear
from classes.Favor import Favor
from classes.Potential import Potential
from classes.MemoryLobby import MemoryLobby
from classes.Momotalk import Momotalk

#TODO actually query the archive/encore banners
ARCHIVE_POOL = [
    "Aru", "Eimi", "Haruna", "Hifumi", "Hina", "Iori", "Maki", "Neru", "Izumi", "Shun", "Sumire", "Tsurugi", "Hibiki", "Karin", "Saya", "Hoshino", "Shiroko", "Mashiro", "Izuna", "Arisu", "Midori", "Cherino", "Yuzu", "Azusa", "Koharu", "Hifumi (Swimsuit)", "Shiroko (Riding)", "Shun (Kid)", "Saya (Casual)", "Asuna (Bunny Girl)", "Natsu", "Ako", "Cherino (Hot Spring)", "Chinatsu (Hot Spring)", "Nodoka (Hot Spring)", "Serika (New Year)", "Sena", "Chihiro",
    "Azusa (Swimsuit)", "Mashiro (Swimsuit)", "Hina (Swimsuit)", "Iori (Swimsuit)", "Neru (Bunny Girl)", "Karin (Bunny Girl)", "Aru (New Year)", "Mutsuki (New Year)", "Izuna (Swimsuit)", "Chise (Swimsuit)"
]


class Character(object):
    def __init__(self, id, dev_name, model_prefab_name, portrait, family_name_en, personal_name_en, family_name_reading_en, personal_name_reading_en, variant, wiki_name, wiki_name_jp, rarity, school, club, role, position, damage_type, armor_type, combat_class, equipment, weapon_type, uses_cover, main_combat_style_id, profile, normal_skill, normal_gear_skill, ex_skill, passive_skill, passive_weapon_skill, sub_skill, stats, weapon, gear, favor, potential, memory_lobby, momotalk, liked_gift_tags, character_pool, costume):
        self.id = id
        self.rarity = rarity
        self._school = school
        self._club = club
        self._role = role
        self.position = position
        self._damage_type = damage_type
        self._armor_type = armor_type
        self._combat_class = combat_class
        self.equipment = equipment
        self.weapon_type = weapon_type
        self._uses_cover = uses_cover
        self.main_combat_style_id = main_combat_style_id
        self.profile = profile
        self.normal_skill = normal_skill
        self.normal_gear_skill = normal_gear_skill
        self.ex_skill = ex_skill
        self.passive_skill = passive_skill
        self.passive_weapon_skill = passive_weapon_skill
        self.sub_skill = sub_skill
        self.stats = stats
        self.weapon = weapon
        self.gear = gear
        self.favor = favor
        self.potential = potential
        self.memory_lobby = memory_lobby
        self.momotalk = momotalk
        self.liked_gift_tags = liked_gift_tags
        self._character_pool = character_pool

        self.costume = costume

        self.dev_name = dev_name
        self.model_prefab_name = model_prefab_name

        self.portrait = portrait
        self.family_name_en = family_name_en
        self.personal_name_en = personal_name_en
        self._family_name_reading_en = family_name_reading_en
        self._personal_name_reading_en = personal_name_reading_en
        self.variant = variant
        self._wiki_name = wiki_name
        self.wiki_name_jp = wiki_name_jp

    def __repr__(self):
        return f"CharacterObject {self.personal_name_en} ({self.variant})"

    @property
    def role(self):
        return {
            'DamageDealer': 'Attacker',
            'Tanker': 'Tank',
            'Supporter': 'Support',
            'Healer': 'Healer',
            'Vehicle': 'Tactical Support'
        }[self._role]

    @property
    def club(self):
        return CLUBS[self._club] if self._club in CLUBS else self._club
    
    @property
    def school(self):
        return SCHOOLS[self._school] if self._school in SCHOOLS else self._school

    @property
    def full_name_en(self):
        full_name = f'{self.family_name_en} {self.personal_name_en}'.strip()
        if self.variant: full_name += ' '+f'({self.variant})'
        return full_name
    
    @property
    def full_name_reading_en(self):
        full_name = f'{self.family_name_reading_en} {self.personal_name_reading_en}'.strip()
        if self.variant: full_name += ' '+f'({self.variant})'
        return full_name
    
    @property
    def family_name_reading_en(self):
        if self._family_name_reading_en: return self._family_name_reading_en
        return self.family_name_en

    @property
    def personal_name_reading_en(self):
        if self._personal_name_reading_en: return self._personal_name_reading_en
        return self.personal_name_en

    @property
    def wiki_name(self):
        if self._wiki_name is not None and self._wiki_name != '':
            return self._wiki_name
        out = self.personal_name_en
        if self.variant: out += ' '+f'({self.variant})'
        return out

    @property
    def wiki_name_base(self):
        if self._wiki_name is not None and self._wiki_name != '':
            return self._wiki_name
        out = self.personal_name_en
        #if self.variant: out += ' '+f'({self.variant})'
        return out


    @property
    def damage_type(self):
        return {
            'Explosion': 'Explosive',
            'Pierce': 'Penetration',
            'Mystic': 'Mystic',
            'Sonic': 'Sonic',
            'Chemical': 'Corrosive'
        }[self._damage_type]

    @property
    def armor_type(self):
        return {
            'LightArmor': 'Light',
            'HeavyArmor': 'Heavy',
            'Unarmed': 'Special',
            'ElasticArmor': 'Elastic',
            'CompositeArmor': 'Composite'
        }[self._armor_type]

    @property
    def combat_class(self):
        return {
            'Main': 'Striker',
            'Support': 'Special'
        }[self._combat_class]

    @property
    def uses_cover(self):
        return 'Yes' if self._uses_cover else 'No'
    
    @property
    def character_pool(self):
        if self._character_pool == 'regular' and self.wiki_name in ARCHIVE_POOL:
            return 'archive'
        if self._character_pool == 'limited' and self.wiki_name in ARCHIVE_POOL:
            return 'encore'
        return self._character_pool

    @classmethod
    def from_data(cls, character_id, data, ext_missing_skill_localization = None, ext_missing_skill_effect_localization = None):
        Skill.missing_skill_localization = ext_missing_skill_localization
        Skill.missing_skill_effect_localization = ext_missing_skill_effect_localization

        character = data.characters[character_id]
        character_ai = data.characters_ai[character['CharacterAIId']]
        costume = data.costumes[character['CostumeGroupId']]

        liked_gift_tags = character_id in data.characters_cafe_tags and data.characters_cafe_tags[character_id]['FavorItemTags'] or None
        portrait = costume['TextureDir'][costume['TextureDir'].rfind('/')+1:]

        wiki_name_jp = character['LocalizeEtcId'] in data.etc_localization and data.etc_localization[character['LocalizeEtcId']].get('NameJp', None) or None

        return cls(
            character['Id'],
            character['DevName'],
            costume['ModelPrefabName'],
            portrait,
            data.translated_characters[character_id]['FamilyNameEn'],
            data.translated_characters[character_id]['PersonalNameEn'],
            data.translated_characters[character_id].get('FamilyNameReadingEn'),
            data.translated_characters[character_id].get('PersonalNameReadingEn'),
            data.translated_characters[character_id]['VariantNameEn'],
            data.translated_characters[character_id].get('Wikiname'),
            wiki_name_jp,
            character['DefaultStarGrade'],
            character['School'],
            character.get('Club'),
            character['TacticRole'],
            character['TacticRange'],
            character['BulletType'],
            character['ArmorType'],
            character['SquadType'],
            character['EquipmentSlot'],
            character['WeaponType'],
            character_ai['CanUseObstacleOfKneelMotion'] or character_ai['CanUseObstacleOfStandMotion'],
            character['MainCombatStyleId'],
            Profile.from_data(character_id, data),
            Skill.from_data(data.characters_skills[(costume['CharacterSkillListGroupId'], 0, 0, 0)]['PublicSkillGroupId'][0], data, show_skill_slot='Normal'),
            (character_id, 0, 2, 0) in data.characters_skills and Skill.from_data(data.characters_skills[(costume['CharacterSkillListGroupId'], 0, 2, 0)]['PublicSkillGroupId'][0], data, show_skill_slot='Gear Normal') or None,
            Skill.from_data(data.characters_skills[(costume['CharacterSkillListGroupId'], 0, 0, 0)]['ExSkillGroupId'][0], data, 5, show_skill_slot='EX'),
            Skill.from_data(data.characters_skills[(costume['CharacterSkillListGroupId'], 0, 0, 0)]['PassiveSkillGroupId'][0], data, show_skill_slot='Passive'),
            Skill.from_data(data.characters_skills[(costume['CharacterSkillListGroupId'], 2, 0, 0)]['PassiveSkillGroupId'][0], data, show_skill_slot='Weapon Passive'),
            Skill.from_data(data.characters_skills[(costume['CharacterSkillListGroupId'], 0, 0, 0)]['ExtraPassiveSkillGroupId'][0], data, show_skill_slot='Sub'),
            Stats.from_data(character_id, data),
            Weapon.from_data(character_id, costume, character['BulletType'], data),
            (character_id, 1) in data.gear and Gear.from_data(character_id, data) or None,
            Favor.from_data(character_id, data),
            Potential.from_data(character_id, data),
            MemoryLobby.from_data(character_id, data),
            Momotalk.from_data(character_id, data),
            liked_gift_tags,
            data.translated_characters[character_id].get('CharacterPool', 'regular') or 'regular',
            costume
        )
