import itertools
import operator
import re

from shared.functions import replace_units, statcalc_replace_statname


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


def _get_skill_effects(group, data):
    """Skill effects used by JP 1.74 character filter. Probably not a straight replica of ingame logic"""
    levels = [level for level in group if level['SkillFilterActivate']]
    if not levels:
        return

    for key in data.skills_localization[max(levels, key=operator.itemgetter('Level'))['LocalizeSkillId']]['SkillEffectList']:
        effect = data.skill_effects_localization[key]
        if effect['SkillFilterActivate']:
            yield effect


def _distinct_tables(skills):
    """Deduplicate tables; sibling skill groups can share all their texts"""
    shown = lambda skill: (skill.name, skill.name_translated, skill.icon, skill._damage_type, skill.damage_target_count, skill.show_skill_slot, skill.effect_names, skill.skill_cost, skill.description_general, [(level.description, level.cost) for level in skill.levels])
    distinct = []
    for skill in skills:
        if all(shown(skill) != shown(other) for other in distinct): distinct.append(skill)
    return distinct


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
    missing_skill_localization = None   # MissingTranslations collector, set by Character.from_data
    missing_skill_effect_localization = None

    def __init__(self, name, name_translated, icon, levels, description_general, max_level, damage_type, skill_cost, effect_data, additional_tooltip = [], select_ex_tooltip = [], show_skill_slot = '', effect_names = [], damage_target_count = 'None'):
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
        self.effect_names = effect_names
        self.damage_target_count = damage_target_count

    @property
    def damage_type(self):
        return {
            'Explosion': 'Explosive',
            'Pierce': 'Penetration',
            'Mystic': 'Mystic',
            'Sonic': 'Sonic',
            'Chemical': 'Corrosive'
        }[self._damage_type]
    
    @classmethod
    def from_data(cls, group_id, data, max_level = 10, show_skill_slot = None):

        group = [skill for skill in data.skills.values() if skill['GroupId'] == group_id]
        if not group:
            raise KeyError(group_id)

        def skill_type(slot):
            return {
                slot: slot,
                'Ex': 'EX',
                'ExtraPassive': 'Sub',
                'Public': 'Normal'
            }[slot]
        
        def format_description(levels, text_en):
            start_variables = re.findall(r'\{\{SkillValue\|([^\}\[]+)\}\}',  levels[0].description)
            end_variables = re.findall(r'\{\{SkillValue\|([^\}\[]+)\}\}',  levels[max_level-1].description)
            range_text = []

            for i, end in enumerate(end_variables):
                start = start_variables[i] if i < len(start_variables) else '0'
                #values listed as 1%/2%/3% get a range each
                parts = zip(start.split('/'), end.split('/')) if start.count('/') == end.count('/') else [(start, end)]
                range_text.append('/'.join(e if s == e else f"{re.findall(r'([0-9a-zA-z./]+).*', s)[0]}~{e}" for s, e in parts))

            for skill_value in range_text:
                text_en = re.sub(r'\$\d+', '{{SkillValue|' + skill_value + '}}', text_en, 1)

            return text_en.replace("\n",'<br>')
        

        additional_tooltip = []
        additional_skill_group_ids = []
        form_conversion_prefixes = set()
        if group[0]['AdditionalToolTipId'] != 0: 
            #print(f"group_id {group_id} has additional tooltips group: {group[0]['AdditionalToolTipId']} at max_level {max_level}")
            for add_tooltip in data.skill_additional_tooltip[group[0]['AdditionalToolTipId']]:
                additional_group_id = add_tooltip['AdditionalSkillGroupId']
                add_max_level = (add_tooltip['ShowSkillSlot'].upper() == 'EX' or show_skill_slot == 'EX') and 5 or 10
                additional_tooltip.append(Skill.from_data(additional_group_id, data, max_level=add_max_level ,show_skill_slot=add_tooltip['ShowSkillSlot']))
                additional_skill_group_ids.append(additional_group_id)

                additional_group = next((skill for skill in data.skills.values() if skill['GroupId'] == additional_group_id), None)
                if additional_group and additional_group.get('TextureSkillCardForFormConversion'):
                    match = re.match(r'^(.*\D)\d+$', additional_group_id)
                    if match:
                        form_conversion_prefixes.add(match.group(1))

            # Form-change skills are not always all listed in the additional-tooltip table.
            # Include sibling forms identified by SkillExcelTable's form-conversion metadata.
            for skill in data.skills.values():
                sibling_group_id = skill['GroupId']
                if (
                    skill['Level'] == 1
                    and skill.get('TextureSkillCardForFormConversion')
                    and sibling_group_id not in additional_skill_group_ids
                    and any(re.fullmatch(re.escape(prefix) + r'\d+', sibling_group_id) for prefix in form_conversion_prefixes)
                ):
                    additional_tooltip.append(Skill.from_data(sibling_group_id, data, max_level=5, show_skill_slot='Ex'))
                    additional_skill_group_ids.append(sibling_group_id)


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
            if cls.missing_skill_localization: cls.missing_skill_localization.add_entry(data.skills_localization[group[0]['LocalizeSkillId']])
        else:  
            skill_name_en = data.translated_skills[group[0]['GroupId']]['NameEn']

        if skill_name_en == None:
            print (f"No translation found for skill {data.skills_localization[group[0]['LocalizeSkillId']]['NameJp']}, group_id {group_id}")


        effect_names = []
        for effect in _get_skill_effects(group, data):
            name_en = effect.get('SkillEffectNameEN')
            if not name_en and cls.missing_skill_effect_localization:
                # texts only: translation rows override the game's fields
                cls.missing_skill_effect_localization.add_entry({key: value for key, value in effect.items() if key == 'Key' or key.endswith(('KR', 'JP'))})
            effect_names.append(name_en or effect['SkillEffectNameJP'])


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
            _distinct_tables(additional_tooltip),
            _distinct_tables(select_ex_tooltip),
            skill_type(show_skill_slot),
            effect_names,
            group[0]['SkillDamageTargetCount'],
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
            
            try:
                addition = data.translated_skills[group_id][f'AddOnLevel{i}']
                #a clause continues the sentence, a new sentence keeps its period
                skill_desc = (skill_desc if re.match(r'(\s|<br>)*[A-Z]', addition) else skill_desc.removesuffix('.')) + addition
            except KeyError: pass

    variables = re.findall(r'\[c]\[[0-9A-Fa-f]{6}]([^\[]*)\[-]\[/c]', replace_units(text_jp))
    #replacement_count = len(re.findall(r'\$[0-9]{1}', skill_desc))
    #if len(variables) > 0 and len(variables) != replacement_count: print(f'Mismatched number of variables ({len(variables)}/{replacement_count}) in {text_jp} / {skill_desc}')

    skill_desc = re.sub(r'\$(\d+)', 
        lambda m: '{{SkillValue|' + variables[int(m.group(1)) - 1] + '}}' if 1 <= int(m.group(1)) <= len(variables) else m.group(0), 
        skill_desc
    ).replace("\n", '<br>')

    return skill_desc
