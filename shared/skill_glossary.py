"""
English wording and number formatting for EXPERIMENTAL skill descriptions generated from skill mechanics (classes/SkillMechanics.py).
Keys are the game's enum names, see shared/battle_schema.json.
"""
import math
import re

FRAMES_PER_SECOND = 30

STAT_NAMES = {
    'MaxHP': 'Max HP', 'AttackPower': 'Attack', 'DefensePower': 'Defense', 'HealPower': 'Healing', 'AccuracyPoint': 'Accuracy', 'AccuracyRate': 'Accuracy',
    'DodgePoint': 'Evasion', 'DodgeRate': 'Evasion', 'CriticalPoint': 'Critical Rate', 'CriticalChanceRate': 'Critical Rate', 'CriticalDamageRate': 'Critical Damage',
    'MoveSpeed': 'Movement Speed', 'StabilityPoint': 'Stability', 'StabilityRate': 'Stability', 'ReloadTime': 'Reload Time', 'MaxBulletCount': 'Ammo Count',
    'IgnoreDelayCount': 'Normal Attack Delay Ignore Count', 'WeaponRange': 'Firing Range', 'BlockRate': 'Block Rate', 'HealEffectivenessRate': 'Healing Received',
    'CriticalChanceResistPoint': 'Critical Resistance', 'CriticalResistChanceRate': 'Critical Resistance', 'CriticalDamageResistRate': 'Critical Damage Resistance',
    'NormalAttackSpeed': 'Attack Speed', 'AmmoCost': 'Ammo Cost', 'DamageRatio': 'Damage Dealt', 'DamagedRatio': 'Damage Taken', 'OppressionPower': 'CC Strength',
    'OppressionResist': 'CC Resistance', 'RegenCost': 'Cost Recovery', 'DefensePenetration': 'Defense Penetration', 'ExtendBuffDuration': 'Buff Duration',
    'ExtendDebuffDuration': 'Debuff Duration', 'ExtendCrowdControlDuration': 'CC Duration', 'EnhanceExplosionRate': 'Explosive Efficiency',
    'EnhancePierceRate': 'Piercing Efficiency', 'EnhanceMysticRate': 'Mystic Efficiency', 'EnhanceSonicRate': 'Sonic Efficiency', 'EnhanceChemicalRate': 'Corrosive Efficiency',
    'EnhanceLightArmorRate': 'damage against Light Armor', 'EnhanceHeavyArmorRate': 'damage against Heavy Armor', 'EnhanceUnarmedRate': 'damage against Special Armor',
    'EnhanceElasticArmorRate': 'damage against Elastic Armor', 'EnhanceCompositeArmorRate': 'damage against Composite Armor', 'EnhanceStructureRate': 'damage against structures',
    'DamageRatio2Increase': 'Damage Dealt', 'DamageRatio2Decrease': 'Damage Dealt', 'DamagedRatio2Increase': 'Damage Taken', 'DamagedRatio2Decrease': 'Damage Taken',
    'ExDamagedRatioIncrease': 'EX Skill Damage Taken', 'ExDamagedRatioDecrease': 'EX Skill Damage Taken', 'EnhanceExDamageRate': 'EX Skill Damage',
    'ReduceExDamagedRate': 'EX Skill Damage Taken', 'EnhanceBasicsDamageRate': 'Base Proficiency', 'ReduceBasicsDamagedRate': 'Base Proficiency Damage Taken',
    'HealRate': 'Healing Dealt', 'MaxCostIncrease': 'Max Cost', 'EnhanceWeakDamageRate': 'Weakness Damage', 'ReduceWeakDamagedRate': 'Weakness Damage Taken',
    'EnhanceResistDamageRate': 'Resisted Damage', 'ReduceResistDamagedRate': 'Resisted Damage Taken', 'AddDamageRatioSynergyBulletType': 'Synergy Damage',
    'DamagedRatio_Obstacle': 'Damage Taken from Obstacles', 'AddSummonedObstacleDamagedRatio': 'Damage Taken by Summoned Obstacles',
}
# stats whose flat BaseAmount is shown as a percentage (10000 = 100%), other flat amounts are shown as is
RATIO_STATS = {name for name in STAT_NAMES if re.match(r'(Enhance|Reduce)\w+Rate$|\w*Damage(d)?Ratio\w*$|Heal\w*Rate$', name) and name not in ('HealEffectivenessRate',)}
# stats where a positive amount means a reduction
INVERTED_STATS = {'DamageRatio2Decrease', 'DamagedRatio2Decrease', 'ExDamagedRatioDecrease', 'ReduceExDamagedRate', 'ReduceBasicsDamagedRate', 'ReduceWeakDamagedRate', 'ReduceResistDamagedRate'}

