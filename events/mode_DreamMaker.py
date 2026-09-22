from events.common import EventContext, template_env
from events.missions import minigame_mission_tables

env = template_env()


def get_mode_dreammaker(ctx: EventContext, season_id: int) -> str:
    data = ctx.data
    dream_info = data.minigame_dream_info[season_id][0]

    title = 'Dream Maker Minigame'
    wikitext = {'title':f"={title}=\n", 'intro':'', 'schedule':'', 'collection':'', 'missions':''}

    template = env.get_template('template_dreammaker_intro.txt')
    wikitext['intro'] = template.render(name=wikitext['title'], dream_info=dream_info)

    template = env.get_template('template_dreammaker_schedule.txt')
    wikitext['schedule'] = template.render(name=wikitext['title'], dream_info=dream_info, dream_schedule=data.minigame_dream_schedule[season_id], dream_schedule_result=data.minigame_dream_schedule_result[season_id], data=data)

    # TODO: Figure out replay scenarios name hashing (data.minigame_dream_replay_scenario)

    template = env.get_template('template_dreammaker_collection.txt')
    wikitext['collection'] = template.render(name=wikitext['title'], dream_collection_scenario=data.minigame_dream_collection_scenario[season_id], event_collection=data.event_content_collection[season_id], data=data)

    wikitext['missions'] = minigame_mission_tables(ctx, season_id)

    return '\n'.join(wikitext.values())
