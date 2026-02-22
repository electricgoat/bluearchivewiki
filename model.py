import itertools
import operator
import re
#from googletrans import Translator

from shared.tag_map import map_tags
from shared.functions import replace_glossary, replace_units, replace_statnames, statcalc_replace_statname, damage_type as damage_type_glossary
from shared.glossary import CLUBS, SCHOOLS

#TODO actually query the archive/encore banners
ARCHIVE_POOL = [
    "Aru", "Eimi", "Haruna", "Hifumi", "Hina", "Iori", "Maki", "Neru", "Izumi", "Shun", "Sumire", "Tsurugi", "Hibiki", "Karin", "Saya", "Hoshino", "Shiroko", "Mashiro", "Izuna", "Arisu", "Midori", "Cherino", "Yuzu", "Azusa", "Koharu", "Hifumi (Swimsuit)", "Shiroko (Riding)", "Shun (Kid)", "Saya (Casual)", "Asuna (Bunny Girl)", "Natsu", "Ako", "Cherino (Hot Spring)", "Chinatsu (Hot Spring)", "Nodoka (Hot Spring)", "Serika (New Year)", "Sena", "Chihiro",
    "Azusa (Swimsuit)", "Mashiro (Swimsuit)", "Hina (Swimsuit)", "Iori (Swimsuit)", "Neru (Bunny Girl)", "Karin (Bunny Girl)", "Aru (New Year)", "Mutsuki (New Year)", "Izuna (Swimsuit)", "Chise (Swimsuit)"
]
missing_skill_localization = None


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
            'Chemical': 'Chemical'
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
    def from_data(cls, character_id, data, ext_missing_skill_localization = None):
        global missing_skill_localization
        missing_skill_localization = ext_missing_skill_localization

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


class Profile(object):
    def __init__(self, family_name_jp, family_name_ruby_jp, personal_name_jp, personal_name_ruby_jp, club, school_year, age, birthday, height, hobbies, designer, illustrator, lobby_illustrator, voice, introduction_jp, introduction_en, weapon_name, weapon_desc, weapon_name_translated, weapon_desc_translated, release_date_jp, release_date_gl):
        self.family_name_jp = family_name_jp
        self.family_name_ruby_jp = family_name_ruby_jp
        self.personal_name_jp = personal_name_jp
        self.personal_name_ruby_jp = personal_name_ruby_jp
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
        profile = data.characters_localization.get(character_id, {})
        localization = data.translated_characters[character_id]

        field_list = ['FamilyName', 'PersonalName', 'CharacterAge', 'CharHeight', 'DesignerName', 'IllustratorName', 'LobbyIllustratorName', 'Voice', 'Hobby', 'ProfileIntroduction', 'WeaponName', 'WeaponDesc' ]
        localized_strings = {}
        for f in field_list:
            localized_strings[f] = localization[f+'En'] if f+'En' in localization and localization[f+'En'] is not None else profile.get(f+'Jp', '')  

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
            profile.get('WeaponNameJp'),
            '<p>' + profile.get('WeaponDescJp', "").replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            localized_strings['WeaponName'],
            '<p>' + localized_strings['WeaponDesc'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            release_date_jp,
            release_date_gl,
        )


def _get_skill_upgrade_materials(level, data):
    recipe = data.recipes[level['RequireLevelUpMaterial']]
    if recipe['RecipeType'] != 'SkillLevelUp':
        return

    ingredients = data.recipes_ingredients[recipe['RecipeIngredientId']]
    ingredients = itertools.chain(
        zip(ingredients['IngredientParcelType'], ingredients['IngredientId'], ingredients['IngredientAmount']),
        zip(ingredients['CostParcelType'], ingredients['CostId'], ingredients['CostAmount'])
    )
    for type_, id, amount in ingredients:
        if type_ == 'Item':
            #yield data.translated_items[id]['NameEn'], data.items[id]['Icon'].rsplit('/', 1)[-1], amount
            yield data.etc_localization[data.items[id]['LocalizeEtcId']]['NameEn'], data.items[id]['Icon'].rsplit('/', 1)[-1], amount
        elif type_ == 'Currency':
            yield data.translated_currencies[id]['NameEn'], data.currencies[id]['Icon'].rsplit('/', 1)[-1], amount


class SkillLevel(object):
    def __init__(self, description, cost, materials):
        self.description = description
        self.cost = cost
        self.materials = materials

    @classmethod
    def from_data(cls, level, group_id, data):
        return cls(
            translate_skill(data.skills_localization[level['LocalizeSkillId']]['DescriptionJp'], level['Level'], group_id, data),
            level['SkillCost'],
            list(_get_skill_upgrade_materials(level, data))
        )