STATUS_NAMES = {
    'Stunned': 'Stun', 'Taunted': 'Taunt', 'Fear': 'Fear', 'Confusion': 'Confusion', 'Charmed': 'Charm', 'Immortal': 'Immortality', 'Untargetable': 'Untargetable',
    'DisableExSkill': 'EX Skill Disable', 'DisableNormalAttack': 'Normal Attack Disable', 'ConcentratedTarget': 'Concentrated Fire', 'Silence': 'Silence', 'Blind': 'Blind',
    'Paralysis': 'Paralysis', 'Frozen': 'Freeze', 'Dead': 'defeated', 'Dying': 'incapacitated', 'Knockback': 'Knockback', 'Airborn': 'Airborne', 'Groggy': 'Groggy',
    'Burn': 'Burn', 'Chill': 'Chill', 'Poison': 'Poison', 'ElectricShock': 'Electric Shock', 'Shield': 'Shield', 'TacticalShield': 'Tactical Shield',
}
CATEGORY_NAMES = {'Attack': 'damage', 'Heal': 'healing', 'Buff': 'buff', 'Debuff': 'debuff', 'CrowdControl': 'crowd control', 'Dummy': 'special effect'}
ARMOR_NAMES = {'LightArmor': 'Light Armor', 'HeavyArmor': 'Heavy Armor', 'Unarmed': 'Special Armor', 'ElasticArmor': 'Elastic Armor', 'CompositeArmor': 'Composite Armor', 'Structure': 'Structure', 'Normal': 'Normal Armor'}
BULLET_NAMES = {'Explosion': 'Explosive', 'Pierce': 'Piercing', 'Mystic': 'Mystic', 'Sonic': 'Sonic', 'Chemical': 'Corrosive', 'Normal': 'Normal', 'Siege': 'Siege'}
ROLE_NAMES = {'DamageDealer': 'Attacker', 'Tanker': 'Tank', 'Supporter': 'Support', 'Healer': 'Healer', 'Vehicle': 'Tactical Support'}
ENTITY_NAMES = {'Student': 'student', 'Minion': 'minion', 'Elite': 'elite enemy', 'Champion': 'champion enemy', 'Boss': 'boss', 'Obstacle': 'obstacle', 'Vehicle': 'vehicle', 'Summoned': 'summoned unit'}
AREA_SHAPES = {'CircleAreaEntityDAO': 'circular', 'CircleAuraEntityDAO': 'circular', 'FanAreaEntityDAO': 'fan-shaped', 'ObbAreaEntityDAO': 'rectangular', 'DonutAreaEntityDAO': 'ring-shaped'}
TARGET_NOUNS = {'Enemy': ('enemy', 'enemies'), 'Ally': ('ally', 'allies'), 'Ally_Except_Self': ('other ally', 'other allies'), 'All_Except_Self': ('other unit', 'other units'),
                'Self_or_Enemy': ('enemy', 'enemies'), 'Ally_or_Enemy': ('unit', 'units'), 'ALL': ('unit', 'units')}
# ModifierCheckTarget: whose state a condition checks
SUBJECTS = {'Caster': 'self', 'Target': 'the target', 'CasterAlly': 'allies', 'CasterEnemy': 'enemies', 'All': 'all units', 'CasterAllyExceptCaster': 'other allies'}
COMPARISONS = {'Equal': '{}', 'NotEqual': 'not {}', 'Less': 'below {}', 'LessOrEqual': 'at or below {}', 'Greater': 'above {}', 'GreaterOrEqual': 'at or above {}'}
COUNT_COMPARISONS = {'Equal': '{}', 'GreaterOrEqual': '{}+', 'LessOrEqual': 'up to {}', 'NotEqual': 'not {}'}


def slot_name(slot: str) -> str:
    """'ExSkill01', 'Ex' -> 'EX' and so on"""
    for prefix, name in (('ExtraPassive', 'Sub'), ('HiddenPassive', 'hidden passive'), ('Passive', 'Passive'), ('Public', 'Normal'), ('Ex', 'EX'), ('Normal', 'normal attack'), ('All', 'any')):
        if slot.startswith(prefix): return name
    return slot


def slot_names(parameters: str) -> str:
    return ' or '.join(slot_name(x.strip()) for x in parameters.split(',') if x.strip())


def truncate(value: float, decimals: int) -> str:
    factor = 10 ** decimals
    text = f'{math.trunc(round(value * factor, 6)) / factor:.{decimals}f}'
    return text.rstrip('0').rstrip('.') if decimals > 0 else text


def percent(value, decimals: int = 1) -> str:
    """Game rates are stored in 1/100ths of a percent, shown truncated to 1 decimal (JP descriptions often drop even that)"""
    return truncate(abs(int(value)) / 100, decimals) + '%'


def seconds(ms) -> str:
    value = truncate(int(ms) / 1000, 2)
    return f"{value} second{'' if value == '1' else 's'}"


def frames(count) -> str:
    return seconds(int(count) * 1000 // FRAMES_PER_SECOND)


def skill_value(text) -> str:
    return '{{SkillValue|' + str(text) + '}}'


def capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def split_words(text: str) -> str:
    """'LightStick_Lv02' -> 'Light Stick Lv02'"""
    return re.sub(r'(?<=[a-z])(?=[A-Z])|_', ' ', text).strip()


def status_name(template_id: str) -> str:
    """Readable name of a regular (non character-unique) effect template, 'CrowdControl_StatusAdd_Stunned' -> 'Stun'"""
    parts = [x for x in re.sub(r'_(Self|Mine|NoVisualEffect)$', '', template_id).split('_') if not re.fullmatch(r'(CH|SM|EN)\d+\w*', x)]
    last = parts[-1] if parts else template_id
    return STATUS_NAMES.get(last, split_words(last).lower() if last in ('DamageOverTime', 'HealOverTime', 'FormConversion', 'StatChange') else split_words(last))
