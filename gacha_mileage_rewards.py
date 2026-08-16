import argparse
import os
import traceback

from jinja2 import Environment, FileSystemLoader

from data import load_data, load_season_data
from model import Item
import shared.functions


args = {}
data = None
season_data = None
items = {}


def wiki_card(type: str, id: int, **params):
    global data, items
    return shared.functions.wiki_card(
        type,
        id,
        data=data,
        characters={},
        items=items,
        furniture={},
        emblems={},
        **params,
    )


def init_data():
    global args, data, season_data, items

    data = load_data(
        args['data_primary'],
        args['data_secondary'],
        args['translation'],
    )
    season_data = load_season_data(args['data_primary'])

    reward_item_ids = {
        parcel_id
        for reward in season_data.shop_recruit_mileage
        for parcel_type, parcel_id in zip(reward['RewardParcelType'], reward['RewardParcelId'])
        if parcel_type == 'Item'
    }

    # shared.functions.wiki_card displays expiring 10-recruitment tickets using
    # the permanent ticket's translated wiki name.
    if 6999 in data.items:
        reward_item_ids.add(6999)

    for item_id in reward_item_ids:
        items[item_id] = Item.from_data(item_id, data)


def get_default_group_ids():
    global season_data

    configured_group_ids = {
        recruit['RecruitMileageGroupId']
        for recruit in season_data.shop_recruit.values()
        if recruit['RecruitMileageGroupId'] > 0
    }
    available_group_ids = {
        reward['MileageGroupId'] for reward in season_data.shop_recruit_mileage
    }

    return sorted(configured_group_ids & available_group_ids or available_group_ids)


def get_group_rewards(group_id: int):
    global season_data

    group_rewards = [
        reward
        for reward in season_data.shop_recruit_mileage
        if reward['MileageGroupId'] == group_id
    ]
    if not group_rewards:
        raise ValueError(f'Mileage group {group_id} was not found')

    return group_rewards


def reward_signature(group_id: int):
    signature = []

    for reward in get_group_rewards(group_id):
        prepared_reward = prepare_reward(reward)
        signature.append((
            reward['IsLoop'],
            reward['RequiredRecruitAmount'],
            tuple(prepared_reward['RewardCards']),
        ))

    return tuple(sorted(signature, key=lambda reward: (reward[0], reward[1])))


def verify_group_rewards(group_ids: list[int]):
    if len(group_ids) < 2:
        print(f'Mileage reward comparison skipped: only group {group_ids[0]} is being exported')
        return True

    reference_group_id = group_ids[0]
    reference_signature = reward_signature(reference_group_id)
    different_group_ids = [
        group_id
        for group_id in group_ids[1:]
        if reward_signature(group_id) != reference_signature
    ]

    if different_group_ids:
        different_groups = ', '.join(str(group_id) for group_id in different_group_ids)
        print(
            f'Mileage rewards are not identical: group {reference_group_id} '
            f'differs from group(s) {different_groups}. Exporting separate tables.'
        )
        return False

    compared_groups = ', '.join(str(group_id) for group_id in group_ids)
    print(f'Mileage rewards are identical across groups {compared_groups}')
    return True


def prepare_reward(reward):
    parcel_lengths = {
        len(reward['RewardParcelType']),
        len(reward['RewardParcelId']),
        len(reward['RewardParcelAmount']),
    }
    if len(parcel_lengths) != 1:
        raise ValueError(f"Reward {reward['Id']} has mismatched parcel fields")

    prepared_reward = reward.copy()
    prepared_reward['RewardCards'] = [
        wiki_card(
            parcel_type,
            reward['RewardParcelId'][index],
            quantity=reward['RewardParcelAmount'][index],
            #text='',
            #size='60px',
            #block=False,
        )
        for index, parcel_type in enumerate(reward['RewardParcelType'])
    ]
    return prepared_reward


def generate(group_id: int):
    global args, season_data

    group_rewards = get_group_rewards(group_id)

    first_time_rewards = sorted(
        (prepare_reward(reward) for reward in group_rewards if not reward['IsLoop']),
        key=lambda reward: reward['RequiredRecruitAmount'],
    )
    repeat_rewards = sorted(
        (prepare_reward(reward) for reward in group_rewards if reward['IsLoop']),
        key=lambda reward: reward['RequiredRecruitAmount'],
    )

    if not first_time_rewards or not repeat_rewards:
        raise ValueError(f'Mileage group {group_id} must have first-time and repeat rewards')

    first_time_end = first_time_rewards[-1]['RequiredRecruitAmount']
    for reward in repeat_rewards:
        reward['FirstTotalRecruitAmount'] = first_time_end + reward['RequiredRecruitAmount']

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('templates/template_gacha_mileage_rewards.txt')
    wikitext = template.render(
        first_time_rewards=first_time_rewards,
        repeat_rewards=repeat_rewards,
    )

    os.makedirs(args['outdir'], exist_ok=True)
    output_path = os.path.join(args['outdir'], f'gacha_mileage_rewards_{group_id}.txt')
    with open(output_path, 'w', encoding='utf8') as file:
        file.write(wikitext)

    print(f'Exported mileage group {group_id} to {output_path}')


def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'mileage_group_id',
        metavar='MILEAGE_GROUP_ID',
        nargs='*',
        type=int,
        help='Mileage group(s) to export; defaults to groups referenced by ShopRecruitExcelTable.json',
    )
    parser.add_argument('-data_primary', metavar='DIR', default='../ba-data/jp', help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary', metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation', metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir', metavar='DIR', default='out', help='Output directory')

    args = vars(parser.parse_args())
    print(args)

    try:
        init_data()
        group_ids = list(dict.fromkeys(args['mileage_group_id'] or get_default_group_ids()))
        verify_group_rewards(group_ids)
        for group_id in group_ids:
            generate(group_id)
    except Exception:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
