from classes.RewardParcel import RewardParcel
from events.common import EventContext, template_env

env = template_env()


def parse_rounds(ctx: EventContext, season_id: int) -> list[dict]:
    data = ctx.data

    rewards = {x['UniqueId']: dict(x) for x in data.minigame_roadpuzzle_reward.get(season_id, [])}
    for reward in rewards.values():
        reward['reward_parcels'] = [RewardParcel(parcel_type, parcel_id, amount, 10000, wiki_card=ctx.wiki_card)
                                    for parcel_type, parcel_id, amount in zip(reward['RewardParcelType'], reward['RewardParcelId'], reward['RewardParcelAmount'])]

    rounds = []
    for round in data.minigame_roadpuzzle_roadround:
        if round['EventContentId'] != season_id:
            continue

        #TODO figure out AdditionalRewardID, pointing to the event shop's rows didn't work
        round = dict(round)
        round['rewards'] = rewards.get(round['RoundReward'])
        round['wiki_additional_rewards'] = []
        rounds.append(round)

    return rounds


def get_mode_road(ctx: EventContext, season_id: int) -> str:
    title = 'Road Puzzle Minigame'
    wikitext = {'title':f"=={title}==", 'intro':'', 'rounds':'', 'maps':''}

    template = env.get_template('template_event_road_rounds.txt')
    wikitext['rounds'] = template.render(rounds=parse_rounds(ctx, season_id))

    return '\n'.join(wikitext.values())