class Skill(object):
    def __init__(self, name, name_translated, icon, levels, description_general, max_level, damage_type, skill_cost, effect_data, additional_tooltip = [], select_ex_tooltip = [], show_skill_slot = ''):
        self.name = name
        self.icon = icon
        self.levels = levels
        self._damage_type = damage_type

        # Extra information
        self.name_translated = name_translated
        self.description_general = description_general
        self.max_level = max_level
        self.skill_cost = skill_cost
        self.effect_data = effect_data
        self.additional_tooltip = additional_tooltip
        self.select_ex_tooltip = select_ex_tooltip
        self.show_skill_slot = show_skill_slot

    @property
    def damage_type(self):
        return {
            'Explosion': 'Explosive',
            'Pierce': 'Penetration',
            'Mystic': 'Mystic',
            'Sonic': 'Sonic'
        }[self._damage_type]
    
    @classmethod
    def from_data(cls, group_id, data, max_level = 10, show_skill_slot = None):
        global missing_skill_localization

        group = [skill for skill in data.skills.values() if skill['GroupId'] == group_id]
        if not group:
            raise KeyError(group_id)

        def skill_type(slot):
            return {
                slot: slot,
                'Ex': 'EX',
                'Extrapassive': 'Sub',
                'Public': 'Normal'
            }[slot]
        
        def format_description(levels, text_en):
            start_variables = re.findall(r'\{\{SkillValue\|([^\}\[]+)\}\}',  levels[0].description)
            end_variables = re.findall(r'\{\{SkillValue\|([^\}\[]+)\}\}',  levels[max_level-1].description)
            range_text = []

            for i in range(len(end_variables)):
                try: stripped_start = re.findall(r'([0-9a-zA-z./]+).*', start_variables[i])
                except IndexError: 
                    start_variables.append(0)
                    stripped_start = [0]

                range_text.append(start_variables[i] != end_variables[i] and f'{stripped_start[0]}~{end_variables[i]}' or f'{end_variables[i]}')

            for skill_value in range_text:
                text_en = re.sub(r'\$\d+', '{{SkillValue|' + skill_value + '}}', text_en, 1)

            return text_en.replace("\n",'<br>')
        

        additional_tooltip = []
        if group[0]['AdditionalToolTipId'] != 0: 
            #print(f"group_id {group_id} has additional tooltips group: {group[0]['AdditionalToolTipId']} at max_level {max_level}")
            for add_tooltip in data.skill_additional_tooltip[group[0]['AdditionalToolTipId']]:
                add_max_level = (add_tooltip['ShowSkillSlot'].upper() == 'EX' or show_skill_slot == 'EX') and 5 or 10
                additional_tooltip.append(Skill.from_data(add_tooltip['AdditionalSkillGroupId'], data, max_level=add_max_level ,show_skill_slot=add_tooltip['ShowSkillSlot']))


        select_ex_tooltip = []
        selectable_ex_skill_groups_added = []
        if group[0]['SelectExSkillToolTipId'] != 0: 
            #print(f"group_id {group_id} has a Select EX tooltips group: {group[0]['SelectExSkillToolTipId']} at max_level {max_level}")
            for add_tooltip in data.skill_select_ex_tooltip[group[0]['SelectExSkillToolTipId']]:
                selectable_ex_skill_groups_added += [add_tooltip['SelectableExSkillGroupId']]
                select_ex_tooltip.append(Skill.from_data(add_tooltip['SelectableExSkillGroupId'], data, max_level=5, show_skill_slot='EX'))
            
            for skill in data.skills.values():
                if skill['Level']==1 and skill['GroupId'].startswith(selectable_ex_skill_groups_added[0][:-1]) and skill['GroupId'] not in selectable_ex_skill_groups_added:
                    #print(f'Adding missing Select EX tooltip for {skill["GroupId"]}')
                    select_ex_tooltip.append(Skill.from_data(skill["GroupId"], data, max_level=5, show_skill_slot='EX'))

                


        levels = [SkillLevel.from_data(level, group_id, data) for level in sorted(group, key=operator.itemgetter('Level'))]

        skill_cost = []
        for i in range(1, max_level):
            if levels[i].cost != levels[i-1].cost:
                #print (f'Skill level {i+1} cost change from {levels[i-1].cost} to {levels[i].cost}')
                skill_cost.append({'level':i+1, 'cost':levels[i].cost})

        try: 
            text_general = data.translated_skills[group_id]["DescriptionGeneral"] 
        except:
            text_general = translate_skill(levels[9].description, max_level, group_id, data)
        description_general = format_description(levels, text_general)


        try: data.translated_skills[group[0]['GroupId']]['NameEn']
        except KeyError: 
            skill_name_en = None
            if missing_skill_localization: missing_skill_localization.add_entry(data.skills_localization[group[0]['LocalizeSkillId']])
        else:  
            skill_name_en = data.translated_skills[group[0]['GroupId']]['NameEn']

        if skill_name_en == None:
            print (f"No translation found for skill {data.skills_localization[group[0]['LocalizeSkillId']]['NameJp']}, group_id {group_id}")


        effect_data = None
        if group_id.find('Passive') > -1 and group_id.find('ExtraPassive') == -1:
            effect_data = {}
            #print(f'Parsing skill {group_id}')

            #TODO THIS IS BROKEN NOW figure it out
            try:
                for effect in data.levelskill[group_id]['EntityTimeline'][len(data.levelskill[group_id]['EntityTimeline'])-2]['Entity']['Abilities'][0]['LogicEffectGroupIds']:
                    amount_base = []
                    amount_percentage = []

                if f'{effect}_Lv1' in data.logiceffectdata and data.logiceffectdata[f'{effect}_Lv1']['EffectData']['Category'] != 'Dummy':
                    for lv in range(1,11):
                        if f'{effect}_Lv{lv}' in data.logiceffectdata: amount_base.append(data.logiceffectdata[f'{effect}_Lv{lv}']['EffectData']['BaseAmount'])
                        else: amount_base.append(data.logiceffectdata[f'{effect}_Lv1']['EffectData']['BaseAmount'])
                        
                        if f'{effect}_Lv{lv}' in data.logiceffectdata: amount_percentage.append(data.logiceffectdata[f'{effect}_Lv{lv}']['EffectData']['TargetCoefficientAmount'])
                        else: amount_percentage.append(data.logiceffectdata[f'{effect}_Lv1']['EffectData']['TargetCoefficientAmount'])
                    if amount_base[9] == '0': amount_base = None
                    if amount_percentage[9] == '0': amount_percentage = None

                    effect_data[effect] = {'stat_name': statcalc_replace_statname(data.logiceffectdata[f'{effect}_Lv1']['EffectData']['StatType']), 'amount_base': amount_base, 'amount_percentage': amount_percentage}
            except: 
                pass
                

        return cls(
            data.skills_localization[group[0]['LocalizeSkillId']]['NameJp'],
            skill_name_en,
            group[0]['IconName'].rsplit('/', 1)[-1],
            levels,
            description_general,
            max_level,
            group[0]['BulletType'],
            skill_cost,
            effect_data,
            additional_tooltip,
            select_ex_tooltip,
            skill_type(show_skill_slot),
        )



