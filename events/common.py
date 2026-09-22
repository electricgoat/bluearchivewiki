"""
What the event page sections share: the context they read from, the template environment and the stage tables.
"""
import os
from typing import NamedTuple

from jinja2 import Environment, FileSystemLoader, Template

import shared.functions
from data import BlueArchiveData, BlueArchiveSeasonData
from model import Character, Item
from classes.Furniture import Furniture
from classes.Emblem import Emblem
from shared.MissingTranslations import MissingTranslations


class EventContext(NamedTuple):
    """The loaded game data and dictionaries, and the collectors of missing translations."""
    data: BlueArchiveData
    season_data: dict[str, BlueArchiveSeasonData]
    characters: dict[int, Character]
    items: dict[int, Item]
    furniture: dict[int, Furniture]
    emblems: dict[int, Emblem]
    missing_localization: MissingTranslations
    missing_code_localization: MissingTranslations
    missing_etc_localization: MissingTranslations

    def wiki_card(self, type: str, id: int, **params) -> str:
        return shared.functions.wiki_card(type, id, self.data, self.characters, self.items, self.furniture, self.emblems, **params)


def template_env(**filters) -> Environment:
    """An environment for the templates in events/, with the filters they share and the given ones."""
    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.globals['len'] = len
    env.filters.update(
        nl2br = shared.functions.nl2br,
        nl2p = shared.functions.nl2p,
        thousands = shared.functions.format_thousands,
        colorize = shared.functions.colorize,
        replace_glossary = shared.functions.replace_glossary,
        **filters,
    )
    return env


def render_stage_tables(template: Template, stages: list, difficulty_names: dict[str, str], skip_empty: bool = True) -> str:
    """A table for each difficulty of difficulty_names that has stages, with a column for each reward tag of its stages.
    skip_empty leaves out the tags whose rewards show no items."""
    wikitext = ''

    for difficulty, name in difficulty_names.items():
        group = [x for x in stages if x.difficulty == difficulty]
        if not group: continue

        reward_types = []
        for stage in group:
            for tag, rewards in stage.rewards.items():
                if tag not in reward_types and (not skip_empty or any(x.wikitext_items() for x in rewards)):
                    reward_types.append(tag)

        wikitext += template.render(stage_type=name, stages=group, reward_types=reward_types, rewardcols=len(reward_types))

    return wikitext
