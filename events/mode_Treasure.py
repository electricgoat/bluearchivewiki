import os
from jinja2 import Environment, FileSystemLoader

import shared.functions
from classes.RewardParcel import RewardParcel

missing_localization = None
missing_code_localization = None

data = {}
characters = {}
items = {}
furniture = {}
emblems = {}


class TreasureReward(object):
    def __init__(self, id, localize_code:str, width:int, height:int, reward_parcel_type:list[str], reward_parcel_id: list[int], reward_parcel_amount: list[int], image:str, wiki_card = None, data = None):
        self.id = id
        self.localize_code = localize_code
        self.width = width
        self.height = height
        self.reward_parcel_type = reward_parcel_type
        self.reward_parcel_id = reward_parcel_id
        self.reward_parcel_amount = reward_parcel_amount
        self.image = image

        self.wiki_card = wiki_card
        self._data = data

    def __repr__(self):
        return str(self.__dict__)

    @property
    def name_en(self):
        key = shared.functions.hashkey(self.localize_code)
        return data.localization[key].get('En', f"Untranslated {key}")

    @property
    def items(self) -> list[RewardParcel]:
        items_list = []

        for i, parcel_id in enumerate(self.reward_parcel_id):
            items_list.append(RewardParcel(
                self.reward_parcel_type[i],
                parcel_id,
                self.reward_parcel_amount[i],
                10000,
                None,
            ))
                
        return items_list
    


    def wikitext_items(self) -> list[str]:
        #assert(self.wiki_card != None)
        items_list = []
        #for item in self.items: print(item)
        #print(f"probs {[x.prob for x in self.items]}")
        #total_prob = sum(x.prob for x in self.items)
        #print(f"total_prob {total_prob}")
        for index, item in enumerate(self.items):
            # if item.id in IGNORE_ITEM_ID:
            #     continue

            #probability = total_prob > 0 and item.prob / total_prob * 100 or 0
            #if use_parcel_prob: probability = self.parcel_prob[index] / 100
            
            #items_list.append(self.wiki_card(item.parcel_type, item.parcel_id, quantity=quantity if quantity!=1 else None, text='', probability=probability if probability<100 else None, block=True, size='60px' )) 
            items_list.append(wiki_card(item.parcel_type, item.parcel_id, quantity=item.amount, text='', probability=None, block=True, size='48px' )) 
        return items_list
    



def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)


def get_mode_treasure(season_id: int, ext_data, ext_characters, ext_items, ext_furniture, ext_emblems, ext_missing_localization, ext_missing_code_localization):
    global data, characters, items, furniture, emblems
    global missing_localization, missing_code_localization
    data = ext_data
    characters = ext_characters
    items = ext_items
    furniture = ext_furniture
    emblems = ext_emblems
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


    wikitext = {'title':'===Inventory Management===', 'rounds':''}

    #board = data.event_content_treasure[season_id]
    #print(board)

    rounds = [x for x in data.event_content_treasure_round[season_id]]
    for round in rounds: 
        round['treasures'] = []
        round['rewards'] = []

        for i, reward_id in enumerate(round['RewardID']): 
            #amount = round['RewardAmount'][i]
            treasure = data.event_content_treasure_reward[reward_id]

            round['treasures'].append(TreasureReward(   treasure['Id'],
                                             treasure['LocalizeCodeID'], 
                                             treasure['CellUnderImageWidth'], 
                                             treasure['CellUnderImageHeight'], 
                                             treasure['RewardParcelType'],
                                             treasure['RewardParcelId'],
                                             treasure['RewardParcelAmount'],
                                             treasure['CellUnderImagePath'].rsplit('/',1)[-1],
                                             #wiki_card,
                                             #data
                                             )
            )
            

    cost_goods_ids = [x['CellCheckGoodsId'] for x in rounds]
    if len(set(cost_goods_ids)) == 1: #all rounds cost the same
        cost_good = data.goods[cost_goods_ids[0]]
        wiki_price = wiki_card('Item', cost_good['ConsumeParcelId'][0], quantity = cost_good['ConsumeParcelAmount'][0])
    else:
        wiki_price = 'varies depending on round'
        
    cell_reward_ids = [x['CellRewardId'] for x in rounds]
    if len(set(cell_reward_ids)) == 1: #all rounds have the same cell reveal reward
        cell_reward = data.event_content_treasure_cell_reward[cell_reward_ids[0]]
        cell_reward_parcels = []
        for i, parcel_id in enumerate(cell_reward['RewardParcelId']):  
            cell_reward_parcels.append(RewardParcel(
                cell_reward['RewardParcelType'][i],
                parcel_id,
                cell_reward['RewardParcelAmount'][i],
                10000,
                None,
                wiki_card,
                data
            ))
        wiki_cell_reward = ", ".join(wiki_card(parcel.parcel_type, parcel.parcel_id, quantity=parcel.amount, probability=None ) for parcel in cell_reward_parcels)

    else:
        wiki_cell_reward = 'varies depending on round'
    

    rounds = sorted(rounds, key=lambda x: x['TreasureRound'])
    template = env.get_template('template_treasure_rounds.txt')
    wikitext['rounds'] = template.render(rounds=rounds, wiki_price=wiki_price, wiki_cell_reward=wiki_cell_reward)

            
    return '\n'.join(wikitext.values()) + '\n'
