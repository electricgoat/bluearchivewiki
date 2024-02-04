import os
import json
from jinja2 import Environment, FileSystemLoader

import shared.functions
from classes.RewardParcel import RewardParcel
from classes.Stage import FieldStage

missing_localization = None
missing_code_localization = None

data = {}
characters = {}
items = {}
furniture = {}



def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture
    return shared.functions.wiki_card(type, id, data=data, characters=None, items=items, furniture=None, **params)


def get_mode_field(season_id: int, ext_data, ext_characters, ext_items, ext_furniture, ext_missing_localization, ext_missing_code_localization):
    global data, characters, items, furniture
    global missing_localization, missing_code_localization
    data = ext_data
    characters = ext_characters
    items = ext_items
    furniture = ext_furniture
    missing_localization = ext_missing_localization
    missing_code_localization = ext_missing_code_localization

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.globals['len'] = len
    
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['nl2br'] = shared.functions.nl2br
    env.filters['nl2p'] = shared.functions.nl2p
    env.filters['shortform_range'] = shortform_range


    wikitext = {'quest':'', 'evidence':'', 'stages':''}

    season = data.field_season[season_id]
    print(season)

    quests = {}
    for entry in data.field_quest[season_id]: 
        rewards = []

        if 'En' not in data.localization[entry['QuestNamKey']] or not data.localization[entry['QuestNamKey']]['En']:
            missing_localization.add_entry(data.localization[entry['QuestNamKey']])
        if 'En' not in data.localization[entry['QuestDescKey']] or not data.localization[entry['QuestDescKey']]['En']:
            missing_localization.add_entry(data.localization[entry['QuestDescKey']])
        for reward in data.field_reward[entry['RewardId']]:
            rewards.append(RewardParcel(reward['RewardParcelType'], reward['RewardId'], [reward['RewardAmount']], [reward['RewardProb']], data=data, wiki_card=wiki_card))
        
        entry['QuestName'] = data.localization[entry['QuestNamKey']]
        entry['QuestDesc'] = data.localization[entry['QuestDescKey']]
        entry['Rewards'] = rewards
        entry['Days'] = [entry['Opendate']]

        if entry['QuestNamKey'] not in quests:
            quests[entry['QuestNamKey']] = entry
        else:
            quests[entry['QuestNamKey']]['Days'].append(entry['Opendate'])

    #sort by first day of quest appearance
    quests = dict(sorted(quests.items(), key=lambda x: x[1]['Opendate']))


    template = env.get_template('template_field_quest.txt')
    wikitext['quest'] = template.render(quests=quests)

    #print(wikitext['quest'])

    evidence = {}
    for entry in data.field_evidence.values():
        localize_key = shared.functions.hashkey(entry['NameLocalizeKey'])
        localize_desc_key = shared.functions.hashkey(entry['DescriptionLocalizeKey'])
        localize_detail_key = shared.functions.hashkey(entry['DetailLocalizeKey'])

        if 'En' not in data.localization[localize_key] or not data.localization[localize_key]['En']:
            missing_localization.add_entry(data.localization[localize_key])
        if 'En' not in data.localization[localize_desc_key] or not data.localization[localize_desc_key]['En']:
            missing_localization.add_entry(data.localization[localize_desc_key])
        if entry['DetailLocalizeKey'] != '' and localize_detail_key in data.localization and ('En' not in data.localization[localize_detail_key] or not data.localization[localize_detail_key]['En']):
            missing_localization.add_entry(data.localization[localize_detail_key])
        
        entry['Name'] = data.localization[localize_key]
        entry['Desc'] = data.localization[localize_desc_key]
        entry['Detail'] = (entry['DetailLocalizeKey'] != '' and localize_detail_key in data.localization) and data.localization[localize_detail_key] or None
        entry['Image'] = entry['ImagePath'].rsplit('/', 1)[-1]

        entry['FromInteraction'] = [x for x in data.field_interaction.values() if 'EvidenceFound' in x['InteractionType'] and entry['UniqueId'] in x['InteractionId'] ][0]
        date_id = entry['FromInteraction']['FieldDateId']
        entry['FromDate'] = data.field_date[date_id]

        reward_id = entry['FromInteraction']['InteractionId'][entry['FromInteraction']['InteractionType'].index("Reward")]
        rewards = []
        for reward in data.field_reward[reward_id]:
            rewards.append(RewardParcel(reward['RewardParcelType'], reward['RewardId'], [reward['RewardAmount']], [reward['RewardProb']], data=data, wiki_card=wiki_card))

        entry['Rewards'] = rewards


        evidence[entry['UniqueId']] = entry

    template = env.get_template('template_field_evidence.txt')
    wikitext['evidence'] = template.render(evidence=evidence)

    #print(wikitext['evidence'])


    stages = {}

    DIFFICULTY = {'Normal':'Story', 'Hard':'Quest', 'VeryHard':'Challenge'}
    difficulty_names = {'Normal':'Story','Hard':'Quest','VeryHard':'Challenge', 'VeryHard_Ex': 'Extra Challenge'}
    stage_reward_types = {x: [] for x in difficulty_names.keys()}
    stages = parse_stages(season_id)

    for stage in stages:
        for reward in stage.rewards.values():
            if reward.tag not in stage_reward_types[stage.difficulty]:
                stage_reward_types[stage.difficulty].append(reward.tag)

    template = env.get_template('template_field_stages.txt')
    for difficulty in stage_reward_types:
        stages_filtered = [x for x in stages if x.difficulty == difficulty]
        if len(stages_filtered): 
            #for stage in stages_filtered: print(stage.rewards)
            wikitext['stages'] += template.render(stage_type=difficulty_names[difficulty], stages=stages_filtered, reward_types=stage_reward_types[difficulty], rewardcols = len(stage_reward_types[difficulty]))

    #print(wikitext['stages']
            
    return '\n'.join(wikitext.values())



def parse_stages(season_id):
    global data
    stages = []

    for stage in data.field_content_stage.values():
        if stage['SeasonId'] != season_id:
            continue
        stage = FieldStage.from_data(stage['Id'], data, wiki_card=wiki_card)
        stages.append(stage)

    return stages



def shortform_range(list: list[int]):
    if not list:
        return "Empty List"

    list.sort()
    ranges = []
    start, end = list[0], list[0]

    for num in list[1:]:
        if num == end + 1:
            end = num
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}~{end}")
            start = end = num

    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}~{end}")

    return ", ".join(ranges)