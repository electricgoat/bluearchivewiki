"""
EXPERIMENTAL: skill descriptions generated from skill mechanics rather than from translated JP text.

A skill's LevelSkill timeline says which LogicEffect groups get applied, to whom, how often and under which conditions,
and the LogicEffect rows (one per skill level) hold the numbers. Enum values in both are resolved to the game's names
by shared/battle_schema.py. Effects are worded by classes/SkillEffects.py, anything unrecognized shows up as
[Type: TemplateId] or (conditional: Type) so gaps are easy to find with scripts/skill_mechanics_check.py.
"""
import collections
import copy
import difflib
import json
import re

from classes.SkillEffects import describe_effect, end_condition, of_target, rate_text
from shared.battle_schema import type_name
from shared.functions import hashkey
from shared.glossary import CLUBS, SCHOOLS
from shared.skill_glossary import (STAT_NAMES, STATUS_NAMES, CATEGORY_NAMES, ARMOR_NAMES, BULLET_NAMES, ROLE_NAMES, ENTITY_NAMES, AREA_SHAPES, TARGET_NOUNS,
                                   SUBJECTS, COMPARISONS, COUNT_COMPARISONS, slot_name, slot_names, truncate, percent, seconds, frames, skill_value, capitalize, split_words, status_name)

SUMMON_SKILL_SLOTS = {'PublicSkillGroupId': 'Normal skill', 'PassiveSkillGroupId': 'Passive skill', 'ExtraPassiveSkillGroupId': 'Sub skill', 'NormalSkillGroupId': 'normal attack'}
# skills without descriptions of their own, whose abilities get described as part of the skill that enables them
UNLOCKABLE_SKILL_SLOTS = {'NormalSkillGroupId': 'normal attacks', 'HiddenPassiveSkillGroupId': 'additionally'}
SPAWN_KINDS = {'CharacterEntityDAO': 'unit', 'BattleItemEntityDAO': 'battle item', 'ObstacleEntityDAO': 'obstacle', 'BarrierObstacleEntityDAO': 'barrier'}
PREVIEW_ENTITIES = ('MainEntityData', 'BundledMainEntityDatas')  # copies of what EntityTimeline/ShotFrames actually spawn
SKILL_VALUE = r'\{\{SkillValue\|([^}]*)\}\}'
# enemy size tags, found by comparing tagged conditions with JP descriptions
SIZE_TAGS = {29: 'medium-sized', 67: 'medium-sized', 26: 'large', 68: 'large', 69: 'large', 30: 'extra-large', 288: 'a boss'}
SQUAD_NAMES = {'Main': 'Striker', 'Support': 'Special', 'TSS': 'Tactical Support'}
MENTION = '\x02([^\x03]*)\x03([^\x04]*)\x04'  # a single target named in a clause, marked with the targeting that picks it (Application.mention)
# parenthesized conditions of a clause: '(if the target has X)', '(against Heavy Armor targets)', '(50% chance)'
CONDITION_NOTE = r'\((?:if |while |against |unless |with |on every |on other |once per |before |at |\{\{SkillValue\|[^}]*\}\} chance)'
VISUAL_MARKERS = r'Visual|_FX$|Emoji'  # markers that only drive visuals
STANDARD_SPLASH_RADIUS = 100  # normal attack area of grenade and rocket launchers
DESCRIBED_SLOTS = ('Ex', 'Public', 'Passive', 'ExtraPassive')  # skill slots with descriptions of their own
PLAIN_ATTACK = r'deal \{\{SkillValue\|100%\}\} of Attack as damage to [a-z ]+?(?: over \{\{SkillValue\|\d+\}\} hits(?: \(\{\{SkillValue\|[\d.]+%\}\} per hit\))?)?'  # a normal attack's damage, which goes without saying
MIN_DELAY = 5 * 30  # frames before an ability delay is worth mentioning


def stacks(effect: dict) -> bool:
    return bool(effect.get('StackSameEffectApplied')) and effect.get('StackSameEffectCount', 0) > 1


def ability_group_lists(node):
    """LogicEffectGroupIds of every ability in a timeline"""
    if isinstance(node, list):
        for item in node: yield from ability_group_lists(item)
    elif isinstance(node, dict):
        if node.get('LogicEffectGroupIds'): yield node['LogicEffectGroupIds']
        for value in node.values():
            if isinstance(value, (dict, list)): yield from ability_group_lists(value)


def skill_slot(group_id: str) -> str:
    """Kind of skill slot a skill group id or SkillSlot belongs to, 'CH0084ExtraPassive01' -> 'ExtraPassive'"""
    return next((slot for slot in ('ExtraPassive', 'HiddenPassive', 'Passive', 'Public', 'Ex', 'Normal') if slot in group_id), group_id)


def tag_number(letters: str) -> int:
    """Tag number of an obfuscated CharacterExcelTable tag, the reverse of tag_string: 'ex' -> 515"""
    number = 0
    for letter in letters: number = number * 52 + ((ord(letter) - ord('A')) * 2 if letter.isupper() else (ord(letter) - ord('a')) * 2 + 1)
    return number


