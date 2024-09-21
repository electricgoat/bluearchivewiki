import os
from jinja2 import Environment, FileSystemLoader

import shared.functions
from events.mission_desc import mission_desc
from classes.RewardParcel import RewardParcel
from collections import namedtuple

missing_localization = None
missing_code_localization = None
missing_etc_localization = None

data = {}
characters = {}
items = {}
furniture = {}
emblems = {}

total_rewards = {}
total_milestone_rewards = {}




def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)


def get_mode_fortunegachashop(season_id: int, ext_data, ext_characters, ext_items, ext_furniture, ext_emblems, ext_missing_localization, ext_missing_code_localization, ext_missing_etc_localization):
    global data, characters, items, furniture, emblems
    global missing_localization, missing_code_localization, missing_etc_localization
    data = ext_data
    characters = ext_characters
    items = ext_items
    furniture = ext_furniture
    emblems = ext_emblems
    missing_localization = ext_missing_localization
    missing_code_localization = ext_missing_code_localization
    missing_etc_localization = ext_missing_etc_localization

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.globals['len'] = len
    
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['nl2br'] = shared.functions.nl2br
    env.filters['nl2p'] = shared.functions.nl2p

    class FortuneTier:
        def __init__(self, wiki_title:str="", total_prob:int=0, total_modifier:int=0, total_mod_limit:int=0, entries:list=[]):
            self.wiki_title = wiki_title
            self.total_prob = total_prob
            self.total_modifier = total_modifier
            self.total_mod_limit = total_mod_limit
            self.entries = entries
    
    title = 'Omikuji'
    template = env.get_template('template_fortunegacha.txt')
    fortune_tiers = {
        5: FortuneTier('Great Blessing (大吉)', 0, 0, 0, []),
        4: FortuneTier('Blessing (吉)', 0, 0, 0, []),
        3: FortuneTier('Modest Blessing (中吉)', 0, 0, 0, []),
        2: FortuneTier('Small Blessing (小吉)', 0, 0, 0, []),
        1: FortuneTier('Future Blessing (末吉)', 0, 0, 0, []),
        0: FortuneTier('Misfortune (凶)', 0, 0, 0, []),
    }

    if season_id in [832, 10832]: 
        title = 'Cooking'
        template = env.get_template('template_fortunegacha_cooking.txt')
        fortune_tiers = {}

    wikitext = {'title':f"=={title}==", 'table':''}


    fortune_gacha = data.event_content_fortune_gacha_shop[season_id]
    
    for box in fortune_gacha:
        tier = box['Grade']
        if tier not in fortune_tiers:
            fortune_tiers[tier] = FortuneTier(f"Grade {tier}", 0, 0, 0, [])
        
        fortune_tiers[tier].total_prob += box['Prob']
        fortune_tiers[tier].total_modifier += box['ProbModifyValue']
        fortune_tiers[tier].total_mod_limit += box['ProbModifyLimit']

        fortune_gacha_group = data.event_content_fortune_gacha[box['FortuneGachaGroupId']]

        if data.etc_localization[fortune_gacha_group['LocalizeEtcId']].get('DescriptionEn', '') == '':
            missing_etc_localization.add_entry(data.etc_localization[fortune_gacha_group['LocalizeEtcId']])

        box['localization'] = data.etc_localization[fortune_gacha_group['LocalizeEtcId']]
        box['icon'] = fortune_gacha_group['IconPath'].rsplit('/',1)[-1]

        box['rewards'] = []
        for index,type in enumerate(box['RewardParcelType']):
            box['rewards'].append(RewardParcel(type, box['RewardParcelId'][index], box['RewardParcelAmount'][index], 10000, data=data, wiki_card=wiki_card))

        fortune_tiers[tier].entries.append(box)


    shop_params = data.event_content_fortune_gacha_modify[season_id][0]

    cost_good = data.goods[fortune_gacha[0]['CostGoodsId']]
    wiki_price = wiki_card('Item', cost_good['ConsumeParcelId'][0], quantity = cost_good['ConsumeParcelAmount'][0])

    wikitext['table'] = template.render(fortune_tiers=fortune_tiers.values(), shop_params = shop_params, wiki_price = wiki_price)
            
    return '\n'.join(wikitext.values())
