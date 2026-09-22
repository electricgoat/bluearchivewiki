"""
Missions and their rewards: the event's missions, its event point milestones, and the missions of its minigames.
"""
from events.common import EventContext, template_env
from events.mission_desc import mission_desc

env = template_env()

CARD_TYPES = {'Item': 'ItemCard', 'Furniture': 'FurnitureCard', 'Equipment': 'ItemCard', 'Currency': 'ItemCard', 'Emblem': 'TitleCard'}


def reward_name(ctx: EventContext, parcel_type: str, parcel_id: int) -> str|None:
    match parcel_type:
        case 'Item':
            return ctx.items[parcel_id].name_en
        case 'Furniture':
            return ctx.furniture[parcel_id].name_en
        case 'Equipment':
            return ctx.data.etc_localization[ctx.data.equipment[parcel_id]['LocalizeEtcId']]['NameEn']
        case 'Currency':
            return ctx.data.etc_localization[ctx.data.currencies[parcel_id]['LocalizeEtcId']]['NameEn']
        case 'Emblem':
            return ctx.emblems[parcel_id].name

    print(f"Unknown reward parcel type {parcel_type}")
    return None


def reward_cards(ctx: EventContext, parcel_types: list[str], parcel_ids: list[int], amounts: list[int]) -> list[str]:
    """The cards of a mission's rewards, in its row of the table. Rewards of unknown types are left out."""
    cards = []

    for parcel_type, parcel_id, amount in zip(parcel_types, parcel_ids, amounts):
        name = reward_name(ctx, parcel_type, parcel_id)
        if name is None: continue
        cards.append('{{TitleCard|'+name+'}}' if parcel_type == 'Emblem' else '{{'+CARD_TYPES[parcel_type]+'|'+name+'|quantity='+str(amount)+'}}')

    return cards


def add_to_totals(totals: dict, parcel_type: str, parcel_id: int, amount: int):
    totals[(parcel_type, parcel_id)] = totals.get((parcel_type, parcel_id), 0) + amount


def total_cards(ctx: EventContext, totals: dict, by_id: bool) -> list[dict]:
    """The cards of the totals, as the templates' total_rewards take them. Mission totals are listed by id, milestone totals by type."""
    cards = []

    for parcel_type, parcel_id in sorted(totals, key=lambda x: (x[1], x[0]) if by_id else x):
        amount = totals[(parcel_type, parcel_id)]
        name = reward_name(ctx, parcel_type, parcel_id)
        if name is None: card = ''
        elif parcel_type == 'Emblem': card = '{{TitleCard|'+name+'|60px|block|text=}}'
        else: card = '{{'+CARD_TYPES[parcel_type]+'|'+name+'|60px|block|quantity='+str(amount)+'|text=}}'
        cards.append({'Card': card})

    return cards


def parse_missions(ctx: EventContext, rows: list[dict], total_categories: list[str]) -> tuple[list[dict], dict]:
    """Copies of the mission rows with their descriptions and reward cards, and the reward totals of the missions of total_categories."""
    missions = []
    totals = {}

    for row in rows:
        mission = dict(row)
        mission_desc(mission, ctx.data, items=ctx.items, furniture=ctx.furniture)
        mission['RewardItemCards'] = reward_cards(ctx, mission['MissionRewardParcelType'], mission['MissionRewardParcelId'], mission['MissionRewardAmount'])
        missions.append(mission)

        if mission['Category'] in total_categories:
            for parcel_type, parcel_id, amount in zip(mission['MissionRewardParcelType'], mission['MissionRewardParcelId'], mission['MissionRewardAmount']):
                add_to_totals(totals, parcel_type, parcel_id, amount)

    return missions, totals


def event_mission_tables(ctx: EventContext, event_id: int, has_missions: bool) -> str:
    """The daily and achievement mission tables. Events without missions still render the (empty) template."""
    rows = [x for x in ctx.data.event_content_mission.values() if x['EventContentId'] == event_id] if has_missions else []
    missions, totals = parse_missions(ctx, rows, ['Achievement', 'EventAchievement'])

    return env.get_template('template_event_missions.txt').render(missions=missions, total_rewards=total_cards(ctx, totals, by_id=True))


def milestone_tables(ctx: EventContext, event_id: int) -> str:
    """The rewards for reaching amounts of event points, if the event has them."""
    milestones = []
    totals = {}

    for row in ctx.data.event_content_stage_total_rewards.values():
        if row['EventContentId'] != event_id: continue

        milestone = dict(row)
        milestone['DescriptionEn'] = f"Event Points: {row['RequiredEventItemAmount']}"
        milestone['RewardItemCards'] = reward_cards(ctx, row['RewardParcelType'], row['RewardParcelId'], row['RewardParcelAmount'])
        milestones.append(milestone)

        for parcel_type, parcel_id, amount in zip(row['RewardParcelType'], row['RewardParcelId'], row['RewardParcelAmount']):
            add_to_totals(totals, parcel_type, parcel_id, amount)

    if not milestones: return ''
    return env.get_template('template_event_milestones.txt').render(milestones=milestones, total_rewards=total_cards(ctx, totals, by_id=False))


def minigame_mission_tables(ctx: EventContext, season_id: int) -> str:
    missions, totals = parse_missions(ctx, ctx.data.minigame_mission[season_id], ['MiniGameEvent', 'MiniGameScore'])

    return env.get_template('template_minigame_missions.txt').render(missions=missions, total_rewards=total_cards(ctx, totals, by_id=True))
