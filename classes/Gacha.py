from shared.functions import translate_package_name

class GachaGroup(object):
    def __init__(self, id:int, name_kr:str, is_recursive:bool, group_type:str, contents:list|None):
        self.id = id
        self.name_kr = name_kr
        #self.name_en = name_en
        self.is_recursive = is_recursive
        self.group_type = group_type

        self.contents = contents


    def __repr__(self):
        return str(self.__dict__)
    

    @property
    def name_en(self):
        return translate_package_name(self.name_kr)
    

    @property
    def list_contents(self):
        for x in self.contents:
            match type(x).__name__:
                case 'GachaGroup':
                    x.list_contents()
                case 'GachaElementRecursive':
                    x.gacha_group.list_contents
                case 'GachaElement':
                    print(x)
        return
    

    @classmethod
    def from_id(cls, id, data):
        entry = data.gacha_groups[id]
        is_recursive = entry.get('IsRecursive', False)
        #print(f"processing gachagroup {id}, is_recursive:{is_recursive}")

        contents = []
        if(is_recursive): contents += [GachaElementRecursive.from_data(x, data) for x in data.gacha_elements_recursive[id]]
        else: contents += [GachaElement.from_data(x) for x in data.gacha_elements[id]]

        return cls(
            id = id,
            name_kr = entry.get('NameKr', ''),
            is_recursive = is_recursive,
            group_type = entry.get('GroupType'),
            contents = contents,
        )



class GachaElement(object):
    def __init__(self, id:int, gacha_group_id:int, parcel_type:str, parcel_id:int, rarity:str, parcel_amount_min:int, parcel_amount_max:int, prob:int, state:int):
        self.id = id
        self.gacha_group_id = gacha_group_id
        self.parcel_type = parcel_type
        self.parcel_id = parcel_id
        self.rarity = rarity
        self.parcel_amount_min = parcel_amount_min
        self.parcel_amount_max = parcel_amount_max
        self.prob = prob
        self.state = state


    def __repr__(self):
        return str(self.__dict__)
    

    @classmethod
    def from_data(cls, data):
        return cls(
            id =            data.get('ID', 0),
            gacha_group_id = data.get('GachaGroupID', 0),
            parcel_type =   data.get('ParcelType', ''),
            parcel_id =     data.get('ParcelID', 0),
            rarity =        data.get('Rarity', ''),
            parcel_amount_min = data.get('ParcelAmountMin', 1),
            parcel_amount_max = data.get('ParcelAmountMax', 1),
            prob =          data.get('Prob', 1),
            state =         data.get('State', 1),
        )
    


class GachaElementRecursive(GachaElement):
    def __init__(self, id:int, gacha_group_id:int, parcel_type:str, parcel_id:int, rarity:str, parcel_amount_min:int, parcel_amount_max:int, prob:int, state:int, gacha_group:GachaGroup):
        self.id = id
        self.gacha_group_id = gacha_group_id
        self.parcel_type = parcel_type
        self.parcel_id = parcel_id
        self.rarity = rarity
        self.parcel_amount_min = parcel_amount_min
        self.parcel_amount_max = parcel_amount_max
        self.prob = prob
        self.state = state

        self.gacha_group = gacha_group


    @classmethod
    def from_data(cls, entry, data):
        gacha_group = GachaGroup.from_id(entry['ParcelID'], data)

        return cls(
            id =            entry.get('ID', 0),
            gacha_group_id = entry.get('GachaGroupID', 0),
            parcel_type =   entry.get('ParcelType', ''),
            parcel_id =     entry.get('ParcelID', 0),
            rarity =        entry.get('Rarity', ''),
            parcel_amount_min = entry.get('ParcelAmountMin', 1),
            parcel_amount_max = entry.get('ParcelAmountMax', 1),
            prob =          entry.get('Prob', 1),
            state =         entry.get('State', 1),
            gacha_group =      gacha_group,
        )
