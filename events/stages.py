"""
The event's own stages, with the strategy maps of its main stages, and its schedule locations.
"""
from classes.Stage import EventStage, DIFFICULTY
from classes.model_event_schedule import EventScheduleLocation
from events.common import EventContext, template_env, render_stage_tables

env = template_env()


def event_stages(ctx: EventContext, event_id: int) -> str:
    """The stage tables, then the strategy maps of the main stages."""
    stages = [EventStage.from_data(x['Id'], ctx.data, wiki_card=ctx.wiki_card, missing_localization=ctx.missing_localization, missing_etc_localization=ctx.missing_etc_localization)
              for x in ctx.data.event_content_stages.values() if x['EventContentId'] == event_id]

    wikitext = render_stage_tables(env.get_template('template_event_stages.txt'), stages, DIFFICULTY)

    hexamaps = {}
    for stage in stages:
        if stage.content_type == 'EventContentMainStage':
            name = f"{DIFFICULTY[stage.difficulty]} {stage.stage_number}"
            hexamaps[name] = {'name': name, 'filename': f"{stage.name}.png"}

    if hexamaps: wikitext += env.get_template('template_event_hexamaps.txt').render(hexamaps=hexamaps.values())
    return wikitext


def schedule_locations(ctx: EventContext, event_id: int) -> str:
    """A table for each group of locations, listing the rewards of its rooms."""
    location_groups = [x['RewardGroupId'] for x in ctx.data.event_content_zone.values() if x['LocationId'] == event_id]
    locations = [EventScheduleLocation.from_data(x['Id'], ctx.data) for x in ctx.data.event_content_location_reward.values() if x['ScheduleGroupId'] in location_groups]

    template = env.get_template('template_schedule.txt')
    wikitext = '=Schedule Locations=\n'

    for group in location_groups:
        group_locations = [x for x in locations if x.group_id == group]
        wikitext += template.render(location_name=group_locations[0].name, locations=group_locations, reward_card=schedule_reward_card)

    return wikitext


def schedule_reward_card(reward) -> str:
    """The card of a reward from classes.model_stages, with its quantity and probability."""
    card_type = reward.type != 'Character' and 'ItemCard' or 'CharacterCard'
    return '{{'+card_type+'|'+(reward.name or 'Unknown')+f'|quantity={reward.amount}|probability={reward.prob:g}|text=|60px|block'+'}}'
