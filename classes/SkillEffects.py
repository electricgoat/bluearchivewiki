"""
EXPERIMENTAL: describes a single LogicEffect (one skill level's row) as an English clause, see classes/SkillMechanics.py.
Clauses start lowercase and have no final period, numbers that are skill values are wrapped in {{SkillValue}}.
"""
import re

from shared.skill_glossary import STAT_NAMES, RATIO_STATS, INVERTED_STATS, STATUS_NAMES, CATEGORY_NAMES, percent, seconds, skill_value, truncate, status_name

# effects that only drive other mechanics and have nothing to say on their own
SILENT_EFFECTS = {'BlackBoardSet', 'BlackBoardAdd', 'BlackBoardAlarmOnReach', 'WriteEntityToBlackboard', 'AddDamageToBlackBoard', 'ResetAutoUseRule',
                  'ApplyLogicDispelCount', 'TargetSlotExSkillCostOverride', 'ChangeSkillCardToCopiedCard', 'AccumulateDamage',
                  'StackDamage', 'ImmediateKill', 'NotMove'}


def duration(effect: dict, key: str = 'Duration') -> str:
    """' for X seconds', or nothing for effects that last until removed"""
    value = int(effect.get(key, -1) or -1)
    return f' for {skill_value(seconds(value))}' if value > 0 else ''


def end_condition(effect: dict) -> str:
    condition = effect.get('EndCondition', 'Duration')
    argument = int(effect.get('EndConditionArgumentFirst', effect.get('EndConditionArgument', -1)) or -1)
    if argument <= 0: return ''
    return {
        'Duration': f' for {skill_value(seconds(argument))}',
        'UseExSkillCount': f' (for {skill_value(argument)} EX skill use{"s" if argument > 1 else ""})',
        'AmmoCount': f' (until {skill_value(argument)} ammo is used)',
        'ReloadCount': f' (until {skill_value(argument)} reload{"s" if argument > 1 else ""})',
        'AmmoHit': f' (for {skill_value(argument)} normal attack{"s" if argument > 1 else ""})',
        'HitCount': f' (for {skill_value(argument)} hits)',
    }.get(condition, f' ({condition} {argument})')


def stacking(effect: dict) -> str:
    if not effect.get('StackSameEffectApplied') or effect.get('StackSameEffectCount', 0) <= 1: return ''
    return f" (stacks up to {skill_value(effect['StackSameEffectCount'])} times)"


def of_target(app, preposition: str = 'of') -> str:
    return '' if app.is_self else f' {preposition} {app.mention}'


def to_target(app) -> str:
    return '' if app.is_self else f' to {app.mention}'


def rate_text(rate, stat) -> str:
    return f'{skill_value(percent(rate))} of {STAT_NAMES.get(stat, stat)}'


def stat_change(effect: dict, app, holder_is_self: bool | None = None) -> str:
    """holder_is_self: whether whoever the effect ends up on is the skill's user, when app does not say (stacks describe their own effect)"""
    stat, source = effect['StatType'], ''
    if effect['TargetCoefficientAmount']: amount, value = effect['TargetCoefficientAmount'], percent(effect['TargetCoefficientAmount'])
    elif effect.get('CasterCoefficientAmount'):
        amount, value = effect['CasterCoefficientAmount'], percent(effect['CasterCoefficientAmount'])
        source = f" of the caster's {STAT_NAMES.get(effect['CasterStatType'], effect['CasterStatType'])}"
    elif stat in RATIO_STATS: amount, value = effect['BaseAmount'], percent(effect['BaseAmount'], 2)
    else: amount, value = effect['BaseAmount'], f"{abs(effect['BaseAmount']):g}"

    increase = (amount > 0) != (stat in INVERTED_STATS)
    # a debuff on the skill's own user says so, "reduce Attack" alone reads as aimed at enemies.
    # Stats carried by a marker are categorized Dummy, their direction tells: lowering a stat, or raising damage taken, is a penalty
    penalty = effect.get('Category') == 'Debuff' or effect.get('Category') == 'Dummy' and increase == ('Damaged' in stat)
    own = ' own' if penalty and (app.is_self if holder_is_self is None else holder_is_self) else ''
    return f"{'increase' if increase else 'reduce'}{own} {STAT_NAMES.get(stat, stat)}{of_target(app)} by {skill_value(value)}{source}"


def form_name(lexicon, group_id: str, form_index: int | None = None, unnamed: str = 'an alternate state') -> str:
    """A form's name as it reads in a clause: names that do not say what they are get 'state' ("Submerged" -> "the Submerged state")"""
    name = lexicon.form_name(group_id, form_index)
    if not name: return unnamed
    return f"the {name}" if re.search(r'(state|stance|mode|form|posture)$', name, re.I) else f'the {name} state'


