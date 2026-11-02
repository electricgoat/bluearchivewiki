from shared.functions import damage_type as damage_type_glossary
from classes.Skill import Skill


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
