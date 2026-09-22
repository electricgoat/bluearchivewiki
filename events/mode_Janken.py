import copy

from classes.Stage import JankenStage
from classes.RewardParcel import RewardParcel
from events.common import EventContext, template_env, render_stage_tables
from events.missions import minigame_mission_tables

env = template_env()

#The minigame is named after the event it appears in, there is no localizable name for it in the game data
MINIGAME_NAMES = {
    860: 'Crab Martial Arts World Championship',
}

STAGE_TYPES = ['Story', 'Normal', 'Challenge']

HAND_LABELS = {'Rock': 'Rock', 'Scissor': 'Scissors', 'Paper': 'Paper'}


#Janken characters, skills and equipment are all named through LocalizeEtcExcelTable
def etc_localize(ctx: EventContext, localize_id: int):
    if localize_id == 0 or localize_id not in ctx.data.etc_localization:
        if localize_id != 0: print(f"Janken: missing etc localization key {localize_id}")
        return {'name': '', 'description': ''}

    entry = ctx.data.etc_localization[localize_id]
    if 'NameEn' not in entry: ctx.missing_etc_localization.add_entry(entry)

    description = entry.get('DescriptionEn') or entry.get('DescriptionJp') or ''
    #Enemy crabs have their description filled in with a placeholder
    if description.strip() == '(X)': description = ''

    return {
        'name': entry.get('NameEn') or entry.get('NameJp') or '',
        'description': description,
    }


#The character table is not tied to an event id, all crabs of all events are listed together
def parse_characters(ctx: EventContext):
    characters_janken = {}

    for character in ctx.data.minigame_janken_character.values():
        character = copy.copy(character)
        character['localize'] = etc_localize(ctx, character['LocalizeId'])
        character['owner'] = etc_localize(ctx, character['CharacterNameLocalizeId'])
        character['skill'] = None
        #Only playable crabs have a portrait icon, opponents are only drawn on the battle screen
        character['image'] = (character['IconResourceName'] or character['BattlePortraitResource']).rsplit('/', 1)[-1]
        character['image_battle'] = character['BattlePortraitResource'].rsplit('/', 1)[-1]

        if character['JankenSkill'] in ctx.data.minigame_janken_character_skill:
            skill = copy.copy(ctx.data.minigame_janken_character_skill[character['JankenSkill']])
            skill['localize'] = etc_localize(ctx, skill['LocalizeId'])
            skill['image'] = character['SkillIconResourceName'].rsplit('/', 1)[-1]
            character['skill'] = skill

        characters_janken[character['Id']] = character

    return characters_janken


def parse_equipment(ctx: EventContext, season_id: int):
    equipment = {}

    for item in ctx.data.minigame_janken_equipment.values():
        if item['EventContentId'] != season_id:
            continue

        item = copy.copy(item)
        item['localize'] = etc_localize(ctx, item['LocalizeId'])
        item['image'] = item['IconResourceName'].rsplit('/', 1)[-1]

        #The table holds one row per tier, they are grouped into a single piece of equipment with a list of tiers
        if item['EquipmentGroup'] not in equipment:
            equipment[item['EquipmentGroup']] = {
                'group': item['EquipmentGroup'],
                'localize': item['localize'],
                'image': item['image'],
                'unlock_stage': item['UnlockConditionStage'],
                'tiers': [],
            }
        equipment[item['EquipmentGroup']]['tiers'].append(item)

    for group in equipment.values():
        group['tiers'].sort(key=lambda x: x['Tier'])

    return equipment


def parse_stages(ctx: EventContext, season_id: int, janken_characters, equipment):
    stages = []
    equipment_by_id = {tier['Id']: tier for group in equipment.values() for tier in group['tiers']}

    for stage in ctx.data.minigame_janken_stage.values():
        if stage['EventContentId'] != season_id:
            continue

        stage = JankenStage.from_data(stage['Id'], ctx.data, wiki_card=ctx.wiki_card, missing_localization=ctx.missing_localization, missing_etc_localization=ctx.missing_etc_localization)

        stage.enemy = janken_characters.get(stage.enemy_id)
        if stage.enemy is None: print(f"Janken: stage {stage.id} opponent {stage.enemy_id} is not in the character table")

        #Story stages are played with a preset crab and equipment, later stage types let the player pick
        stage.echelon = [{
            'character': janken_characters.get(x['CharacterID']),
            'equipment': equipment_by_id.get(x['EquipMentID']),
        } for x in stage.fixed_echelon]

        stages.append(stage)

    stages.sort(key=lambda x: (STAGE_TYPES.index(x.difficulty) if x.difficulty in STAGE_TYPES else len(STAGE_TYPES), x.stage_number))

    return stages


#Opponents pick their hand out of a set of weighted probability profiles
def parse_enemy_ai(ctx: EventContext, ai_profile_id):
    profiles = []
    total_chance = sum(x['GroupChance'] for x in ctx.data.minigame_janken_character_ai.get(ai_profile_id, []))

    for profile in ctx.data.minigame_janken_character_ai.get(ai_profile_id, []):
        profiles.append({
            'id': profile['Id'],
            'hands': {label: profile[hand] / 100 for hand, label in HAND_LABELS.items()},
            'chance': total_chance > 0 and profile['GroupChance'] / total_chance * 100 or 0,
        })

    return profiles


