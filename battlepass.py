"""
The wiki's Battle Pass page (<outdir>/shops/Battle_Pass.txt): how the pass works, then each season's dates, offers, missions, level rewards and news ticker.
"""
import os
import argparse
from datetime import datetime
from typing import NamedTuple

from jinja2 import Environment, FileSystemLoader

import shared.functions
from data import load_data, load_battle_pass_data, BlueArchiveData, BlueArchiveBattlePassData
from model import Item
from classes.Character import Character
from classes.Furniture import Furniture
from classes.Emblem import Emblem
from events.mission_desc import description_cleanup
from shared.MissingTranslations import MissingTranslations
from shared.standard_dictionaries import build_standard_dictionaries

missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")


#A season's offers, by the BattlePassInfoExcelTable column naming their product group: their names, given the game's (the upgrade's is Growth CH+'s), and what each does besides giving its parcels
OFFERS = {
    'NormalProductGroupID':          ('{name}',         ['Unlocks the Growth CH rewards']),
    'PremiumProductGroupID':         ('{name}',         ['Unlocks the Growth CH rewards', '+{levels} pass levels at once']),
    'DiscountPremiumProductGroupID': ('{name} upgrade', ['Upgrades Growth CH to Growth CH+', '+{levels} pass levels at once']),
}

#The groups of the mission table, by BattlePassMissionExcelTable Category, in table order: their headings, given the points of all their missions
MISSION_CATEGORIES = {'Daily': 'Daily: {points} points a day', 'Weekly': 'Weekly: {points} points a week', 'Achievement': 'Achievements: {points} points total'}

#The currency of each region's product prices
PRICE_SIGNS = {'jp': '¥', 'gl': '₩'}

#Parcels the page shows as others: paid Pyroxenes (currency 2) as Pyroxenes (3), which the game tracks apart but treats alike
PARCEL_ALIASES = {('Currency', 2): ('Currency', 3)}


class BattlePassContext(NamedTuple):
    """The loaded game data and dictionaries."""
    data: BlueArchiveData
    battle_pass: dict[str, BlueArchiveBattlePassData]
    characters: dict[int, Character]
    items: dict[int, Item]
    furniture: dict[int, Furniture]
    emblems: dict[int, Emblem]

    def wiki_card(self, type: str, id: int, **params) -> str:
        return shared.functions.wiki_card(type, id, self.data, self.characters, self.items, self.furniture, self.emblems, **params)


env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))


def generate(ctx: BattlePassContext, outdir: str):
    seasons = sorted(ctx.battle_pass['jp'].info.values(), key=lambda x: x['SalePeriodFrom'])
    intro = mechanics(ctx, seasons[-1])
    for info in seasons:
        if mechanics(ctx, info) != intro: print(f"Season {info['Id']} works otherwise than the introduction, from season {seasons[-1]['Id']}, says: {mechanics(ctx, info)}")
        compare_regions(ctx, info)

    wikitext = env.get_template('templates/template_battle_pass.txt').render(
        launch = {region.upper(): wiki_date(min(x['SalePeriodFrom'] for x in bp.info.values())) for region, bp in ctx.battle_pass.items() if bp.info},
        intro = intro,
        seasons = [season(ctx, x) for x in seasons],
    )

    os.makedirs(os.path.join(outdir, 'shops'), exist_ok=True)
    with open(os.path.join(outdir, 'shops', 'Battle_Pass.txt'), 'w', encoding="utf8") as f:
        f.write(wikitext)


def mechanics(ctx: BattlePassContext, info: dict) -> dict:
    """What the page's introduction says of how a season's pass works."""
    goods = ctx.data.goods[info['PassLvUpGoodsID']]
    #The point limit's weeks: the first one starts with the season, the second when a week starts
    week = datetime.fromisoformat(ctx.battle_pass['jp'].exp_limits[info['Id']][1]['LimitStartTime'])
    return {
        'level_points': f"{info['NextLvNeedExp']:,}",
        'max_level': max(x['Level'] for x in ctx.battle_pass['jp'].levels[info['Id']]),
        'week_start': f"{week:%A}s at {week:%H:%M}",
        'level_price': ' '.join(f"{amount:,}{ctx.wiki_card(type, id, text=None)}" for type, id, amount in zip(goods['ConsumeParcelType'], goods['ConsumeParcelId'], goods['ConsumeParcelAmount'])),
        'bonus_levels': info['BuyPremiumLvUpAmount'],
    }


def compare_regions(ctx: BattlePassContext, info: dict):
    """The page shows the JP season but for its dates and offers: say if GL's differs."""
    gl = ctx.battle_pass['gl'].info.get(info['Id'])
    if gl and content(ctx.battle_pass['gl'], gl) != content(ctx.battle_pass['jp'], info):
        print(f"GL's season {info['Id']} differs from JP's, whose levels, rewards, missions and news ticker the page shows")


