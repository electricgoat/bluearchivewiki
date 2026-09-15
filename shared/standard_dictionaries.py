"""
Routine dictionaries of objects that are used in multiple scripts.

This module sits above the model: model.py and classes/* must never import it, or the imports go circular.
"""
import collections
import traceback

from model import Character, Item
from classes.Furniture import Furniture
from classes.Emblem import Emblem


StandardDictionaries = collections.namedtuple('StandardDictionaries', ['characters', 'items', 'furniture', 'emblems'])


def build_characters(data, missing_skill_localization = None) -> dict[int, Character]:
    characters = {}

    for row in data.characters.values():
        if not row['IsPlayableCharacter'] or row['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(row['Id'], data, missing_skill_localization)
        except Exception as err:
            print(f"Failed to parse character {row['DevName']}: {err}")
            traceback.print_exc()
            continue

        characters[character.id] = character

    return characters


def build_items(data) -> dict[int, Item]:
    items = {}

    for row in data.items.values():
        try:
            item = Item.from_data(row['Id'], data)
        except Exception as err:
            print(f"Failed to parse item {row['Id']}: {err}")
            traceback.print_exc()
            continue

        items[item.id] = item

    return items


def build_furniture(data) -> dict[int, Furniture]:
    furniture = {}

    for row in data.furniture.values():
        try:
            piece = Furniture.from_data(row['Id'], data)
        except Exception as err:
            print(f"Failed to parse furniture {row['Id']}: {err}")
            traceback.print_exc()
            continue

        furniture[piece.id] = piece

    return furniture


def build_emblems(data, characters:dict[int, Character], missing_localization = None, missing_etc_localization = None) -> dict[int, Emblem]:
    """Emblems need the characters dictionary built first."""
    emblems = {}

    for emblem_id in data.emblem:
        try:
            emblem = Emblem.from_data(emblem_id, data, characters, ext_missing_etc_localization = missing_etc_localization, ext_missing_localization = missing_localization)
        except Exception as err:
            print(f"Failed to parse emblem {emblem_id}: {err}")
            traceback.print_exc()
            continue

        emblems[emblem.id] = emblem

    return emblems


def build_standard_dictionaries(data, missing_localization = None, missing_etc_localization = None, missing_skill_localization = None) -> StandardDictionaries:
    """All four dictionaries, for scripts that need every one of them."""
    characters = build_characters(data, missing_skill_localization)

    return StandardDictionaries(
        characters = characters,
        items = build_items(data),
        furniture = build_furniture(data),
        emblems = build_emblems(data, characters, missing_localization, missing_etc_localization),
    )
