"""
The event's shops: the exchange or mini shop, the supply boxes, and the card draw.
"""
import re

from events.common import EventContext, template_env

env = template_env()

#Both content types list the same shop info rows, only the title differs
SHOP_TITLES = {'Shop': 'Exchange Shop', 'MiniShop': 'Mini Shop'}


def parse_shops(ctx: EventContext, event_id: int) -> list[dict]:
    """Copies of the event's shop info rows, with their currency and goods. Shops without a cost parcel type are left out."""
    shops = []

    for row in ctx.data.event_content_shop_info[event_id]:
        if len(row['CostParcelType']) == 0:
            print(f"Shop {row['CategoryType']} has no cost parcel type, skipping")
            continue

        shop = dict(row)
        if shop['CostParcelType'][0] == 'Item':
            shop['wiki_currency_name'] = ctx.items[shop['CostParcelId'][0]].name_en
        elif shop['CostParcelType'][0] == 'Currency':
            shop['wiki_currency_name'] = ctx.data.etc_localization[ctx.data.currencies[shop['CostParcelId'][0]]['LocalizeEtcId']]['NameEn']
        else:
            print(f"Unknown shop currency type for {shop}")

        shop['wiki_currency'] = f"{{{{ItemCard|{shop['wiki_currency_name']}}}}}"
        shop['wiki_title'] = f"{{{{ItemCard|{shop['wiki_currency_name']}|48px}}}}"
        shop['total_cost'] = 0
        shop['shop_content'] = [dict(x) for x in ctx.data.event_content_shop[event_id] if x['CategoryType'] == shop['CategoryType']]

        for shop_item in shop['shop_content']:
            good = ctx.data.goods[shop_item['GoodsId'][0]]
            reward_quantity = good['ParcelAmount'][0]
            limit = shop_item['PurchaseCountLimit']
            shop_item['wiki_card'] = ctx.wiki_card(good['ParcelType'][0], good['ParcelId'][0], quantity = reward_quantity > 1 and reward_quantity or None)
            shop_item['cost'] = good['ConsumeParcelAmount'][0]
            shop_item['stock'] = limit if limit > 0 else '∞'
            shop_item['subtotal'] = shop_item['cost'] * limit if limit > 0 else ''

            if limit > 0: shop['total_cost'] += shop_item['cost'] * limit

        shops.append(shop)

    return shops


def shop_tables(shops: list[dict], title: str) -> str:
    template = env.get_template('template_shop.txt')
    return f'=={title}==\n<div style="display: flex; flex-flow: row wrap; align-items: flex-start; gap: 4px;">\n' + ''.join(template.render(shop=x) for x in shops) + '</div>\n'


def box_gacha(ctx: EventContext, event_id: int) -> str:
    """A tab for each supply box, boxes with the same contents as an earlier one sharing its tab."""
    boxes = [dict(x) for x in ctx.data.event_content_box_gacha_manage[event_id]]

    for box in boxes:
        box['wiki_title'] = f"Box {box['Round']}{box['IsLoop']==True and '+' or ''}"
        box['Items'] = [{'GroupId': x['GroupId'], 'GroupElementAmount': x['GroupElementAmount'], 'IsPrize': x['IsPrize'], 'GoodsId': x['GoodsId'], 'DisplayOrder': x['DisplayOrder']} for x in ctx.data.event_content_box_gacha_shop[event_id] if x['Round'] == box['Round']]

        first_good = ctx.data.goods[box['Items'][0]['GoodsId'][0]]
        box['wiki_price'] = ctx.wiki_card(first_good['ConsumeParcelType'][0], first_good['ConsumeParcelId'][0], quantity = first_good['ConsumeParcelAmount'][0])
        box['total_stock'] = 0
        box['is_duplicate'] = False

        for box_item in box['Items']:
            good = ctx.data.goods[box_item['GoodsId'][0]]
            reward_quantity = good['ParcelAmount'][0]
            box_item['wiki_card'] = ctx.wiki_card(good['ParcelType'][0], good['ParcelId'][0], quantity = reward_quantity > 1 and reward_quantity or None)
            box['total_stock'] += box_item['GroupElementAmount']

        box['total_price'] = box['total_stock'] * first_good['ConsumeParcelAmount'][0]

    for index, box in enumerate(boxes):
        if index < 2: continue

        for earlier in boxes[:index]:
            if box['Items'] == earlier['Items']:
                box['is_duplicate'] = True
                earlier['wiki_title'] += f"/{box['Round']}"

    template = env.get_template('template_boxgacha.txt')
    wikitext = '==Supply Box==\n<tabber>\n' + ''.join(template.render(box=x) for x in boxes if not x['is_duplicate'])
    return wikitext.rstrip('|-|\n') + '</tabber>\n'


