from typing import NamedTuple

import shared.functions
from events.common import EventContext, template_env

env = template_env()


class TreasureReward(NamedTuple):
    """A treasure hidden on a round's board, with its name and reward cards resolved."""
    name_en: str
    width: int
    height: int
    image: str
    cards: list[str]

    def wikitext_items(self) -> list[str]:
        return self.cards


def parse_treasure(ctx: EventContext, treasure: dict) -> TreasureReward:
    return TreasureReward(
        treasure_name(ctx, treasure),
        treasure['CellUnderImageWidth'],
        treasure['CellUnderImageHeight'],
        treasure['CellUnderImagePath'].rsplit('/',1)[-1],
        [ctx.wiki_card(parcel_type, parcel_id, quantity=amount, text='', probability=None, block=True, size='48px')
         for parcel_type, parcel_id, amount in zip(treasure['RewardParcelType'], treasure['RewardParcelId'], treasure['RewardParcelAmount'])],
    )


def treasure_name(ctx: EventContext, treasure: dict) -> str:
    key = shared.functions.hashkey(treasure['LocalizeCodeID'])
    if key not in ctx.data.localization:
        print(f"Missing localize key {key} for treasure reward {treasure['Id']} ({treasure['LocalizeCodeID']})")
        return treasure['LocalizeCodeID']

    localization = ctx.data.localization[key]
    if 'En' not in localization: ctx.missing_localization.add_entry(localization)

    return localization.get('En') or localization.get('Jp') or treasure['LocalizeCodeID']


def get_mode_treasure(ctx: EventContext, season_id: int) -> str:
    data = ctx.data
    wikitext = {'title':'===Inventory Management===', 'rounds':''}

    rounds = [dict(x) for x in sorted(data.event_content_treasure_round[season_id], key=lambda x: x['TreasureRound'])]
    for round in rounds:
        round['treasures'] = [parse_treasure(ctx, data.event_content_treasure_reward[x]) for x in round['RewardID']]

    cost_goods_ids = [x['CellCheckGoodsId'] for x in rounds]
    if len(set(cost_goods_ids)) == 1: #all rounds cost the same
        cost_good = data.goods[cost_goods_ids[0]]
        wiki_price = ctx.wiki_card('Item', cost_good['ConsumeParcelId'][0], quantity = cost_good['ConsumeParcelAmount'][0])
    else:
        wiki_price = 'varies depending on round'

    cell_reward_ids = [x['CellRewardId'] for x in rounds]
    if len(set(cell_reward_ids)) == 1: #all rounds have the same cell reveal reward
        cell_reward = data.event_content_treasure_cell_reward[cell_reward_ids[0]]
        wiki_cell_reward = ", ".join(ctx.wiki_card(parcel_type, parcel_id, quantity=amount, probability=None)
                                     for parcel_type, parcel_id, amount in zip(cell_reward['RewardParcelType'], cell_reward['RewardParcelId'], cell_reward['RewardParcelAmount']))
    else:
        wiki_cell_reward = 'varies depending on round'

    template = env.get_template('template_treasure_rounds.txt')
    wikitext['rounds'] = template.render(rounds=rounds, wiki_price=wiki_price, wiki_cell_reward=wiki_cell_reward)

    return '\n'.join(wikitext.values()) + '\n'
