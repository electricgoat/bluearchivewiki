import os
from jinja2 import Environment, FileSystemLoader

import shared.functions
from classes.RewardParcel import RewardParcel

missing_localization = None
missing_code_localization = None
missing_etc_localization = None

data = {}
characters = {}
items = {}
furniture = {}
emblems = {}


def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)


def parse_clue_search_rounds(season_id):
    """Parse ClueSearch rounds and rewards"""
    global data
    rounds_data = []
    
    # Get all clues for this event
    clues = data.event_content_clue[season_id]
    
    # Sort clues by ClueId to maintain order
    clues = sorted(clues, key=lambda x: x['ClueId'])
    
    main_clue_ids = [x['ClueId'] for x in clues]
    
    # Get round information
    if season_id in data.event_content_clue_search_round:
        rounds_info = data.event_content_clue_search_round[season_id]
        
        for round_info in rounds_info:
            round_data = {
                'round_number': round_info.get('Round', 0),
                'clue_requirements': [0] * len(clues),  # Initialize with 0 for the number of clue types
                'reward_parcels': [],
            }
            
            # Map clue requirements to the 6 main clue types
            clue_ids = round_info.get('ClueId', [])
            clue_costs = round_info.get('ClueCostAmount', [])
            
            for clue_id, cost in zip(clue_ids, clue_costs):
                if clue_id in main_clue_ids:
                    # Find the index of this clue in the main list
                    clue_index = main_clue_ids.index(clue_id)
                    round_data['clue_requirements'][clue_index] += cost
            
            # Get rewards for this round
            reward_id = round_info.get('RewardId')
            if reward_id and reward_id in data.event_content_clue_search_reward:
                reward_data = data.event_content_clue_search_reward[reward_id]
                
                for i, parcel_type in enumerate(reward_data.get('RewardParcelType', [])):
                    parcel_id = reward_data['RewardParcelId'][i]
                    parcel_amount = reward_data['RewardParcelAmount'][i]
                    
                    parcel = RewardParcel(
                        parcel_type,
                        parcel_id,
                        parcel_amount,
                        10000,
                        wiki_card=wiki_card,
                        data=data
                    )
                    round_data['reward_parcels'].append(parcel)
            
            rounds_data.append(round_data)
    
    return rounds_data, clues


def get_clue_display_data(clue):
    """Resolve localized clue display data with safe fallbacks."""
    global data
    global missing_localization, missing_etc_localization

    localization = data.etc_localization.get(clue.get('LocalizeEtcId'), {})

    if clue.get('LocalizeEtcId') in data.etc_localization:
        if ('NameEn' not in localization or 'DescriptionEn' not in localization) and missing_etc_localization is not None:
            missing_etc_localization.add_entry(localization)

    name = localization.get('NameEn') or localization.get('NameJp') or f"Clue {clue.get('ClueId', '')}".strip()
    description = localization.get('DescriptionEn') or localization.get('DescriptionJp') or ''

    if not description:
        hint_localize_id = clue.get('Hintlocalizeid')

        if hint_localize_id in data.localization:
            hint_localization = data.localization[hint_localize_id]
            if 'En' not in hint_localization and missing_localization is not None:
                missing_localization.add_entry(hint_localization)

            description = hint_localization.get('En') or hint_localization.get('Jp') or ''
        elif hint_localize_id in data.etc_localization:
            hint_localization = data.etc_localization[hint_localize_id]
            if ('NameEn' not in hint_localization and 'DescriptionEn' not in hint_localization) and missing_etc_localization is not None:
                missing_etc_localization.add_entry(hint_localization)

            description = (
                hint_localization.get('DescriptionEn')
                or hint_localization.get('DescriptionJp')
                or hint_localization.get('NameEn')
                or hint_localization.get('NameJp')
                or ''
            )

    image_path = clue.get('ClueImagePath') or clue.get('SlotClueImagePath') or ''
    image_name = image_path.rsplit('/', 1)[-1] + '.png' if image_path else ''

    return {
        'name': name,
        'description': description.replace('\n', '<br>'),
        'image_name': image_name,
    }


