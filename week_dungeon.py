from dataclasses import replace
import os
import re
import sys
import traceback
#import json
import argparse

from jinja2 import Environment, FileSystemLoader

import wikitextparser as wtp
import wiki
import shared.functions

from data import load_data, load_season_data
from model import Item, Furniture, Character
from classes.Gacha import GachaGroup, GachaElement

args = None
data = None
items = {}
season_data = {'jp':None, 'gl':None}

# This is to avoid unpacking 4-oopart gachagroups, which looks too messy to display on the page.
FAKE_ITEMS = {
    #ChaserA
    10110 : 'Random Bounty Artifact - Classroom 1',
    10111 : 'Random Bounty Artifact - Classroom 2',
    10112 : 'Random Bounty Artifact - Classroom 3',
    10113 : 'Random Bounty Artifact - Classroom 4',

    #ChaserB
    10114 : 'Random Bounty Artifact - Desert Railroad 1',
    10115 : 'Random Bounty Artifact - Desert Railroad 2',
    10116 : 'Random Bounty Artifact - Desert Railroad 3',
    10117 : 'Random Bounty Artifact - Desert Railroad 4',

    #ChaserC
    10118 : 'Random Bounty Artifact - Overpass 1',
    10119 : 'Random Bounty Artifact - Overpass 2',
    10120 : 'Random Bounty Artifact - Overpass 3',
    10121 : 'Random Bounty Artifact - Overpass 4',

}


# class RewardParcel(object):
#     def __init__(self, parcel_type, parcel_id, amount, parcel_prob):
#         #self.id = id
#         self.parcel_type = parcel_type
#         self.parcel_id = parcel_id
#         self.amount = amount
#         self.parcel_prob = parcel_prob

#     @property
#     def items(self):
#         items_list = []
#         for i in range(len(self.parcel_type)):
#             items_list.append({'parcel_type':self.parcel_type[i], 'parcel_id':self.parcel_id[i], 'amount':self.amount[i]}) 
#         return items_list
    
#     @property
#     def wiki_items(self):
#         items_list = []
#         for i in range(len(self.parcel_type)):
#             items_list.append(wiki_card(self.parcel_type[i], self.parcel_id[i], quantity=self.amount[i], text='', block=True, size='60px' )) 
#         return items_list
    
#     def format_wiki_items(self, **params):
#         items_list = []
#         for i in range(len(self.parcel_type)):
#             items_list.append(wiki_card(self.parcel_type[i], self.parcel_id[i], quantity=self.amount[i], **params )) 
#         return items_list


#     @classmethod
#     def from_data(cls, type:str, id:int, amount:int, prob:int):
#         return cls(
#             type,
#             id,
#             amount,
#             prob,
#         )




