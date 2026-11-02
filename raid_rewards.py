"""
The rewards pages of the raid modes' seasons, which raid.py makes for Total Assault, eliminate_raid.py for Grand Assault and multifloor_raid.py
for Limit Break Assault.
"""
import os
import json
import time
import difflib
import itertools
import collections

import wiki
import shared.functions

Mode = collections.namedtuple('Mode', 'name, type, suffix, keywords, section, aux, template')
TOTAL_ASSAULT = Mode('Total Assault', 'Raid', '', 'Raid,Total Assault,total war',
                     "==Rewards==\n{{RaidRewards}}", 'raid_rewards_aux.json', './raid/template_raid_rewards.txt')
GRAND_ASSAULT = Mode('Grand Assault', 'Elimination', ' (Grand Assault)', 'Elimination Raid,Grand Assault',
                     "==Rewards==\n{{RaidRewards|Type=Elimination}}", 'eliminate_raid_rewards_aux.json', './raid/template_raid_rewards.txt')
LIMIT_BREAK = Mode('Limit Break Assault', 'Limit Break', ' (Limit Break Raid)', 'Limit Break Raid,Limit Break Assault,multifloor,tower',
                   "===Stats===\n{{RaidRewards|Type=Limit Break}}", 'multifloor_raid_rewards_aux.json', './raid/template_multifloor_raid_rewards.txt')

#The regions of the Global version, in the order of their columns on a page: what the ranks of each are named after RankStart and RankEnd in Global's
#ranking reward tables, and its name
GLOBAL_REGIONS = {'Na': 'North America', 'Global': 'Europe', 'Asia': 'Asia', 'Tw': 'TW/HK', '': 'Korea'}

#The boss's stats a Limit Break Assault page lists for each floor
FLOOR_STATS = ['MaxHP100', 'AttackPower100', 'DefensePower100', 'CriticalResistPoint', 'CriticalDamageResistRate', 'GroggyGauge']



def raid_page(mode, raid):
    return raid.name + mode.suffix



def ranks(start, end):
    return f"{start}~{end or '∞'}"



def date_range(season):
    return f"{{{{DateRange|{shared.functions.format_datetime(season['SeasonStartData'])}|{shared.functions.format_datetime(season['SeasonEndData'])}}}}}"



def rewards_page(mode, season):
    """The season's rewards page. JP's two beta seasons of a mode both go by season 0, so their pages name the raid as well."""
    return f"{mode.name}/Season {season['SeasonDisplay']} rewards" + (f" ({season['raid'].shortname})" if season['SeasonDisplay'] == 0 else '')



def seasons_as_ran(mode, seasons, translation):
    """The seasons with the rewards they ran with, where the mode's aux file keeps those: the game data rewrites past seasons."""
    with open(os.path.join(translation, mode.aux), encoding="utf8") as f:
        aux = {x['SeasonId']: x for x in json.load(f)['jp']}

    print (f"Rewards of seasons {', '.join(str(x['SeasonId']) for x in seasons if x['SeasonId'] in aux)} are those of {mode.aux}")
    return [x | aux.get(x['SeasonId'], {}) for x in seasons]



def global_seasons(seasons, seasons_gl, ranking_rewards_gl={}):
    """Gives each JP season its Global season, as season['global']: the one of the same raid, environment and Limit Break armor where the two
    servers' seasons come in the same order (all of Grand Assault's and Limit Break Assault's; Total Assault's from season 50 on, and most before).
    A season Global hasn't had yet, or not in JP's order, gets None. A Global season of a mode with ranking rewards gets its ranking brackets,
    each as its ranks in each of GLOBAL_REGIONS."""
    key = lambda x: (x['raid'], x['env'], x.get('challenge'))
    blocks = difflib.SequenceMatcher(None, [key(x) for x in seasons], [key(x) for x in seasons_gl], autojunk=False).get_matching_blocks()
    pairs = {seasons[block.a + i]['SeasonId']: seasons_gl[block.b + i] for block in blocks for i in range(block.size)}

    for season in pairs.values() if ranking_rewards_gl else []:
        #The table has a group's brackets twice where it has two sets of rewards for the group
        rows = ranking_rewards_gl[season['RankingRewardGroupId']]
        season['brackets'] = list(dict.fromkeys(tuple(ranks(x[f"RankStart{region}"], x[f"RankEnd{region}"]) for region in GLOBAL_REGIONS) for x in rows))

    return [x | {'global': pairs.get(x['SeasonId'])} for x in seasons]