def card_shop(ctx: EventContext, event_id: int, shops: list[dict]) -> str:
    """The card draw: sets of 4 cards, each giving the rewards on it."""
    card_groups = ctx.data.event_content_card
    card_shop = ctx.data.event_content_card_shop[event_id]
    card_tiers = sorted(set([x['Rarity'] for x in card_shop]), key=lambda x: ('SSR', 'SR', 'R', 'N').index(x))

    #RefreshGroups are expected to be [1, 2, 3, 4], with 1~3 being complete duplicates and 4 being the SR+ rarity one.
    card_set = [dict(x) for x in card_shop if x['RefreshGroup'] == 1]
    for index, card in enumerate(card_set):
        #IconPath strings are lowercase while the actual resource names are capitalized
        card['image'] = '_'.join(word.upper() if word.lower() in ['sr', 'ssr'] else word.capitalize() for word in re.split(r'[_ ]', card_groups[card["CardGroupId"]]['IconPath'].rsplit('/', 1)[-1]))
        card['wiki_image_rowspan'] = 1

        card['LocalizeEtcId'] = card_groups[card["CardGroupId"]]['LocalizeEtcId']
        card['name'] = ctx.data.etc_localization[card['LocalizeEtcId']]['NameJp'].capitalize()

        #Cards of the same group share one image cell
        while card['CardGroupId'] == card_set[index-1]['CardGroupId']:
            card['image'] = None
            card_set[index-1]['wiki_image_rowspan'] += 1
            index -= 1

        card['wiki_items'] = [ctx.wiki_card(parcel_type, parcel_id, quantity = amount, text = None, size = '60px', block = True)
                              for parcel_type, parcel_id, amount in zip(card['RewardParcelType'], card['RewardParcelId'], card['RewardParcelAmount'])]

    cardshop_data = {tier: {'total_prob':0} for tier in card_tiers}
    for card in card_set:
        cardshop_data[card['Rarity']]['total_prob'] += card['Prob']

    cost_good = ctx.data.goods[card_set[0]['CostGoodsId']]
    wiki_price = ctx.wiki_card('Item', cost_good['ConsumeParcelId'][0], quantity = cost_good['ConsumeParcelAmount'][0])

    if len(cost_good['ConsumeExtraAmount'])>1 and cost_good['ConsumeExtraAmount'][0] != cost_good['ConsumeExtraAmount'][1]:
        pricing_structure = f"Revealing the first card will cost {wiki_price}, and the price will increase by {cost_good['ConsumeExtraAmount'][1]-cost_good['ConsumeExtraAmount'][0]} for any subsequent card after it ({cost_good['ConsumeExtraAmount'][0]}, {cost_good['ConsumeExtraAmount'][1]}, {cost_good['ConsumeExtraAmount'][2]}, and finally {cost_good['ConsumeExtraAmount'][3]}); player can reset the hand at any point instead of revealing the next card, resetting the cost."
    else:
        pricing_structure = f"Revealing each card will cost {wiki_price}; player can reset the hand at any point instead of revealing the next card."

    guaranteed_currency_shop = {x['CategoryType']: x for x in shops}.get('EventContent_2')
    return env.get_template('template_cardshop.txt').render(card_set=card_set, cardshop_data=cardshop_data, card_tiers=card_tiers, wiki_price=wiki_price, shop_guaranteed_currency=guaranteed_currency_shop and guaranteed_currency_shop['wiki_currency'] or None, pricing_structure=pricing_structure)