def translate_skill(text_jp, skill_level, group_id, data):
    try: skill_desc = data.translated_skills[group_id]['DescriptionEn']
    except KeyError: 
        skill_desc = text_jp
        #print(f'{group_id} translation is missing')
    else:

        for i in range(skill_level+1):
            try: skill_desc = data.translated_skills[group_id][f'ReplaceOnLevel{i}']
            except KeyError: pass
            
            try: skill_desc = skill_desc.removesuffix('.') + data.translated_skills[group_id][f'AddOnLevel{i}']
            except KeyError: pass

    variables = re.findall(r'\[c]\[[0-9A-Fa-f]{6}]([^\[]*)\[-]\[/c]', replace_units(text_jp))
    #replacement_count = len(re.findall(r'\$[0-9]{1}', skill_desc))
    #if len(variables) > 0 and len(variables) != replacement_count: print(f'Mismatched number of variables ({len(variables)}/{replacement_count}) in {text_jp} / {skill_desc}')

    skill_desc = re.sub(r'\$(\d+)', 
        lambda m: '{{SkillValue|' + variables[int(m.group(1)) - 1] + '}}' if 1 <= int(m.group(1)) <= len(variables) else m.group(0), 
        skill_desc
    ).replace("\n", '<br>')

    return skill_desc