def describe_marker(effect: dict, app, lexicon) -> str | None:
    """Character-unique effects (Dummy_ templates): named states and stack counters, which may also carry a stat change"""
    name = lexicon.marker_name(effect['TemplateId'])
    has_stat = effect['Type'] == 'StatChange' and (effect['TargetCoefficientAmount'] or effect['BaseAmount'] or effect.get('CasterCoefficientAmount'))
    lasts = int(effect.get('EndConditionArgument', effect.get('EndConditionArgumentFirst', -1)) or -1)
    if not has_stat and (not lexicon.is_notable_marker(effect) or effect.get('EndCondition', 'Duration') == 'Duration' and 0 < lasts < 1000): return None

    stacks = effect.get('StackSameEffectCount', 0) if effect.get('StackSameEffectApplied') else 0
    subject = 'gain' if app.is_self else f'grant {app.mention}'
    gained = len(app.hit_rates) or 1
    text = f'{subject} {skill_value(gained)} "{name}" stack{"s" if gained > 1 else ""} (up to {skill_value(stacks)})' if stacks > 1 else f'{subject} "{name}"'
    if family := lexicon.family_name(effect['TemplateId']): text = f"{subject} \"{family}\" at level {skill_value(int(re.search(r'(\d+)$', effect['TemplateId']).group(1)))}"
    if has_stat: text += (': each stack will ' if stacks > 1 else ', which will ') + stat_change(effect, app.as_self(), holder_is_self=app.is_self)
    return text + end_condition(effect)


