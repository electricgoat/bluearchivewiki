import os
import copy
from jinja2 import Environment, FileSystemLoader

import shared.functions
from events.mission_desc import mission_desc
from classes.Stage import DefenseStage
from classes.RewardParcel import RewardParcel

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


def parse_stages(season_id):
    global data
    global missing_localization, missing_etc_localization
    stages = []

    for stage in data.minigame_defense_stage.values():
        if stage['EventContentId'] != season_id:
            continue
        stage = DefenseStage.from_data(stage['Id'], data, wiki_card=wiki_card, missing_localization=missing_localization, missing_etc_localization=missing_etc_localization)
        stages.append(stage)
                
    return stages



def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)


def get_mode_defense(season_id: int, ext_data, ext_characters, ext_items, ext_furniture, ext_emblems, ext_missing_localization, ext_missing_code_localization, ext_missing_etc_localization):
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


    title = 'Hi-Lo Ha-Lo Minigame'
    wikitext = {'title':f"=={title}==", 'intro':'', 'banned':'', 'stages':'', 'collection':'', 'missions':''}


    template = env.get_template('template_defense_intro.txt')
    wikitext['intro'] = template.render(name=title, defense_info = data.minigame_defense_info[season_id])
    #print(wikitext['intro'])

    template = env.get_template('template_banned_characters.txt')
    ban_ids = [x['CharacterId'] for x in data.minigame_defense_character_ban[season_id]]
    wikitext['banned'] = template.render(character_names = [characters[x].wiki_name for x in characters if x in ban_ids ])
    #print(wikitext['banned'])


    stages = {}

    DIFFICULTY_NAMES = {'Normal':'Story', 'Hard':'Normal', 'VeryHard':'Challenge'}
    stage_reward_types = {x: [] for x in DIFFICULTY_NAMES.keys()}
    stages = parse_stages(season_id)

    for stage in stages:
        for reward_tag in stage.rewards.keys():
            if reward_tag not in stage_reward_types[stage.difficulty] and len([x.wikitext_items() for x in stage.rewards[reward_tag] if len(x.wikitext_items())])>0:
                stage_reward_types[stage.difficulty].append(reward_tag)

    template = env.get_template('template_event_stages.txt')
    for difficulty in stage_reward_types:
        stages_filtered = [x for x in stages if x.difficulty == difficulty]
        if len(stages_filtered): 
            #for stage in stages_filtered: print(stage.rewards)
            wikitext['stages'] += template.render(stage_type=DIFFICULTY_NAMES[difficulty], stages=stages_filtered, reward_types=stage_reward_types[difficulty], rewardcols = len(stage_reward_types[difficulty]))
    #print(wikitext['stages'])




            
    return '\n'.join(wikitext.values())