class Stats(object):
    def __init__(self, attack, defense, hp, healing, accuracy, evasion, critical_rate, critical_damage, stability,
                 firing_range, cc_strength, cc_resistance, city_affinity, outdoor_affinity, indoor_affinity, move_speed, ammo_count, ammo_cost, regen_cost):
        self.attack = attack
        self.defense = defense
        self.hp = hp
        self.healing = healing
        self.accuracy = accuracy
        self.evasion = evasion
        self.critical_rate = critical_rate
        self._critical_damage = critical_damage
        self.stability = stability
        self.firing_range = firing_range
        self.cc_strength = cc_strength
        self.cc_resistance = cc_resistance
        self.city_affinity = city_affinity
        self.outdoor_affinity = outdoor_affinity
        self.indoor_affinity = indoor_affinity
        self.move_speed = move_speed
        self.ammo_count = ammo_count
        self.ammo_cost = ammo_cost
        self.regen_cost = regen_cost

    @property
    def critical_damage(self):
        return self._critical_damage // 100

    @classmethod
    def from_data(cls, character_id, data):
        stats = data.characters_stats[character_id]
        return cls(
            (stats['AttackPower1'], stats['AttackPower100']),
            (stats['DefensePower1'], stats['DefensePower100']),
            (stats['MaxHP1'], stats['MaxHP100']),
            (stats['HealPower1'], stats['HealPower100']),
            stats['AccuracyPoint'],
            stats['DodgePoint'],
            stats['CriticalPoint'],
            stats['CriticalDamageRate'],
            stats['StabilityPoint'],
            stats['Range'],
            stats['OppressionPower'],
            stats['OppressionResist'],
            stats['StreetBattleAdaptation'],
            stats['OutdoorBattleAdaptation'],
            stats['IndoorBattleAdaptation'],
            stats['MoveSpeed'],
            stats['AmmoCount'],
            stats['AmmoCost'],
            stats['RegenCost']
        )


class Weapon(object):
    def __init__(self, id, image_path, attack_power, attack_power_100, max_hp, max_hp_100, heal_power, heal_power_100, stat_type, stat_value, rank2_desc, rank3_desc, rank4_desc):
        self.id = id
        self.image_path = image_path
        self.attack_power = attack_power
        self.attack_power_100 = attack_power_100
        self.max_hp = max_hp
        self.max_hp_100 = max_hp_100
        self.heal_power = heal_power
        self.heal_power_100 = heal_power_100
        self.stat_type = stat_type
        self.stat_value = stat_value
        self.rank2_desc = rank2_desc
        self.rank3_desc = rank3_desc
        self.rank4_desc = rank4_desc


    @classmethod
    def from_data(cls, character_id, costume, bullet_type, data):
        weapon = data.weapons[character_id]
        stats = data.characters_stats[character_id]


        weapon_passive_skill = Skill.from_data(data.characters_skills[(costume['CharacterSkillListGroupId'], 2, 0, 0)]['PassiveSkillGroupId'][0], data, show_skill_slot="Weapon Passive")

        #print (passive_skill.name_translated)
        #try: data.translated_skills[group[0]['GroupId']]['NameEn']
        #except KeyError: 
        #    skill_name_en = None
        #else:  
        #    skill_name_en = data.characters_skills[(costume['CharacterSkillListGroupId'], 0)]['PassiveSkillGroupId'][0] #data.translated_skills[group[0]['GroupId']]['NameEn']

        rank2_desc = f'Passive Skill changes to <b>{weapon_passive_skill.name_translated}</b>'

                
        def affinity_type(affinity_change_type):
            return {
                'Street': 'Urban',
                'Outdoor': 'Outdoor',
                'Indoor': 'Indoor'
            }[affinity_change_type]

        def offset_affinity(start_letter, offset_int):
            affinity_values = ['D','C','B','A','S','SS']
            index = affinity_values.index(start_letter)

            return affinity_values[index+offset_int]

        affinity_change_type =  weapon['StatType'][2].replace("BattleAdaptation_Base", "")
        old_affinity_letter =  stats[affinity_change_type+'BattleAdaptation']

        rank3_desc = f"{{{{Icon|{affinity_type(affinity_change_type)}|size=20}}}} {affinity_type(affinity_change_type)} area affinity {{{{Affinity|{offset_affinity(old_affinity_letter,weapon['StatValue'][2])}}}}} {offset_affinity(old_affinity_letter,weapon['StatValue'][2])}"

        if data.characters[character_id]['SquadType'] == 'Main': #Striker
            rank4_desc = f"Increase {damage_type_glossary(bullet_type)} Efficiency by 10%."
        elif data.characters[character_id]['SquadType'] == 'Support': #Special
            rank4_desc = f"Increase maximum Cost by 0.5."
        else: rank4_desc = '' 


        return cls(
            weapon['Id'],
            weapon['ImagePath'].rsplit('_', 1)[-1],
            weapon['AttackPower'],
            weapon['AttackPower100'],
            weapon['MaxHP'],
            weapon['MaxHP100'],
            weapon['HealPower'],
            weapon['HealPower100'],
            weapon['StatType'],
            weapon['StatValue'],
            rank2_desc,
            rank3_desc,
            rank4_desc,
        )