def content(battle_pass: BlueArchiveBattlePassData, info: dict) -> list:
    """What a region's season asks and gives, but for its dates and offers."""
    rules = [info[x] for x in ['NextLvNeedExp', 'PassLvUpGoodsID', 'BuyPremiumLvUpAmount', 'ExclusiveRewardID', 'ExclusiveEmblemID']]
    limits = [x['ExpLimitAmount'] for x in battle_pass.exp_limits[info['Id']]]
    tables = [battle_pass.levels[info['Id']], battle_pass.missions[info['Id']], battle_pass.flavor_text[info['FlavorTextGroupID']]]
    return [rules, limits, *tables, battle_pass.rewards[info['FreeRewardGroupID']], battle_pass.rewards[info['PurchaseRewardGroupID']]]


def season(ctx: BattlePassContext, info: dict) -> dict:
    """A season's section: its dates in each region, weekly point limit, title and exclusive reward, offers, missions, level rewards and news ticker."""
    jp = ctx.battle_pass['jp']
    free, paid = jp.rewards[info['FreeRewardGroupID']], jp.rewards[info['PurchaseRewardGroupID']]
    exclusive = next((x for x in free + paid if x['Id'] == info['ExclusiveRewardID']), None)
    return {
        'id': info['Id'],
        'periods': {region.upper(): sale_period(x.info.get(info['Id'])) for region, x in ctx.battle_pass.items()},
        'weekly_limit': weekly_limit(jp.exp_limits[info['Id']]),
        'title': ctx.wiki_card('Emblem', info['ExclusiveEmblemID']),
        'exclusive': exclusive and {'card': reward_card(ctx, exclusive), 'level': exclusive['Level']},
        'offers': offers(ctx, info),
        'missions': missions(ctx, jp.missions[info['Id']]),
        'levels': level_rewards(ctx, jp.levels[info['Id']], free, paid),
        'totals': [total_cards(ctx, free), total_cards(ctx, paid)],
        'ticker': ticker(ctx, jp.flavor_text[info['FlavorTextGroupID']]),
    }


def sale_period(info: dict|None) -> str:
    """When a region's season runs; N/A if the region lacks it."""
    return date_range(info['SalePeriodFrom'], info['SalePeriodTo']) if info else 'N/A'


def weekly_limit(limits: list[dict]) -> str:
    """The most points a week of the season can give, or each week's if they differ."""
    amounts = {x['ExpLimitAmount'] for x in limits}
    if len(amounts) == 1: return f"{amounts.pop():,}"
    return ', '.join(f"{x['ExpLimitAmount']:,} ({date_range(x['LimitStartTime'], x['LimitEndTime'])})" for x in limits)


def date_range(start: str, end: str) -> str:
    """A {{DateRange}} of two times of the data (UTC+9), which the wiki shows in the reader's time zone."""
    return f"{{{{DateRange|{shared.functions.format_datetime(start)}|{shared.functions.format_datetime(end)}}}}}"


def offers(ctx: BattlePassContext, info: dict) -> list[dict]:
    """The cells of the season's offers, priced in the currency of each region that has the season. The contents are JP's, and GL's
    too where they differ. A region's product is its first store's: the stores agree."""
    entries = []
    for column, (name, effects) in OFFERS.items():
        products = {region: x.products[x.info[info['Id']][column]][0] for region, x in ctx.battle_pass.items() if info['Id'] in x.info}
        jp, gl = products['jp'], products.get('gl')
        contents = [x.format(levels=info['BuyPremiumLvUpAmount']) for x in effects] + parcel_cards(ctx, jp)
        if gl and parcels(gl) != parcels(jp): contents.append(f"<small>GL: {' '.join(parcel_cards(ctx, gl))}</small>")
        entries.append({
            'name': name.format(name=offer_name(ctx, jp)),
            'product_id': jp['ProductId'],
            'contents': '<br>'.join(contents),
            'prices': {region.upper(): f"{PRICE_SIGNS[region]}{products[region]['Price']:,}" if region in products else 'N/A' for region in ctx.battle_pass},
        })

    return entries


def parcels(product: dict) -> list[tuple[str, int, int]]:
    return [parcel(*x) for x in zip(product['ParcelType'], product['ParcelId'], product['ParcelAmount'])]


def parcel(type: str, id: int, amount: int) -> tuple[str, int, int]:
    """A parcel as the page shows it (PARCEL_ALIASES)."""
    return (*PARCEL_ALIASES.get((type, id), (type, id)), amount)


def parcel_cards(ctx: BattlePassContext, product: dict) -> list[str]:
    return [parcel_card(ctx, *x) for x in parcels(product)]


def offer_name(ctx: BattlePassContext, product: dict) -> str:
    """The name of the product's cash shop row, in English if there is one. A product without one goes by its store product Id."""
    row = ctx.battle_pass['jp'].shop_cash.get(product['Id'], {})
    localized = ctx.data.etc_localization.get(row.get('LocalizeEtcId'))
    if localized is None:
        print(f"Product {product['Id']} has no name, using its store product Id {product['ProductId']}")
        return product['ProductId']

    return english(localized, missing_etc_localization, 'Name')


