from shared.functions import replace_glossary

furniture_interactions = None

class Furniture(object):
    def __init__(self, id, rarity, category, subcategory, size_width, size_height, size_other, comfort_bonus, name_jp, name_en, desc_jp, desc_en, icon, group, 
                 interaction, 
                 interaction_req: dict, 
                 interaction_add: dict, 
                 interaction_make: dict, 
                 interaction_only: dict, 
                 sources
                ):
        self.id = id
        self.rarity = rarity
        self._category = category
        self._subcategory = subcategory
        self.size_width = size_width
        self.size_height = size_height
        self.size_other = size_other
        self.comfort_bonus = comfort_bonus
        self.name_jp = name_jp
        self.name_en = name_en
        self.desc_jp = desc_jp
        self.desc_en = desc_en
        self.icon = icon
        self.group = group
        self.interaction = interaction
        self.interaction_req = interaction_req
        self.interaction_add = interaction_add
        self.interaction_make = interaction_make
        self.interaction_only = interaction_only
        self.sources = sources


    def __repr__(self):
        return str(self.__dict__)

    @property
    def category(self):
        return {
            'Furnitures': 'furniture',
            'Interiors': 'cafe decoration',
            'Decorations': 'decoration'
        }[self._category]

    @property
    def subcategory(self):
        return {
            'Floor': 'floor',
            'Wallpaper': 'wallpaper',
            'Background': 'background',
            'WallDecoration': 'wall',
            'Closet': 'closet',
            'FloorDecoration': 'floor',
            'Chair': 'chair',
            'Table': 'table',
            'Prop': 'prop',
            'HomeAppliance': 'appliance',
            'FurnitureEtc': 'trophy',
            'Bed': 'bed'
        }[self._subcategory]
    
    @property
    def interaction_all(self):
        return self.interaction_req | self.interaction_add | self.interaction_make | self.interaction_only

    @classmethod
    def from_data(cls, furniture_id, data):
        global furniture_interactions
        furniture = data.furniture[furniture_id]

        if furniture_interactions == None:
            print("Cataloging furniture interactions")
            furniture_interactions = FurnitureInteraction.get_dict(data)


        name_en = 'NameEn' in data.etc_localization[furniture['LocalizeEtcId']] and data.etc_localization[furniture['LocalizeEtcId']]['NameEn'] or None
        desc_en = 'DescriptionEn' in data.etc_localization[furniture['LocalizeEtcId']] and data.etc_localization[furniture['LocalizeEtcId']]['DescriptionEn'] or None
        
        furniture_group = furniture['SetGroudpId'] > 0 and FurnitureGroup.from_data(furniture['SetGroudpId'], data) or None

        interaction = []
        interaction_tags = set(furniture['CafeCharacterStateReq'] + furniture['CafeCharacterStateAdd'] + furniture['CafeCharacterStateMake'] + furniture['CafeCharacterStateOnly'])
        for item in data.cafe_interaction.values():
            if item['CafeCharacterState'] and bool(interaction_tags.intersection(item['CafeCharacterState'])):
                
                character_wiki_name = data.translated_characters[item['CharacterId']]['PersonalNameEn']
                character_wiki_name += f" ({data.translated_characters[item['CharacterId']]['VariantNameEn']})" if 'VariantNameEn' in data.translated_characters[item['CharacterId']] and data.translated_characters[item['CharacterId']]['VariantNameEn'] is not None else ''

                interaction.append(character_wiki_name)

        interaction_req = {x:furniture_interactions[x] for x in furniture['CafeCharacterStateReq']}
        interaction_add = {x:furniture_interactions[x] for x in furniture['CafeCharacterStateAdd']}
        interaction_make = {x:furniture_interactions[x] for x in furniture['CafeCharacterStateMake']}
        interaction_only = {x:furniture_interactions[x] for x in furniture['CafeCharacterStateOnly']}

        return cls(
            furniture['Id'],
            furniture['StarGradeInit'],
            furniture['Category'],
            furniture['SubCategory'],
            furniture['SizeWidth'],
            furniture['SizeHeight'],
            furniture['OtherSize'],
            furniture['ComfortBonus'],
            data.etc_localization[furniture['LocalizeEtcId']]['NameJp'],
            replace_glossary(name_en),
            data.etc_localization[furniture['LocalizeEtcId']]['DescriptionJp'],
            replace_glossary(desc_en),
            furniture['Icon'][furniture['Icon'].rfind('/')+1:],
            furniture_group,
            interaction,
            interaction_req,
            interaction_add,
            interaction_make,
            interaction_only,
            None #CraftNodes.from_data(furniture_id, data)
        )

        

