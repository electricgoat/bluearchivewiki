"""
Keeps the rewards of the raid seasons as they ran, where the game data shows them otherwise now: translation/raid_rewards_aux.json
for Total Assault, translation/eliminate_raid_rewards_aux.json for Grand Assault, translation/multifloor_raid_rewards_aux.json
for Limit Break Assault.

python raid_history.py [-data_primary DIR] [-translation DIR]
"""
import os
import re
import sys
import json
import argparse
import functools
import subprocess
import collections
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

from data import load_generic
import raid_seasons
import eliminate_raid_seasons
import multifloor_raid_seasons
import raid_rewards
from raid_rewards import TOTAL_ASSAULT, GRAND_ASSAULT, LIMIT_BREAK

#What a season's rewards page shows of the reward tables' rows
RANKING_FIELDS = ['RankStart', 'RankEnd', 'RewardParcelType', 'RewardParcelUniqueId', 'RewardParcelAmount']
SCORE_FIELDS = ['SeasonRewardParcelType', 'SeasonRewardParcelUniqueId', 'SeasonRewardAmount']

JST = timezone(timedelta(hours=9))

#The versions up to v1.12 were imported on 2021-12-05, so they go by the patch day their tags carry (MMDD, from v1.4 on) instead of their commit time.
#The patches before v1.4 go by the day of the update they belong to. The undated rest is skipped: the pre-launch v0.22, and the client's own tables
#of v1.0, v1.1 and v1.2, which are older than the patches before them
IMPORTED = datetime(2021, 12, 6)
EARLY_VERSIONS = {
    'v1.0.78359-m28_1_0_1_mashiro3': '2021-02-04',
    'v1.1.79928-m28_1_1_1':          '2021-02-25',
    'v1.2.81489-m29_1_2_0':          '2021-03-11',
    'v1.2.81489-m29_1_2_0_izuna':    '2021-03-11',
    'v1.2.81489-m29_1_2_2':          '2021-03-11',
    'v1.2.81489-m29_1_2_3':          '2021-03-11',
    'v1.3.85633-m30_1_3_0':          '2021-03-25',
    'v1.3.85633-m30_1_3_1':          '2021-03-25',
}


def git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(['git', '-C', repo, *args], capture_output=True, encoding='utf8')


def version_time(tag: str, committed: datetime) -> datetime|None:
    """When a data version came out (UTC+9); None for the versions to skip."""
    if committed >= IMPORTED: return committed
    if tag in EARLY_VERSIONS: return datetime.fromisoformat(EARLY_VERSIONS[tag])

    day = re.search(r'_(\d\d)(\d\d)(_|$)', tag)
    return datetime(2021, int(day[1]), int(day[2])) if day else None


def table(repo: str, commit: str, name: str) -> list[dict]:
    """A table of a data version, from DB/ if the version has it there, as data.py reads the tables."""
    for folder in ['DB', 'Excel']:
        show = git(repo, 'show', f"{commit}:{folder}/{name}")
        if show.returncode == 0: return json.loads(show.stdout)['DataList']
    return []


def history(repo: str, names: list[str]) -> list[dict]:
    """The data versions that changed one of a mode's tables, oldest first: when each came out, its tag and its commit."""
    versions = []
    paths = [f"{folder}/{name}" for folder in ['DB', 'Excel'] for name in names]

    for line in git(repo, 'log', '--reverse', '--format=%H %ct %s', '--', *paths).stdout.splitlines():
        commit, committed, tag = line.split(' ', 2)
        time = version_time(tag, datetime.fromtimestamp(int(committed), JST).replace(tzinfo=None))
        if time is not None: versions.append({'time': time, 'tag': tag, 'commit': commit})

    return versions


def grouped(rows: list[dict], key: str) -> dict:
    groups = collections.defaultdict(list)
    for row in rows: groups[row[key]].append(row)
    return dict(groups)


def ranking_tables(seasons, score_rewards, ranking_rewards) -> SimpleNamespace:
    """The rows of Total Assault's or Grand Assault's tables, as data.py keys them."""
    return SimpleNamespace(
        seasons={x['SeasonId']: x for x in seasons},
        score_rewards={x['SeasonRewardId']: x for x in score_rewards}, ranking_rewards=grouped(ranking_rewards, 'RankingRewardGroupId'),
    )


def floor_tables(seasons, stages, rewards, stat_changes, stats, characters, grounds) -> SimpleNamespace:
    """The rows of Limit Break Assault's tables, as data.py names and keys them; of the characters and grounds, only those of its floors."""
    bosses, grounds_used = {x['RaidCharacterId'] for x in stages}, {x['GroundId'] for x in stages}
    return SimpleNamespace(
        seasons={x['SeasonId']: x for x in seasons},
        multi_floor_raid_stage=grouped(stages, 'BossGroupId'), multi_floor_raid_reward=grouped(rewards, 'RewardGroupId'),
        multi_floor_raid_stat_change={x['StatChangeId']: x for x in stat_changes},
        characters_stats={x['CharacterId']: x for x in stats if x['CharacterId'] in bosses},
        characters={x['Id']: x for x in characters if x['Id'] in bosses},
        ground={x['Id']: x for x in grounds if x['Id'] in grounds_used},
    )


