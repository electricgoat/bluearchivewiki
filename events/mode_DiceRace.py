import copy

from classes.RewardParcel import RewardParcel
from events.common import EventContext, template_env

env = template_env()


def get_mode_dicerace(ctx: EventContext, season_id: int) -> str:
    data = ctx.data
    dice_race = data.event_content_dice_race[season_id]

    title = 'Dice Race'
    wikitext = {'title':f"\n=={title}==", 'intro':'', 'lap_rewards':'===Lap Completion Rewards===\n', }

    good = data.goods[dice_race['DiceCostGoodsId']]
    dice_cost_wiki_card = ctx.wiki_card(good['ConsumeParcelType'][0], good['ConsumeParcelId'][0], quantity = good['ConsumeParcelAmount'][0])

    lap_reward_data = [dict(x) for x in data.event_content_dice_race_total_reward[season_id]]
    total_lap_rewards = {}

    for lap_reward in lap_reward_data:
        lap_reward['parcels'] = []
        for parcel_type, parcel_id, amount in zip(lap_reward['RewardParcelType'], lap_reward['RewardParcelId'], lap_reward['RewardParcelAmount']):
            parcel = RewardParcel(parcel_type, parcel_id, amount, 10000, None, wiki_card=ctx.wiki_card, data=data)
            lap_reward['parcels'].append(parcel)

            if parcel_id not in total_lap_rewards:
                total_lap_rewards[parcel_id] = copy.copy(parcel)
            else:
                total_lap_rewards[parcel_id].amount += parcel.amount

    template = env.get_template('template_dicerace_intro.txt')
    wikitext['intro'] += template.render(season_id=season_id, die_cost=dice_cost_wiki_card, event_info=dice_race, nodes=data.event_content_dice_race_node[season_id])

    template = env.get_template('template_dicerace_lap_rewards.txt')
    wikitext['lap_rewards'] += template.render(lap_reward_data=lap_reward_data, total_rewards=total_lap_rewards)

    return '\n'.join(wikitext.values())