def describe_effect(effect: dict, app, lexicon) -> str | None:
    kind, template = effect['Type'], effect['TemplateId']
    if kind in SILENT_EFFECTS: return None
    if 'Dummy' in template and kind in ('Dummy', 'StatChange'): return describe_marker(effect, app, lexicon)

    match kind:
        case 'Dummy':
            return None

        case 'Damage':
            # every hit deals its DamageDistributeRate share of the rate, JP descriptions show either the total or a single hit
            rate, hits = effect['BonusRateFirst'], len(app.hit_rates)
            text = f"deal {rate_text(rate * sum(app.hit_rates) // 10000, effect['BonusSourceFirst'])} as damage to {app.mention}"
            if hits > 1:
                text += f' over {skill_value(hits)} hits'
                if len(set(app.hit_rates)) == 1: text += f' ({skill_value(percent(rate * app.hit_rates[0] // 10000))} per hit)'
            if app.bounces: text += f', bouncing to up to {skill_value(app.bounces)} more {"enemies" if app.bounces > 1 else "enemy"}'
            if effect.get('DefensePenetrationRate', 10000) < 10000: text += f" (ignores {skill_value(percent(10000 - effect['DefensePenetrationRate']))} of Defense)"
            if app.piercing: text += f" (damage −{skill_value(percent(app.piercing[0]))} for each enemy pierced, down to {skill_value(percent(app.piercing[1]))})"
            if effect.get('ApplyStability') is False: text += ' (always deals maximum damage)'
            if effect.get('CriticalCheck') == 'Always': text += ' (always critical)'
            elif effect.get('CriticalCheck') == 'Never': text += ' (cannot be critical)'
            return text

        case 'ExtraStatDamage':
            if effect.get('BonusSourceBlackboardKeyString'):
                return f"deal damage equal to {skill_value(percent(effect['BonusRateBlackboard']))} of the accumulated amount to {app.mention}"
            if effect.get('AddSource', 'None') != 'None':
                return f"deal damage to {app.mention} equal to {skill_value(percent(effect['AddRate']))} of {effect['AddSource']}"
            return f"deal damage to {app.mention} scaling with {effect.get('MultiplySource', 'stats')}"

        case 'DamageOverTime':
            return f"inflict {status_name(template)} on {app.mention}, dealing {rate_text(effect['BonusRateFirst'], effect['BonusSourceFirst'])} as damage over time{duration(effect)}"

        case 'DamageByHit':
            text = f"mark {app.mention}{duration(effect)}: each hit it takes deals an additional {rate_text(effect['BonusRateFirst'], effect['BonusSourceFirst'])} as damage"
            if effect.get('RemoveCondition') == 'TriggerCountOver': text += f" (up to {skill_value(effect['RemoveConditionArgument'])} times)"
            return text

        case 'Heal' | 'MaxHpOverHeal':
            text = f"recover HP{of_target(app)} by {rate_text(effect['BonusRate'], effect['BonusSource'])}"
            if kind == 'MaxHpOverHeal':
                text += f"; overhealing converts into extra HP (up to {skill_value(percent(effect['TemporaryHpLimitRateByTargetMaxHp']))} of Max HP)"
            return text

        case 'HealOverTime':
            return f"grant{'' if app.is_self else ' ' + app.mention} healing over time equal to {rate_text(effect['BonusRate'], effect['BonusSource'])}{duration(effect)}"

        case 'HealByHit' | 'ShieldHealByHit':
            restores = 'shield' if kind == 'ShieldHealByHit' else 'HP'
            text = f"each hit taken{of_target(app, 'by')} restores {restores} by {rate_text(effect['BonusRate'], effect['BonusSource'])}{duration(effect)}"
            if effect.get('RemoveCondition') == 'TriggerCountOver': text += f" (up to {skill_value(effect['RemoveConditionArgument'])} times)"
            return text

        case 'Shield':
            shield = 'tactical shield' if effect.get('ShieldId') == 'Tactical' else 'shield'
            return f"grant {app.mention} a {shield} equal to {rate_text(effect['CasterCoefficientAmount'], effect['CasterStatType'])}{duration(effect)}"

        case 'StatChange':
            return stat_change(effect, app) + end_condition(effect) + stacking(effect)

        case 'StatusAdd' | 'StatusAddWithParameter' | 'StatusAddWithStringParameter':
            # brief internal locks during a skill's animation
            if effect['Category'] == 'Dummy' and effect['TargetStatus'].startswith('Disable') and 0 < int(effect.get('Duration', 0)) <= 1000: return None
            status = STATUS_NAMES.get(effect['TargetStatus'], effect['TargetStatus'])
            if effect['Category'] in ('CrowdControl', 'Debuff'): return f"inflict {status} on {app.mention}{duration(effect)}"
            return f"grant {status}{to_target(app)}{duration(effect)}"

        case 'StatusRemove':
            return f"remove {STATUS_NAMES.get(effect['TargetStatus'], effect['TargetStatus'])}{of_target(app, 'from')}"

        case 'Dispel':
            count = effect['DispelCount']
            return f"remove {skill_value(count)} {CATEGORY_NAMES.get(effect['DispelTarget'], effect['DispelTarget'])}{'s' if count > 1 else ''}{of_target(app, 'from')}"

        case 'DispelLogicEffectTemplate':
            removed = effect['LogicEffectTemplateToDispel']
            if 'FormConversion' in removed: return f"exit {form_name(lexicon, effect['GroupId'], unnamed='the alternate state')}"
            if 'Dummy' in removed:
                if not lexicon.is_notable_marker_template(removed): return None
                name = f'"{lexicon.family_name(removed) or lexicon.marker_name(removed)}"'
            else: name = status_name(removed)
            return f"remove {'all ' if effect['DispelCount'] >= 10 else ''}{name}{of_target(app, 'from')}"

        case 'DispelLogicEffectGroupId':
            # removing another skill's effect: 'remove the "Surfacing!" effect'. Removals within the same skill are internal
            skill = lexicon.group_skill(effect['LogicEffectGroupIdToDispel'])
            if skill is None or skill == lexicon.group_skill(effect['GroupId']): return None
            return f'remove the "{lexicon.skill_name(skill)}" effect{of_target(app, "from")}'

        case 'Immune':
            statuses = [status_name(v) for k, v in effect.items() if k.startswith('TargetLogicEffectTemplateId') and v]
            return f"grant{'' if app.is_self else ' ' + app.mention} immunity to {', '.join(statuses)}{duration(effect)}"

        case 'Knockback':
            if effect['KnockbackDirection'] == 'Caster': return None
            return f"{'pull' if effect['KnockbackDirection'] == 'TargetToCaster' else 'knock back'} {app.mention}"

        case 'ReloadAmmo':
            return 'reload immediately' if app.is_self else f'reload the weapon of {app.mention}'

        case 'AddCurrentAmmo':
            count = effect['AmmoCountToAdd']
            return f"{'add' if count > 0 else 'remove'} {skill_value(abs(count))} ammo{' to ' if count > 0 else ' from '}{app.mention}"

        case 'AddSkillCost':
            return f"recover {skill_value(truncate(effect['Amount'] * max(len(app.hit_rates), 1) / 10000, 2))} skill cost"

        case 'SkillCostChange' | 'ExtraSkillCostChange':
            value = percent(effect['Coefficient']) if effect.get('Coefficient') else f"{abs(effect['BaseAmount']):g}"
            cost = 'additional EX skill cost' if kind == 'ExtraSkillCostChange' else 'skill cost'
            return f"{'reduce' if (effect.get('Coefficient') or effect['BaseAmount']) < 0 else 'increase'} {cost}{of_target(app)} by {skill_value(value)}{end_condition(effect)}"

        case 'FormConversion':
            return f"enter {form_name(lexicon, effect['GroupId'], effect['FormIndex'])}" + end_condition({'EndCondition': effect['FormConversionEndCondition'], 'EndConditionArgument': effect['EndConditionArgument']})

        case 'CostOverloadEnable':
            return f"grant Cost Overload{to_target(app)}{end_condition(effect)}"

        case 'ExSkillCardRedrawGauge':
            if effect.get('InitialRedrawStackCount'): return f"immediately draw {skill_value(effect['InitialRedrawStackCount'])} EX skill card{'s' if effect['InitialRedrawStackCount'] > 1 else ''} on next EX skill use"
            return None

        case 'Accumulate':
            return (f"for {skill_value(seconds(effect['Duration']))}, store {skill_value(percent(effect['AccumulateRate']))} of the damage allies deal to {app.mention}, "
                    f"then deal the stored amount as damage (up to {rate_text(effect['LimitSourceStatRate'], effect['LimitSourceStat'])})")

        case 'DamagedMultiplierbyDamageOverTime':
            return f"increase {status_name(template)} damage taken by {app.mention} by {skill_value(percent(effect['AddRate']))}{duration({'Duration': effect['RemoveConditionArgument']})}"

        case 'AmplifyDoTReducePeriod':
            return f"shorten the {status_name(effect['TargetLogicEffectTemplateId'])} damage interval on {app.mention} by {skill_value(percent(effect['PeriodReduceRate']))}{duration(effect)}"

        case 'AmplifyDoTAdditionalTick':
            return (f"{status_name(effect['TargetLogicEffectTemplateId'])} on {app.mention} deals {skill_value(effect['AdditionalTickDamageApplyCount'])} additional ticks "
                    f"of {skill_value(percent(effect['AdditionalTickDamageRate']))} damage{duration(effect)}")

        case 'AccumulateDamageFromTargets':
            # damage stored on a target and dealt at once when the effect ends: Iroha (Swimsuit)'s Suitcase. Copies without an object are visual only
            if not effect.get('ObjectLogicEffectGroupId') or effect['ObjectLogicEffectGroupId'] not in lexicon.data.logic_effects: return None
            name = lexicon.marker_name(lexicon.data.logic_effects[effect['ObjectLogicEffectGroupId']][0]['TemplateId'])
            holders = lexicon.data.logic_effects.get(effect.get('TargetLogicEffectGroupId'), [{}])[0].get('TemplateId')
            dealers = f'allies with "{lexicon.marker_name(holders)}"' if holders else 'allies'
            ends = ' or '.join(x for x, key in (('ends', 'IsWriteWhenLogicExpired'), ('is removed', 'IsWriteWhenLogicDispelled')) if effect.get(key)) or 'ends'
            text = (f'grant {app.mention} "{name}"{duration({"Duration": effect.get("EndConditionArgument")})}, storing {skill_value(percent(effect["AccumulateRate"]))} '
                    f'of the damage {dealers} deal to the target and dealing it once "{name}" {ends}')
            if effect.get('LimitSourceBlackboardKeyString'):
                recorder = next((rows[0] for rows in lexicon.data.logic_effects.values() if rows[0]['Type'] == 'AddDamageToBlackBoard' and rows[0].get('BlackBoardKey') == effect['LimitSourceBlackboardKeyString']), {})
                text += f" (up to {skill_value(percent(effect['LimitSourceBlackboardRate']))} of the caster's {'EX skill ' if recorder.get('SkillTypeFilter') == 'Ex' else ''}damage)"
            return text

        case 'DamageTransfer':
            # parts of a boss sharing the damage they take with it: Perorozilla's minions
            holder = '' if app.is_self else f' {app.mention}'
            takes = 'taken' if app.is_self else 'it takes' if app.target.startswith(('one ', 'the ')) else 'they take'
            return f"make{holder or ' self'} pass {skill_value(percent(effect['TransferRatio']))} of the damage {takes} on to the caster{duration(effect)}"

        case 'AddCurrentATG':
            return f"{'increase' if effect['Amount'] > 0 else 'reduce'} ATG{of_target(app)} by {skill_value(abs(effect['Amount']))}"

        case 'SkillCardCopyTarget':
            # the caster's card turns into the copy, which lasts a number of uses and costs relative to the copied skill
            copy = lexicon.data.logic_effects.get(effect.get('ChangeSkillCardToCCToCasterLogicEffectGroupId'), [{}])[0]
            notes = []
            if effect.get('EndCondition') == 'TriggerCount':
                uses = int(effect['EndConditionArgument'])
                notes.append('usable once' if uses == 1 else f'usable {skill_value(uses)} times')
            if change := copy.get('CopiedCardCostModifyByAmount'):
                notes.append(f"costs {skill_value(abs(change))} {'less' if change < 0 else 'more'} than the original{', minimum 0' if change < 0 else ''}")
            # the used card stays in hand, replaced by the copy
            return f"replace this card with a copy of the EX skill card of {app.mention}" + (f" ({'; '.join(notes)})" if notes else '')

    return f'[{kind}: {template}]'
