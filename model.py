import itertools
import operator
import re
#from googletrans import Translator


class Character(object):
    def __init__(self, id, name, dev_name, model_prefab_name, portrait, name_en, family_name_en, rarity, school, club, role, position, damage_type, armor_type, combat_class, equipment, weapon_type, uses_cover, profile, normal_skill, normal_gear_skill, ex_skill, passive_skill, passive_weapon_skill, sub_skill, stats, weapon, gear, favor, memory_lobby, momotalk, liked_gift_tags, is_limited):
        self.id = id
        self.name = name
        self.rarity = rarity
        self.school = school
        self._club = club
        self._role = role
        self.position = position
        self._damage_type = damage_type
        self._armor_type = armor_type
        self._combat_class = combat_class
        self.equipment = equipment
        self.weapon_type = weapon_type
        self._uses_cover = uses_cover
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
        self.memory_lobby = memory_lobby
        self.momotalk = momotalk
        self.liked_gift_tags = liked_gift_tags
        self.is_limited = is_limited

        self.dev_name = dev_name
        self.model_prefab_name = model_prefab_name

        self.portrait = portrait
        self.name_translated = name_en
        self.family_name_translated = family_name_en

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
        return {
            self._club: self._club,
            'Countermeasure': 'Countermeasure Council',
            'GourmetClub': 'Gourmet Research Club',
            'RemedialClass': 'Supplemental Classes Club',
            'SisterHood': 'Sisterhood',
            'Kohshinjo68': 'Handyman 68',
            'CleanNClearing': 'Cleaning & Clearing',
            'Shugyobu': 'Inner Discipline Club',
            'MatsuriOffice': 'Festival Organization Committee',
            'Endanbou': 'Chinese alchemy study group',
            'Class227': 'Class No. 227',
            'HoukagoDessert': 'After School Sweets Club',
            'GameDev': 'Game Development Club',
            'Veritas': 'Veritas',
            'Engineer': 'Engineering Club',
            'KnightsHospitaller': 'Rescue Knights',
            'FoodService': 'School Lunch Club',
            'PandemoniumSociety': 'Pandemonium Society',
            'RabbitPlatoon': 'RABBIT Platoon',
            'Emergentology': 'Emergency Medicine Department',
            'RedwinterSecretary': 'Red Winter Secretariat',
            'Fuuki': 'Disciplinary Committee',
            'NinpoKenkyubu': 'Ninjutsu Research Department',
            'anzenkyoku': 'Community Safety Bureau',
            'Justice': 'Justice Actualization Committee',
            'TrinityVigilance': 'Vigilante Corps',
            'Onmyobu': 'Yin-Yang Сlub',
            'BookClub': 'Library Committee',
            'Meihuayuan': 'Plum Blossom Garden',
            'TrainingClub': 'Training Club',
            'SPTF': 'Supernatural Phenomenon Task Force',
            'TheSeminar': 'Seminar',
            'AriusSqud': 'Arius Squad',
            'EmptyClub': 'no club'
        }[self._club]

    @property
    def damage_type(self):
        return {
            'Explosion': 'Explosive',
            'Pierce': 'Penetration',
            'Mystic': 'Mystic'
        }[self._damage_type]

    @property
    def armor_type(self):
        return {
            'LightArmor': 'Light',
            'HeavyArmor': 'Heavy',
            'Unarmed': 'Special'
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
    def name_normalized(self):
        return re.split("[ _(]", self.name_translated)[0]

    @classmethod
    def from_data(cls, character_id, data):
        character = data.characters[character_id]
        character_ai = data.characters_ai[character['CharacterAIId']]
        liked_gift_tags = data.characters_cafe_tags[character_id]['FavorItemTags']
        portrait = character['TextureDir'][character['TextureDir'].rfind('/')+1:]

        return cls(
            character['Id'],
            data.characters_localization[character_id]['PersonalNameJp'],
            character['DevName'],
            character['ModelPrefabName'],
            portrait,
            data.translated_characters[character_id]['PersonalNameEn'],
            data.translated_characters[character_id]['FamilyNameEn'],
            character['DefaultStarGrade'],
            character['School'] != 'RedWinter' and character['School'] or 'Red Winter',
            character['Club'],
            character['TacticRole'],
            character['TacticRange'],
            character['BulletType'],
            character['ArmorType'],
            character['SquadType'],
            character['EquipmentSlot'],
            character['WeaponType'],
            character_ai['CanUseObstacleOfKneelMotion'] or character_ai['CanUseObstacleOfStandMotion'],
            Profile.from_data(character_id, data),
            Skill.from_data(data.characters_skills[(character_id, 0, 0, False)]['PublicSkillGroupId'][0], data),
            (character_id, 0, 2, False) in data.characters_skills and Skill.from_data(data.characters_skills[(character_id, 0, 2, False)]['PublicSkillGroupId'][0], data) or None,
            Skill.from_data(data.characters_skills[(character_id, 0, 0, False)]['ExSkillGroupId'][0], data, 5),
            Skill.from_data(data.characters_skills[(character_id, 0, 0, False)]['PassiveSkillGroupId'][0], data),
            Skill.from_data(data.characters_skills[(character_id, 2, 0, False)]['PassiveSkillGroupId'][0], data),
            Skill.from_data(data.characters_skills[(character_id, 0, 0, False)]['ExtraPassiveSkillGroupId'][0], data),
            Stats.from_data(character_id, data),
            Weapon.from_data(character_id, data),
            (character_id, 1) in data.gear and Gear.from_data(character_id, data) or None,
            Favor.from_data(character_id, data),
            MemoryLobby.from_data(character_id, data),
            Momotalk.from_data(character_id, data),
            liked_gift_tags,
            'IsLimited' in data.translated_characters[character_id] or False
        )


class Profile(object):
    def __init__(self, full_name, age, birthday, height, hobbies, illustrator, voice, introduction_jp, introduction_en, reading, release_date_jp, weapon_name, weapon_desc, weapon_name_translated, weapon_desc_translated):
        self.full_name = full_name
        self._age = age
        self._birthday = birthday
        self.height = height
        self.hobbies = hobbies
        self.illustrator = illustrator
        self.voice = voice
        self.introduction_jp = introduction_jp
        self.introduction_en = introduction_en
        self.reading = reading
        self.release_date_jp = release_date_jp
        self.weapon_name = weapon_name
        self.weapon_desc = weapon_desc
        self.weapon_name_translated = weapon_name_translated
        self.weapon_desc_translated = weapon_desc_translated

    @property
    def age(self):
        return self._age[:-1]

    @property
    def birthday(self):
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

    @classmethod
    def from_data(cls, character_id, data):
        profile = data.characters_localization[character_id]
        weapon = data.translated_weapons[character_id]

        hobbies = 'HobbiesEn' in data.translated_characters[character_id] and data.translated_characters[character_id]['HobbiesEn'] or profile['HobbyJp']
        illustrator = 'Illust' in data.translated_characters[character_id] and data.translated_characters[character_id]['Illust'] or profile['ArtistNameJp']
        voice = 'VoiceEn' in data.translated_characters[character_id] and data.translated_characters[character_id]['VoiceEn'] or profile['CharacterVoiceJp']
        age = 'AgeEn' in data.translated_characters[character_id] and data.translated_characters[character_id]['AgeEn']+' ' or profile['CharacterAgeJp']
        height = 'HeightEn' in data.translated_characters[character_id] and data.translated_characters[character_id]['HeightEn'] or profile['CharHeightJp']
        release_date_jp = 'ReleaseDateJp' in data.translated_characters[character_id] and data.translated_characters[character_id]['ReleaseDateJp'] or ''
        introduction_en = 'ProfileIntroductionEn' in data.translated_characters[character_id] and data.translated_characters[character_id]['ProfileIntroductionEn'] or ''
 

        #translator = Translator()
        #
        #weapon_name_translated = translator.translate(profile['WeaponNameJp'], dest='en', src='ja').text
        #weapon_desc_translated = translator.translate(profile['WeaponDescJp'], dest='en', src='ja').text
        #print(weapon_name_translated)
        #weapon_name_translated = None
        #weapon_desc_translated = None

        return cls(
            f'{profile["FamilyNameJp"]} {profile["PersonalNameJp"]}',
            age,
            profile['BirthDay'],
            height,
            hobbies,
            illustrator,
            voice,
            '<p>' + profile['ProfileIntroductionJp'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            '<p>' + introduction_en.replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            f'{profile["FamilyNameRubyJp"]} {profile["PersonalNameJp"]}',
            release_date_jp,
            profile['WeaponNameJp'],
            '<p>' + profile['WeaponDescJp'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            weapon['NameEN'],
            '<p>' + weapon['DescriptionEN'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
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
    def __init__(self, name, name_translated, icon, levels, description_general, damage_type, skill_cost, effect_data):
        self.name = name
        self.icon = icon
        self.levels = levels
        self._damage_type = damage_type

        # Extra information
        self.name_translated = name_translated
        self.description_general = description_general
        #self.max_level = 10
        self.skill_cost = skill_cost
        self.effect_data = effect_data

    @property
    def damage_type(self):
        return {
            'Explosion': 'Explosive',
            'Pierce': 'Penetration',
            'Mystic': 'Mystic'
        }[self._damage_type]

    @classmethod
    def from_data(cls, group_id, data, max_level = 10):
        group = [skill for skill in data.skills.values() if skill['GroupId'] == group_id]
        if not group:
            raise KeyError(group_id)





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
                text_en = re.sub(r'\$[0-9]{1}', '{{SkillValue|' + skill_value + '}}', text_en, 1)

            return text_en.replace("\n",'<br>')

        levels = [SkillLevel.from_data(level, group_id, data) for level in sorted(group, key=operator.itemgetter('Level'))]

        skill_cost = []
        for i in range(1, max_level):
            if levels[i].cost != levels[i-1].cost:
                #print (f'Skill level {i+1} cost change from {levels[i-1].cost} to {levels[i].cost}')
                skill_cost.append({'level':i+1, 'cost':levels[i].cost})

        text_general = translate_skill(levels[9].description, max_level, group_id, data)
        description_general = format_description(levels, text_general)


        try: data.translated_skills[group[0]['GroupId']]['NameEn']
        except KeyError: 
            skill_name_en = None
        else:  
            skill_name_en = data.translated_skills[group[0]['GroupId']]['NameEn']

        if skill_name_en == None:
            print (f"No translation found for skill {data.skills_localization[group[0]['LocalizeSkillId']]['NameJp']}, group_id {group_id}")


        effect_data = None
        if group_id.find('Passive') > -1 and group_id.find('ExtraPassive') == -1:
            effect_data = {}
            #print(f'Parsing skill {group_id}')
            for effect in data.levelskill[group_id]['EntityTimeline'][len(data.levelskill[group_id]['EntityTimeline'])-2]['Entity']['Abilities'][0]['LogicEffectGroupIds']:
                amount_base = []
                amount_percentage = []

                if data.logiceffectdata[f'{effect}_Lv1']['EffectData']['Category'] != 'Dummy':
                    for lv in range(1,11):
                        amount_base.append(data.logiceffectdata[f'{effect}_Lv{lv}']['EffectData']['BaseAmount'])
                        amount_percentage.append(data.logiceffectdata[f'{effect}_Lv{lv}']['EffectData']['TargetCoefficientAmount'])
                    if amount_base[9] == '0': amount_base = None
                    if amount_percentage[9] == '0': amount_percentage = None

                    effect_data[effect] = {'stat_name': statcalc_replace_statname(data.logiceffectdata[f'{effect}_Lv1']['EffectData']['StatType']), 'amount_base': amount_base, 'amount_percentage': amount_percentage}
                
            #print(effect_data)
        

        return cls(
            data.skills_localization[group[0]['LocalizeSkillId']]['NameJp'],
            skill_name_en,
            group[0]['IconName'].rsplit('/', 1)[-1],
            levels,
            description_general,
            group[0]['BulletType'],
            skill_cost,
            effect_data
        )


def replace_units(text):
    
    text = re.sub('1回', 'once', text)
    #text = re.sub('2回', 'twice', text)
    #text = re.sub('3回', 'three times', text)
    text = re.sub('回', '', text)
    text = re.sub('つ', '', text)
    text = re.sub('秒', ' seconds', text)
    text = re.sub('個', '', text)
    text = re.sub('発分', ' hits', text)
    return text

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

    for i in range(len(variables)):
        skill_desc = re.sub(f'\${i+1}', '{{SkillValue|' + variables[i] + '}}', skill_desc).replace("\n",'<br>')
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
    def __init__(self, id, image_path, attack_power, attack_power_100, max_hp, max_hp_100, heal_power, heal_power_100, stat_type, stat_value, rank2_desc, rank3_desc):
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



    @classmethod
    def from_data(cls, character_id, data):
        weapon = data.weapons[character_id]
        stats = data.characters_stats[character_id]



        weapon_passive_skill = Skill.from_data(data.characters_skills[(character_id, 2, 0, False)]['PassiveSkillGroupId'][0], data)

        #print (passive_skill.name_translated)
        #try: data.translated_skills[group[0]['GroupId']]['NameEn']
        #except KeyError: 
        #    skill_name_en = None
        #else:  
        #    skill_name_en = data.characters_skills[(character_id, False)]['PassiveSkillGroupId'][0] #data.translated_skills[group[0]['GroupId']]['NameEn']

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
        #{{Icon|Urban|size=20}} Urban area affinity {{Affinity|SS}} SS


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
            rank3_desc
        )


class Gear(object):
    def __init__(self, name_en, name_jp, desc_en, desc_jp, icon, tier1_desc, tier2_desc, levels, effect_data):
        self.name_en = name_en
        self.name_jp = name_jp
        self.desc_en = desc_en
        self.desc_jp = desc_jp
        self.icon = icon
        self.tier1_desc = tier1_desc
        self.tier2_desc = tier2_desc
        self.levels = levels
        self.effect_data = effect_data

    @classmethod
    def from_data(cls, character_id, data):
        levels = {}

        for gear in data.gear:
            if gear[0] == character_id:
                levels[gear[1]] = {'stat_type':replace_statnames(data.gear[(character_id , gear[1])]['StatType']), 'stat_value':data.gear[(character_id , gear[1])]['MaxStatValue']}


        tier1_desc = "Increase " + levels[1]['stat_type'][0] + " by {{SkillValue|" + str(levels[1]['stat_value']) + "}}"
        tier2_desc = 'Normal Skill changes to '

        effect_data = {'stat_name': replace_statnames(levels[1]['stat_type'][0]), 'amount_base': str(levels[1]['stat_value'])}

        return cls(
            'NameEn' in data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]] and data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['NameEn'] or None,
            data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['NameJp'],
            'DescriptionEn' in data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]] and '<p>' + data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['DescriptionEn'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>' or None,
            '<p>' + data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['DescriptionJp'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            data.gear[(character_id , 1)]['Icon'].rsplit('/', 1)[-1],
            tier1_desc,
            tier2_desc,
            levels,
            effect_data
        )
        

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


class MemoryLobby(object):
    def __init__(self, image, unlock_level):
        self.image = image
        self.unlock_level = unlock_level


    @classmethod
    def from_data(cls, character_id, data):
        try: lobby_data = data.memory_lobby[character_id]
        except KeyError: return cls( None, None )

        unlock_level = None
        for favor_reward in data.favor_rewards:
            if favor_reward[0] == character_id:
                if 'MemoryLobby' in data.favor_rewards[(character_id , favor_reward[1])]['RewardParcelType']: unlock_level = data.favor_rewards[(character_id , favor_reward[1])]['FavorRank']
        
        return cls(
            lobby_data['RewardTextureName'][lobby_data['RewardTextureName'].rfind('/')+1:],
            unlock_level
        )


class Momotalk(object):
    def __init__(self, levels):
        self.levels = levels

    @classmethod
    def from_data(cls, character_id, data):
        levels = []


        for favor_reward in data.favor_rewards:
            if favor_reward[0] == character_id:
                #print(data.favor_rewards[(character_id , favor_reward[1])]['FavorRank'])
                levels.append(favor_reward[1])  

        return cls(
            levels
        )


def replace_statnames(stat_list):
    list_out = []
    if type(stat_list) == str: stat_list = [stat_list] 
    
    for item in stat_list:
        item = re.sub('_Base', '', item)
        item = re.sub('Power', '', item)
        item = re.sub('Max', '', item)
        item = re.sub('Point', '', item)
        item = re.sub('Rate', '', item)
        item = re.sub('Normal', '', item)
        item = re.sub('Heal', 'Healing', item)
        item = re.sub('Speed', ' Speed', item)
        item = re.sub('Damage', ' Damage', item)

        list_out.append(item)     
    #return([re.sub('_Base', '', item) for item in stat_list])
    return (list_out)

def statcalc_replace_statname(stat_name):
    return {
            'AttackPower': 'attack',
            'DefensePower': 'defense',
            'HealPower': 'healing',
            'MaxHP': 'hp',

            'CriticalDamageRate': 'crit_damage',
            'CriticalPoint': 'crit_rate',
            'AccuracyPoint': 'accuracy',
            'DodgePoint': 'evasion',
            'OppressionPower': 'cc_str',
            '': 'cc_res',
            '': 'crit_res',
            '': 'critdamage_res',
            'HealEffectivenessRate': 'healing_inc',
            'StabilityPoint': 'stability',
            'NormalAttackSpeed': '',
            'BlockRate': '',
            'MoveSpeed': 'move_speed',
            'DefensePenetration': '',
            'MaxBulletCount': ''
        }[stat_name]