def ranking_rewards(season: dict, tables: SimpleNamespace) -> dict:
    """What a season's rewards page shows of a version's tables: its score milestones, its ranking brackets and what each of them gives."""
    return {
        'StackedSeasonRewardGauge': season['StackedSeasonRewardGauge'],
        'RankingReward': [{x: row[x] for x in RANKING_FIELDS} for row in tables.ranking_rewards[season['RankingRewardGroupId']]],
        'SeasonReward': [{x: tables.score_rewards[id][x] for x in SCORE_FIELDS} for id in season['SeasonRewardId']],
    }


def floor_rewards(season: dict, tables: SimpleNamespace) -> dict:
    """What a Limit Break Assault season's page shows of a version's tables: the floors of its boss."""
    return {'Floors': raid_rewards.floors(season['OpenRaidBossGroupId'], tables)}


#A raid mode's tables; what keys their rows; what lists its seasons; when a season's rewards were last given; and what its page shows of the tables
History = collections.namedtuple('History', 'names, keyed, seasons, until, rewards')
MODES = {
    TOTAL_ASSAULT: History(
        ['RaidSeasonManageExcelTable.json', 'RaidStageSeasonRewardExcelTable.json', 'RaidRankingRewardExcelTable.json'],
        ranking_tables, lambda tables: raid_seasons.prepare_seasons(tables.seasons, 'jp'), 'SettlementEndDate', ranking_rewards),
    GRAND_ASSAULT: History(
        ['EliminateRaidSeasonManageExcelTable.json', 'EliminateRaidStageSeasonRewardExcelTable.json', 'EliminateRaidRankingRewardExcelTable.json'],
        ranking_tables, lambda tables: eliminate_raid_seasons.prepare_seasons(tables.seasons, 'jp'), 'SettlementEndDate', ranking_rewards),
    LIMIT_BREAK: History(
        ['MultiFloorRaidSeasonManageExcelTable.json', 'MultiFloorRaidStageExcelTable.json', 'MultiFloorRaidRewardExcelTable.json', 'MultiFloorRaidStatChangeExcelTable.json',
         'CharacterStatExcelTable.json', 'CharacterExcelTable.json', 'GroundExcelTable.json'],
        floor_tables, lambda tables: multifloor_raid_seasons.prepare_seasons(tables.seasons, 'jp', tables), 'SeasonEndDate', floor_rewards),
}


@functools.cache
def tables(repo: str, commit: str, mode: raid_rewards.Mode) -> SimpleNamespace:
    """A mode's tables as a data version had them."""
    return MODES[mode].keyed(*[table(repo, commit, name) for name in MODES[mode].names])


def difference(key: str, then: list, now: list) -> str:
    """How a season's rewards as it ran differ from what the game data has now."""
    changed = sum(a != b for a, b in zip(then, now)) + abs(len(then) - len(now))
    match key:
        case 'StackedSeasonRewardGauge':
            return f"score milestones up to {then[-1]:,}, now {now[-1]:,}"
        case 'RankingReward':
            return "other ranking rewards" if len(then) == len(now) else f"ranking rewards in {len(then)} brackets, now {len(now)}"
        case 'SeasonReward':
            return f"other rewards for {changed} of {len(then)} milestones"
        case _:
            return f"other boss stats or rewards on {changed} of {len(then)} floors"


def aux_json(aux: dict[str, list[dict]]) -> str:
    """The aux file: a region's entries, with a table row to a line."""
    regions = []
    for region, entries in aux.items():
        blocks = []
        for entry in entries:
            fields = []
            for key, value in entry.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    rows = ',\n'.join(f"                {json.dumps(row)}" for row in value)
                    fields.append(f'            "{key}": [\n{rows}\n            ]')
                else:
                    fields.append(f'            "{key}": {json.dumps(value)}')
            blocks.append('        {\n' + ',\n'.join(fields) + '\n        }')
        regions.append(f'    "{region}": [\n' + ',\n'.join(blocks) + '\n    ]')

    return '{\n' + ',\n'.join(regions) + '\n}\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data, a git repository with a commit per data version')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')

    args = vars(parser.parse_args())
    print(args)

    for mode, (names, keyed, list_seasons, until, rewards) in MODES.items():
        print(f"============ {mode.name} ============")
        current = keyed(*[load_generic(args['data_primary'], name, key=None) for name in names])
        seasons = list_seasons(current)
        versions = history(args['data_primary'], names)

        entries = []
        for season in seasons:
            ended = datetime.fromisoformat(season[until])
            ran = next((x for x in reversed(versions) if x['time'] <= ended and season['SeasonId'] in tables(args['data_primary'], x['commit'], mode).seasons), None)
            if not ran:
                if ended < datetime.now(JST).replace(tzinfo=None):
                    sys.exit(f"No data version in the git history of {args['data_primary']} has {mode.name} season {season['SeasonId']}, which ended {ended:%Y-%m-%d}: {mode.aux} is left as it is")
                continue

            tables_then = tables(args['data_primary'], ran['commit'], mode)
            then, now = rewards(tables_then.seasons[season['SeasonId']], tables_then), rewards(season, current)
            changed = {key: then[key] for key in then if then[key] != now[key]}
            if not changed: continue

            entries.append({'SeasonId': season['SeasonId'], 'Version': ran['tag'], **changed})
            print(f"Season {season['SeasonId']} ({season['SeasonDisplay']}, {season['raid_name']}) ran with {ran['tag']}: {'; '.join(difference(key, then[key], now[key]) for key in changed)}")

        with open(os.path.join(args['translation'], mode.aux), 'w', encoding="utf8") as f:
            f.write(aux_json({'jp': entries}))
        print(f"Kept {len(entries)} of {len(seasons)} seasons in {mode.aux}")


if __name__ == '__main__':
    main()
