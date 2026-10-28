from classes.Stage import TankStage, DIFFICULTY
from events.common import EventContext, template_env, reward_types
from events.missions import minigame_mission_tables

env = template_env()

STAGE_TYPES = {'Racing': 'Race', 'Boss': 'Boss', 'Free': 'Free'}


def localized(ctx: EventContext, key: int) -> str:
    """The English text of a localization key, or the Japanese one until it has a translation."""
    text = ctx.data.localization.get(key, {})
    if text and 'En' not in text: ctx.missing_localization.add_entry(text)
    return text.get('En') or text.get('Jp', '')


def parse_tanks(ctx: EventContext, season_id: int, stages: dict[int, TankStage]) -> dict[int, dict]:
    """The event's tanks by group: a playable tank with a row for each upgrade level, or a boss or rival tank."""
    tanks = {}

    for row in ctx.data.minigame_tank_character[season_id]:
        if row['GroupId'] not in tanks:
            tanks[row['GroupId']] = {
                'name': localized(ctx, row['TankName']),
                'team': localized(ctx, row['TeamName']),
                'image': row['IconResourceName'],
                'unlock': stages.get(row['UnlockConditionStageId']),
                'playable': row['Playable'],
                'levels': [],
            }

        upgrade_cost = ctx.wiki_card(row['UpgradeItemParcelType'], row['UpgradeItemParcelId'], quantity=row['UpgradeItemAmount']) if row['UpgradeItemParcelType'] != 'None' else ''
        tanks[row['GroupId']]['levels'].append(dict(row) | {'upgrade_cost': upgrade_cost})

    return tanks


def unlock_stage(ctx: EventContext, season_id: int) -> str:
    """The event stage to clear to open the minigame."""
    season = ctx.season_data['jp'].event_content_season[(season_id, 'MiniGameTank')]
    stage = ctx.data.event_content_stages[season['EventCampaignStageId'][0]]
    return f"{DIFFICULTY[stage['StageDifficulty']]} {stage['StageNumber']}"


def get_mode_tank(ctx: EventContext, season_id: int) -> str:
    data = ctx.data

    title = 'Tank Racing Minigame'
    wikitext = {'title': f"=={title}==", 'intro': '', 'tanks': '', 'stages': '', 'missions': ''}

    rows = sorted(data.minigame_tank_stage[season_id], key=lambda x: x['StageNumber'])
    stages = {x['UniqueId']: TankStage.from_data(x, data, wiki_card=ctx.wiki_card, missing_localization=ctx.missing_localization) for x in rows}
    tanks = parse_tanks(ctx, season_id, stages)

    #A boss stage pits each tank against a boss, race stages have rival tanks cutting in
    characters = {x['UniqueId']: x for x in data.minigame_tank_character[season_id]}
    levels = {x['StageId']: x for x in data.minigame_tank_level[season_id]}
    for stage in stages.values():
        stage.bosses = [{'player': tanks[player], 'boss': tanks[boss]} for player, boss in stage.boss_entries.items()]
        if not stage.bosses: stage.rivals = [characters[x] for x in levels[stage.id]['RivalCharacterId']]

    costs = {(x['CostParcelType'], x['CostParcelId'], x['CostParcelAmount']) for x in rows if x['CostParcelType'] != 'None'}
    upgrade_items = {(x['UpgradeItemParcelType'], x['UpgradeItemParcelId']) for x in data.minigame_tank_character[season_id] if x['UpgradeItemParcelType'] != 'None'}
    time_limits = {x.battle_duration for x in stages.values()}

    template = env.get_template('template_tank_intro.txt')
    wikitext['intro'] = template.render(
        season_id=season_id,
        name=title,
        unlock_stage=unlock_stage(ctx, season_id),
        costs=[ctx.wiki_card(parcel_type, parcel_id, quantity=amount) for parcel_type, parcel_id, amount in sorted(costs)],
        upgrade_items=[ctx.wiki_card(parcel_type, parcel_id) for parcel_type, parcel_id in sorted(upgrade_items)],
        time_limit=f"{max(time_limits) // 60}:{max(time_limits) % 60:02}" if len(time_limits) == 1 else '',
        has_bosses=any(x.bosses for x in stages.values()),
        free_stages=[x for x in stages.values() if x.difficulty == 'Free'],
    )

    template = env.get_template('template_tank_characters.txt')
    wikitext['tanks'] = template.render(tanks=[x for x in tanks.values() if x['playable']])

    types = reward_types(list(stages.values()))
    template = env.get_template('template_tank_stages.txt')
    wikitext['stages'] = template.render(stages=stages.values(), stage_types=STAGE_TYPES, reward_types=types, rewardcols=len(types))

    if season_id in data.minigame_mission:
        wikitext['missions'] = minigame_mission_tables(ctx, season_id)

    return '\n'.join(wikitext.values())