def missions(ctx: BattlePassContext, rows: list[dict]) -> dict[str, list[dict]]:
    """The season's missions and the points each gives, under the headings of their categories, in display order."""
    groups = {}
    for row in sorted(rows, key=lambda x: x['DisplayOrder']):
        if row['ViewFlag']: groups.setdefault(row['Category'], []).append(row)

    unlisted = set(groups) - set(MISSION_CATEGORIES)
    if unlisted: print(f"MISSION_CATEGORIES lists no categories {sorted(unlisted)}, their missions are left out")

    return {
        heading.format(points=f"{sum(x['BattlePassExpAmount'] for x in groups[category]):,}"): [{'text': mission_text(ctx, x), 'points': f"{x['BattlePassExpAmount']:,}"} for x in groups[category]]
        for category, heading in MISSION_CATEGORIES.items() if category in groups
    }


def mission_text(ctx: BattlePassContext, mission: dict) -> str:
    """The mission's description, in English if there is one, with its count filled in and the plurals agreeing with it."""
    count = mission['CompleteConditionCount']
    text = description_cleanup(english(ctx.data.localization[mission['Description']], missing_localization).replace('{0}', f"{count:,}"))
    return text.replace('(s)', 's' if count > 1 else '').replace(' 1 days', ' 1 day')


def level_rewards(ctx: BattlePassContext, levels: list[dict], *tracks: list[dict]) -> list[dict]:
    """A row per pass level: whether its rewards are pickups (the pass's featured ones), and the cards of its rewards on each track."""
    rows = []
    for level in sorted(levels, key=lambda x: x['Level']):
        cells = [' '.join(reward_card(ctx, x) for x in track if x['Level'] == level['Level']) for track in tracks]
        rows.append({'level': level['Level'], 'pickup': level['IsPickUpReward'], 'rewards': cells})

    return rows


def total_cards(ctx: BattlePassContext, track: list[dict]) -> str:
    """The cards of all a track gives, by parcel type and Id."""
    totals = {}
    for type, id, amount in map(reward_parcel, track):
        totals[(type, id)] = totals.get((type, id), 0) + amount

    return ''.join(parcel_card(ctx, type, id, amount, text=None, size='60px', block=True) for (type, id), amount in sorted(totals.items()))


def reward_card(ctx: BattlePassContext, reward: dict) -> str:
    return parcel_card(ctx, *reward_parcel(reward))


def reward_parcel(reward: dict) -> tuple[str, int, int]:
    return parcel(reward['RewardParcelType'], reward['RewardParcelUniqueId'], reward['RewardParcelAmount'])


def parcel_card(ctx: BattlePassContext, type: str, id: int, amount: int, **params) -> str:
    """A parcel's card. Student frames have no cards on the wiki, they go by name."""
    if type == 'StudentFrame':
        return f"Student frame: {english(ctx.data.etc_localization[ctx.data.student_frame[id]['LocalizeEtcId']], missing_etc_localization, 'Name')}"

    return ctx.wiki_card(type, id, quantity=amount if amount > 1 else None, **params)


def ticker(ctx: BattlePassContext, rows: list[dict]) -> list[dict]:
    """The season's news ticker headlines, in Japanese and English. The lines of a headline (TextGroup) show one after another (Sort).
    The Japanese is the JP data's own: the combined localization has GL's, an older text for the first season's ticker."""
    headlines = {}
    for row in sorted(rows, key=lambda x: (x['TextGroup'], x['Sort'])):
        headlines.setdefault(row['TextGroup'], []).append(row['LocalizeCodeId'])

    entries = []
    for keys in headlines.values():
        translated = [translation(ctx.data.localization[x], missing_localization) for x in keys]
        entries.append({'jp': '<br>'.join(ctx.battle_pass['jp'].localization[x]['Jp'] for x in keys), 'en': '<br>'.join(translated) if any(translated) else ''})

    return entries


def translation(localized: dict, missing: MissingTranslations, field: str = '') -> str:
    """A localization row's English text of the field (LocalizeEtcExcelTable has Name and Description, LocalizeExcelTable one text).
    A row without one goes to the missing translations dump."""
    if not localized.get(f"{field}En"): missing.add_entry(localized)
    return localized.get(f"{field}En", '')


def english(localized: dict, missing: MissingTranslations, field: str = '') -> str:
    """The row's translation(), or its Japanese if it has none."""
    return translation(localized, missing, field) or localized[f"{field}Jp"]


def wiki_date(time: str) -> str:
    return time[:10].replace('-', '/')


def init(args: dict) -> BattlePassContext:
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    return BattlePassContext(
        data = data,
        battle_pass = {'jp': load_battle_pass_data(args['data_primary']), 'gl': load_battle_pass_data(args['data_secondary'])},
        **build_standard_dictionaries(data)._asdict(),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')

    args = vars(parser.parse_args())
    print(args)

    ctx = init(args)
    generate(ctx, args['outdir'])
    missing_localization.write()
    missing_etc_localization.write()


if __name__ == '__main__':
    main()
