from classes.RewardParcel import RewardParcel
from events.common import EventContext, template_env

env = template_env()

OMIKUJI_TIERS = {
    5: 'Great Blessing (大吉)',
    4: 'Blessing (吉)',
    3: 'Modest Blessing (中吉)',
    2: 'Small Blessing (小吉)',
    1: 'Future Blessing (末吉)',
    0: 'Misfortune (凶)',
}

#The cooking minigame uses the fortune gacha tables, with grades of its own
COOKING_SEASONS = [832, 10832]


class FortuneTier:
    def __init__(self, wiki_title: str):
        self.wiki_title = wiki_title
        self.total_prob = 0
        self.total_modifier = 0
        self.total_mod_limit = 0
        self.entries = []


def get_mode_fortunegachashop(ctx: EventContext, season_id: int) -> str:
    data = ctx.data

    if season_id in COOKING_SEASONS:
        title = 'Cooking'
        template = env.get_template('template_fortunegacha_cooking.txt')
        fortune_tiers = {}
    else:
        title = 'Omikuji'
        template = env.get_template('template_fortunegacha.txt')
        fortune_tiers = {grade: FortuneTier(name) for grade, name in OMIKUJI_TIERS.items()}

    wikitext = {'title':f"=={title}==", 'table':''}

    fortune_gacha = [dict(x) for x in data.event_content_fortune_gacha_shop[season_id]]
    for box in fortune_gacha:
        if box['Grade'] not in fortune_tiers:
            fortune_tiers[box['Grade']] = FortuneTier(f"Grade {box['Grade']}")

        tier = fortune_tiers[box['Grade']]
        tier.total_prob += box['Prob']
        tier.total_modifier += box['ProbModifyValue']
        tier.total_mod_limit += box['ProbModifyLimit']

        fortune_gacha_group = data.event_content_fortune_gacha[box['FortuneGachaGroupId']]
        localization = data.etc_localization[fortune_gacha_group['LocalizeEtcId']]
        if localization.get('DescriptionEn', '') == '':
            ctx.missing_etc_localization.add_entry(localization)

        box['localization'] = localization
        box['icon'] = fortune_gacha_group['IconPath'].rsplit('/',1)[-1]
        box['rewards'] = [RewardParcel(parcel_type, parcel_id, amount, 10000, data=data, wiki_card=ctx.wiki_card)
                          for parcel_type, parcel_id, amount in zip(box['RewardParcelType'], box['RewardParcelId'], box['RewardParcelAmount'])]

        tier.entries.append(box)

    cost_good = data.goods[fortune_gacha[0]['CostGoodsId']]
    wiki_price = ctx.wiki_card('Item', cost_good['ConsumeParcelId'][0], quantity = cost_good['ConsumeParcelAmount'][0])

    wikitext['table'] = template.render(fortune_tiers=fortune_tiers.values(), shop_params=data.event_content_fortune_gacha_modify[season_id][0], wiki_price=wiki_price)

    return '\n'.join(wikitext.values())
