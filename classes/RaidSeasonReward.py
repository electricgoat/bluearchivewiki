from typing import Callable, Any

class RaidSeasonReward(object):
    def __init__(self, id, parcel_type, parcel_id, parcel_name, amount, wiki_card):
        self.id = id
        self.parcel_type = parcel_type
        self.parcel_id = parcel_id
        self.parcel_name = parcel_name
        self.amount = amount

        self._wiki_card = wiki_card

    @property
    def items(self):
        items_list = []
        for i in range(len(self.parcel_type)):
            items_list.append({'parcel_type':self.parcel_type[i], 'parcel_id':self.parcel_id[i], 'amount':self.amount[i]}) 
        return items_list
    
    @property
    def wiki_items(self):
        items_list = []
        for i in range(len(self.parcel_type)):
            items_list.append(self._wiki_card(self.parcel_type[i], self.parcel_id[i], quantity=self.amount[i], text='', block=True, size='60px' )) 
        return items_list
    
    def format_wiki_items(self, **params):
        items_list = []
        for i in range(len(self.parcel_type)):
            items_list.append(self._wiki_card(self.parcel_type[i], self.parcel_id[i], quantity=self.amount[i], **params )) 
        return items_list


    @classmethod
    def from_data(cls, id: int, data, wiki_card: Callable[[str, int], Any]): #note that this takes actual table such as data.raid_stage_season_reward or data.eliminate_raid_stage_season_reward
        item = data[id]
        
        return cls(
            item['SeasonRewardId'],
            item['SeasonRewardParcelType'],
            item['SeasonRewardParcelUniqueId'],
            "",
            item['SeasonRewardAmount'],
            wiki_card,
        )