class RewardParcel(object):
    def __init__(self, parcel_type, parcel_id, amount: list[int], parcel_prob: list[int]):
        #self.id = id
        self.parcel_type = parcel_type
        self.parcel_id = parcel_id
        self.amount = amount
        self.parcel_prob = parcel_prob

    def __repr__(self):
        return str(self.__dict__)


    @property
    def items(self) -> list:
        items_list = []

        match self.parcel_type:
            case 'GachaGroup':
                gg = GachaGroup.from_id(self.parcel_id, data)
                items_list += gg.contents
            case 'Item':
                items_list.append(GachaElement(0, 0, self.parcel_type, self.parcel_id, '', self.amount[0], self.amount[0], 1, 1)) 
            case 'Currency':
                items_list.append(GachaElement(0, 0, self.parcel_type, self.parcel_id, '', self.amount[0], self.amount[0], 1, 1)) 
            case _:
                print(f"Unknown parcel type {self.parcel_type}")
                
        return items_list
    


    def wikitext_items(self, use_parcel_prob = False) -> list[str]:
        items_list = []
        total_prob = sum(x.prob for x in self.items)
        for index, item in enumerate(self.items):
            #print(item)
            quantity = item.parcel_amount_min == item.parcel_amount_max and item.parcel_amount_max or f"{item.parcel_amount_min}~{item.parcel_amount_max}"
            probability = item.prob / total_prob * 100
            if use_parcel_prob: probability = self.parcel_prob[index] / 100
            

            items_list.append(wiki_card(item.parcel_type, item.parcel_id, quantity=quantity if quantity!=1 else None, text='', probability=probability if probability<100 else None, block=True, size='60px' )) 
        return items_list
    

    @property
    def wikitext_itemgroup(self) -> str:

        wikitext = ''
        wikitext += '<div class="itemgroup btag"><span class="tag' + ((len(self.items)<3 and len(self.amount)>2) and ' condensed' or '') + '">' + ", ".join([f"{self.amount[i]}×{'%g' % (self.parcel_prob[i]/100)}%" for i,_ in enumerate(self.amount)]) + '</span>'
        wikitext += "".join(self.wikitext_items())
        wikitext += '</div>'

        return wikitext
                

    @property
    def wikitext(self) -> str:
        if self.parcel_id in FAKE_ITEMS:
            probability = f"{'%g' % (self.parcel_prob[0]/100)}"
            quantity = self.amount[0]
            return("{{" + f"ItemCard|{FAKE_ITEMS[self.parcel_id]}{quantity>1 and f'|quantity={quantity}' or ''}{probability!=100 and f'|probability={probability}' or ''}|text=|60px|block" + "}}")

        elif len(self.amount) > 1 or (self.parcel_type == 'GachaGroup' and len(self.items)>1): return self.wikitext_itemgroup

        else: return "".join(self.wikitext_items(use_parcel_prob = True))

    
    def format_wiki_items(self, **params):
        items_list = []
        for i in range(len(self.parcel_type)):
            items_list.append(wiki_card(self.parcel_type[i], self.parcel_id[i], quantity=self.amount[i], **params )) 
        return items_list
    


    def add_drop(self, amount:int, parcel_prob:int):
        self.amount += amount
        self.parcel_prob += parcel_prob


    @classmethod
    def from_data(cls, id: int, data): #note that this takes actual table such as data.eliminate_raid_stage_season_reward
        item = data[id]
        
        return cls(
            item['RewardParcelType'],
            item['RewardParcelId'],
            [item['RewardParcelAmount']],
            [item['RewardParcelProbability']],
        )
    


def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture
    return shared.functions.wiki_card(type, id, data=data, characters=None, items=items, furniture=None, **params)




def generate():
    global args, data, season_data, items
    
    week_dungeon_types = set()
    for weekday in season_data['jp'].week_dungeon_open_schedule.values():
        week_dungeon_types.update(weekday['Open'])
    print(sorted(week_dungeon_types))

    stages = []

    for stage in season_data['jp'].week_dungeon.values():
        # if stage['WeekDungeonType'] != 'ChaserC':
        #     continue
        stage['Name'] = chr(stage['Difficulty'] + 64)
        stage['RewardParcels'] = []
        stage['Rewards'] = {}

        if stage['StageRewardId']>0: 
            stage['RewardParcels'] = season_data['jp'].week_dungeon_reward[stage['StageRewardId']]
            print(f"================== {stage['StageId']} Difficulty{stage['Difficulty']} {stage['Name']} ==================")
            for parcel in [x for x in stage['RewardParcels'] if x['RewardParcelProbability']>0]:
                reward = RewardParcel(parcel['RewardParcelType'], parcel['RewardParcelId'], [parcel['RewardParcelAmount']], [parcel['RewardParcelProbability']]) 

                if reward.parcel_id in stage['Rewards']:
                    stage['Rewards'][reward.parcel_id].add_drop(reward.amount, reward.parcel_prob)
                else:
                    stage['Rewards'][reward.parcel_id] = reward

        stages.append(stage)


        # for reward_parcel in stage['Rewards'].values():
        #     #print(reward_parcel)
        #     print(reward_parcel.wikitext, end=' ')
        # print()



    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    template = env.get_template('./template_week_dungeon.txt')

    for dungeon_type in week_dungeon_types:
        wikitext = template.render(stages=[x for x in stages if x['WeekDungeonType'] == dungeon_type] )
        with open(os.path.join(args['outdir'], 'week_dungeon', f'{dungeon_type}.txt'), 'w', encoding="utf8") as f:
            f.write(wikitext)
            f.close()




def init_data():
    global args, data, season_data, items
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    season_data['jp'] = load_season_data(args['data_primary'])
    season_data['gl'] = load_season_data(args['data_secondary']) 

    for item in data.items.values():
        try:
            item = Item.from_data(item['Id'], data)
            items[item.id] = item
        except Exception as err:
            print(f'Failed to parse for item {item}: {err}')
            traceback.print_exc()
            continue



def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')


    args = vars(parser.parse_args())
    print(args)


    try:
        init_data()
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