def total(parcels):
    """What the parcels give in all, as parcels in the order the wiki lists rewards in."""
    amounts = {}
    for type, id, amount in parcels:
        amounts[(type, id)] = amounts.get((type, id), 0) + amount

    return [(type, id, amounts[(type, id)]) for type, id in sorted(amounts, key=lambda x: shared.functions.item_sort_order({'parcel_type': x[0], 'parcel_id': x[1]}))]



def season_rewards(season, ranking_rewards, score_rewards, wiki_card):
    """What the season's rewards page shows: the cards of its ranking brackets, of its score milestones, and of all the milestones give.
    The rows are those of the mode's tables, or the season's own if it is one of seasons_as_ran.
    A bracket has its ranks on JP and in Global's regions, if the season's Global season has as many brackets: those give the same rewards."""
    ranking = season.get('RankingReward') or ranking_rewards[season['RankingRewardGroupId']]
    milestones = season.get('SeasonReward') or [score_rewards[x] for x in season['SeasonRewardId']]
    parcels = [list(zip(x['SeasonRewardParcelType'], x['SeasonRewardParcelUniqueId'], x['SeasonRewardAmount'])) for x in milestones]

    brackets_gl = season['global']['brackets'] if season['global'] else []
    if len(brackets_gl) != len(ranking):
        if season['global']: print (f"Season {season['SeasonId']} has {len(ranking)} ranking brackets, its Global season {len(brackets_gl)}: its page lists JP's alone")
        brackets_gl = []

    def card(type, id, amount, **params):
        #The wiki's furniture pages, which ba-cafe names, say Outdoor where the Global version says Field: "Binah Gold Trophy - Outdoor Warfare"
        text = wiki_card(type, id, quantity=amount, text='', **params)
        return text.replace('Field', 'Outdoor') if type == 'Furniture' else text

    return {
        'regions': list(GLOBAL_REGIONS.values()) if brackets_gl else [],
        'ranking': [{
            'ranks': ranks(x['RankStart'], x['RankEnd']),
            'ranks_gl': ranks_gl,
            'cards': [card(type, id, amount, size='60px', block=True) for type, id, amount in zip(x['RewardParcelType'], x['RewardParcelUniqueId'], x['RewardParcelAmount'])],
        } for x, ranks_gl in zip(ranking, brackets_gl or [()] * len(ranking))],
        'milestones': [{
            'score': score,
            'cards': [card(type, id, amount) for type, id, amount in x],
        } for score, x in zip(season['StackedSeasonRewardGauge'], parcels)],
        'total': [card(type, id, amount, size='60px', block=True) for type, id, amount in total(sum(parcels, []))],
    }



def floors(group, data):
    """The floors of a Limit Break Assault boss group, each as a season's page lists it: the floor to clear before it (0 if none), the boss's
    level, types and stats there, and what clearing it gives. data has the group's tables as data.py's load_data names them."""
    stages = data.multi_floor_raid_stage[group]
    floor_of = {x['Id']: x['Difficulty'] for x in stages}
    rows = []

    for stage in stages:
        boss = stage['RaidCharacterId']
        changes = [x for x in data.multi_floor_raid_stat_change.values() if x['StatChangeId'] in stage['StatChangeId'] and boss in x['ApplyCharacterId']]

        def stat(name):
            #A floor's stat is the boss's own with the floor's changes of it: added to, then multiplied (in 1/10000)
            changed = [(x['StatAdd'][i], x['StatMultiply'][i]) for x in changes for i, type in enumerate(x['StatType']) if type == name.replace('100', '')]
            base = data.characters_stats[boss][name]
            return round((base + sum(x[0] for x in changed)) * (1 + sum(x[1] for x in changed) / 10000)) if changed else base

        rows.append({
            'Difficulty': stage['Difficulty'], 'OpenCondition': floor_of.get(stage['StageOpenCondition'], 0), 'LevelBoss': data.ground[stage['GroundId']]['LevelBoss'],
            'BulletType': data.characters[boss]['BulletType'], 'ArmorType': data.characters[boss]['ArmorType'],
            **{x: stat(x) for x in FLOOR_STATS},
            'ClearReward': [[x['ClearStageRewardParcelType'], x['ClearStageRewardParcelUniqueID'], x['ClearStageRewardAmount']] for x in data.multi_floor_raid_reward[stage['RewardGroupId']]],
        })

    return rows



