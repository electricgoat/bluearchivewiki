from classes.Gacha import GachaGroup, GachaElement
import shared.functions

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


IGNORE_ITEM_ID = {
    767, #200~800 credits, removed to reduce clutter
}


class RewardParcel(object):
    def __init__(self, parcel_type, parcel_id, amount: list[int], parcel_prob: list[int], tag = None, wiki_card = None, data = None):
        #self.id = id
        self.parcel_type = parcel_type
        self.parcel_id = parcel_id
        self.amount = amount
        self.parcel_prob = parcel_prob
        self.tag = tag

        self.wiki_card = wiki_card
        self._data = data

    def __repr__(self):
        return str(self.__dict__)


    @property
    def items(self) -> list:
        items_list = []

        match self.parcel_type:
            case 'GachaGroup':
                assert(self._data != None)
                gg = GachaGroup.from_id(self.parcel_id, self._data)
                items_list += gg.contents
            case 'Item':
                items_list.append(GachaElement(0, 0, self.parcel_type, self.parcel_id, '', self.amount[0], self.amount[0], 1, 1)) 
            case 'Currency':
                items_list.append(GachaElement(0, 0, self.parcel_type, self.parcel_id, '', self.amount[0], self.amount[0], 1, 1)) 
            case 'Equipment':
                items_list.append(GachaElement(0, 0, self.parcel_type, self.parcel_id, '', self.amount[0], self.amount[0], 1, 1)) 
            case _:
                print(f"Unknown parcel type {self.parcel_type}")
                
        return items_list
    


    def wikitext_items(self, use_parcel_prob = False) -> list[str]:
        assert(self.wiki_card != None)
        items_list = []
        #for item in self.items: print(item)
        #print(f"probs {[x.prob for x in self.items]}")
        total_prob = sum(x.prob for x in self.items)
        #print(f"total_prob {total_prob}")
        for index, item in enumerate(self.items):
            if item.id in IGNORE_ITEM_ID:
                continue

            quantity = item.parcel_amount_min == item.parcel_amount_max and item.parcel_amount_max or f"{item.parcel_amount_min}~{item.parcel_amount_max}"
            probability = total_prob > 0 and item.prob / total_prob * 100 or 0
            if use_parcel_prob: probability = self.parcel_prob[index] / 100
            
            #items_list.append(self.wiki_card(item.parcel_type, item.parcel_id, quantity=quantity if quantity!=1 else None, text='', probability=probability if probability<100 else None, block=True, size='60px' )) 
            if probability>0: items_list.append(self.wiki_card(item.parcel_type, item.parcel_id, quantity=quantity, text='', probability=probability > 5 and round(probability,1) or round(probability,2) if probability<100 else None, block=True, size='48px' )) 
        return items_list
    

    @property
    def wikitext_itemgroup(self) -> str:
        if len(self.items) == 0: return ''

        wikitext = ''
        wikitext += '<div class="itemgroup btag"><span class="tag' + ((len(self.items)<3 and len(self.amount)>2) and ' condensed' or '') + '">' + ", ".join([f"{self.amount[i]}×{'%g' % round(self.parcel_prob[i]/100, 2)}%" for i,_ in enumerate(self.amount)]) + '</span>'
        wikitext += "".join(self.wikitext_items())
        wikitext += '</div>'

        return wikitext
                

    @property
    def wikitext(self) -> str:
        if self.parcel_id in FAKE_ITEMS:
            
            probability = f"{'%g' % (self.parcel_prob[0]/100)}"
            quantity = self.amount[0]
            return("{{" + f"ItemCard|{FAKE_ITEMS[self.parcel_id]}{quantity>1 and f'|quantity={quantity}' or ''}{probability!=100 and f'|probability={probability > 5 and round(probability,1) or round(probability,2)}' or ''}|text=|60px|block" + "}}")

        elif len(self.amount) > 1 or (self.parcel_type == 'GachaGroup' and len(self.items)>1): return self.wikitext_itemgroup

        else: return "".join(self.wikitext_items(use_parcel_prob = True))

    
    def format_wiki_items(self, **params):
        items_list = []
        for i in range(len(self.parcel_type)):
            items_list.append(self.wiki_card(self.parcel_type[i], self.parcel_id[i], quantity=self.amount[i], **params )) 
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
            data = data
        )


# def wiki_card(type: str, id: int, **params):
#     global data, characters, items, furniture
#     return shared.functions.wiki_card(type, id, data=data, characters=None, items=items, furniture=None, **params)