def tag_string(tag: int) -> str:
    """Obfuscated FlatData.Tag name of a tag number, as used in CharacterExcelTable Tags: base 52 over AaBb..Zz"""
    letters = ''
    while True:
        tag, digit = divmod(tag, 52)
        letters = chr((ord('A') if digit % 2 == 0 else ord('a')) + digit // 2) + letters
        if tag == 0: return letters


class Lexicon(object):
    """Names and lookups that need game data beyond a single skill, shared by every skill described from the same data"""
    _instances = {}

    def __init__(self, data):
        self.data = data
        self.students = [x for x in data.characters.values() if x['IsPlayableCharacter'] and x['ProductionStep'] == 'Release']
        self.name_tokens = {token.lower() for x in data.characters.values() if x['IsPlayableCharacter'] or x['DevName'].startswith('SM') for token in x['DevName'].split('_')}
        self.visible_templates = set(data.logic_effect_visuals)
        # a template can be reused by unrelated effects: it stacks only if every group using it stacks, and templates of many owners are generic internal flags
        groups = collections.defaultdict(list)
        for group_id, rows in data.logic_effects.items(): groups[rows[0]['TemplateId']].append((group_id, stacks(rows[0])))
        self.stacking_templates = {template for template, users in groups.items() if all(stacking for _, stacking in users)}
        self.generic_templates = {template for template, users in groups.items() if len({group_id.split('_')[0] for group_id, _ in users}) >= 3}
        self._form_templates = None
        self.skill_lists = collections.defaultdict(list)
        for key, row in data.characters_skills.items():
            for group_ids in (v for k, v in row.items() if k.endswith('SkillGroupId')):
                for group_id in group_ids: self.skill_lists[group_id].append(key)
        self.skills = {}
        self.skill_data_keys = {x['GroupId']: x['SkillDataKey'] for x in data.skills.values()}
        self._brief_flags = None
        self._skill_names_jp = None
        self._referenced = {}
        self._timelines = {}
        self._resolving = set()
        self.tag_names = {}  # tag numbers named by spawn conditions: 696 -> 'Raid_Lunatic'

    @classmethod
    def of(cls, data):
        if id(data) not in cls._instances: cls._instances = {id(data): cls(data)}
        return cls._instances[id(data)]

    def mechanics(self, group_id: str, max_level: int, caster: dict | None = None):
        """Nested SkillMechanics (summons, forms, unlocked abilities), or None for skills without mechanics data"""
        key = (group_id, max_level, caster and caster['Id'])
        if key not in self.skills:
            try: self.skills[key] = SkillMechanics.from_data(group_id, self.data, max_level, nested=True, caster=caster)
            except (KeyError, StopIteration): self.skills[key] = None
        return self.skills[key]

    def marker_name(self, template_id: str) -> str:
        """Name of a character-unique effect: translation/SkillEffects.json, or words left over from its TemplateId"""
        if template_id not in self.data.translated_skill_effects and (family := self.family_name(template_id)):
            return f"{family} level {int(re.search(r'(\d+)$', template_id).group(1))}"
        if template_id in self.data.translated_skill_effects:
            names = self.data.translated_skill_effects[template_id]
            if names.get('NameEn') or names.get('NameJp'): return names.get('NameEn') or names['NameJp']
        noise = r'dummy|effect|check|icon|buff|debuff|original|default|lv\d*|\d+|ex|public|passive|extra|hidden|normal|gear|weapon|ch\d+|sm\d+|status|add'
        words = [x for x in split_words(re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', template_id)).split() if not re.fullmatch(noise, x.lower()) and x.lower() not in self.name_tokens]
        return ' '.join(words) or 'unique effect'

    def is_notable_marker_template(self, template_id: str) -> bool:
        """Markers players can see (buff icon) or count (stacks), rather than internal flags"""
        if template_id in self.data.translated_skill_effects or self.family_name(template_id): return True
        if re.search(VISUAL_MARKERS, template_id): return False
        if hashkey(template_id) in self.visible_templates: return True
        return template_id not in self.generic_templates and template_id in self.stacking_templates

    def family_name(self, template_id: str) -> str | None:
        """Name of a numbered marker family ('Dummy_CH0355_01_Flower_Icon01' -> 'Flower Bud') when the family has a name of its own"""
        match = re.match(r'^(Dummy.*?)_?(?:Lv)?\d{1,2}$', template_id)
        names = self.data.translated_skill_effects.get(match.group(1), {}) if match and match.group(1) != template_id else {}
        return names.get('NameEn') or names.get('NameJp') or None

    def is_notable_marker(self, effect: dict) -> bool:
        if effect['TemplateId'] in self.data.translated_skill_effects or self.family_name(effect['TemplateId']): return True
        if re.search(VISUAL_MARKERS, effect['TemplateId']): return False
        if hashkey(effect['TemplateId']) in self.visible_templates: return True
        return effect['TemplateId'] not in self.generic_templates and stacks(effect)

    @property
    def brief_flags(self) -> set[str]:
        """Internal markers that never last over a second, such as a lock while another skill finishes"""
        if self._brief_flags is None:
            durations = collections.defaultdict(set)
            for rows in self.data.logic_effects.values():
                if rows[0]['Type'] == 'Dummy': durations[rows[0]['TemplateId']].add(int(rows[0].get('EndConditionArgument', 0) or 0))
            self._brief_flags = {template for template, values in durations.items() if all(0 < x <= 1000 for x in values) and not self.is_notable_marker_template(template)}
        return self._brief_flags

    @property
    def form_templates(self) -> dict[str, str]:
        """
        Internal markers other skills check to know about a form: 'form' ones come from skills that convert form (having them means being in the alternate form),
        'form attack' ones are put on targets by skills only used in an alternate form (the target was hit by them)
        """
        if self._form_templates is None:
            self._form_templates = {}
            data_keys = {x['GroupId']: x['SkillDataKey'] for x in self.data.skills.values()}
            for group_id, keys in self.skill_lists.items():
                if not data_keys.get(group_id) or data_keys[group_id] not in self.data.levelskill: continue
                rows = [self.data.logic_effects[x][0] for group_ids in ability_group_lists(self.data.levelskill[data_keys[group_id]]) for x in group_ids if x in self.data.logic_effects]
                markers = {x['TemplateId'] for x in rows if x['Type'] == 'Dummy' and not self.is_notable_marker(x) and not re.search(r'\d+$', x['TemplateId'])}
                if any(x['Type'] == 'FormConversion' for x in rows): self._form_templates |= dict.fromkeys(markers, 'form')
                elif all(key[3] > 0 for key in keys): self._form_templates |= dict.fromkeys(markers, 'form attack')
        return self._form_templates

    def effect_name(self, template_id: str) -> str:
        return f'"{self.marker_name(template_id)}"' if 'Dummy' in template_id else status_name(template_id)

    def group_effect_name(self, group_id: str) -> str:
        rows = self.data.logic_effects.get(group_id)
        return self.effect_name(rows[0]['TemplateId']) if rows else split_words(group_id)

    def character_name(self, character_id: int) -> str:
        names = self.data.translated_characters.get(character_id)
        if names is None: return self.data.characters.get(character_id, {}).get('DevName', str(character_id))
        return names['PersonalNameEn'] + (f" ({names['VariantNameEn']})" if names.get('VariantNameEn') else '')

    def personal_names(self, characters: list[dict]) -> str:
        return ', '.join(sorted({self.data.translated_characters.get(x['Id'], {}).get('PersonalNameEn', x['DevName']) for x in characters}))

    def tag_text(self, tags: list[int], enemies: bool = False) -> str:
        """Enemy sizes, or who has any of these tags as a group of students"""
        if enemies and all(x in SIZE_TAGS for x in tags): return ' or '.join(dict.fromkeys(SIZE_TAGS[x] for x in tags))
        names = {tag_string(x) for x in tags}
        holders = [x for x in self.data.characters.values() if names & set(x.get('Tags') or [])]
        # tags shared by a student and a unit she summons pick out that summon
        students_holding = {x['DevName'].split('_')[0] for x in holders if x['TacticEntityType'] == 'Student'}
        if any(x['TacticEntityType'] == 'Summoned' for x in holders) and len(students_holding) == 1: return 'the summon'
        having = [x for x in self.students if names & set(x['Tags'])]
        if not having: return ' or '.join(dict.fromkeys(SIZE_TAGS.get(x, f'tagged {self.tag_names.get(x, x)}') for x in tags))
        if len(having) > len(self.students) * 0.9: return 'students'
        for field, glossary in (('Club', CLUBS), ('School', SCHOOLS)):
            values = {x.get(field) for x in having}
            # a club or school only when all of its students have the tags
            if len(values) == 1 and None not in values and all(names & set(x['Tags']) for x in self.students if x.get(field) in values): return f'{glossary.get(*values, *values)} students'
        return self.personal_names(having)

    def form_skills(self, group_id: str, form_index: int) -> dict[str, str]:
        """Normal attack and skills a character uses in another form, where they differ from the base form"""
        keys = self.skill_lists.get(group_id)
        if not keys: return {}
        base = self.data.characters_skills[(keys[0][0], 0, 0, 0)]
        form = self.data.characters_skills.get((keys[0][0], 0, 0, form_index))
        if form is None: return {}
        changed = {label: form[slot][0] for slot, label in SUMMON_SKILL_SLOTS.items() if form.get(slot) and form[slot] != base.get(slot)}
        ex_skills = [x for x in form.get('ExSkillGroupId', []) if x != 'EmptySkill' and x not in base.get('ExSkillGroupId', [])]
        if ex_skills and group_id not in ex_skills: changed['EX skill'] = ex_skills[0]
        return changed

    def base_form_ex_skill(self, group_id: str) -> str | None:
        """EX skill a character gets back when leaving the form whose EX skill this is"""
        keys = self.skill_lists.get(group_id)
        if not keys or any(x[3] == 0 for x in keys): return None
        base = self.data.characters_skills.get((keys[0][0], 0, 0, 0), {})
        return next((x for x in base.get('ExSkillGroupId', []) if x != 'EmptySkill'), None)

    def skill_name(self, group_id: str) -> str:
        """Translated name of a skill group, the translated name of another group with the same JP name (later stages of a skill), or its JP name"""
        if self.data.translated_skills.get(group_id, {}).get('NameEn'): return self.data.translated_skills[group_id]['NameEn']
        name = self.skill_names_jp.get(group_id, group_id)
        return next((self.data.translated_skills[x]['NameEn'] for x, jp in self.skill_names_jp.items() if jp == name and self.data.translated_skills.get(x, {}).get('NameEn')), name)

    @property
    def skill_names_jp(self) -> dict[str, str]:
        if self._skill_names_jp is None:
            self._skill_names_jp = {x['GroupId']: self.data.skills_localization[x['LocalizeSkillId']]['NameJp'] for x in self.data.skills.values()
                                    if self.data.skills_localization.get(x['LocalizeSkillId'], {}).get('NameJp')}
        return self._skill_names_jp

    def blackboard_entity_name(self, key: str) -> str | None:
        """
        Name of the marker given together with writing a unit to a blackboard key, which targeting then picks by that key:
        Iroha (Swimsuit) writes her Partner to 'CH0346_Saboru' while granting "Partner"
        """
        writers = {group for group, rows in self.data.logic_effects.items() if rows[0]['Type'] == 'WriteEntityToBlackboard' and rows[0].get('BlackboardKeyToWrite') == key}
        def walk(node):
            if isinstance(node, list): return next((x for x in map(walk, node) if x), None)
            if not isinstance(node, dict): return None
            if writers & set(node.get('LogicEffectGroupIds', [])):
                markers = [self.data.logic_effects[g][0] for g in node['LogicEffectGroupIds'] if g in self.data.logic_effects and self.data.logic_effects[g][0]['Type'] == 'Dummy']
                if markers: return self.marker_name(markers[0]['TemplateId'])
            return next((x for x in map(walk, node.values()) if x), None)
        for skill in {self.group_skill(x) for x in writers} - {None}:
            if (name := walk(self.data.levelskill[self.skill_data_keys[skill]])): return name
        return None

    def counter_name(self, key: str, group_id: str) -> str | None:
        """
        Name of the marker a character stacks together with adding to a blackboard counter, as the counter's name:
        Ibuki (Swimsuit) adds to 'PersonalResourceCommon' while gaining "Seashell" stacks
        """
        character = self.character_part(group_id)
        adders = {group for group, rows in self.data.logic_effects.items() if rows[0]['Type'] == 'BlackBoardAdd' and rows[0].get('BlackBoardKey') == key and self.character_part(group) == character}
        def walk(node):
            if isinstance(node, list): return next((x for x in map(walk, node) if x), None)
            if not isinstance(node, dict): return None
            if adders & set(node.get('LogicEffectGroupIds', [])):
                markers = [self.data.logic_effects[g][0] for g in node['LogicEffectGroupIds'] if g in self.data.logic_effects and self.data.logic_effects[g][0]['Type'] == 'Dummy']
                if markers and self.is_notable_marker(markers[0]): return self.marker_name(markers[0]['TemplateId'])
            return next((x for x in map(walk, node.values()) if x), None)
        for skill in {group.replace('_', '').rsplit('Effect', 1)[0] for group in adders}:
            key_data = next((v for k, v in self.skill_data_keys.items() if k.replace('_', '') == skill), None)
            if key_data and (name := walk(self.data.levelskill[key_data])): return name
        return None

    @staticmethod
    def character_part(group_id: str) -> str | None:
        """'CH0347_HiddenPassive01_Effect01' or 'CH0347HiddenPassive01' -> 'CH0347'"""
        match = re.match(r'^(.+?)_?(?:Ex|Public|Passive|ExtraPassive|WeaponPassive|GearPublic|HiddenPassive|Normal)\d+(?:_|$)', group_id)
        return match.group(1) if match else None

    def character_abilities(self, group_id: str) -> list[tuple[str, dict, dict, list[dict]]]:
        """
        Every ability of every skill of the character an effect group belongs to:
        (skill group id, ability, the entity holding it, the other abilities of that entity)
        """
        character = self.character_part(group_id)
        if character is None: return []
        if character not in self._timelines:
            abilities = []
            def walk(skill, node, entity):
                if isinstance(node, list):
                    for item in node: walk(skill, item, entity)
                if not isinstance(node, dict): return
                if type_name(node).endswith('EntityDAO'): entity = node
                for key in ('Abilities', 'AreaAbilities', 'InitialAbilities'):
                    siblings = node.get(key) or []
                    abilities.extend((skill, ability, entity, siblings) for ability in siblings if isinstance(ability, dict) and 'LogicEffectGroupIds' in ability)
                for key, value in node.items():
                    if key not in PREVIEW_ENTITIES: walk(skill, value, entity)
            for skill, data_key in self.skill_data_keys.items():
                if data_key and re.match(rf'^{re.escape(character)}(?:Ex|Public|Passive|ExtraPassive|WeaponPassive|GearPublic|HiddenPassive|Normal)\d', skill):
                    try: walk(skill, self.data.levelskill[data_key], {})
                    except KeyError: pass
            self._timelines[character] = abilities
        return self._timelines[character]

    def template_groups(self, template_id: str) -> list[str]:
        return [group for group, rows in self.data.logic_effects.items() if rows[0]['TemplateId'] == template_id]

    def proxy_flag(self, template_id: str) -> dict | None:
        """
        The condition an internal flag stands for, when a character sets the flag on itself only depending on that one condition about others:
        Shun (Swimsuit) Kid gets 'Dummy_CH0355_02_CheckAddCostAlly' if another ally has tag 872, so not having it means no such ally
        """
        groups = self.template_groups(template_id)
        rows = [self.data.logic_effects[g][0] for g in groups]
        if not rows or any(r['Type'] != 'Dummy' or int(r.get('EndConditionArgument', 0) or 0) > 0 or stacks(r) for r in rows) or self.is_notable_marker_template(template_id): return None
        setters = [(ability, entity) for g in groups[:1] for _, ability, entity, _ in self.character_abilities(g) if set(ability['LogicEffectGroupIds']) & set(groups)]
        if len(setters) != 1: return None
        ability, entity = setters[0]
        modifiers = ability.get('Modifiers') or []
        side = (entity.get('EssentialCandidateRule') or {}).get('TargetSide')
        if len(modifiers) == 1 and modifiers[0].get('CheckTarget') not in ('Caster', 'Target') and side in ('Self', None, 'None'): return modifiers[0]
        return None

    def unit_counter(self, template_id: str) -> tuple[str, str] | None:
        """
        A stacking marker a character gives itself once per unit carrying a tag it put on them, as a count of those units:
        Shun (Swimsuit) Kid's 'Count Ally' stacks are one per other ally tagged plus one for herself -> ('ally (including self)', 'allies (including self)')
        """
        if template_id in self._resolving or template_id not in self.stacking_templates: return None
        groups = self.template_groups(template_id)
        skills = {skill for g in groups[:1] for skill, ability, _, _ in self.character_abilities(g) if set(ability['LogicEffectGroupIds']) & set(groups)}
        if len(skills) != 1: return None
        self._resolving.add(template_id)
        try: skill = self.mechanics(skills.pop(), 1)
        finally: self._resolving.discard(template_id)
        if skill is None: return None
        apps = [app for app in skill.applications if self.data.logic_effects[app.group_id][0]['TemplateId'] == template_id]
        tagged = {x.checks[0] for app in apps for x in app.conditions if x.checks}
        if not apps or len(tagged) != 1 or any(len(app.conditions) != 1 or not app.conditions[0].tier for app in apps): return None
        offsets = {len(app.hit_rates) - app.conditions[0].tier['sort'] for app in apps}
        taggers = [app for app in skill.applications if self.data.logic_effects[app.group_id][0]['TemplateId'] in tagged and not app.conditions and not app.is_self]
        if len(offsets) != 1 or not taggers: return None
        singular, plural = TARGET_NOUNS.get(taggers[0].rule.get('TargetSide'), ('unit', 'units'))
        if offsets.pop() == 1: return f"{singular.removeprefix('other ')} (including self)", f"{plural.removeprefix('other ')} (including self)"
        return singular, plural

    def role_variant(self, template_id: str) -> tuple[str, str] | None:
        """
        A marker given next to another one only to targets of a class, so other skills can count that class:
        Ibuki (Swimsuit)'s 'Dummy_CH0347_PlayFriend_Dealer' is "Friend" for Attackers -> ('Attacker', 'Dummy_CH0347_PlayFriend')
        """
        groups = set(self.template_groups(template_id))
        for _, ability, _, siblings in (x for g in list(groups)[:1] for x in self.character_abilities(g)):
            if not groups & set(ability['LogicEffectGroupIds']): continue
            modifiers = ability.get('Modifiers') or []
            if len(modifiers) != 1 or type_name(modifiers[0]) != 'CountListTacticRoleModifierDAO' or modifiers[0].get('CheckTarget') != 'Target' or len(modifiers[0].get('TacticRoleList', [])) != 1: return None
            for sibling in siblings:
                if sibling.get('Modifiers'): continue
                base = next((self.data.logic_effects[g][0]['TemplateId'] for g in sibling['LogicEffectGroupIds'] if g in self.data.logic_effects and self.data.logic_effects[g][0]['Type'] == 'Dummy'), None)
                if base and base != template_id: return ROLE_NAMES.get(modifiers[0]['TacticRoleList'][0], modifiers[0]['TacticRoleList'][0]), base
        return None

    def hosting_skills(self, group_id: str) -> set[str]:
        """Skills of the character that carry abilities belonging to this skill's slot (IsReferenceSkillSlot)"""
        slot = skill_slot(group_id)
        return {skill for skill, ability, _, _ in self.character_abilities(group_id)
                if skill != group_id and ability.get('IsReferenceSkillSlot') and skill_slot(ability.get('ReferenceSkillSlot') or '') == slot}

    def hidden_ex_draw(self, group_id: str) -> bool:
        """Whether a hidden passive of the character draws an EX skill card when an EX skill is used (Shun (Swimsuit), described with her EX skill)"""
        for skill, ability, _, _ in self.character_abilities(group_id):
            if 'HiddenPassive' not in skill and skill_slot(ability.get('ReferenceSkillSlot') or '') != 'HiddenPassive': continue
            for g in ability['LogicEffectGroupIds']:
                row = self.data.logic_effects.get(g, [{}])[0]
                # any EX skill, with a draw ready from the start (slot-specific gauges and gauges filled by other mechanics are described where they belong)
                if (row.get('Type') == 'ExSkillCardRedrawGauge' and row.get('GaugeChargeCondition') == 'UseSkill' and str(row.get('ConditionParameter')).lower() == 'ex'
                        and row.get('InitialRedrawStackCount', 0) > 0 and set(row.get('TargetExSkillSlot') or ['None']) == {'None'}): return True
        return False

    def referenced_names(self, group_id: str) -> set[str]:
        """
        Every name the skills of a group's character check or point to: TemplateIds and group ids in conditions and triggers,
        and in fields of the effects those skills apply other than the effects' own ids (removing a marker does not use it)
        """
        character = self.character_part(group_id)
        if character not in self._referenced:
            names = set()
            def tokens(node): names.update(re.findall(r'\w+', json.dumps(node, ensure_ascii=False)))
            def walk(node, checking):
                if isinstance(node, list):
                    for item in node: walk(item, checking)
                if not isinstance(node, dict): return
                if checking: tokens(node); return
                for group in node.get('LogicEffectGroupIds', []):
                    for row in self.data.logic_effects.get(group, [])[:1]:
                        tokens({k: v for k, v in row.items() if k not in ('GroupId', 'TemplateId', 'CommonVisualId', 'LogicEffectTemplateToDispel')})
                if node.get('SpawnConditionParameter'): tokens(node['SpawnConditionParameter'])
                for key, value in node.items():
                    if key not in PREVIEW_ENTITIES: walk(value, key in ('Modifiers', 'TriggerCondition', 'AutoUseRule'))
            for skill in {skill for skill, *_ in self.character_abilities(group_id)}:
                try: walk(self.data.levelskill[self.skill_data_keys[skill]], False)
                except KeyError: pass
            self._referenced[character] = names
        return self._referenced[character]

    def timer_period(self, template_id: str, group_id: str) -> float | None:
        """
        Seconds between uses of a skill used whenever an internal timer marker runs out, 'Dummy_CH0346_Public01Trigger':
        the marker's duration plus the frame it is applied at, when every skill of the character applying it agrees on that,
        and a passive triggered by using the skill starts the timer again
        """
        rows = [self.data.characters_skills[key] for key in self.skill_lists.get(group_id, [])]
        periods, restarts = set(), False
        def walk(node, frame):
            if isinstance(node, list):
                for item in node: walk(item, frame)
            if not isinstance(node, dict): return
            frame += node.get('Frame', 0) + node.get('StartDelay', 0)
            for group in node.get('LogicEffectGroupIds', []):
                effect = self.data.logic_effects.get(group, [{}])[0]
                if effect.get('TemplateId') == template_id and int(effect.get('EndConditionArgument', 0) or 0) > 0:
                    period = int(effect['EndConditionArgument']) / 1000 + frame / 30
                    periods.add(round(period) if abs(period - round(period)) <= 0.1 else round(period, 1))
            for key, value in node.items():
                if key not in PREVIEW_ENTITIES: walk(value, frame)
        for group in {g for row in rows for field, ids in row.items() if field.endswith('SkillGroupId') for g in ids}:
            if group not in self.skill_data_keys: continue
            try: timeline = self.data.levelskill[self.skill_data_keys[group]]
            except KeyError: continue
            before = len(periods)
            walk(timeline, 0)
            trigger = timeline.get('TriggerCondition') or {}
            if len(periods) > before or template_id in str(timeline):
                restarts |= trigger.get('Event') in ('BattleEntity_UseSkillStart', 'BattleEntity_UseSkillEnd') and trigger.get('Parameters') == skill_slot(group_id)
        return periods.pop() if len(periods) == 1 and restarts else None

    def form_id(self, group_id: str, form_index: int | None = None) -> str | None:
        """
        Id of a character form in translation/SkillEffects.json, 'CH0368_1': the character part of an effect group's id and a FormIndex.
        Without a FormIndex, the form the group's skill is used in
        """
        match = re.match(r'^(.+?)_(?:Ex|Public|Passive|ExtraPassive|WeaponPassive|GearPublic|HiddenPassive|Normal)\d+_', group_id)
        if form_index is None: form_index = max((key[3] for key in self.skill_lists.get(self.group_skill(group_id), [])), default=0)
        return f'{match.group(1)}_{form_index}' if match and form_index else None

    def form_name(self, group_id: str, form_index: int | None = None) -> str | None:
        """Name of a character form, 'Submerged state'"""
        names = self.data.translated_forms.get(self.form_id(group_id, form_index), {})
        return names.get('NameEn') or names.get('NameJp') or None

    def group_skill(self, group_id: str) -> str | None:
        """Described skill an effect group belongs to by its name, 'CH0368_Ex02_Effect01' -> 'CH0368Ex02'"""
        match = re.match(r'^(.+?)_((?:Ex|Public|Passive|ExtraPassive|WeaponPassive|GearPublic)\d+)_', group_id)
        if not match: return None
        skill = match.group(1) + match.group(2)
        return skill if skill in self.skill_lists else None

    def unlockable_skills(self, group_id: str) -> list[tuple[str, str]]:
        """(label, group id) of normal attacks and hidden passives in the skill lists a skill belongs to, and of the character's summons' skills"""
        found = {}
        for key in (x for x in self.skill_lists.get(group_id, []) if x[3] == 0):
            for slot, label in UNLOCKABLE_SKILL_SLOTS.items():
                for sibling in self.data.characters_skills[key].get(slot, []):
                    if sibling != group_id: found.setdefault(sibling, label)
        for character in self.summoned_characters(group_id):
            skill_list = self.data.characters_skills.get((self.data.costumes[character['CostumeGroupId']]['CharacterSkillListGroupId'], 0, 0, 0), {})
            for slot in list(SUMMON_SKILL_SLOTS) + ['HiddenPassiveSkillGroupId']:
                for skill in skill_list.get(slot, []): found.setdefault(skill, 'the summon')
        return [(label, sibling) for sibling, label in found.items()]

    def summoned_characters(self, group_id: str) -> list[dict]:
        """Characters the skills of a group's character summon"""
        names = {node['UniqueName'] for _, _, entity, _ in self.character_abilities(group_id) for node in [entity] if type_name(node) == 'CharacterEntityDAO' and node.get('UniqueName')}
        return [x for x in self.data.characters.values() if x['DevName'] in names]

    def level_markers(self, group_id: str) -> dict[str, int]:
        """
        Markers a character gives itself to carry a skill level to skills that cannot check it, one template per level:
        Reisa (Magical)'s 'Dummy_CH0326_PublicLevelCheck_Lv03' stands for level 3 of her Normal skill
        """
        markers = {}
        for group, rows in self.data.logic_effects.items():
            # hidden passives are what carry levels around
            if 'HiddenPassive' not in group or self.character_part(group) != self.character_part(group_id): continue
            # one group per level, or one group whose rows carry a template per level
            named = {int(match.group(1)): rows[0]['TemplateId'] for match in [re.search(r'_Lv(\d+)$', group)] if match}
            named = named or {row['Level']: row['TemplateId'] for row in rows} if len(rows) > 1 else named
            if named and len(set(named.values())) == len(named) and all(re.search(rf'Lv0?{level}$', template) for level, template in named.items()):
                markers.update({template: level for level, template in named.items()})
        return markers


class Condition(object):
    """A requirement for an ability to apply. Tiered conditions (counts of stacks, allies etc.) let abilities that only differ by count merge into one clause"""
    def __init__(self, text: str, tier: dict | None = None, template: str | None = None, include: bool = True, checks: tuple | None = None, caster_tags: frozenset | None = None):
        self.text = text
        self.caster_tags = caster_tags  # tag numbers the caster needs any of (or none of): raid difficulty variants
        self.tier = tier            # key, sort, count (text), unit, phrase ('with {count} {unit}')
        self.template = template    # TemplateId a has/has not condition checks on the caster
        self.include = include
        self.checks = checks        # (TemplateId, CheckTarget) of any condition on an effect

    def __repr__(self):
        return self.text


def tier_condition(key, count_min: int, count_max: int, unit: str, units: str) -> Condition:
    count = f'{count_min}' if count_min == count_max else f'{count_min}+' if count_max < 0 or count_max >= 99 else f'{count_min}~{count_max}'
    return Condition(f'with {skill_value(count)} {unit if count == "1" else units}', {'key': key, 'sort': count_min, 'count': count, 'unit': unit, 'phrase': 'with {count} {unit}'})


def count_condition(key, count_min: int, count_max: int, include: bool, check_target: str, name: str, unit: str, units: str, template: str | None = None) -> Condition:
    """Condition on how many of something there are: having any of it at all, or a count tier. Excluded ranges get turned around"""
    unbounded = count_max < 0 or count_max >= 99
    checks = (template, check_target) if template else None
    if count_min <= 1 and unbounded: return Condition(has_condition(check_target, include, name), include=include, checks=checks)
    if not include:
        if count_min <= 0: count_min, count_max = count_max + 1, -1
        elif unbounded: count_min, count_max = 0, count_min - 1
    condition = tier_condition(key, count_min, count_max, unit, units)
    condition.checks = checks
    return condition


def template_condition(template: str, check_target: str, include: bool, lexicon: Lexicon) -> Condition:
    """Having an effect or not. Markers numbered by level or stage (_Lv2, Check02) are tiers"""
    caster_template = template if check_target == 'Caster' else None
    if lexicon.form_templates.get(template) == 'form':
        return Condition(f"while {'' if include else 'not '}in an alternate state", template=caster_template, include=include, checks=(template, check_target))
    if lexicon.form_templates.get(template) == 'form attack':
        return Condition(f"if {SUBJECTS.get(check_target, 'the target')} {'was' if include else 'was not'} hit by an attack made in an alternate state", template=caster_template, include=include, checks=(template, check_target))

    text = has_condition(check_target, include, lexicon.effect_name(template))
    level = re.match(r'^(.*?)_?Lv(\d+)$', template) or re.match(r'^(Dummy.*?\D)(\d{2})$', template)
    tier = None
    if level and lexicon.marker_name(level.group(1)) == 'unique effect' and not lexicon.is_notable_marker_template(template):
        # unnamed numbered markers are stages
        stage = int(level.group(2))
        text = f'at stage {stage}' if include else f'before stage {stage}'
        if include: tier = {'key': ('stage', level.group(1)), 'sort': stage, 'count': str(stage), 'unit': 'stage', 'phrase': 'at {unit} {count}'}
    elif level and include:
        tier = {'key': ('marker level', level.group(1)), 'sort': int(level.group(2)), 'count': str(int(level.group(2))), 'unit': f'{lexicon.effect_name(level.group(1))} level', 'phrase': 'at {unit} {count}'}
    return Condition(text, tier, template=caster_template, include=include, checks=(template, check_target))


def has_condition(check_target: str, has: bool, what: str) -> str:
    if check_target == 'Caster': return f"while {'having' if has else 'not having'} {what}"
    return f"if {SUBJECTS.get(check_target, check_target)} {'has' if has else 'does not have'} {what}"


def describe_modifier(modifier: dict, lexicon: Lexicon) -> Condition | tuple | None:
    """A Condition, or (slot, operator, level) for a skill level check"""
    kind = type_name(modifier).removesuffix('ModifierDAO')
    include = modifier.get('IncludeType', 'Include') != 'Exclude'
    subject = SUBJECTS.get(modifier.get('CheckTarget'), 'the target')
    among = {'CasterAlly': 'among allies (including self)', 'CasterAllyExceptCaster': 'among other allies', 'CasterEnemy': 'among enemies'}.get(modifier.get('CheckTarget'), f'on {subject}')

    match kind:
        case 'SkillLevel':
            return (skill_slot(modifier['SkillSlot']), modifier['Operator'], modifier['SkillLevel'])
        case 'LogicEffectTemplate':
            if modifier['CheckTarget'] == 'Caster' and (proxy := lexicon.proxy_flag(modifier['TemplateId'])):
                return describe_modifier(dict(proxy, IncludeType='Include' if (proxy.get('IncludeType') != 'Exclude') == include else 'Exclude'), lexicon)
            return template_condition(modifier['TemplateId'], modifier['CheckTarget'], include, lexicon)
        case 'CountLogicEffectTemplate' | 'CountListLogicEffectTemplate':
            templates = modifier.get('TemplateIdList') or [modifier['TemplateId']]
            name = ' or '.join(lexicon.effect_name(x) for x in templates)
            held = '' if modifier['CheckTarget'] == 'Caster' else f' {among}'
            # none of a marker that never stacks on self or the target is simply not having it, stack counts and holders among allies are tiers
            if include and modifier['CountMin'] <= 0 and modifier['CountMax'] == 0 and modifier['CheckTarget'] in ('Caster', 'Target') and not any(x in lexicon.stacking_templates for x in templates):
                return describe_modifier({'$type': 'LogicEffectTemplateModifierDAO', 'TemplateId': templates[0], 'IncludeType': 'Exclude', 'CheckTarget': modifier['CheckTarget']}, lexicon)
            if modifier['CheckTarget'] == 'Caster' and len(templates) == 1 and (units := lexicon.unit_counter(templates[0])):
                return count_condition(('units', templates[0]), modifier['CountMin'], modifier['CountMax'], include, 'Caster', units[1], units[1], units[1])
            if len(templates) == 1 and (variant := lexicon.role_variant(templates[0])):
                name = f'{variant[0]} {lexicon.effect_name(variant[1])}'
                return count_condition(('templates', *templates, modifier['CheckTarget']), modifier['CountMin'], modifier['CountMax'], include, modifier['CheckTarget'], name, f'{name}{held}', f'{name}s{held}', templates[0])
            return count_condition(('templates', *templates, modifier['CheckTarget']), modifier['CountMin'], modifier['CountMax'], include, modifier['CheckTarget'], name, f'{name} stack{held}', f'{name} stacks{held}', templates[0])
        case 'CountListLogicEffectGroupId':
            name = ' or '.join(lexicon.group_effect_name(x) for x in modifier['LogicEffectGroupIdList'])
            template = lexicon.data.logic_effects[modifier['LogicEffectGroupIdList'][0]][0]['TemplateId'] if modifier['LogicEffectGroupIdList'][0] in lexicon.data.logic_effects else None
            return count_condition(('groups', *modifier['LogicEffectGroupIdList'], modifier['CheckTarget']), modifier['CountMin'], modifier['CountMax'], include, modifier['CheckTarget'], name, f'{name} {among}', f'{name} {among}', template)
        case 'LogicEffectCategory':
            return Condition(has_condition(modifier['CheckTarget'], include, f"a {CATEGORY_NAMES.get(modifier['LogicEffectCategory'], modifier['LogicEffectCategory'])}"))
        case 'CountListLogicEffectCategory':
            names = ' or '.join(CATEGORY_NAMES.get(x, x) for x in modifier['LogicEffectCategoryList'])
            return count_condition(('categories', *modifier['LogicEffectCategoryList'], modifier['CheckTarget']), modifier['CountMin'], modifier['CountMax'], include, modifier['CheckTarget'], f'a {names}', f'{names} {among}', f'{names}s {among}')
        case 'CountTagConditional':
            count = COUNT_COMPARISONS.get(modifier['DiffOperator'], '{}').format(modifier['Count'])
            group = lexicon.tag_text(modifier['TagConstraintsInt'])
            return Condition(f'with {skill_value(count)} {group} {among}', {'key': ('tags', *modifier['TagConstraintsInt'], modifier['CheckTarget']), 'sort': modifier['Count'],
                                                                           'count': count, 'unit': f'{group} {among}', 'phrase': 'with {count} {unit}'})
        case 'TagConditional':
            if modifier['CheckTarget'] in ('CasterAlly', 'CasterAllyExceptCaster'):
                other = 'another ally' if modifier['CheckTarget'] == 'CasterAllyExceptCaster' else 'an ally'
                return Condition(f"{'if' if include else 'unless'} {other} is {lexicon.tag_text(modifier['TagConstraintsInt']).replace(', ', ' or ')}", include=include)
            return Condition(f"if {subject} {'is' if include else 'is not'} {lexicon.tag_text(modifier['TagConstraintsInt'], enemies=modifier['CheckTarget'] == 'Target')}",
                             include=include, caster_tags=frozenset(modifier['TagConstraintsInt']) if modifier['CheckTarget'] == 'Caster' else None)
        case 'CountEntityListCombined':
            # units matching every enabled check get counted
            checks = []
            if modifier.get('CheckTemplateId'):
                templates = modifier['TemplateId']['List']
                internal = all('Dummy' in x and not lexicon.is_notable_marker_template(x) for x in templates)
                checks.append('affected' if internal else 'with ' + ' or '.join(lexicon.effect_name(x) for x in templates))
            if modifier.get('CheckLogicEffectCategory'): checks.append('with ' + ' or '.join(CATEGORY_NAMES.get(x, x) for x in modifier['LogicEffectCategory']['List']))
            if modifier.get('CheckTacticRole'): checks.append('/'.join(ROLE_NAMES.get(x, x) for x in modifier['TacticRole']['TacticRoleList']))
            if modifier.get('CheckArmorType'): checks.append('/'.join(ARMOR_NAMES.get(x, x) for x in modifier.get('ArmorType', {}).get('ArmorTypeList', [])))
            if modifier.get('CheckBulletType'): checks.append('/'.join(BULLET_NAMES.get(x, x) for x in modifier.get('BulletType', {}).get('BulletTypeList', [])))
            if modifier.get('CheckEntityInCircle'): checks.append(f"within {modifier['EntityInCircle']['RangeMax']} range")
            noun = {'CasterAlly': ('ally', 'allies'), 'CasterAllyExceptCaster': ('other ally', 'other allies'), 'CasterEnemy': ('enemy', 'enemies')}.get(modifier['CheckTarget'], ('unit', 'units'))
            adjectives = ' '.join(x for x in checks if not x.startswith('with') and not x.startswith('within'))
            trailing = ' '.join(x for x in checks if x.startswith('with'))
            unit, units = (' '.join(x for x in (adjectives, n, trailing) if x) for n in noun)
            return count_condition(('entities', str(checks), modifier['CheckTarget']), modifier['CountMin'], modifier['CountMax'], include, modifier['CheckTarget'], units, unit, units)
        case 'CountListLogicEffectType':
            names = ' or '.join(split_words(x).lower() for x in modifier['LogicEffectTypeList'])
            return count_condition(('types', *modifier['LogicEffectTypeList'], modifier['CheckTarget']), modifier['CountMin'], modifier['CountMax'], include, modifier['CheckTarget'],
                                   f'a {names} effect', f'{names} effect {among}', f'{names} effects {among}')
        case 'CountListTacticRole':
            if modifier['CheckTarget'] == 'Target' and modifier['CountMin'] <= 1 and include:
                names = ' or '.join(ROLE_NAMES.get(x, x) for x in modifier['TacticRoleList'])
                return Condition(f"if the target is {'an' if names[:1] in 'AEIOU' else 'a'} {names}")
            names = ' or '.join(ROLE_NAMES.get(x, x) for x in modifier['TacticRoleList'])
            return tier_condition(('roles', *modifier['TacticRoleList'], modifier['CheckTarget']), modifier['CountMin'], modifier['CountMax'], f'{names} {among}', f'{names}s {among}')
        case 'CountSquadAbsence':
            what = {'Dead': 'defeated ally', 'EmptySlot': 'empty squad slot'}.get(modifier['AbsenceType'], 'absent ally')
            return tier_condition(('absence', modifier['AbsenceType']), modifier['AbsenceRangeMin'], modifier['AbsenceRangeMax'], what, what + 's')
        case 'SchoolConditional':
            school = SCHOOLS.get(modifier['SchoolConstraint']['School'], modifier['SchoolConstraint']['School'])
            school_included = modifier['SchoolConstraint']['IncludeType'] != 'Exclude'
            count = modifier['CountConstraint']
            if count['DiffOperator'] == 'None' or modifier['CheckTarget'] == 'Target':
                return Condition(f"if {subject} {'is' if school_included else 'is not'} a {school} student")
            count_text = COUNT_COMPARISONS.get(count['DiffOperator'], '{}').format(count['Count'])
            students = f"{'' if school_included else 'non-'}{school} students {among}"
            return Condition(f'with {skill_value(count_text)} {students}', {'key': ('school', school, school_included, modifier['CheckTarget']), 'sort': count['Count'],
                                                                           'count': count_text, 'unit': students, 'phrase': 'with {count} {unit}'})
        case 'HpRate':
            return Condition(f"if {subject} HP is {COMPARISONS[modifier['Operator']].format(skill_value(percent(modifier['HpRate'])))}")
        case 'HpRateDamage':
            return Condition(f"damage ×{skill_value(f'{modifier['MaxDamageMultiplier'] / 10000:g}~{modifier['MinDamageMultiplier'] / 10000:g}')} the lower {subject} HP is")
        case 'StatValueDamage':
            stat = STAT_NAMES.get(modifier['StatType'], modifier['StatType'])
            return Condition(f"damage ×{skill_value(f'{modifier['MinDamageMultiplier'] / 10000:g}~{modifier['MaxDamageMultiplier'] / 10000:g}')} based on {subject} {stat}")
        case 'TargetDistanceDamage':
            return Condition(f"damage ×{skill_value(f'{modifier['MinMultiplier'] / 10000:g}~{modifier['MaxMultiplier'] / 10000:g}')} based on distance to the target")
        case 'CoverStateDamage':
            return Condition(f"damage ×{skill_value(f'{modifier['Multiplier'] / 10000:g}')} if the target is {'in cover' if modifier['CoverState'] == 'Covered' else 'not in cover'}")
        case 'TacticEntityDamage':
            return Condition(f"damage ×{skill_value(f'{modifier['Multiplier'] / 10000:g}')} against {ENTITY_NAMES.get(modifier['TacticEntity'], modifier['TacticEntity'])}s")
        case 'CoverStateConditional':
            cover = 'in cover' if modifier['CoverState'] == 'Covered' else 'not in cover'
            return Condition(f"while {cover}" if modifier['CheckTarget'] == 'Caster' else f"if {subject} is {cover}")
        case 'StatusConditional':
            if not include and modifier['StatusToCheck'] in ('Dead', 'Dying'): return None  # abilities never apply to defeated units anyway
            return Condition(f"if {subject} is {'' if include else 'not '}{STATUS_NAMES.get(modifier['StatusToCheck'], modifier['StatusToCheck'])}")
        case 'CharacterIdConditional':
            return Condition(f"if {subject} is {'' if include else 'not '}{' or '.join(lexicon.character_name(x) for x in modifier['CharacterIdList'])}")
        case 'PersonalityIdConditional':
            characters = [x for x in lexicon.students if x['PersonalityId'] in modifier['PersonalityIdList']]
            return Condition(f"if {subject} is {'' if include else 'not '}{lexicon.personal_names(characters).replace(', ', ' or ')}")
        case 'FormIndexCheck':
            form = 'an alternate state' if modifier['FormIndex'] else 'the normal state'
            return Condition(f"while {'' if include else 'not '}in {form}")
        case 'ArmorCondition':
            return Condition(f"{'against' if include else 'unless against'} {ARMOR_NAMES.get(modifier['ArmorType'], modifier['ArmorType'])} targets")
        case 'BulletTypeCondition':
            return Condition(f"if {subject} attack type is {'' if include else 'not '}{BULLET_NAMES.get(modifier['BulletType'], modifier['BulletType'])}")
        case 'TacticEntityConditional':
            constraint = modifier['Constraint']
            entity = ENTITY_NAMES.get(constraint['TacticEntity'], str(constraint['TacticEntity']))
            return Condition(f"{entity}s only" if constraint['IncludeType'] != 'Exclude' else f"except {entity}s")
        case 'TargetSideConditional':
            return Condition(f"if {subject} is {'' if include else 'not '}{TARGET_NOUNS.get(modifier['TargetSide'], ('', modifier['TargetSide']))[1]}")
    return Condition(f'conditional: {kind}')


def spawn_condition(node: dict, lexicon: Lexicon) -> Condition | tuple | None:
    """Conditions on SkillEntitySpawner timeline entries"""
    condition, parameter = node['SpawnCondition'], node.get('SpawnConditionParameter', '')
    subject = 'the target' if node.get('SpawnConditionCheckTarget') == 'Target' else 'self'
    include = not condition.startswith('Exclude')
    match condition:
        case 'None': return None
        case 'Rate': return Condition(f'{skill_value(percent(parameter))} chance')
        case 'HPRateUnder' | 'HPRateOver': return Condition(f"if {subject} HP is {'below' if condition == 'HPRateUnder' else 'above'} {skill_value(percent(parameter))}")
        case 'IncludeLogicEffectTemplateId' | 'ExcludeLogicEffectTemplateId':
            return template_condition(parameter, 'Caster' if subject == 'self' else 'Target', include, lexicon)
        case 'IncludeArmorType' | 'ExcludeArmorType': return Condition(f"{'against' if include else 'unless against'} {ARMOR_NAMES.get(parameter, parameter)} targets")
        case 'IncludeTag' | 'ExcludeTag':
            tags = [int(x) for x in re.findall(r'\d+', str(node.get('SpawnConditionParameterForTag') or parameter))]
            lexicon.tag_names.update(zip(tags, re.split(r',\s*', parameter)))
            return Condition(f"if {subject} {'is' if include else 'is not'} {lexicon.tag_text(tags, enemies=subject != 'self')}", include=include,
                             caster_tags=frozenset(tags) if subject == 'self' else None)
        case 'IncludeFormIndex' | 'ExcludeFormIndex': return Condition(f"while {'' if include else 'not '}in an alternate state")
        case 'TargetSideId': return Condition(f"if the target is {TARGET_NOUNS.get(parameter, ('', parameter))[1]}")
        case 'UsedExtraSkillCostSameOrOver' | 'UsedExtraSkillCostSameOrUnder':
            return Condition(f"if {skill_value(parameter)} or {'more' if condition.endswith('Over') else 'less'} additional skill cost was spent")
    return Condition(f'conditional: {condition} {parameter}'.strip())


def candidate_filters(rule: dict | None, lexicon: Lexicon, enemies: bool) -> tuple[str, str]:
    """Adjectives and a trailing qualifier for targets narrowed down by an OptionalCandidateRule: ('Striker', 'with HP below 50%')"""
    if not rule: return '', ''
    adjectives, qualifiers = [], []
    def active(constraint): return constraint and constraint.get('IncludeType', 'None') != 'None'
    def negation(constraint): return 'non-' if constraint['IncludeType'] == 'Exclude' else ''

    if (key := (rule.get('BlackboardConstraint') or {}).get('KeyString')) and (name := lexicon.blackboard_entity_name(key)): qualifiers.append(f'with "{name}"')
    if active(squad := rule.get('SquadTypeConstraint')): adjectives.append(negation(squad) + SQUAD_NAMES.get(squad['SquadType'], str(squad['SquadType'])))
    if active(role := rule.get('TacticRoleConstraint')) and role['TacticRole']: adjectives.append(negation(role) + '/'.join(ROLE_NAMES.get(x, x) for x in role['TacticRole']))
    if active(school := rule.get('SchoolConstraint')): adjectives.append(negation(school) + SCHOOLS.get(school['School'], str(school['School'])))
    if active(weapon := rule.get('WeaponConstraint')): adjectives.append(negation(weapon) + str(weapon['Weapon']))
    if active(bullet := rule.get('BulletConstraint')): adjectives.append(negation(bullet) + BULLET_NAMES.get(bullet['BulletType'], str(bullet['BulletType'])))
    if active(ranges := rule.get('TacticRangeConstraint')) and ranges['TacticRanges']: adjectives.append(negation(ranges) + '/'.join(ranges['TacticRanges']).lower() + '-line')
    if active(tags := rule.get('TagConstraint')) and tags.get('TagNamesInt'):
        group = lexicon.tag_text(tags['TagNamesInt'], enemies)
        qualifiers.append(group if group == 'the summon' else f"{'who are' if tags['IncludeType'] != 'Exclude' else 'who are not'} {group}")
    if active(personalities := rule.get('PersonalityIdConstraint')) and personalities.get('PersonalityIds'):
        characters = [x for x in lexicon.students if x['PersonalityId'] in personalities['PersonalityIds']]
        qualifiers.append(f"({'only ' if personalities['IncludeType'] != 'Exclude' else 'except '}{lexicon.personal_names(characters)})")
    if (hp := rule.get('HPRateConstraint', {})).get('ConstraintType', 'None') != 'None':
        qualifiers.append(f"with HP {'above' if hp['ConstraintType'] == 'HPOver' else 'below'} {skill_value(percent(hp['HPRate']))}")
    if rule.get('CoverState', 'None') != 'None': qualifiers.append('in cover' if rule['CoverState'] == 'Covered' else 'not in cover')
    return ' '.join(adjectives), ' '.join(qualifiers)


class Application(object):
    """A LogicEffect group applied by a skill, together with the targeting, timing and conditions it is applied under"""
    def __init__(self, group_id: str, context: dict, conditions: list[Condition], level_checks: list[tuple], reference_slot: str | None = None):
        self.group_id = group_id
        self.reference_slot = reference_slot        # SkillSlot whose skill the ability belongs to, when hosted by another skill's timeline
        self.rule = context['rule']
        self.filters = context['filters']
        self.sort = context['sort']
        self.area = context['area']
        self.selection = context.get('selection')     # the timeline entity whose targeting picks the targets, same for abilities sharing it
        self.radius = context.get('radius')           # of a circular or fan-shaped area
        self.area_frames = context['area_frames']     # how long an area or aura lingers
        self.interval = context['interval']           # how often an aura applies its abilities
        self.delay = context['delay'] if context['delay'] >= MIN_DELAY else 0
        self.bounces = context['bounces']
        self.conditions = conditions
        self.level_checks = level_checks              # (slot, operator, level)
        self.hit_rates = []                           # DamageDistributeRate of every hit
        self.piercing = context.get('piercing')        # (damage lost per enemy pierced, the floor it stops at)
        self.fallback = None                          # target text of a second pick when the first finds nobody
        self.frame = context.get('frame', 0) + context['delay']  # when the ability applies, counted from the skill's start

    @property
    def key(self):
        return (self.group_id, self.target, tuple(x.text for x in self.conditions), tuple(self.level_checks), self.delay, self.reference_slot)

    @property
    def is_self(self):
        return self.rule.get('TargetSide') in ('Self', None, 'None')

    @property
    def target(self) -> str:
        side, count = self.rule.get('TargetSide', 'None'), self.rule.get('MaxTargetCount', 1)
        if side in ('Self', 'None'): return 'self'
        if side in ('EventTarget', 'Spawned'): return self.rule['Name']

        adjectives, qualifier = self.filters
        if qualifier == 'the summon': return qualifier
        singular, plural = (re.sub(r'^(other )?', lambda m: f'{m.group(0)}{adjectives} ' if adjectives else m.group(0), x) for x in TARGET_NOUNS.get(side, (side, side)))
        if self.area and count == 1: text = f'one {singular}'
        elif self.area: text = f'{plural} in a {self.area} area'
        else: text = f'one {singular}' if count == 1 else f'all {plural}' if count < 0 else f'up to {count} {plural}'
        if qualifier: text += f' {qualifier}'
        if self.sort and count > 0 and (not self.area or count == 1): text += f' {self.sort}'
        if self.fallback: text += f' (or, if there is none, {self.fallback})'
        return text

    @property
    def mention(self) -> str:
        """Target text for clauses: a single target is marked with its targeting, so the next clause about it can call it 'the target' (refer_back)"""
        text = self.target
        return f'\x02{self.selection}\x03{text}\x04' if self.selection is not None and text.startswith('one ') else text

    def as_self(self):
        return Application(self.group_id, {'rule': {'TargetSide': 'Self'}, 'filters': ('', ''), 'sort': None, 'area': None, 'area_frames': 0, 'interval': 0, 'delay': 0, 'bounces': 0}, [], [])

    def level_conditions(self, slot_levels: dict[str, int]) -> list[Condition] | None:
        """None if a skill level check fails, otherwise conditions for checks on skills whose level is not known here"""
        unresolved = []
        for slot, operator, value in self.level_checks:
            if slot not in slot_levels:
                count = f'{value}+' if operator == 'GreaterOrEqual' else str(value)
                tier = {'key': ('skill level', slot), 'sort': value, 'count': count, 'unit': f'{slot_name(slot)} skill level', 'phrase': 'at {unit} {count}'} if operator in ('Equal', 'GreaterOrEqual') else None
                unresolved.append(Condition(f'if {slot_name(slot)} skill level is {COMPARISONS[operator].format(value)}', tier))
                continue
            level = slot_levels[slot]
            if not {'Equal': level == value, 'NotEqual': level != value, 'Less': level < value, 'LessOrEqual': level <= value,
                    'Greater': level > value, 'GreaterOrEqual': level >= value}.get(operator, True): return None
        return unresolved


def sort_text(rule: dict, lexicon: Lexicon) -> str | None:
    """How targets get picked, 'with the lowest HP'"""
    criteria, order = rule['SortCriteria'], rule['OrderBy'].lower()
    match criteria:
        case 'Distance': return 'farthest away' if order == 'highest' else None
        case 'None': return None
        case 'LogicEffectTemplateCount': return f"prioritizing those with {lexicon.effect_name(rule['SortParameter'])}" if rule.get('SortParameter') else None
        case 'HPRate' | 'CurrentHP': return f'with the {order} HP'
        case 'Stat': return f"with the {order} {STAT_NAMES.get(rule.get('SortStat'), 'stat')}"
        case 'BuffCount' | 'DebuffCount' | 'CrowdControlCount': return f"with the {'most' if order == 'highest' else 'fewest'} {CATEGORY_NAMES[criteria.removesuffix('Count').replace('Buff', 'Buff')] if criteria.removesuffix('Count') in CATEGORY_NAMES else split_words(criteria.removesuffix('Count')).lower()}s"
        case 'SummonedTime': return f"summoned {'most recently' if order == 'highest' else 'earliest'}"
    return f"with the {order} {STAT_NAMES.get(criteria, split_words(criteria))}"


def bounce_depth(node) -> int:
    depth = 0
    while isinstance(node, dict) and node:
        depth, node = depth + 1, node.get('BounceProjectileEntity')
    return depth


def collect_applications(node, applications: dict, summons: dict, context: dict):
    """Walks a timeline down to its abilities, carrying targeting and hit info down from the entities they sit in"""
    if isinstance(node, list):
        for item in node: collect_applications(item, applications, summons, context)
        return
    if not isinstance(node, dict): return

    lexicon, node_type = context['lexicon'], type_name(node)
    if node_type.endswith('EntityDAO'):
        # areas that sweep (a growing ring, a turning fan, a rectangle moving forward) cover a different part on every hit frame, hitting an enemy once
        sweeps = (node.get('CollisionProperty') or {}).get('TransformType', 'None') not in ('None', None)
        context = dict(context, hit_frames=1 if sweeps else len(node.get('HitFrames', [])) or 1)
        if node.get('EssentialCandidateRule', {}).get('TargetSide', 'None') not in ('None', -1):
            context['rule'] = node['EssentialCandidateRule']
            context['selection'] = id(node)
            context['filters'] = candidate_filters(node.get('OptionalCandidateRule'), lexicon, node['EssentialCandidateRule']['TargetSide'] == 'Enemy')
        if node.get('TargetSortRule', {}).get('IsValid'): context['sort'] = sort_text(node['TargetSortRule'], lexicon)
        if node.get('TargetContainerIndex'): context['other_target'] = True
        if node_type in AREA_SHAPES: context['area'] = AREA_SHAPES[node_type]
        if node_type in AREA_SHAPES and node.get('Radius'): context['radius'] = node['Radius']
        if node_type.endswith(('AreaEntityDAO', 'AuraEntityDAO')) and node.get('Duration', 0) > 30: context['area_frames'] = node['Duration']
        if node_type.endswith('AuraEntityDAO') and node.get('Interval', 0) > 0: context['interval'] = node['Interval']
        if node.get('Piercing') and node.get('ReduceDamageRatePerHit'): context['piercing'] = (node['ReduceDamageRatePerHit'], node.get('MaxReducedDamageRate') or 0)
        if 0 < node.get('SpawnRate', 10000) < 10000: context['conditions'] = context['conditions'] + [Condition(f"{skill_value(percent(node['SpawnRate']))} chance")]
        if node_type in SPAWN_KINDS and node.get('UniqueName'): summons.setdefault(node['UniqueName'], (node, context['conditions']))

    if 'DamageDistributeRate' in node and 'Entity' in node:
        context = dict(context, distribute=node['DamageDistributeRate'])
    if node.get('SpawnCondition', 'None') != 'None':
        described = spawn_condition(node, lexicon)
        context = dict(context, conditions=context['conditions'] + [described])
    if node.get('StartDelay', 0) > 0:
        context = dict(context, delay=context['delay'] + node['StartDelay'])
    if node.get('Frame', 0) > 0 and 'Entity' in node:
        context = dict(context, frame=context.get('frame', 0) + node['Frame'])

    if 'LogicEffectGroupIds' in node:
        conditions, level_checks = [], []
        for modifier in node.get('Modifiers', []):
            described = describe_modifier(modifier, lexicon)
            if isinstance(described, tuple): level_checks.append(described)
            elif described: conditions.append(described)
        reference_slot = node['ReferenceSkillSlot'] if node.get('IsReferenceSkillSlot') else None
        for group_id in node['LogicEffectGroupIds']:
            if group_id not in lexicon.data.logic_effects or group_id in context['skip_groups']: continue
            app = Application(group_id, context, context['conditions'] + conditions, level_checks, reference_slot)
            app = applications.setdefault(app.key, app)
            if not (context.get('other_target') and app.hit_rates): app.hit_rates += [context['distribute']] * context['hit_frames']

    has_timeline = bool(node.get('EntityTimeline') or node.get('ShotFrames'))
    for key, value in node.items():
        if not isinstance(value, (dict, list)) or key in ('Modifiers', 'TriggerSourceFindRule', 'BounceProjectileEntity') or (has_timeline and key in PREVIEW_ENTITIES): continue
        if key == 'InitialAbilities' and node_type in SPAWN_KINDS:
            # abilities a spawned unit or object starts with apply to itself
            name = 'the summon' if node_type == 'CharacterEntityDAO' else f'the {SPAWN_KINDS[node_type]}'
            collect_applications(value, applications, summons, dict(context, rule={'TargetSide': 'Spawned', 'Name': name}, filters=('', '')))
        else: collect_applications(value, applications, summons, context)

    if node.get('BounceProjectileEntity'):
        # the projectile bounces on through nested copies of itself, abilities that only the bounces have are described separately
        bounces = bounce_depth(node['BounceProjectileEntity'])
        own_groups = {group_id for ability in node.get('Abilities', []) for group_id in ability.get('LogicEffectGroupIds', [])}
        bounce_groups = {group_id for ability in node['BounceProjectileEntity'].get('Abilities', []) for group_id in ability.get('LogicEffectGroupIds', [])}
        name = f"up to {bounces} enem{'ies' if bounces > 1 else 'y'} it bounces to"
        bounce = {k: v for k, v in node['BounceProjectileEntity'].items() if k != 'BounceProjectileEntity'}
        collect_applications(bounce, applications, summons, dict(context, rule={'TargetSide': 'EventTarget', 'Name': name}, skip_groups=own_groups))
        context = dict(context, bounces=bounces)
        for key, app in applications.items():
            if app.group_id in own_groups & bounce_groups and app.target == Application(app.group_id, context, [], []).target: app.bounces = bounces


def condition_expression(expression: str, lexicon: Lexicon) -> str:
    """Readable form of a passive's ConditionExpression, such as 'GetHPRate() <= 3000 && HasLogicEffectTemplate(X) == false'"""
    parts = []
    for atom in re.split(r'\s*(&&|\|\|)\s*', expression.strip()):
        if atom in ('&&', '||'): parts.append('and' if atom == '&&' else 'or'); continue
        negated = bool(re.search(r'==\s*false|!=\s*true', atom))
        if match := re.match(r'GetHPRate\(\)\s*(<=|<|>=|>|==?)\s*(\d+)', atom):
            operator = {'<': 'Less', '<=': 'LessOrEqual', '>': 'Greater', '>=': 'GreaterOrEqual', '=': 'Equal', '==': 'Equal'}[match.group(1)]
            parts.append(f'HP is {COMPARISONS[operator].format(skill_value(percent(match.group(2))))}')
        elif match := re.match(r'GetFormIndex\(\)\s*==?\s*(\d+)', atom):
            parts.append('in an alternate state' if int(match.group(1)) else 'in the normal state')
        elif match := re.match(r"HasLogicEffectTemplate\(\s*'?([\w]+)'?\s*\)", atom):
            parts.append(f"{'not having' if negated else 'having'} {lexicon.effect_name(match.group(1))}")
        elif match := re.search(r'BehaviorType\.(\w+)', atom):
            behavior = match.group(1)
            parts.append('using EX skill' if behavior.startswith('UseExSkill') else 'using Normal skill' if behavior.startswith('UsePublicSkill') else split_words(behavior).lower())
        elif atom.startswith('IsReloading'):
            parts.append('not reloading' if negated else 'reloading')
        else: parts.append(atom)
    return ' '.join(parts)


def passive_trigger(timeline: dict, lexicon: Lexicon) -> tuple[str, str | None, str | None]:
    """Header ('every 6 enemies defeated by allies'), trigger chance and trigger limit of a passive skill"""
    trigger = timeline['TriggerCondition']
    event, parameters, count = trigger['Event'], trigger['Parameters'], timeline.get('TryCount', 0)
    source = timeline.get('TriggerSourceFindRule', {}).get('EssentialCandidate', {}).get('TargetSide', 'Self')
    by = {'Ally': ' by allies', 'Ally_Except_Self': ' by other allies', 'Enemy': ' by enemies', 'ALL': ' by anyone'}.get(source, '')
    name = lexicon.effect_name(parameters) if parameters else ''
    slots = slot_names(parameters) if parameters and parameters != 'All' else ''
    category = CATEGORY_NAMES.get(parameters, parameters)

    counted, single = {
        'Immediate': ('', ''),
        'BattleEntity_NormalAttack': ('normal attacks', 'on normal attack'),
        'BattleEntity_UseSkillStart': (f'{slots or "skill"} skill uses', f'when using {slots + " " if slots else "a "}skill'),
        'BattleEntity_UseSkillEnd': (f'{slots or "skill"} skill uses', f'after using {slots + " " if slots else "a "}skill'),
        'BattleEntity_Attack': ('attacks', 'when attacking'),
        'BattleEntity_DamageHit': ('hits', 'when hitting an enemy' + (f' with {slots}' if slots else '')),
        'BattleEntity_Damaged': ('hits taken', 'when taking damage'),
        'BattleEntity_Attacked': ('hits taken', 'when attacked'),
        'BattleEntity_Heal': ('heals', 'when healing' + (f' with {slots} skill' if slots else '')),
        'BattleEntity_Healed': ('times healed', 'when receiving healing'),
        'BattleEntity_Dying': ('', 'when incapacitated'),
        'BattleEntity_Died': ('', 'when defeated'),
        'BattleEntity_Dodged': ('evasions', 'on evasion'),
        'BattleEntity_AttackCritical': ('critical hits', 'on critical hit'),
        'BattleEntity_KillEnemy': ('enemies defeated', 'when defeating an enemy'),
        'BattleEntity_KillAlly': ('allies defeated', 'when an ally is defeated'),
        'BattleEntity_Reload': ('reloads', 'on reload'),
        'BattleEntity_AddLogicEffectTemplate': (f'{name} gained', f'when gaining {name}'),
        'BattleEntity_RemoveLogicEffectTemplate': (f'times {name} ends', f'when {name} ends'),
        'BattleEntity_AddLogicEffectGroupId': (f'{lexicon.group_effect_name(parameters)} gained', f'when gaining {lexicon.group_effect_name(parameters)}'),
        'BattleEntity_RemoveLogicEffectGroupId': ('', f'when {lexicon.group_effect_name(parameters)} ends'),
        'BattleEntity_AddLogicEffectCategory': (f'{category}s received', f'when receiving {category}'),
        'BattleEntity_AppliedLogicEffectCategory': (f'{category}s applied', f'when applying {category}'),
        'BattleEntity_AppliedLogicEffectGroupId': (f'{lexicon.group_effect_name(parameters)} applied', f'when applying {lexicon.group_effect_name(parameters)}'),
        'BattleEntity_AppliedLogicEffectTemplate': (f'{name} applied', f'when applying {name}'),
        'BattleEntity_CoverStart': ('', 'when taking cover'),
        'BattleEntity_CoverEnd': ('', 'when leaving cover'),
        'BattleEntity_UseExSkillCost': ('EX skill cost spent', 'when spending EX skill cost'),
        'BattleEntity_DecreasedAmmoCount': ('ammo used', 'when using ammo'),
        'BattleEntity_DispelLogicEffectCategory': ('', f'when removing {category}'),
        'BattleEntity_DispelledLogicEffectCategory': ('', f'when {category} gets removed'),
        'Battle_Polling': ('', ''),
        'Battle_Periodic': ('', f'every {skill_value(frames(parameters))}' if parameters.isdigit() else 'periodically'),
        'BattleEntityState_OnOff': ('', ''),
        'BattleEntityState_NotMoving': ('', f'after not moving for {skill_value(frames(parameters))}' if parameters.isdigit() and int(parameters) > 1 else 'while not moving'),
        'BattleEntityState_Reloading': ('', 'while reloading'),
        'BattleEntityState_Moving': ('', 'while moving'),
    }.get(event, ('', f'on {split_words(str(event))}'))

    header = f'every {skill_value(count)} {counted}{by}' if count > 1 and counted else single + (by if single else '')
    if trigger['ConditionExpression']:
        expression = condition_expression(trigger['ConditionExpression'], lexicon)
        header = f'{header} while {expression}' if header else f'while {expression}'

    chance = percent(trigger['TriggerRate']) if 0 < trigger['TriggerRate'] < 10000 else None
    limit = timeline.get('MaxTriggerCount', -1)
    return header.strip(), chance, f'up to {skill_value(limit)} time{"s" if limit > 1 else ""} per battle' if limit > 0 and event != 'Immediate' else None


def auto_use_trigger(rule: dict, lexicon: Lexicon, group_id: str) -> tuple[str, str | None, str | None]:
    """Header, trigger chance and trigger limit of a skill used automatically (Normal skills)"""
    argument, count = rule['ConditionArgument'], rule.get('TryCount', 0)
    number = int(argument) if argument.lstrip('-').isdigit() else 0
    by = {'CasterAlly': ' by allies', 'CasterAllyExceptCaster': ' by other allies', 'CasterEnemy': ' by enemies', 'All': ' by anyone'}.get(rule.get('ConditionCheckTarget'), '')
    subject = {'CasterAlly': 'an ally', 'CasterAllyExceptCaster': 'another ally', 'CasterEnemy': 'an enemy', 'Target': 'the target'}.get(rule.get('ConditionCheckTarget'), 'own')
    slots = slot_names(argument) if argument and argument != 'All' else ''
    category = CATEGORY_NAMES.get(argument, argument)
    # internal timer markers the skill waits for make it periodic
    period = rule['ConditionType'] == 'RemoveLogicEffectTemplateId' and not lexicon.is_notable_marker_template(argument) and lexicon.timer_period(argument, group_id)
    if rule['ConditionType'] == 'Interval' and 0 < number <= 30:
        # a skill used on the first frame: once, or on its cooldown from then on
        if rule.get('MaxTriggerCount') == 1: return 'at the start of battle', None, None
        if rule.get('CoolTimeNotTrigger'): return f"at the start of battle and every {skill_value(frames(rule['CoolTimeNotTrigger']))}", None, None

    counted, single = {
        'None': ('', ''),
        'Interval': ('', f'every {skill_value(frames(number))}' if number else ''),
        'HpUnder': ('', f"when {subject} HP falls below {skill_value(percent(number))}"),
        'HpOver': ('', f"when {subject} HP is above {skill_value(percent(number))}"),
        'HasLogicEffectCategory': ('', f'while {subject} has {category}'),
        'AmmoCountUnder': ('', f'when ammo falls to {skill_value(argument)} or lower'),
        'OnAttackIng': ('attacks', 'when attacking'),
        'KillTarget': ('enemies defeated', 'when defeating an enemy'),
        'GainBattleItem': ('battle items picked up', 'when picking up a battle item'),
        'HitLogicEffectCategory': (f'{category}s received', f'when receiving {category}'),
        'CriticalAttack': ('critical hits', 'on critical hit'),
        'CriticalAttacked': ('critical hits taken', 'when taking a critical hit'),
        'Healed': ('times healed', 'when receiving healing'),
        'Dodged': ('evasions', 'on evasion'),
        'Blocked': ('blocked attacks', 'when blocking an attack'),
        'CoverTime': ('', f'after staying in cover for {skill_value(frames(number))}' if number else 'while in cover'),
        'UseSkill': (f'{slots or "skill"} skill uses', f'when using {slots + " " if slots else "a "}skill'),
        'HitLogicEffectGroupId': ('', f'when hit by {lexicon.group_effect_name(argument)}'),
        'HitLogicEffectTemplateId': ('', f'when hit by {lexicon.effect_name(argument)}'),
        'Attacked': ('hits taken', 'when attacked'),
        'RemoveLogicEffectTemplateId': ('', f'every {skill_value(seconds(period * 1000))}' if period else f'when {lexicon.effect_name(argument)} ends'),
    }.get(rule['ConditionType'], ('', f"on {split_words(rule['ConditionType'])} ({argument})"))

    header = f'every {skill_value(count)} {counted}{by}' if count > 1 and counted else single + (by if single and by else '')
    chance = percent(rule['TriggerRate']) if 0 < rule['TriggerRate'] < 10000 else None
    limit = rule.get('MaxTriggerCount', -1)
    return header.strip(), chance, f'up to {skill_value(limit)} time{"s" if limit > 1 else ""} per battle' if limit > 0 and rule['ConditionType'] != 'None' else None


def trigger_templates(timeline: dict) -> set[str]:
    """Effect templates a skill's trigger depends on"""
    trigger, rule = timeline.get('TriggerCondition', {}), timeline.get('AutoUseRule', {})
    templates = set(re.findall(r"HasLogicEffectTemplate\(\s*'?(\w+)", trigger.get('ConditionExpression', '')))
    if 'LogicEffectTemplate' in str(trigger.get('Event')): templates.add(trigger['Parameters'])
    if 'LogicEffectTemplate' in str(rule.get('ConditionType')): templates.add(rule['ConditionArgument'])
    return templates


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def number(text: str) -> float | None:
    match = re.match(r'[\d.]+', text)
    return float(match.group(0)) if match else None


def sum_values(texts: list[str]) -> str:
    """Clauses of the same shape with their values added up, 'deal 200% ...' + 'deal 100% ...' -> 'deal 300% ...'"""
    columns = zip(*(re.findall(SKILL_VALUE, text) for text in texts))
    def total(values):
        if len(set(values)) == 1 or any(number(x) is None for x in values): return values[0]
        return f'{sum(number(x) for x in values):.1f}'.rstrip('0').rstrip('.') + re.sub(r'^[\d.]+', '', values[0])
    sums = iter([total(x) for x in columns])
    return re.sub(SKILL_VALUE, lambda m: skill_value(next(sums)), texts[0])


def merge_tiers(clauses: list[tuple[str, Condition]]) -> str:
    """One clause for abilities that differ only by a tier: 'by 8.4%/16.8% with 1/2 X', plus the step per unit when values grow evenly"""
    by_count = collections.defaultdict(list)
    for text, condition in clauses: by_count[condition.tier['count']].append((text, condition))
    # several abilities at the same tier (base damage and bonus damage) add up
    clauses = sorted([(sum_values([x[0] for x in group]), group[0][1]) for group in by_count.values()], key=lambda x: x[1].tier['sort'])
    tier = clauses[0][1].tier
    if len(clauses) == 1: return f'{clauses[0][0]} ({clauses[0][1].text})'

    values = [re.findall(SKILL_VALUE, text) for text, _ in clauses]
    if len({len(x) for x in values}) != 1: return '; '.join(f'{text} ({condition.text})' for text, condition in clauses)
    changing = [i for i in range(len(values[0])) if len({x[i] for x in values}) > 1]
    if not changing: return clauses[0][0]
    columns = iter(['/'.join(x[i] for x in values) if i in changing else values[0][i] for i in range(len(values[0]))])
    text = re.sub(SKILL_VALUE, lambda m: skill_value(next(columns)), clauses[0][0])
    text += ' ' + tier['phrase'].format(count=skill_value('/'.join(condition.tier['count'] for _, condition in clauses)), unit=tier['unit'])

    # levels of a gauge or form multiply a single value
    if len(changing) == 1 and tier['phrase'].startswith('at') and all(number(x[changing[0]]) for x in values):
        points = [number(x[changing[0]]) for x in values]
        if tier['key'][0] == 'marker level' and all(abs(x / points[0] * 20 - round(x / points[0] * 20)) < 0.1 for x in points): text += f" (×{skill_value('/'.join(f'{x / points[0]:.2f}'.rstrip('0').rstrip('.') for x in points))})"

    # a single value growing by the same step for every unit of count
    sorts = [condition.tier['sort'] for _, condition in clauses]
    if len(changing) == 1 and tier['phrase'].startswith('with') and all(number(x[changing[0]]) is not None for x in values):
        points = [number(x[changing[0]]) for x in values]
        steps = [(b - a) / (sb - sa) for a, b, sa, sb in zip(points, points[1:], sorts, sorts[1:]) if sb != sa]
        if steps and max(steps) - min(steps) <= 0.15 and steps[0] > 0:
            unit = re.sub(r'[\d.~/]+', '', values[0][changing[0]])
            decimals = max([1, *(len(x.split('.')[1]) for x in re.findall(r'\d+\.\d+', values[0][changing[0]]))])
            text += f' (+{skill_value(f"{sum(steps) / len(steps):.{decimals}f}".rstrip("0").rstrip(".") + unit)} for each)'
    return text


def timing(app: Application, effect: dict) -> str:
    """When and for how long an ability applies, beyond what the effect itself says"""
    text = ''
    hits = len(app.hit_rates)
    if app.interval: text = f' every {skill_value(frames(app.interval))} for {skill_value(frames(app.area_frames))}'
    elif app.area_frames and effect['Type'] in ('Heal', 'HealOverTime') and hits > 1: text = f' {skill_value(hits)} times over {skill_value(frames(app.area_frames))}'
    elif app.area_frames and effect['Type'] not in ('Damage', 'Heal', 'Knockback') and not has_duration(effect):
        text = f' while in the area (lasts {skill_value(frames(app.area_frames))})'
    elif effect['Type'] == 'Heal' and hits > 1: text = f' {skill_value(hits)} times'
    if app.delay: text = f' after {skill_value(frames(app.delay))}' + text
    return text


def has_duration(effect: dict) -> bool:
    return any(int(effect.get(key, 0) or 0) > 0 for key in ('Duration', 'EndConditionArgumentFirst', 'EndConditionArgument'))


def damage_totals(entries: list[tuple]) -> dict[int, int]:
    """Total damage rate of several effect groups dealing damage to the same target (JP descriptions often only give the total), by the index of the last of them"""
    groups = collections.defaultdict(list)
    for index, (app, effect, conditions) in enumerate(entries):
        if effect['Type'] == 'Damage' and not app.bounces and not any(x.tier for x in conditions):
            condition_keys = tuple((x.text, x.tier and x.tier['count']) for x in conditions)
            groups[(app.target, condition_keys, effect['BonusSourceFirst'], effect.get('DefensePenetrationRate'), effect.get('CriticalCheck'))].append(index)

    return {indexes[-1]: sum(entries[i][1]['BonusRateFirst'] * sum(entries[i][0].hit_rates) // 10000 for i in indexes) for indexes in groups.values() if len(indexes) > 1}


def unmarked(text: str) -> str:
    """Clause text without target marks"""
    return re.sub(MENTION, r'\2', text)


def refer_back(clauses: list[str]) -> list[str]:
    """
    A clause about the same single target as the clause right before it joins it: 'deal 10% of Attack as damage to one enemy and reduce their Evasion by 5%'.
    Conditions would read as applying to the whole sentence and bounces make 'them' unclear, so such clauses stay apart and say 'the target'
    """
    def joinable(clause): return not re.search(CONDITION_NOTE, clause) and ', bouncing to' not in clause
    sentences, previous = [], None
    for clause in clauses:
        mentions = re.findall(MENTION, clause)
        if mentions and mentions[0] == previous and sentences and joinable(clause) and joinable(sentences[-1][-1]):
            # 'reduce Evasion of X by 5%' -> 'reduce their Evasion by 5%', 'inflict Stun on X' -> 'inflict Stun on them'
            clause, possessive = re.subn(rf'^(\S+) (?:the )?(.+?) of {MENTION}', r'\1 their \2', clause, count=1)
            sentences[-1].append(unmarked(clause if possessive else re.sub(MENTION, 'them', clause, count=1)))
        else:
            if mentions and mentions[0] == previous: clause = re.sub(MENTION, 'the target', clause, count=1)
            sentences.append([unmarked(clause)])
        previous = mentions[-1] if mentions else None
    return [parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}" for parts in sentences]


def join_stat_changes(clauses: list[str]) -> list[str]:
    joined = []
    for clause in clauses:
        match = re.fullmatch(r'((?:increase|reduce) .+? by )(\{\{SkillValue\|[^}]*\}\})(.*)', clause)
        previous = re.fullmatch(r'((?:increase|reduce) .+? by )(\{\{SkillValue\|[^}]*\}\}(?: and \{\{SkillValue\|[^}]*\}\})?)(.*)', joined[-1]) if joined else None
        if match and previous and unmarked(match.group(1)) == unmarked(previous.group(1)) and unmarked(match.group(3)) == unmarked(previous.group(3)):
            joined[-1] = f'{previous.group(1)}{previous.group(2)} and {match.group(2)}{match.group(3)}'
        else: joined.append(clause)
    return joined


class Summon(object):
    """A unit or object spawned by a skill (vehicle, turret, mine etc.). Units act through skills of their own"""
    def __init__(self, dev_name: str, kind: str, duration: int, skills: dict):
        self.dev_name = dev_name
        self.kind = kind
        self.duration = duration
        self.skills: dict[str, SkillMechanics] = skills

    @classmethod
    def from_data(cls, dev_name: str, entity: dict, lexicon: Lexicon, max_level: int, caster: dict | None = None):
        data = lexicon.data
        duration = int(entity.get('Duration', 0)) * 1000 // 30
        character = next((x for x in data.characters.values() if x['DevName'] == dev_name), None)
        if character is None: return cls(None, SPAWN_KINDS[type_name(entity)], duration, {})

        skill_list = data.characters_skills.get((data.costumes[character['CostumeGroupId']]['CharacterSkillListGroupId'], 0, 0, 0), {})
        skills = {label: skill for slot, label in SUMMON_SKILL_SLOTS.items() for group_id in skill_list.get(slot, []) if (skill := lexicon.mechanics(group_id, max_level, character if caster else None))}

        # vehicles' summon time is in TacticalSupportSystem, other summons use the entity's own duration
        tss = data.tactical_support_system.get(character['Id'])
        kind = 'vehicle' if character['TacticEntityType'] == 'Vehicle' else SPAWN_KINDS[type_name(entity)]
        return cls(dev_name, kind, tss['SummonedTime'] if tss else duration, skills)

    def describe(self, level: int) -> tuple[str, list[str]]:
        """Summoning clause, and a sentence for each of the summon's skills"""
        verb = 'summon' if self.skills or self.kind == 'vehicle' else 'place'
        clause = f"{verb} {'an' if self.kind[0] in 'aeio' else 'a'} {self.kind}" + (f' ({self.dev_name})' if self.dev_name and self.skills else '')
        if 0 < self.duration < 1000000: clause += f' for {skill_value(seconds(self.duration))}'
        sentences = [f'{capitalize(self.kind)} {label}: {text}' for label, skill in self.skills.items() if (text := skill.describe(level))]
        return clause, sentences


class SkillMechanics(object):
    def __init__(self, group_id: str, lexicon: Lexicon, header: str, chance: str | None, cooldown: str | None, limit: str | None,
                 applications: list[Application], summons: list[Summon], trigger_templates: set[str], selectable: int, max_level: int, nested: bool,
                 caster: dict | None = None):
        self.group_id = group_id
        self.lexicon = lexicon
        self.header = header
        self.chance = chance
        self.cooldown = cooldown
        self.limit = limit
        self.applications = applications
        self.summons = summons
        self.trigger_templates = trigger_templates
        self.selectable = selectable        # EX skills a select EX skill chooses from
        self.normal_attack = 'Normal' in group_id
        self.max_level = max_level
        self.nested = nested
        self.caster = caster                # the character using the skill, when known (raid bosses of a difficulty)
        self.caster_tags = frozenset(tag_number(x) for x in caster.get('Tags', [])) if caster else None

    def __repr__(self):
        return f'SkillMechanics {self.group_id}'

    @property
    def description_general(self) -> str:
        """Max level description, with values that change across levels shown as a start~end range"""
        first, last = self.describe(1), self.describe(self.max_level)
        start_values, end_values = re.findall(SKILL_VALUE, first), re.findall(SKILL_VALUE, last)
        if len(start_values) == len(end_values): pairs = dict(enumerate(range(len(end_values))))
        else:
            # higher levels can add clauses: values pair up in order by the words right before and after them
            def contexts(text):
                parts = re.split(SKILL_VALUE, text)[::2]
                return [((parts[i].split() or [''])[-1], (parts[i + 1].split() or [''])[0]) for i in range(len(parts) - 1)]
            matcher = difflib.SequenceMatcher(None, contexts(first), contexts(last), autojunk=False)
            pairs = {block.b + k: block.a + k for block in matcher.get_matching_blocks() for k in range(block.size)}

        index = iter(range(len(end_values)))
        def merge(match):
            j = next(index)
            if j not in pairs or start_values[pairs[j]] == match.group(1): return match.group(0)
            start, end = start_values[pairs[j]], match.group(1)
            if start.count('/') != end.count('/'): return match.group(0)
            return skill_value(re.match(r'[\d.]+', start).group(0) + '~' + end if start[:1].isdigit() else f'{start}~{end}')
        return re.sub(SKILL_VALUE, merge, last)

    def effect(self, app: Application, level: int) -> dict:
        rows = self.lexicon.data.logic_effects[app.group_id]
        return rows[min(level, len(rows)) - 1]

    def templates_applied(self, level: int | None = None) -> set[str]:
        """TemplateIds this skill applies at a level, or at any level"""
        if level: return {self.effect(app, level)['TemplateId'] for app in self.applications}
        return {row['TemplateId'] for app in self.applications for row in self.lexicon.data.logic_effects[app.group_id]}

    def stage_description(self, effect: dict, level: int) -> str | None:
        """
        EX skills that turn into another stage of themselves with every use (same name, the next form's EX skill):
        'each use reduces the damage of this skill by 290% of Attack for the rest of the battle (up to 3 times)'
        """
        name, chain, conversion = self.lexicon.skill_name(self.group_id), [self], effect
        while conversion and len(chain) < 10:
            following = self.lexicon.form_skills(chain[-1].group_id, conversion['FormIndex']).get('EX skill')
            skill = following and self.lexicon.skill_name(following) == name and self.lexicon.mechanics(following, self.max_level, self.caster)
            # stages last for the rest of the battle
            if not skill or conversion['FormConversionEndCondition'] != 'Duration' or int(conversion['EndConditionArgument']) > 0: break
            chain.append(skill)
            conversion = next((row for app in skill.applications if (row := skill.effect(app, level))['Type'] == 'FormConversion'), None)
        if len(chain) < 2: return None

        def damage(skill): return sum(skill.effect(app, level)['BonusRateFirst'] * sum(app.hit_rates) / 10000 for app in skill.applications if skill.effect(app, level)['Type'] == 'Damage')
        changes = [damage(b) - damage(a) for a, b in zip(chain, chain[1:])]
        if not all(map(damage, chain)) or not changes[0] or max(changes) - min(changes) > abs(changes[0]) * 0.01: return None
        return (f"each use {'reduces' if changes[0] < 0 else 'increases'} the damage of this skill by {rate_text(abs(sum(changes) / len(changes)), 'AttackPower')} "
                f"for the rest of the battle (up to {skill_value(len(changes))} time{'s' if len(changes) > 1 else ''})" + ('; the card stays in hand' if effect.get('ExSkillCardRedrawInHand') else ''))

    def alarm_description(self, effect: dict, level: int) -> str | None:
        """What happens once a blackboard counter reaches a value: 'when "Seashell" reaches 12 stacks, remove all "Seashell" and gain "Seashell Flower"'"""
        counter = self.lexicon.counter_name(effect['BlackBoardKey'], effect['GroupId'])
        parts = self.nested_effects(effect['AlarmEffectGroupIdList'], level)
        if not parts: return None
        reached = f'"{counter}" reaches {skill_value(effect["AlarmValue"])} stacks' if counter else f'the counter reaches {skill_value(effect["AlarmValue"])}'
        return f"when {reached}, {parts}"

    def nested_effects(self, group_ids: str, level: int) -> str | None:
        """Effects another effect applies to its holder, as one clause: 'remove all "Seashell" and gain "Seashell Flower"'"""
        parts = []
        for group_id in re.split(r',\s*', group_ids):
            if group_id not in self.lexicon.data.logic_effects: continue
            rows = self.lexicon.data.logic_effects[group_id]
            row = rows[min(level, len(rows)) - 1]
            app = Application(group_id, {'rule': {'TargetSide': 'Self'}, 'filters': ('', ''), 'sort': None, 'area': None, 'area_frames': 0, 'interval': 0, 'delay': 0, 'bounces': 0}, [], [])
            text = self.gauge_text(row, app) if row['Type'] == 'GroggyGauge' else describe_effect(row, app, self.lexicon)
            if text is None: continue
            if row['Type'] == 'FormConversion': text += self.form_description(row, level)
            parts.append(text)
        return ', '.join(parts[:-1]) + ' and ' + parts[-1] if len(parts) > 1 else parts[0] if parts else None

    def gauge_text(self, effect: dict, app: Application) -> str:
        """Groggy gauge change, as a share of the caster's gauge when the caster is known: Goz's 250000000 of 2000000000 is 12.5%"""
        amount = effect['Amount']
        size = self.lexicon.data.characters_stats.get(self.caster['Id'], {}).get('GroggyGauge') if self.caster and app.is_self else None
        value = percent(abs(amount) * 10000 // size) if size else f'{abs(amount) / 10000:g} points'
        return f"{'increase' if amount > 0 else 'reduce'} the groggy gauge{of_target(app)} by {skill_value(value)}"

    def crowd_control_gauge_text(self, effect: dict, app: Application, level: int) -> str | None:
        """Crowd control filling a gauge instead: Hod's 'at 6 seconds of crowd control, increase damage taken, raise the groggy gauge and reduce ATG'"""
        parts = self.nested_effects(effect.get('MaxGaugeLogicEffectGroupIdList', ''), level)
        holder = 'self' if app.is_self else app.mention
        text = f"crowd control durations on {holder} fill a gauge"
        if effect.get('IsCalculateOppression'): text += ' (faster with higher CC Strength)'
        if effect.get('GaugeReduceValuePerSecond'): text += f" that drains by {skill_value(seconds(effect['GaugeReduceValuePerSecond']))} per second"
        return text + (f"; at {skill_value(seconds(effect['MaxGaugeValue']))}, {parts}" if parts else '')

    def form_description(self, effect: dict, level: int) -> str:
        """What changes in another form, with abilities gated by markers this skill applies at this level resolved"""
        active = self.templates_applied(level)
        gates = {template: template in active for template in self.templates_applied()}
        texts = []
        for label, group_id in self.lexicon.form_skills(self.group_id, effect['FormIndex']).items():
            if label == 'EX skill':
                # the new EX skill replaces the card in hand instead of the used card cycling out: JP calls it drawing the card, when it mentions it at all
                texts.append(f'EX skill changes to "{self.lexicon.skill_name(group_id)}"' + ('; the card stays in hand' if effect.get('ExSkillCardRedrawInHand') else ''))
                continue
            skill = self.lexicon.mechanics(group_id, self.max_level, self.caster)
            if skill is None: continue
            # when the form's abilities depend on this skill's effects, those are what changes
            required = skill.gating_templates() & set(gates) or None
            if text := skill.describe(level, gates, required, {skill_slot(self.group_id): level}, base_attack=False): texts.append(f'{label}: {text[:1].lower()}{text[1:].rstrip(".")}')
        return ' (' + '; '.join(texts) + ')' if texts else ''

    def unlocked_description(self, level: int) -> tuple[list[str], set[str]]:
        """Abilities of normal attacks and hidden passives that only apply while an effect this skill applies at this level is present, and those effects"""
        markers = {self.effect(app, level)['TemplateId']: self.effect(app, level) for app in self.applications if 'Dummy' in self.effect(app, level)['TemplateId']}
        sentences, used = [], set()
        for label, group_id in self.lexicon.unlockable_skills(self.group_id):
            skill = self.lexicon.mechanics(group_id, self.max_level, self.caster)
            if skill is None: continue
            required = set(markers) & (skill.gating_templates() | skill.trigger_templates)
            if not required: continue
            gates = {x: True for x in required} | {template: value == level for template, value in self.lexicon.level_markers(self.group_id).items()}
            text = skill.describe(level, gates, required, {skill_slot(self.group_id): level}, base_attack=False)
            if ratio := skill.radius_change(required):
                text = f'area radius ×{skill_value(truncate(ratio, 2))}' + (f'; {text[:1].lower()}{text[1:]}' if text else '.')
            if text:
                sentences.append(f"{capitalize(label)}{''.join(dict.fromkeys(end_condition(markers[x]) for x in required))}: {text[:1].lower()}{text[1:]}")
                used |= required
        return sentences, used

    def radius_change(self, markers: set[str]) -> float | None:
        """
        How many times the standard splash radius the normal attack area requiring one of these markers is.
        Sub skills widen normal attacks this way: the attack spawns the area variant matching the marker the Sub skill grants.
        Descriptions measure it against the standard splash of grenade and rocket launchers, even where a student's own area is already wider (Shigure)
        """
        if not self.normal_attack: return None
        radii = {app.radius for app in self.applications if app.radius and any(x.template in markers and x.include for x in app.conditions)}
        if len(radii) != 1 or STANDARD_SPLASH_RADIUS in radii: return None
        return radii.pop() / STANDARD_SPLASH_RADIUS

    def once_per_battle_templates(self) -> set[str]:
        """Internal flags a skill puts on its user for good, while its abilities require not having them"""
        rows = [row for app in self.applications for row in self.lexicon.data.logic_effects[app.group_id][:1]]
        flags = {row['TemplateId'] for app, row in zip(self.applications, rows) if app.is_self and row['Type'] == 'Dummy'
                 and int(row.get('EndConditionArgument', 0) or 0) <= 0 and not self.lexicon.is_notable_marker(row)}
        flags -= {x.checks[0] for app in self.applications for x in app.conditions if x.include and x.checks}
        flags -= {row.get('LogicEffectTemplateToDispel') for row in rows}
        return {x.template for app in self.applications for x in app.conditions if x.template in flags and not x.include}

    def use_counter(self) -> tuple[list[str], str] | None:
        """
        Internal markers counting uses of the skill: the first gets applied while having none of them, each next one while having the previous one,
        and abilities checking for the last one happen on every Nth use. Returns the markers in order and the last one
        """
        applied = {}
        for app in self.applications:
            row = self.lexicon.data.logic_effects[app.group_id][0]
            # markers numbered by level are stages, described as tiers instead
            if app.is_self and row['Type'] == 'Dummy' and not self.lexicon.is_notable_marker(row) and not re.search(r'Lv\d+$', row['TemplateId']): applied[row['TemplateId']] = app
        if len(applied) < 2: return None

        first = next((template for template, app in applied.items() if app.conditions and all(not x.include and x.template in applied for x in app.conditions)), None)
        chain = [first] if first else []
        while chain:
            following = next((template for template, app in applied.items() if template not in chain and any(x.include and x.template == chain[-1] for x in app.conditions)), None)
            if following is None: break
            chain.append(following)
        return (chain, chain[-1]) if len(chain) >= 2 else None

    def applied_markers(self, self_applied: bool) -> dict[str, list[Application]]:
        """Internal (not notable) marker templates this skill applies, to self or to others, with the applications doing it"""
        markers = collections.defaultdict(list)
        for app in self.applications:
            row = self.lexicon.data.logic_effects[app.group_id][0]
            if row['Type'] == 'Dummy' and app.is_self == self_applied and not self.lexicon.is_notable_marker(row): markers[row['TemplateId']].append(app)
        return markers

    def stage_chain(self) -> list[str]:
        """Unnamed stage markers (_Lv1, _Lv2..) the skill advances through: the first applied while having none, each next one while having the previous one"""
        applied = {template: apps for template, apps in self.applied_markers(True).items() if re.search(r'Lv\d+$', template)}
        first = next((template for template, apps in applied.items() if any(app.conditions and all(not x.include for x in app.conditions if x.checks and x.checks[0] in applied) for app in apps)), None)
        chain = [first] if first else []
        while chain:
            following = next((template for template, apps in applied.items() if template not in chain and any(x.include and x.checks and x.checks[0] == chain[-1] for app in apps for x in app.conditions)), None)
            if following is None: break
            chain.append(following)
        return chain if len(chain) >= 2 else []

    def hit_markers(self) -> set[str]:
        """Markers this skill puts on its targets and checks on them again, counting earlier hits on the same target"""
        applied = {self.effect(app, 1)['TemplateId'] for app in self.applications
                   if app.rule.get('TargetSide') in ('Enemy', 'EventTarget') and 'Dummy' in self.effect(app, 1)['TemplateId'] and self.effect(app, 1)['Type'] == 'Dummy'}
        applied -= set(self.lexicon.data.translated_skill_effects)  # named effects are what they are called
        return {x.checks[0] for app in self.applications for x in app.conditions if x.checks and x.checks[0] in applied and x.checks[1] == 'Target'}

    def consumed_markers(self) -> dict[str, str]:
        """Internal flags set while having a named marker this skill also removes: having the flag means a stack of that marker was consumed"""
        removed = {row.get('LogicEffectTemplateToDispel') for app in self.applications for row in self.lexicon.data.logic_effects[app.group_id][:1]}
        flags = {}
        for template, apps in self.applied_markers(True).items():
            consumed = next((x.checks[0] for app in apps for x in app.conditions if x.include and x.checks and x.checks[0] in removed and self.lexicon.is_notable_marker_template(x.checks[0])), None)
            if consumed: flags[template] = consumed
        return flags

    def role_conditions(self, conditions: list[Condition], chain: list[str], hits: set[str], consumed: dict[str, str]) -> list[Condition]:
        """Conditions on internal markers reworded by what those markers stand for"""
        result, stage = [], None
        for condition in conditions:
            template = condition.checks and condition.checks[0]
            if template in chain:
                # having stage N means this use advances to the next one, having the last one means staying there, having none of the later ones is stage 1
                if condition.include: stage = max(stage or 0, min(chain.index(template) + 2, len(chain)))
                else: stage = stage or 1
            elif template in hits:
                if not condition.tier: result.append(Condition('if already hit' if condition.include else 'if not already hit'))
                else:
                    # a lone 0 tier reads as not hit yet, together with other tiers it merges into the hit counts
                    count = condition.tier['count']
                    unit = 'earlier hit on the same target' if count == '1' else 'earlier hits on the same target'
                    result.append(Condition('if not already hit' if count == '0' else f'with {skill_value(count)} {unit}', dict(condition.tier, unit=unit)))
            elif template in self.lexicon.form_templates and template in self.templates_applied():
                # the skill's own flags are not about some other form skill
                result.append(Condition(has_condition(condition.checks[1], condition.include, self.lexicon.effect_name(template)), condition.tier, condition.template, condition.include, condition.checks))
            elif template in consumed:
                result.append(Condition(f"if a {self.lexicon.effect_name(consumed[template])} stack was consumed" if condition.include else 'otherwise'))
            else: result.append(condition)
        if stage: result.append(Condition(f'at stage {stage}', {'key': ('stage', chain[0]), 'sort': stage, 'count': str(stage), 'unit': 'stage', 'phrase': 'at {unit} {count}'}))
        return result

    def hosted_for_other_skill(self, app: Application) -> bool:
        """
        Whether an ability belongs to another described skill (IsReferenceSkillSlot), which describes it itself: Kokoro's EX grants her ExtraPassive's buff.
        Abilities hosted by normal attacks and hidden passives are described by the skills that give them, such as a form's normal attack scaling with EX level
        """
        own = skill_slot(self.group_id)
        return bool(app.reference_slot) and own in DESCRIBED_SLOTS and skill_slot(app.reference_slot) in DESCRIBED_SLOTS and skill_slot(app.reference_slot) != own

    def hosted_applications(self) -> list[Application]:
        """
        This skill's own abilities that other skills of the character carry for it (IsReferenceSkillSlot), which is where JP describes them:
        Kurumi's EX grants the Cost Recovery her Sub skill is about, at the Sub skill's level
        """
        own = skill_slot(self.group_id)
        if self.nested or own not in DESCRIBED_SLOTS: return []
        found = {}
        for host in sorted(self.lexicon.hosting_skills(self.group_id)):
            skill = self.lexicon.mechanics(host, self.max_level, self.caster)
            for app in skill.applications if skill else []:
                if app.reference_slot and skill_slot(app.reference_slot) == own and skill_slot(host) != own: found.setdefault(app.key, app)
        return [app for key, app in found.items() if key not in {x.key for x in self.applications}]

    def expired_timers(self) -> set[tuple[str, int]]:
        """
        (TemplateId, frame) of the skill's own internal timers that have always run out by the time an ability checks them
        """
        timers = {}
        for app in self.applications:
            row = self.lexicon.data.logic_effects[app.group_id][0]
            if app.is_self and row['Type'] == 'Dummy' and not app.conditions and int(row.get('EndConditionArgument', 0) or 0) > 0 and not self.lexicon.is_notable_marker(row):
                timers[row['TemplateId']] = max(timers.get(row['TemplateId'], 0), app.frame + int(row['EndConditionArgument']) * 30 // 1000)
        return timers

    def mirror_templates(self) -> set[str]:
        """
        Unnamed markers that only display another marker of the skill, such as the "Battle Sense" icon showing Saori (Dress)'s counter:
        applied only depending on other markers the skill applies, and never checked or pointed to by anything of the character
        """
        applied = collections.defaultdict(list)
        for app in self.applications:
            row = self.lexicon.data.logic_effects[app.group_id][0]
            if row['Type'] == 'Dummy': applied[row['TemplateId']].append(app)
        referenced = self.lexicon.referenced_names(self.group_id)
        return {template for template, apps in applied.items()
                if template not in self.lexicon.data.translated_skill_effects and not self.lexicon.family_name(template)
                and template not in referenced and not {app.group_id for app in apps} & referenced
                and all(app.conditions and all(x.checks and x.checks[0] != template and x.checks[0] in applied for x in app.conditions) for app in apps)}

    def tag_applications(self) -> dict[str, Application]:
        """
        Brief internal markers put on unconditionally picked targets only for other abilities of the skill to find them again,
        like 'the ally with the highest Critical Damage' among all allies: {TemplateId: the application picking the targets}
        """
        tags, fallbacks = {}, {}
        for app in self.applications:
            row = self.lexicon.data.logic_effects[app.group_id][0]
            if row['Type'] != 'Dummy' or app.is_self or not 0 < int(row.get('EndConditionArgument', 0) or 0) <= 1000 or self.lexicon.is_notable_marker(row): continue
            if not app.conditions: tags.setdefault(row['TemplateId'], app)
            # picking again when the first pick found nobody
            elif len(app.conditions) == 1 and not app.conditions[0].include and app.conditions[0].checks == (row['TemplateId'], 'CasterAllyExceptCaster'): fallbacks.setdefault(row['TemplateId'], app)
        for template, app in tags.items():
            if template in fallbacks and fallbacks[template].target != app.target: app.fallback = fallbacks[template].target
        return tags

    def borrowed_templates(self) -> set[str]:
        """
        Markers that belong to another described skill: granted by abilities this skill hosts for that skill's slot (IsReferenceSkillSlot),
        and internal flags this skill sets depending on those markers. Abilities requiring them are that other skill's mechanics
        """
        borrowed = {template for app in self.applications if self.hosted_for_other_skill(app)
                    and 'Dummy' in (template := self.lexicon.data.logic_effects[app.group_id][0]['TemplateId'])}
        while True:
            flags = {template for applied in (self.applied_markers(False), self.applied_markers(True)) for template, apps in applied.items() if 'Dummy' in template
                     and any(x.checks and x.checks[0] in borrowed for app in apps for x in app.conditions)} - borrowed
            if not flags: return borrowed
            borrowed |= flags

    def gating_templates(self) -> set[str]:
        return {x.template for app in self.applications for x in app.conditions if x.template}

    def describe(self, level: int, gates: dict[str, bool] | None = None, required: set[str] | None = None, slot_levels: dict[str, int] | None = None, base_attack: bool = True) -> str:
        """
        Description at a skill level.
        gates: marker TemplateIds known to be present or absent on the caster, conditions on them get resolved instead of shown
        required: only describe abilities that depend on one of these markers
        slot_levels: levels of other skills, for skill level checks on them
        """
        if self.selectable: return f'Choose one of {skill_value(self.selectable)} EX skills to use.'
        # the skill asking for this description is what triggers it: 'when gaining "Trigger"' says nothing on its own
        header = '' if any(self.header == f'when gaining {self.lexicon.effect_name(x)}' and not self.lexicon.is_notable_marker_template(x) for x in required or ()) else self.header
        gates, slot_levels = gates or {}, (slot_levels or {}) | {skill_slot(self.group_id): level}
        ungated = {app.group_id for app in self.applications if not any(x.template in (required or ()) for x in app.conditions)}
        clauses, tiers, summon_sentences = [], collections.defaultdict(list), []
        for summon in self.summons:
            clause, sentences = summon.describe(level)
            clauses.append(clause)
            summon_sentences += sentences

        unlocked, unlocking = ([], set()) if self.nested else self.unlocked_description(level)
        chain, hits, consumed = self.stage_chain(), self.hit_markers(), self.consumed_markers()
        once = self.once_per_battle_templates() - set(chain) - set(consumed)
        counter = self.use_counter()
        uses = f'on every {ordinal(len(counter[0]))} use' if counter else ''

        borrowed, tags, timers = self.borrowed_templates(), self.tag_applications(), self.expired_timers()
        # markers that stand for another effect (a Suitcase storing damage) are described by that effect
        objects = {row.get('ObjectLogicEffectGroupId') for app in self.applications for row in self.lexicon.data.logic_effects[app.group_id][:1]}
        mirrors = self.mirror_templates()
        entries = []
        for app in self.applications + self.hosted_applications():
            if app.group_id in objects: continue
            row = self.lexicon.data.logic_effects[app.group_id][0]
            if row['TemplateId'] in mirrors or row.get('LogicEffectTemplateToDispel') in mirrors: continue
            if row['Type'] == 'Dummy' and self.lexicon.role_variant(row['TemplateId']): continue
            # a hidden passive's card draw on EX skill use belongs to the EX skill's description
            if row['Type'] == 'ExSkillCardRedrawGauge' and skill_slot(app.reference_slot or '') == 'HiddenPassive' and skill_slot(self.group_id) != 'Ex': continue
            def timing_detail(x): return not x.include and (x.template in timers and app.frame >= timers[x.template] or x.template in self.lexicon.brief_flags and x.template not in self.templates_applied())
            if any(map(timing_detail, app.conditions)):
                app = copy.copy(app)
                app.conditions = [x for x in app.conditions if not timing_detail(x)]
            # abilities for whoever got tagged apply to the tagged targets
            if tag := next((x for x in app.conditions if x.include and x.checks and x.checks[1] == 'Target' and x.checks[0] in tags and tags[x.checks[0]].target != app.target), None):
                tagged, app = tags[tag.checks[0]], copy.copy(app)
                app.rule, app.filters, app.sort, app.area, app.selection, app.fallback = tagged.rule, tagged.filters, tagged.sort, tagged.area, tagged.selection, tagged.fallback
                app.conditions = [x for x in app.conditions if x is not tag]
            # mechanics of another described skill hosted here are left to that skill's description
            if self.hosted_for_other_skill(app): continue
            if any(x.include and x.checks and x.checks[0] in borrowed for x in app.conditions): continue
            if self.lexicon.data.logic_effects[app.group_id][0].get('LogicEffectTemplateToDispel') in borrowed: continue
            if borrowed: app = copy.copy(app); app.conditions = [x for x in app.conditions if not (x.checks and x.checks[0] in borrowed)]
            if any(gates[x.template] != x.include for x in app.conditions if x.template in gates): continue
            # the caster's tags settle which variant applies (raid boss difficulties)
            if self.caster_tags is not None and any(x.caster_tags for x in app.conditions):
                if any(bool(x.caster_tags & self.caster_tags) != x.include for x in app.conditions if x.caster_tags): continue
                app = copy.copy(app)
                app.conditions = [x for x in app.conditions if not x.caster_tags]
            if required and not required & self.trigger_templates and (app.group_id in ungated or not any(x.template in required for x in app.conditions)): continue
            level_conditions = app.level_conditions(slot_levels)
            if level_conditions is None: continue
            effect = self.effect(app, level)
            if effect['TemplateId'] in borrowed: continue
            if effect['Type'] == 'Dummy' and (effect['TemplateId'] in once or effect['TemplateId'] in unlocking and not self.lexicon.is_notable_marker(effect)): continue
            if counter and effect['TemplateId'] in counter[0]: continue
            if effect['Type'] == 'Dummy' and effect['TemplateId'] in set(chain) | hits | set(consumed): continue
            conditions = [Condition('once per battle') if x.template in once else x for x in app.conditions if x.template not in gates]
            if counter:
                if any(x.template == counter[1] for x in conditions): conditions = [Condition(uses if x.include else 'on other uses') if x.template == counter[1] else x for x in conditions if x.template not in counter[0][:-1]]
                elif any(x.template in counter[0] for x in conditions): continue
            conditions = self.role_conditions(conditions, chain, hits, consumed) + level_conditions
            if 0 < effect['ApplyRate'] < 10000: conditions.append(Condition(f"{skill_value(percent(effect['ApplyRate']))} chance"))
            entries.append((app, effect, conditions))

        totals = {} if self.normal_attack else damage_totals(entries)
        for index, (app, effect, conditions) in enumerate(entries):
            # a numbered marker family replacing its previous level grows: 'after 3.8 seconds, "Flower Bud" grows to level 2'
            family = effect['Type'] == 'Dummy' and self.lexicon.family_name(effect['TemplateId'])
            grows = family and next((x for x in conditions if x.include and x.checks and x.checks[0] != effect['TemplateId'] and self.lexicon.family_name(x.checks[0]) == family), None)
            if effect['Type'] == 'BlackBoardAlarmOnReach': clause = self.alarm_description(effect, level)
            elif effect['Type'] == 'GroggyGauge': clause = self.gauge_text(effect, app)
            elif effect['Type'] == 'CrowdControlGauge': clause = self.crowd_control_gauge_text(effect, app, level)
            elif grows:
                conditions = [x for x in conditions if x is not grows]
                clause = f'"{family}" grows to level {skill_value(int(re.search(r"(\d+)$", effect["TemplateId"]).group(1)))}'
                if app.frame: clause = f'after {skill_value(seconds(app.frame * 1000 // 30))}, {clause}'
            else: clause = describe_effect(effect, app, self.lexicon)
            if clause is None: continue
            if effect['Type'] == 'FormConversion': clause = self.stage_description(effect, level) or clause + self.form_description(effect, level)
            if 'FormConversion' in effect.get('LogicEffectTemplateToDispel', '') and (ex_skill := self.lexicon.base_form_ex_skill(self.group_id)):
                clause += f' (EX skill changes to "{self.lexicon.skill_name(ex_skill)}")'
            if not grows: clause += timing(app, effect)
            if index in totals: clause += f" ({skill_value(percent(totals[index]))} of {STAT_NAMES.get(effect['BonusSourceFirst'], effect['BonusSourceFirst'])} in total)"

            tier = next((x for x in conditions if x.tier), None)
            plain = [x.text for x in conditions if x is not tier]
            if plain: clause += ' (' + ', '.join(plain) + ')'
            if not base_attack and self.normal_attack and not tier and re.fullmatch(PLAIN_ATTACK, unmarked(clause)): continue
            # clauses merge by their text, whichever targeting picks their targets
            if tier:
                key = (tier.tier['key'], re.sub(SKILL_VALUE, '#', unmarked(clause)))
                if key not in tiers: clauses.append(key)
                tiers[key].append((clause, tier))
            elif unmarked(clause) not in {unmarked(x) for x in clauses if isinstance(x, str)}: clauses.append(clause)

        clauses = join_stat_changes([merge_tiers(tiers[x]) if isinstance(x, tuple) else x for x in clauses])
        if (skill_slot(self.group_id) == 'Ex' and not self.nested and all(key[3] == 0 for key in self.lexicon.skill_lists.get(self.group_id, []))
                and not any(re.search(r'stays in hand| draw |replace this card', x) for x in clauses) and self.lexicon.hidden_ex_draw(self.group_id)):
            clauses.append('immediately draw an EX skill card')
        plain_clauses = {unmarked(x) for x in clauses}
        clauses = [x for x in clauses if not (x.endswith(' (if not already hit)') and unmarked(x).removesuffix(' (if not already hit)') in plain_clauses)]
        clauses = refer_back(list({unmarked(x): x for x in clauses}.values()))  # merging tiers and resolving gates can leave the same clause twice
        text = ''
        if clauses:
            if self.chance: clauses[0] = f'{skill_value(self.chance)} chance to {clauses[0]}'
            text = '. '.join(capitalize(clause) for clause in clauses) + '.'
            if header: text = f'{capitalize(header)}, {text[:1].lower()}{text[1:]}'
            notes = [x for x in (self.limit, self.cooldown and f'cooldown: {skill_value(self.cooldown)}') if x]
            if notes: text += f" ({'; '.join(capitalize(x) for x in notes)})"
        return ' '.join(([text] if text else []) + unlocked + summon_sentences)

    @classmethod
    def from_data(cls, group_id: str, data, max_level: int = 10, nested: bool = False, caster: dict | None = None):
        """
        nested: skills of summons, forms and unlocked abilities, which do not describe summons and unlocks of their own
        caster: the character using the skill, when known: its tags settle conditions on them (raid boss difficulty variants), its stats give gauge sizes
        """
        lexicon = Lexicon.of(data)
        caster_tags = frozenset(tag_number(x) for x in caster.get('Tags', [])) if caster else None
        skill = next(skill for skill in data.skills.values() if skill['GroupId'] == group_id)
        timeline = data.levelskill[skill['SkillDataKey']]

        # passives without targeting of their own apply to self, or to whoever the triggering event involved
        default_rule = {'TargetSide': 'Self', 'MaxTargetCount': 1}
        if timeline.get('SkillTargetType') in ('UseTriggerTarget', 'UseTriggerTargetExceptSelf'): default_rule = {'TargetSide': 'EventTarget', 'Name': 'the target'}
        elif timeline.get('SkillTargetType') == 'UseTriggerSource' and timeline.get('TriggerSourceFindRule', {}).get('EssentialCandidate', {}).get('TargetSide') != 'Self':
            default_rule = {'TargetSide': 'EventTarget', 'Name': 'the triggering unit'}
        root_rule = timeline['EssentialCandidateRule'] if timeline.get('EssentialCandidateRule', {}).get('TargetSide', 'None') not in ('None', -1) else default_rule
        # bundled timelines pick one target per container, the player choosing several single targets
        containers = 1 + max(((entry.get('Entity') or {}).get('TargetContainerIndex', 0) for entry in timeline.get('EntityTimeline', [])), default=0)
        if containers > 1 and root_rule.get('MaxTargetCount') == 1: root_rule = dict(root_rule, MaxTargetCount=containers)

        applications, summons = {}, {}
        collect_applications(timeline, applications, summons, {
            'lexicon': lexicon,
            'rule': root_rule,
            'selection': 'root',
            'filters': candidate_filters(timeline.get('OptionalCandidateRule'), lexicon, root_rule.get('TargetSide') == 'Enemy'),
            'sort': sort_text(timeline['TargetSortRule'], lexicon) if timeline.get('TargetSortRule', {}).get('IsValid') else None,
            'area': None,
            'area_frames': 0,
            'interval': 0,
            'delay': 0,
            'conditions': [],
            'distribute': 10000,
            'hit_frames': 1,
            'bounces': 0,
            'skip_groups': set(),
        })

        header, chance, limit = '', None, None
        if type_name(timeline) == 'PassiveSkillDAO': header, chance, limit = passive_trigger(timeline, lexicon)
        elif timeline.get('AutoUseRule'): header, chance, limit = auto_use_trigger(timeline['AutoUseRule'], lexicon, group_id)
        cooldown = seconds(skill['CoolTime']) if skill['CoolTime'] > 0 and not header.startswith('every') else None

        return cls(
            group_id,
            lexicon,
            header,
            chance,
            cooldown,
            limit,
            list(applications.values()),
            [] if nested else [x for name, (entity, conditions) in summons.items() if caster_tags is None or all(bool(c.caster_tags & caster_tags) == c.include for c in conditions if c.caster_tags)
                               if (x := Summon.from_data(name, entity, lexicon, max_level, caster))],
            trigger_templates(timeline),
            len(timeline.get('SelectableExSkillList', [])),
            max_level,
            nested,
            caster,
        )
