from classes.Stage import DefenseStage
from events.common import EventContext, template_env, render_stage_tables
from events.missions import minigame_mission_tables

env = template_env()

DIFFICULTY_NAMES = {'Normal':'Story', 'Hard':'Normal', 'VeryHard':'Challenge'}


def get_mode_defense(ctx: EventContext, season_id: int) -> str:
    data = ctx.data

    title = 'Hi-Lo Ha-Lo Minigame'
    wikitext = {'title':f"=={title}==", 'intro':'', 'banned':'', 'stages':'', 'missions':''}

    template = env.get_template('template_defense_intro.txt')
    wikitext['intro'] = template.render(name=title, defense_info=data.minigame_defense_info[season_id])

    template = env.get_template('template_banned_characters.txt')
    ban_ids = [x['CharacterId'] for x in data.minigame_defense_character_ban[season_id]]
    wikitext['banned'] = template.render(character_names=[ctx.characters[x].wiki_name for x in ctx.characters if x in ban_ids])

    stages = [DefenseStage.from_data(x['Id'], data, wiki_card=ctx.wiki_card, missing_localization=ctx.missing_localization, missing_etc_localization=ctx.missing_etc_localization)
              for x in data.minigame_defense_stage.values() if x['EventContentId'] == season_id]
    wikitext['stages'] = render_stage_tables(env.get_template('template_event_stages.txt'), stages, DIFFICULTY_NAMES)

    wikitext['missions'] = minigame_mission_tables(ctx, season_id)

    return '\n'.join(wikitext.values())