def generate_clue_info_table(clues):
    """Generate a clue reference table with image, name, and description."""
    if not clues:
        return ''

    wikitext = '{| class="wikitable limitwidth-1024"\n'
    wikitext += '|+ Clues\n'
    wikitext += '|-\n'
    wikitext += '! Image !! Clue\n'

    for clue in clues:
        clue_data = get_clue_display_data(clue)
        wikitext += '|-\n'

        if clue_data['image_name']:
            wikitext += f"| [[File:{clue_data['image_name']}|80px|{clue_data['name']}]]\n"
        else:
            wikitext += '| \n'

        wikitext += f"| '''{clue_data['name']}'''"
        if clue_data['description']:
            wikitext += f"\n\n{clue_data['description']}"
        wikitext += '\n'

    wikitext += '|}\n'
    return wikitext


def generate_clue_search_table(rounds_data, clues):
    """Generate the wiki table for ClueSearch rounds"""
    wikitext = '{| class="wikitable"\n'
    wikitext += '|+ Clue board rewards\n'
    wikitext += '|-\n'
    wikitext += '! rowspan="2" | Round !! colspan="' + str(len(clues)) + '" | Clues number required !! rowspan="2" | Total Cost !! rowspan="2" | Clear rewards\n'
    wikitext += '|-\n'
    
    # Clue headers
    for i, clue in enumerate(clues):
        clue_data = get_clue_display_data(clue)
        wikitext += f"! {{{{ItemCard|{clue_data['name']}|text=|48px|block}}}}<br>Clue {i+1}\n"
    
    wikitext += '|-\n'
    
    # Build rows for each round
    if rounds_data:
        for round_info in rounds_data:
            round_num = round_info['round_number']
            wikitext += f'! {round_num} \n'
            
            # Clue requirements
            for requirement in round_info['clue_requirements']:
                wikitext += f'|| {requirement if requirement > 0 else ""} '
            
            #Total cost            
            total_cost = sum(round_info['clue_requirements'])
            wikitext += '|| {{ItemCard|Event Points|quantity=' + str(total_cost * 200) + '|text=}} '

            # Rewards
            wikitext += '|| '
            if round_info['reward_parcels']:
                reward_cards = []
                for parcel in round_info['reward_parcels']:
                    wikitext_items = parcel.wikitext_items()
                    reward_cards.extend(wikitext_items)
                
                wikitext += ' '.join(reward_cards) if reward_cards else ''
            
            wikitext += '\n|-\n'
    else:
        # Placeholder rows if no round data available
        for i in range(1, 8):
            wikitext += f'| {i} || || || || || || || \n'
            wikitext += '|-\n'
    
    wikitext += '|}\n'
    return wikitext


def get_mode_cluesearch(season_id: int, ext_data, ext_characters, ext_items, ext_furniture, ext_emblems, ext_missing_localization, ext_missing_code_localization, ext_missing_etc_localization):
    """Export ClueSearch minigame data"""
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

    title = 'Clue Search'
    wikitext = {'title': f"\n=={title}==", 'intro': '', 'clues': '', 'rounds': ''}

    # Parse rounds and clues
    rounds_data, clues = parse_clue_search_rounds(season_id)
    
    # Generate intro text
    wikitext['intro'] = f"Clue search is the new minigame type introduced for this event. Players are presented with a clue board that requires submitting specific numbers of each of {len(clues)} clue types to complete. Clues can be purchased at the Event Points store for {{{{ItemCard|Event Points|quantity=200}}}} each; turning clues back is also available at the recycling shop for a full Event Points refund. Submitting each clue awards player {{{{ItemCard|Credits|quantity=50000}}}}.\n"

    # Generate clue reference table
    wikitext['clues'] = generate_clue_info_table(clues)
    
    # Generate table
    wikitext['rounds'] = generate_clue_search_table(rounds_data, clues)
    
    return '\n'.join(wikitext.values())
