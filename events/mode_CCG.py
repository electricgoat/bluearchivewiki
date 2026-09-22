import re

from events.common import EventContext, template_env

LOCALIZE_PLACEHOLDER = {'Jp':'Missing Jp localization','En':'Missing En localization'}

ICON_MAP = {
    'Equipment' : 'Gear',
    'Spell' : 'Event',
    'Zone' : 'Location',
}


def parse_cards(ctx: EventContext) -> tuple[list[dict], list[dict], list[dict]]:
    """Copies of the rows of the characters, cards and skills, with their localization. The tables aren't split by event."""
    localization = ctx.data.localization

    characters = [dict(x) for x in ctx.data.minigame_ccg_character.values()]
    cards = [dict(x) for x in ctx.data.minigame_ccg_card.values()]
    for card in characters + cards:
        if card['Name'] in localization:
            card['Localization'] = localization[card['Name']]
            if 'En' not in localization[card['Name']]: ctx.missing_localization.add_entry(localization[card['Name']])

    skills = [dict(x) for x in ctx.data.minigame_ccg_skill.values()]
    for skill in skills:
        skill['LocalizeName'] = localization.get(skill['Name'], None)
        if 'En' not in localization[skill['Name']]: ctx.missing_localization.add_entry(localization[skill['Name']])

        skill['LocalizeDescription'] = localization.get(skill['Description'], None)
        if skill['Description'] != 0 and skill['Description'] in localization and 'En' not in localization[skill['Description']]:
            ctx.missing_localization.add_entry(localization[skill['Description']])

    return characters, cards, skills


def colorize_flavor_text(text:str):
    return re.sub(r'\[c]\[75b4c0]\[i]([^\[]*)\[/i]\[-]\[/c]', r'<p class="flavor-text">\1</p>', text)


def colorize_values(text:str):
    return re.sub(r'\[c]([^\[]*)\[/c]', r'{{SkillValueWrap|\1}}', text)


#{param;DrawCardNum}
def format_param(text:str):
    return re.sub(r'\{param;([^\[]*)\}', r'\1', text)


#{tag;Hyakkiyako}
def format_tag(text:str):
    return re.sub(r'\{tag;([^\[]*)\}', r'{{SkillValueWrap|#\1}}', text)


def format_tags(tags:list):
    return " ".join([f"#{x}" for x in tags])


#{char;848029}, {skill;8480219}, {card;848220}
def reference_filter(kind: str, rows: list[dict], localization: dict):
    """A filter replacing {kind;id} with the English name of the row with that id, or with the id if there is none."""
    names = {x['Id']: x['Name'] for x in rows}

    def replace(match):
        id = int(match.group(1))
        try:
            return f"{localization.get(names[id], LOCALIZE_PLACEHOLDER)['En']}"
        except Exception:
            return f'{id}'

    return lambda text: re.sub(r'\{' + kind + r';([^\[]*)\}', replace, text)


def get_mode_ccg(ctx: EventContext, season_id: int) -> str:
    characters, cards, skills = parse_cards(ctx)
    localization = ctx.data.localization

    env = template_env(
        colorize_values = colorize_values,
        flavor_text = colorize_flavor_text,
        format_tags = format_tags,
        format_param = format_param,
        format_tag = format_tag,
        format_char = reference_filter('char', characters, localization),
        format_skill = reference_filter('skill', skills, localization),
        format_card = reference_filter('card', cards, localization),
    )
    shared_params = dict(skills={x['Id']:x for x in skills}, icon_map=ICON_MAP, localization=localization, localize_placeholder=LOCALIZE_PLACEHOLDER)

    def is_enemy(card: dict) -> bool:
        return card['ImagePath'].rsplit('/',1)[-1].startswith('Enemy')

    title = 'Collectible Card Game'
    wikitext = {'title':f"=={title}==", 'intro':'', 'strikers':'===Striker Characters===\n', 'specials':'===Special Characters===\n', 'enemy_strikers':'===Enemy Striker Characters===\n', 'enemy_specials':'===Enemy Special Characters===\n', 'cards':'===Playable Cards===\n'}

    template = env.get_template('template_ccg_characters.txt')
    wikitext['strikers'] += template.render(cards=[x for x in characters if x['Type'] == 'Striker' and not is_enemy(x)], **shared_params)
    wikitext['specials'] += template.render(cards=[x for x in characters if x['Type'] != 'Striker' and not is_enemy(x)], **shared_params)
    wikitext['enemy_strikers'] += template.render(cards=[x for x in characters if x['Type'] == 'Striker' and is_enemy(x)], **shared_params)
    wikitext['enemy_specials'] += template.render(cards=[x for x in characters if x['Type'] != 'Striker' and is_enemy(x)], **shared_params)

    template = env.get_template('template_ccg_cards.txt')
    wikitext['cards'] += template.render(cards=cards, **shared_params)

    return '\n'.join(wikitext.values())