class Gear(object):
    def __init__(self, name_en, name_jp, desc_en, desc_jp, icon, tiers, tier1_desc, tier2_desc, effect_data, unlock_level):
        self.name_en = name_en
        self.name_jp = name_jp
        self.desc_en = desc_en
        self.desc_jp = desc_jp
        self.icon = icon
        self.tiers = tiers
        self.tier1_desc = tier1_desc
        self.tier2_desc = tier2_desc
        self.effect_data = effect_data
        self.unlock_level = unlock_level


    @classmethod
    def from_data(cls, character_id, data):
        gear_tiers_data = [entry for entry in data.gear.values() if entry['CharacterId'] == character_id]
        # if not gear:
        #     raise KeyError(character_id)

        tiers = [GearTier.from_data(tier, data) for tier in sorted(gear_tiers_data, key=operator.itemgetter('Tier'))]
        unlock_level = tiers[0].unlock_favor

        
        stat_bonus_text = []
        for index,stat_type in enumerate(tiers[0].stats['stat_type']):
            stat_bonus_text.append(stat_type + " by {{SkillValue|" + str(tiers[0].stats['stat_value'][index]) + "}}")

        tier1_desc = "Increase " + (" and ".join(stat_bonus_text))
        tier2_desc = 'Normal Skill changes to '

        effect_data = {'stat_name': tiers[0].stats['stat_type'][0], 'amount_base': str(tiers[0].stats['stat_value'][0])}

        if 'NameEn' not in data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]: print (f"Missing Unique Gear translation, LocalizeEtcId {data.gear[(character_id , 1)]['LocalizeEtcId']}")

        return cls(
            'NameEn' in data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]] and data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['NameEn'] or None,
            data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['NameJp'],
            'DescriptionEn' in data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]] and '<p>' + data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['DescriptionEn'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>' or None,
            '<p>' + data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['DescriptionJp'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            data.gear[(character_id , 1)]['Icon'].rsplit('/', 1)[-1],
            tiers,
            tier1_desc,
            tier2_desc,
            effect_data,
            unlock_level,
        )
    

class GearTier(object):
    def __init__(self, tier, unlock_favor, materials, stats):
        self.tier = tier
        self.unlock_favor = unlock_favor
        self.materials = materials
        self.stats = stats

    @classmethod
    def from_data(cls, tier, data):
        return cls(
            tier['Tier'],
            tier['OpenFavorLevel'],
            tier['Tier']>1 and list(_get_recipe_materials(data.gear[(tier['CharacterId'], tier['Tier']-1)]['RecipeId'], data)) or None,
            {'stat_type':replace_statnames(tier['StatType']), 'stat_value':tier['MaxStatValue']}
        )


def _get_recipe_materials(recipe_id, data):
    if recipe_id not in data.recipes:
        return
    recipe = data.recipes[recipe_id]
    #if recipe['RecipeType'] != 'EquipmentTierUp':
    #    return

    ingredients = data.recipes_ingredients[recipe['RecipeIngredientId']]
    ingredients = itertools.chain(
        zip(ingredients['IngredientParcelType'], ingredients['IngredientId'], ingredients['IngredientAmount']),
        zip(ingredients['CostParcelType'], ingredients['CostId'], ingredients['CostAmount'])
    )
    for type_, id, amount in ingredients:
        if type_ == 'Item':
            #yield data.etc_localization[data.items[id]['LocalizeEtcId']]['NameEn'], data.items[id]['Icon'].rsplit('/', 1)[-1], amount
            yield data.etc_localization[data.items[id]['LocalizeEtcId']]['NameEn'], amount
        elif type_ == 'Currency':
            #yield data.translated_currencies[id]['NameEn'], data.currencies[id]['Icon'].rsplit('/', 1)[-1], amount
            yield data.translated_currencies[id]['NameEn'], amount
            
        

class Favor(object):
    def __init__(self, levels):
        self.levels = levels

    @classmethod
    def from_data(cls, character_id, data):
        levels = {}

        for favor_level in data.favor_levels:
            if favor_level[0] == character_id:
                #print(replace_statnames(data.favor_levels[(character_id , favor_level[1])]['StatType']))
                levels[favor_level[1]] = {'stat_type':replace_statnames(data.favor_levels[(character_id , favor_level[1])]['StatType']), 'stat_value':data.favor_levels[(character_id , favor_level[1])]['StatValue']}  

        return cls(
            levels
        )
    

class Potential(object):
    def __init__(self, groups):
        self.groups = groups

        self.stat_groups = ['AttackPower', 'MaxHP', 'HealPower']

    @property
    def max_level(self):
        return len(self.groups['AttackPower']['levels'])
    

    @classmethod
    def from_data(cls, character_id, data):

        potential_groups = {x['PotentialStatBonusRateType']:x for x in data.character_potential[character_id]}
        
        for stat_group in potential_groups.values():
            stat_group['levels'] = data.character_potential_stat[stat_group['PotentialStatGroupId']]
            for level in stat_group['levels']:
                level['materials'] = _get_recipe_materials(level['RecipeId'], data)
                #print(recipe)

        #print(potential_levels)
        return cls(
            potential_groups
        )


class MemoryLobby(object):
    def __init__(self, image, bgm_id, unlock_level, lobby_id_list = []):
        self.image = image
        self.bgm_id = bgm_id
        self.unlock_level = unlock_level
        self.lobby_id_list = lobby_id_list


    @classmethod
    def from_data(cls, character_id, data):
        lobby_id_list = [x['Id'] for x in data.memory_lobby.values() if x['CharacterId'] == character_id]
        try: 
            lobby_data = data.memory_lobby[lobby_id_list[0]]
        except KeyError: return cls( None, None, 1, [] )
        except IndexError: return cls( None, None, 1, [] )

        unlock_level = None
        for favor_reward in data.favor_rewards:
            if favor_reward[0] == character_id:
                if 'MemoryLobby' in data.favor_rewards[(character_id , favor_reward[1])]['RewardParcelType']: unlock_level = data.favor_rewards[(character_id , favor_reward[1])]['FavorRank']
        
        return cls(
            lobby_data['RewardTextureName'][lobby_data['RewardTextureName'].rfind('/')+1:],
            lobby_data['BGMId'],
            unlock_level,
            lobby_id_list
        )


class Momotalk(object):
    def __init__(self, levels):
        self.levels = levels

    @classmethod
    def from_data(cls, character_id, data):
        levels = []

        for favor_reward in data.favor_rewards:
            if favor_reward[0] == character_id:
                #print(data.favor_rewards[(character_id , favor_reward[1])])
                levels.append(data.favor_rewards[(character_id , favor_reward[1])])  

        return cls(
            levels
        )



class Item(object):
    def __init__(self, id, rarity, category, name_jp, name_en, desc_jp, desc_en, icon, splash_icon, tags, characters_favorite, characters_likes, collection, tier, recipe, expiration_datetime: str = ""):
        self.id = id
        self.rarity = rarity
        self._category = category
        self.name_jp = name_jp
        self.name_en = name_en
        self.desc_jp = desc_jp
        self.desc_en = desc_en
        self.icon = icon
        self.splash_icon = splash_icon
        self.tags = tags
        self.characters_favorite = characters_favorite
        self.characters_likes = characters_likes
        self.collection = collection
        self.tier = tier
        self.recipe = recipe
        self.expiration_datetime = expiration_datetime


    @property
    def category(self):
        return {
            self._category : self._category,
            'Favor': 'Gifts',
            'Collectible':'Collectible',
            'Material':'Material',
            'Coin':'Currency',
            'Consumable':'Consumable',
            'CharacterExpGrowth':'Activity Report',
            'WeaponExpGrowth':'Weapon Component',
            'Exp':'Enhancement Stone',
            'SecretStone':'Eleph'
        }[self._category]



    @classmethod
    def from_data(cls, item_id, data):
        item = data.items[item_id]
        name_en = 'NameEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['NameEn'] or None
        desc_en = 'DescriptionEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['DescriptionEn'] or None

        # if name_en == None:
        #     print (f"No translation found for item {data.etc_localization[item['LocalizeEtcId']]['NameJp']}, id {item_id}, localizeEtcId {item['LocalizeEtcId']}")

        characters_favorite = []
        characters_likes = []


        tags_mapped = map_tags(item['Tags'])
        tags_list = "FavorItem" in tags_mapped and tags_mapped.remove("FavorItem") or tags_mapped
        tags_filtered = filter(lambda x: not x.startswith('F_') and not x.startswith('TagName'), tags_list)
        item_tags = list(tags_filtered)


        for character_id in data.characters_cafe_tags:
            character_wiki_name = data.translated_characters[character_id]['PersonalNameEn']
            character_wiki_name += f" ({data.translated_characters[character_id]['VariantNameEn']})" if 'VariantNameEn' in data.translated_characters[character_id] and data.translated_characters[character_id]['VariantNameEn'] is not None else ''
 
            tag_intersect = list(set(data.characters_cafe_tags[character_id]['FavorItemUniqueTags'] + data.characters_cafe_tags[character_id]['FavorItemTags']) & set(item['Tags']))
            
            if len(tag_intersect) >1 and character_wiki_name not in characters_favorite: 
                characters_favorite.append(character_wiki_name)
            if len(tag_intersect)==1 and character_wiki_name not in characters_likes: 
                characters_likes.append(character_wiki_name)

        if (len(characters_favorite)): characters_favorite.sort()
        if (len(characters_likes)): characters_likes.sort()

        match item['ItemCategory']:
            case 'Material':
                collection = item['Icon'][item['Icon'].rfind('/')+1:item['Icon'].rfind('_')].replace('Item_Icon_','').replace('Material_','')
            case 'Coin':
                collection = re.sub(r'_[0-9]+_', '_', item['Icon'])[item['Icon'].rfind('/')+1:].replace('Item_Icon_','')
                collection = re.sub(r'_[0-9]+$', '', collection)
                #print (collection)
            case _:        
                collection = None


        return cls(
            item['Id'],
            item['Quality']-1,
            item['ItemCategory'],
            data.etc_localization[item['LocalizeEtcId']]['NameJp'].replace("\n",' '),
            replace_glossary(name_en),
            data.etc_localization[item['LocalizeEtcId']]['DescriptionJp'] != None and data.etc_localization[item['LocalizeEtcId']]['DescriptionJp'].replace("\n\n",'<br>').replace("\n",'<br>') or '',
            desc_en != None and replace_glossary(desc_en).replace("\n\n",'<br>').replace("\n",'<br>') or '',
            item['Icon'][item['Icon'].rfind('/')+1:],
            item['Icon'][item['Icon'].rfind('_')+1:],
            item_tags,
            characters_favorite,
            characters_likes,
            collection,
            'Quality' in item and item['Quality'] or None,
            None, #recipe
            item.get('ExpirationDateTime', ""),
        )


    @classmethod
    def from_equipment_data(cls, item_id, data):
        item = data.equipment[item_id]
        name_en = 'NameEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['NameEn'] or None
        desc_en = 'DescriptionEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['DescriptionEn'] or None

        quality =  {
            0: '0',
            5: '0',
            10:'1',
            20:'2',
            50:'3'
        }[item['CraftQuality']]
        
        category =  item['EquipmentCategory'][:-1] == 'WeaponExpGrowth' and 'WeaponExpGrowth' or item['EquipmentCategory']

        match category:
            case 'WeaponExpGrowth':
                collection = re.sub(r'_[0-9]+_', '_', item['Icon'])[item['Icon'].rfind('/')+1:].replace('Equipment_Icon_','')
                collection = re.sub(r'_[0-9]+$', '', collection)
                #print (collection)
            case 'Exp':        
                collection = 'Exp'
            case _:        
                collection = None

        tier = 'TierInit' in item and item['TierInit'] or None


        
        def get_recipe(item, data):
            #item RecipeId is for upgrading to the next tier, so we need to find previous tier equipment
            source_id = None
            for id in data.equipment:
                if (data.equipment[id]['NextTierEquipment'] == item['Id']):
                    #print (f"Source for item {item['Id']} found, id {id}")
                    source_id = id
                    break
            
            if (source_id == None): 
                return None

            recipe = data.recipe_ingredients[data.recipes[data.equipment[source_id]['RecipeId']]['RecipeIngredientId']]
            recipe_ingredient_names = []

            for ingredient_id in recipe['IngredientId']:
                recipe_ingredient_names.append ('NameEn' in data.etc_localization[data.equipment[ingredient_id]['LocalizeEtcId']] and data.etc_localization[data.equipment[ingredient_id]['LocalizeEtcId']]['NameEn'] or None)

            recipe['IngredientName'] = recipe_ingredient_names
            return recipe


        recipe = None
        recipe = get_recipe(item, data)
        #print(recipe)



        return cls(
            item['Id'],
            quality,
            category,
            data.etc_localization[item['LocalizeEtcId']]['NameJp'],
            replace_glossary(name_en),
            data.etc_localization[item['LocalizeEtcId']]['DescriptionJp'],
            replace_glossary(desc_en),
            item['Icon'][item['Icon'].rfind('/')+1:],
            item['Icon'][item['Icon'].rfind('_')+1:],
            [],
            [],
            [],
            collection,
            tier,
            recipe
        )



# def replace_glossary(item = None):
#     print ("model > replace_glossary is deprecated")
#     if item != None:
#         item = re.sub('Field', 'Outdoor', item)

#     return (item)


class Furniture(object):
    def __init__(self, id, rarity, category, subcategory, size_width, size_height, size_other, comfort_bonus, name_jp, name_en, desc_jp, desc_en, icon, group, interaction, sources):
        self.id = id
        self.rarity = rarity
        self._category = category
        self._subcategory = subcategory
        self.size_width = size_width
        self.size_height = size_height
        self.size_other = size_other
        self.comfort_bonus = comfort_bonus
        self.name_jp = name_jp
        self.name_en = name_en
        self.desc_jp = desc_jp
        self.desc_en = desc_en
        self.icon = icon
        self.group = group
        self.interaction = interaction
        self.sources = sources

    def __repr__(self):
        return str(self.__dict__)

    @property
    def category(self):
        return {
            'Furnitures': 'furniture',
            'Interiors': 'cafe decoration',
            'Decorations': 'decoration'
        }[self._category]

    @property
    def subcategory(self):
        return {
            'Floor': 'floor',
            'Wallpaper': 'wallpaper',
            'Background': 'background',
            'WallDecoration': 'wall',
            'Closet': 'closet',
            'FloorDecoration': 'floor',
            'Chair': 'chair',
            'Table': 'table',
            'Prop': 'prop',
            'HomeAppliance': 'appliance',
            'FurnitureEtc': 'trophy',
            'Bed': 'bed'
        }[self._subcategory]

    @classmethod
    def from_data(cls, furniture_id, data):
        print ("model > Furniture class is deprecated, use classes.Funiture > Furniture")

        furniture = data.furniture[furniture_id]
        name_en = 'NameEn' in data.etc_localization[furniture['LocalizeEtcId']] and data.etc_localization[furniture['LocalizeEtcId']]['NameEn'] or None
        desc_en = 'DescriptionEn' in data.etc_localization[furniture['LocalizeEtcId']] and data.etc_localization[furniture['LocalizeEtcId']]['DescriptionEn'] or None
        
        furniture_group = furniture['SetGroudpId'] > 0 and FurnitureGroup.from_data(furniture['SetGroudpId'], data) or None

        interaction = []
        interaction_tags = set(furniture['CafeCharacterStateReq'] + furniture['CafeCharacterStateAdd'] + furniture['CafeCharacterStateMake'] + furniture['CafeCharacterStateOnly'])
        for item in data.cafe_interaction.values():
            if item['CafeCharacterState'] and bool(interaction_tags.intersection(item['CafeCharacterState'])):
                
                character_wiki_name = data.translated_characters[item['CharacterId']]['PersonalNameEn']
                character_wiki_name += f" ({data.translated_characters[item['CharacterId']]['VariantNameEn']})" if 'VariantNameEn' in data.translated_characters[item['CharacterId']] and data.translated_characters[item['CharacterId']]['VariantNameEn'] is not None else ''

                interaction.append(character_wiki_name)

        return cls(
            furniture['Id'],
            furniture['StarGradeInit'],
            furniture['Category'],
            furniture['SubCategory'],
            furniture['SizeWidth'],
            furniture['SizeHeight'],
            furniture['OtherSize'],
            furniture['ComfortBonus'],
            data.etc_localization[furniture['LocalizeEtcId']]['NameJp'],
            replace_glossary(name_en),
            data.etc_localization[furniture['LocalizeEtcId']]['DescriptionJp'],
            replace_glossary(desc_en),
            furniture['Icon'][furniture['Icon'].rfind('/')+1:],
            furniture_group,
            interaction,
            None #CraftNodes.from_data(furniture_id, data)
        )

        

class FurnitureGroup(object):
    def __init__(self, id, bonus_count, bonus_comfort, set_name_jp, set_name_en, set_desc_jp, set_desc_en, series_jp, series_en):
        self.id = id
        self.bonus_count = bonus_count
        self.bonus_comfort = bonus_comfort
        self.set_name_jp = set_name_jp
        self.set_name_en = set_name_en
        self.set_desc_jp = set_desc_jp
        self.set_desc_en = set_desc_en
        self.series_jp = series_jp
        self.series_en = series_en


    @classmethod
    def from_data(cls, group_id, data):
        print ("model > FurnitureGroup class is deprecated, use classes.Funiture > FurnitureGroup")

        furniture_group = data.furniture_group[group_id]
        #print(data.etc_localization[furniture['LocalizeEtcId']])
        name_en = 'NameEn' in data.etc_localization[furniture_group['GroupNameLocalize']] and data.etc_localization[furniture_group['GroupNameLocalize']]['NameEn'] or None
        desc_en = 'DescriptionEn' in data.etc_localization[furniture_group['GroupNameLocalize']] and data.etc_localization[furniture_group['GroupNameLocalize']]['DescriptionEn'] or None
        

        try: 
            series_jp = data.etc_localization[furniture_group['LocalizeEtcId']]['NameJp'] 
        except:
            series_jp = None
            pass
        try: 
            series_en = data.etc_localization[furniture_group['LocalizeEtcId']]['NameEn'] 
        except:
            series_en = None
            #print(furniture_group['LocalizeEtcId'])
            pass

        return cls(
            furniture_group['Id'],
            furniture_group['RequiredFurnitureCount'],
            furniture_group['ComfortBonus'],
            data.etc_localization[furniture_group['GroupNameLocalize']]['NameJp'],
            replace_glossary(name_en),
            data.etc_localization[furniture_group['GroupNameLocalize']]['DescriptionJp'],
            replace_glossary(desc_en),
            series_jp,
            replace_glossary(series_en)
        )