class FurnitureGroup(object):
    def __init__(self, id, bonus_count, bonus_comfort, set_name_jp, set_name_en, set_desc_jp, set_desc_en, series_jp, series_en):
        self.id = id
        self.bonus_count = bonus_count
        self.bonus_comfort = bonus_comfort
        self.set_name_jp = set_name_jp
        self.set_name_en = set_name_en
        self.set_desc_jp = set_desc_jp
        self.set_desc_en = set_desc_en
        self.series_jp = series_jp
        self.series_en = series_en


    @classmethod
    def from_data(cls, group_id, data):
        furniture_group = data.furniture_group[group_id]
        #print(data.etc_localization[furniture['LocalizeEtcId']])
        name_en = 'NameEn' in data.etc_localization[furniture_group['GroupNameLocalize']] and data.etc_localization[furniture_group['GroupNameLocalize']]['NameEn'] or None
        desc_en = 'DescriptionEn' in data.etc_localization[furniture_group['GroupNameLocalize']] and data.etc_localization[furniture_group['GroupNameLocalize']]['DescriptionEn'] or None
        

        try: 
            series_jp = data.etc_localization[furniture_group['LocalizeEtcId']]['NameJp'] 
        except:
            series_jp = None
            pass
        try: 
            series_en = data.etc_localization[furniture_group['LocalizeEtcId']]['NameEn'] 
        except:
            series_en = None
            #print(furniture_group['LocalizeEtcId'])
            pass

        return cls(
            furniture_group['Id'],
            furniture_group['RequiredFurnitureCount'],
            furniture_group['ComfortBonus'],
            data.etc_localization[furniture_group['GroupNameLocalize']]['NameJp'],
            replace_glossary(name_en),
            data.etc_localization[furniture_group['GroupNameLocalize']]['DescriptionJp'],
            replace_glossary(desc_en),
            series_jp,
            replace_glossary(series_en)
        )
    


class FurnitureInteraction(object):
    def __init__(self, character_state: str, character_id: int, ignore_if_unobtained: bool, ignore_if_unobtained_start: str, ignore_if_unobtained_end: str):
        self.character_state = character_state
        self.character_id = character_id
        self.ignore_if_unobtained = ignore_if_unobtained
        self.ignore_if_unobtained_start = ignore_if_unobtained_start
        self.ignore_if_unobtained_end = ignore_if_unobtained_end

    def __repr__(self):
        return str(self.__dict__)
    
    @classmethod
    def list_character_states(cls, character_id, data) -> list:
        list = []
        interaction = data.cafe_interaction[character_id]

        for state in interaction['CafeCharacterState']:
            list.append(cls(
                state,
                interaction["CharacterId"],
                interaction["IgnoreIfUnobtained"],
                interaction["IgnoreIfUnobtainedStartDate"],
                interaction["IgnoreIfUnobtainedEndDate"],
            ))

        return list
        

    @staticmethod
    def get_dict(data, key = 'character_state') -> dict:
        entries = []

        for character_id in data.cafe_interaction:
            entries += FurnitureInteraction.list_character_states(character_id, data)
            
        return {getattr(x, 'character_state'):x for x in entries}
