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

        # self.wiki_card = wiki_card
        # self._data = data

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
    

    # @property
    # def wikitext_itemgroup(self) -> str:
    #     if len(self.items) == 0: return ''

    #     wikitext = ''
    #     wikitext += '<div class="itemgroup btag"><span class="tag' + ((len(self.items)<3 and len(self.amount)>2) and ' condensed' or '') + '">' + ", ".join([f"{self.amount[i]}×{'%g' % round(self.parcel_prob[i]/100, 2)}%" for i,_ in enumerate(self.amount)]) + '</span>'
    #     wikitext += "".join(self.wikitext_items())
    #     wikitext += '</div>'

    #     return wikitext
                

    # @property
    # def wikitext(self) -> str:
    #     if self.parcel_id in FAKE_ITEMS:
            
    #         probability = f"{'%g' % (self.parcel_prob[0]/100)}"
    #         quantity = self.amount[0]
    #         return("{{" + f"ItemCard|{FAKE_ITEMS[self.parcel_id]}{quantity>1 and f'|quantity={quantity}' or ''}{probability!=100 and f'|probability={probability > 5 and round(probability,1) or round(probability,2)}' or ''}|text=|60px|block" + "}}")

    #     elif len(self.amount) > 1 or (self.parcel_type == 'GachaGroup' and len(self.items)>1): return self.wikitext_itemgroup

    #     else: return "".join(self.wikitext_items(use_parcel_prob = True))

    
    # def format_wiki_items(self, **params):
    #     items_list = []
    #     for i in range(len(self.parcel_type)):
    #         items_list.append(self.wiki_card(self.parcel_type[i], self.parcel_id[i], quantity=self.amount[i], **params )) 
    #     return items_list
    


    # def add_drop(self, amount:int, parcel_prob:int):
    #     self.amount += amount
    #     self.parcel_prob += parcel_prob





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


    wikitext = {'title':'===Inventory Management===', 'rounds':'', 'rewards':''}

    board = data.event_content_treasure[season_id]
    #print(board)

    rounds = [x for x in data.event_content_treasure_round[season_id]]
    for round in rounds: 
        round['rewards'] = []

        for i, reward_id in enumerate(round['RewardID']): 
            #amount = round['RewardAmount'][i]
            treasure = data.event_content_treasure_reward[reward_id]

            round['rewards'].append(TreasureReward(   treasure['Id'],
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

        

    rounds = sorted(rounds, key=lambda x: x['TreasureRound'])
    template = env.get_template('template_treasure_rounds.txt')
    wikitext['rounds'] = template.render(rounds=rounds)

            
    return '\n'.join(wikitext.values())