def parse_score_rewards(ctx: EventContext, season_id: int):
    tiers = []
    total_rewards = {}

    reward_score = ctx.data.minigame_janken_reward_score.get(season_id)
    if reward_score is None: return tiers, total_rewards

    for i, reward_id in enumerate(reward_score['ScoreRewardId']):
        reward = ctx.data.minigame_janken_reward_score_item[reward_id]
        parcels = []

        for j, parcel_id in enumerate(reward['ParcelUniqueId']):
            parcel = RewardParcel(
                reward['ParcelType'][j],
                parcel_id,
                reward['Amount'][j],
                10000,
                None,
                wiki_card=ctx.wiki_card,
                data=ctx.data
            )
            parcels.append(parcel)

            if (parcel.parcel_type, parcel.parcel_id) not in total_rewards:
                total_rewards[(parcel.parcel_type, parcel.parcel_id)] = copy.copy(parcel)
            else:
                total_rewards[(parcel.parcel_type, parcel.parcel_id)].amount += parcel.amount

        tiers.append({
            'score': reward_score['StackedScore'][i],
            'parcels': parcels,
        })

    return tiers, total_rewards


def get_mode_janken(ctx: EventContext, season_id: int) -> str:
    data = ctx.data

    title = MINIGAME_NAMES.get(season_id, 'Rock-Paper-Scissors Minigame')
    wikitext = {'title': f"=={title}==", 'intro': '', 'characters': '', 'equipment': '', 'enemy_ai': '', 'stages': '', 'score_rewards': '', 'missions': ''}

    janken_info = data.minigame_janken_info.get(season_id)
    if janken_info is None:
        print(f"Janken: no MinigameJankenInfo data for event {season_id}")
        return ''

    janken_characters = parse_characters(ctx)
    equipment = parse_equipment(ctx, season_id)
    stages = parse_stages(ctx, season_id, janken_characters, equipment)

    wiki_play_cost = ctx.wiki_card(janken_info['CostParcelType'], janken_info['CostParcelId'])
    wiki_upgrade_cost = ctx.wiki_card(janken_info['CostParcelEquipUpgradeType'], janken_info['CostParcelEquipUpgradeId'])
    tier_up_costs = [janken_info[f'NeedItemAmountT{tier}'] for tier in range(2, janken_info['EquipmentMaxTier'] + 1)]

    template = env.get_template('template_janken_intro.txt')
    wikitext['intro'] = template.render(season_id=season_id, name=title, janken_info=janken_info, wiki_play_cost=wiki_play_cost, wiki_upgrade_cost=wiki_upgrade_cost, challenge_stages=[x for x in stages if x.difficulty == 'Challenge'])

    #Character ids are prefixed with the event id they belong to
    playable = [x for x in janken_characters.values() if x['IsPlayable'] and x['Id'] // 1000 == season_id]
    if not len(playable):
        print(f"Janken: no playable characters with an id prefixed by event {season_id}, listing all of them instead")
        playable = [x for x in janken_characters.values() if x['IsPlayable']]

    template = env.get_template('template_janken_characters.txt')
    wikitext['characters'] = template.render(characters=sorted(playable, key=lambda x: x['DisplayOrder']))

    template = env.get_template('template_janken_equipment.txt')
    wikitext['equipment'] = template.render(equipment=sorted(equipment.values(), key=lambda x: x['group']), max_tier=janken_info['EquipmentMaxTier'], wiki_upgrade_cost=wiki_upgrade_cost, tier_up_costs=tier_up_costs)

    #All opponents of an event are expected to share one AI profile group
    ai_profiles = sorted(set(janken_characters[x.enemy_id]['AiProfile'] for x in stages if x.enemy_id in janken_characters))
    if len(ai_profiles) > 1: print(f"Janken: opponents use more than one AI profile group ({ai_profiles}), only {ai_profiles[0]} is listed")

    if ai_profiles:
        template = env.get_template('template_janken_enemy_ai.txt')
        wikitext['enemy_ai'] = template.render(profiles=parse_enemy_ai(ctx, ai_profiles[0]), hands=list(HAND_LABELS.values()))

    wikitext['stages'] = render_stage_tables(env.get_template('template_janken_stages.txt'), stages, {x: x for x in STAGE_TYPES})

    score_reward_tiers, score_total_rewards = parse_score_rewards(ctx, season_id)
    if score_reward_tiers:
        template = env.get_template('template_janken_score_rewards.txt')
        wikitext['score_rewards'] = template.render(tiers=score_reward_tiers, total_rewards=score_total_rewards.values())

    if season_id in data.minigame_mission:
        wikitext['missions'] = minigame_mission_tables(ctx, season_id)

    return '\n'.join(wikitext.values())
