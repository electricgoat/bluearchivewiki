import copy

import shared.functions
from classes.RewardParcel import RewardParcel
from classes.Stage import FieldStage, DIFFICULTY
from events.common import EventContext, template_env, render_stage_tables


def field_rewards(ctx: EventContext, reward_id: int) -> list[RewardParcel]:
    return [RewardParcel(x['RewardParcelType'], x['RewardId'], [x['RewardAmount']], [x['RewardProb']], data=ctx.data, wiki_card=ctx.wiki_card) for x in ctx.data.field_reward[reward_id]]


def note_missing(ctx: EventContext, key: int):
    """Note the localization under key as missing a translation if it has no English text."""
    if not ctx.data.localization[key].get('En'):
        ctx.missing_localization.add_entry(ctx.data.localization[key])


def get_mode_field(ctx: EventContext, season_id: int) -> str:
    data = ctx.data
    env = template_env(shortform_range=shortform_range)

    wikitext = {'quest':'', 'evidence':'', 'stages':''}

    season = data.field_season[season_id]
    print(season)

    quests = {}
    total_permanent_rewards = {}
    for entry in data.field_quest[season_id]:
        note_missing(ctx, entry['QuestNamKey'])
        note_missing(ctx, entry['QuestDescKey'])

        entry = dict(entry)
        entry['QuestName'] = data.localization[entry['QuestNamKey']]
        entry['QuestDesc'] = data.localization[entry['QuestDescKey']]
        entry['Rewards'] = field_rewards(ctx, entry['RewardId'])
        entry['Days'] = [entry['Opendate']]

        if entry['QuestNamKey'] not in quests:
            quests[entry['QuestNamKey']] = entry
        else:
            quests[entry['QuestNamKey']]['Days'].append(entry['Opendate'])

        if not entry['IsDaily']:
            for reward in entry['Rewards']:
                if (reward.parcel_type, reward.parcel_id) not in total_permanent_rewards:
                    total_permanent_rewards[(reward.parcel_type, reward.parcel_id)] = copy.copy(reward)
                else:
                    total_permanent_rewards[(reward.parcel_type, reward.parcel_id)].amount += reward.amount

    #sort by first day of quest appearance
    quests = dict(sorted(quests.items(), key=lambda x: x[1]['Opendate']))

    template = env.get_template('template_field_quest.txt')
    wikitext['quest'] = template.render(quests=quests, total_permanent_rewards=sorted(total_permanent_rewards.values(), key=lambda x: x.parcel_id))


    evidence = {}
    for entry in [x for x in data.field_evidence.values() if x['SeasonId'] == season_id]:
        localize_key = shared.functions.hashkey(entry['NameLocalizeKey'])
        localize_desc_key = shared.functions.hashkey(entry['DescriptionLocalizeKey'])
        localize_detail_key = shared.functions.hashkey(entry['DetailLocalizeKey'])
        has_detail = entry['DetailLocalizeKey'] != '' and localize_detail_key in data.localization

        note_missing(ctx, localize_key)
        note_missing(ctx, localize_desc_key)
        if has_detail: note_missing(ctx, localize_detail_key)

        entry = dict(entry)
        entry['Name'] = data.localization[localize_key]
        entry['Desc'] = data.localization[localize_desc_key]
        entry['Detail'] = data.localization[localize_detail_key] if has_detail else None
        entry['Image'] = entry['ImagePath'].rsplit('/', 1)[-1]

        entry['FromInteraction'] = [x for x in data.field_interaction.values() if 'EvidenceFound' in x['InteractionType'] and entry['UniqueId'] in x['InteractionId'] ][0]
        entry['FromDate'] = data.field_date[entry['FromInteraction']['FieldDateId']]

        if 'Reward' in entry['FromInteraction']['InteractionType']:
            entry['Rewards'] = field_rewards(ctx, entry['FromInteraction']['InteractionId'][entry['FromInteraction']['InteractionType'].index("Reward")])
        else:
            entry['Rewards'] = []

        evidence[entry['UniqueId']] = entry

    template = env.get_template('template_field_evidence.txt')
    wikitext['evidence'] = template.render(evidence=evidence)


    stages = [FieldStage.from_data(x['Id'], data, wiki_card=ctx.wiki_card) for x in data.field_content_stage.values() if x['SeasonId'] == season_id]
    #unlike the event's stages, field stages list the reward tags that show no items too
    wikitext['stages'] = render_stage_tables(env.get_template('template_field_stages.txt'), stages, DIFFICULTY, skip_empty=False)

    return "=Field Mission=\n" + '\n'.join(wikitext.values())


def shortform_range(numbers: list[int]):
    if not numbers:
        return "Empty List"

    numbers = sorted(numbers)
    ranges = []
    start, end = numbers[0], numbers[0]

    for num in numbers[1:]:
        if num == end + 1:
            end = num
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}~{end}")
            start = end = num

    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}~{end}")

    return ", ".join(ranges)