def floor_rewards(floors, wiki_card):
    """What a Limit Break Assault season's page shows: its floors in brackets, the floors that open together, each floor with the cards of its
    clear rewards and each bracket with those of what its floors give in all."""
    brackets = [list(x) for _, x in itertools.groupby(floors, key=lambda x: x['OpenCondition'])]

    return [{
        'floors': ranks(rows[0]['Difficulty'], rows[-1]['Difficulty']),
        'rows': [x | {'cards': [wiki_card(type, id, quantity=amount, text='') for type, id, amount in x['ClearReward']]} for x in rows],
        'cards': [wiki_card(type, id, quantity=amount, text='', size='60px', block=True) for type, id, amount in total(sum([x['ClearReward'] for x in rows], []))],
    } for rows in brackets]



def rewards_pages(mode, seasons, rewards, env):
    """The wikitext of the seasons' rewards pages, by SeasonId. rewards has the season_rewards of each, or its floor_rewards."""
    template = env.get_template(mode.template)
    wikitexts = {}

    for season in seasons:
        #Seasons of a raid with the same rewards share a tab on its page: each names the first of them
        first = next(x for x in seasons if x['raid'] == season['raid'] and rewards[x['SeasonId']] == rewards[season['SeasonId']])
        wikitexts[season['SeasonId']] = template.render(
            mode=mode, info=season['raid'], season=season, raid_page=raid_page(mode, season['raid']), rewards_season=first['SeasonDisplay'], page=rewards_page(mode, season),
            period=date_range(season), period_gl=season['global'] and date_range(season['global']), rewards=rewards[season['SeasonId']],
        ).strip()

    return wikitexts



def publish(mode, seasons, wikitexts, args):
    """Publishes the rewards pages of the chosen seasons: the current and previous ones of each server unless told otherwise (-all_seasons,
    -season_id), since the game data of a past season may have changed since it ran. Global's are the ones whose pages get its dates and brackets now.
    A published page stores itself in the raid_rewards bucket, from which the mode's section of its raid's page makes its tabs.
    That page needs a purge to show what the bucket has got: Bucket doesn't refresh the pages that read it."""
    if args['all_seasons']: chosen = seasons
    elif args['season_id']: chosen = [x for x in seasons if x['SeasonId'] in args['season_id']]
    else: chosen = [x for x in seasons if x in seasons[-2:] + [y for y in seasons if y['global']][-2:]]

    published = {}
    for season in chosen:
        page, wikitext = rewards_page(mode, season), wikitexts[season['SeasonId']]
        if not wiki.page_exists(page, wikitext):
            print (f"Publishing {page}")
            wiki.publish(page, wikitext, 'Generated raid rewards page')
            published[page] = season['raid']

    if published:
        await_rows(published)
        wiki.purge_all([raid_page(mode, x) for x in dict.fromkeys(published.values())], forcelinkupdate=True)



def await_rows(pages):
    """Waits for the published pages to be in the raid_rewards bucket: Bucket stores a page's rows once its save has answered."""
    for delay in [0, 2, 5, 10, 20]:
        time.sleep(delay)
        missing = set(pages) - {x['page_name'] for x in wiki.bucket("bucket('raid_rewards').select('page_name').limit(5000).run()")}
        if not missing: return

    print (f"The raid_rewards bucket hasn't got {', '.join(sorted(missing))} yet: purge their raids' pages later for the tabs to show")
