import re

from shared.tag_map import map_tags
from shared.functions import replace_glossary


class Item(object):
    def __init__(self, id, rarity, category, name_jp, name_en, desc_jp, desc_en, icon, splash_icon, tags, characters_favorite, characters_likes, collection, tier, recipe, expiration_datetime: str = ""):
        self.id = id
        self.rarity = rarity
        self._category = category
        self.name_jp = name_jp
        self.name_en = name_en
        self.desc_jp = desc_jp
        self.desc_en = desc_en
        self.icon = icon
        self.splash_icon = splash_icon
        self.tags = tags
        self.characters_favorite = characters_favorite
        self.characters_likes = characters_likes
        self.collection = collection
        self.tier = tier
        self.recipe = recipe
        self.expiration_datetime = expiration_datetime


    @property
    def category(self):
        return {
            self._category : self._category,
            'Favor': 'Gifts',
            'Collectible':'Collectible',
            'Material':'Material',
            'Coin':'Currency',
            'Consumable':'Consumable',
            'CharacterExpGrowth':'Activity Report',
            'WeaponExpGrowth':'Weapon Component',
            'Exp':'Enhancement Stone',
            'SecretStone':'Eleph'
        }[self._category]



    @classmethod
    def from_data(cls, item_id, data):
        item = data.items[item_id]
        name_en = 'NameEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['NameEn'] or None
        desc_en = 'DescriptionEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['DescriptionEn'] or None

        # if name_en == None:
        #     print (f"No translation found for item {data.etc_localization[item['LocalizeEtcId']]['NameJp']}, id {item_id}, localizeEtcId {item['LocalizeEtcId']}")

        characters_favorite = []
        characters_likes = []


        tags_mapped = map_tags(item['Tags'])
        tags_list = "FavorItem" in tags_mapped and tags_mapped.remove("FavorItem") or tags_mapped
        tags_filtered = filter(lambda x: not x.startswith('F_') and not x.startswith('TagName'), tags_list)
        item_tags = list(tags_filtered)


        for character_id in data.characters_cafe_tags:
            character_wiki_name = data.translated_characters[character_id]['PersonalNameEn']
            character_wiki_name += f" ({data.translated_characters[character_id]['VariantNameEn']})" if 'VariantNameEn' in data.translated_characters[character_id] and data.translated_characters[character_id]['VariantNameEn'] is not None else ''
 
            tag_intersect = list(set(data.characters_cafe_tags[character_id]['FavorItemUniqueTags'] + data.characters_cafe_tags[character_id]['FavorItemTags']) & set(item['Tags']))
            
            if len(tag_intersect) >1 and character_wiki_name not in characters_favorite: 
                characters_favorite.append(character_wiki_name)
            if len(tag_intersect)==1 and character_wiki_name not in characters_likes: 
                characters_likes.append(character_wiki_name)

        if (len(characters_favorite)): characters_favorite.sort()
        if (len(characters_likes)): characters_likes.sort()

        match item['ItemCategory']:
            case 'Material':
                collection = item['Icon'][item['Icon'].rfind('/')+1:item['Icon'].rfind('_')].replace('Item_Icon_','').replace('Material_','')
            case 'Coin':
                collection = re.sub(r'_[0-9]+_', '_', item['Icon'])[item['Icon'].rfind('/')+1:].replace('Item_Icon_','')
                collection = re.sub(r'_[0-9]+$', '', collection)
                #print (collection)
            case _:        
                collection = None


        return cls(
            item['Id'],
            item['Quality']-1,
            item['ItemCategory'],
            data.etc_localization[item['LocalizeEtcId']]['NameJp'].replace("\n",' '),
            replace_glossary(name_en),
            data.etc_localization[item['LocalizeEtcId']]['DescriptionJp'] != None and data.etc_localization[item['LocalizeEtcId']]['DescriptionJp'].replace("\n\n",'<br>').replace("\n",'<br>') or '',
            desc_en != None and replace_glossary(desc_en).replace("\n\n",'<br>').replace("\n",'<br>') or '',
            item['Icon'][item['Icon'].rfind('/')+1:],
            item['Icon'][item['Icon'].rfind('_')+1:],
            item_tags,
            characters_favorite,
            characters_likes,
            collection,
            'Quality' in item and item['Quality'] or None,
            None, #recipe
            item.get('ExpirationDateTime', ""),
        )


    @classmethod
    def from_equipment_data(cls, item_id, data):
        item = data.equipment[item_id]
        name_en = 'NameEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['NameEn'] or None
        desc_en = 'DescriptionEn' in data.etc_localization[item['LocalizeEtcId']] and data.etc_localization[item['LocalizeEtcId']]['DescriptionEn'] or None

        quality =  {
            0: '0',
            5: '0',
            10:'1',
            20:'2',
            50:'3'
        }[item['CraftQuality']]
        
        category =  item['EquipmentCategory'][:-1] == 'WeaponExpGrowth' and 'WeaponExpGrowth' or item['EquipmentCategory']

        match category:
            case 'WeaponExpGrowth':
                collection = re.sub(r'_[0-9]+_', '_', item['Icon'])[item['Icon'].rfind('/')+1:].replace('Equipment_Icon_','')
                collection = re.sub(r'_[0-9]+$', '', collection)
                #print (collection)
            case 'Exp':        
                collection = 'Exp'
            case _:        
                collection = None

        tier = 'TierInit' in item and item['TierInit'] or None


        
        def get_recipe(item, data):
            #item RecipeId is for upgrading to the next tier, so we need to find previous tier equipment
            source_id = None
            for id in data.equipment:
                if (data.equipment[id]['NextTierEquipment'] == item['Id']):
                    #print (f"Source for item {item['Id']} found, id {id}")
                    source_id = id
                    break
            
            if (source_id == None): 
                return None

            recipe = data.recipe_ingredients[data.recipes[data.equipment[source_id]['RecipeId']]['RecipeIngredientId']]
            recipe_ingredient_names = []

            for ingredient_id in recipe['IngredientId']:
                recipe_ingredient_names.append ('NameEn' in data.etc_localization[data.equipment[ingredient_id]['LocalizeEtcId']] and data.etc_localization[data.equipment[ingredient_id]['LocalizeEtcId']]['NameEn'] or None)

            recipe['IngredientName'] = recipe_ingredient_names
            return recipe


        recipe = None
        recipe = get_recipe(item, data)
        #print(recipe)



        return cls(
            item['Id'],
            quality,
            category,
            data.etc_localization[item['LocalizeEtcId']]['NameJp'],
            replace_glossary(name_en),
            data.etc_localization[item['LocalizeEtcId']]['DescriptionJp'],
            replace_glossary(desc_en),
            item['Icon'][item['Icon'].rfind('/')+1:],
            item['Icon'][item['Icon'].rfind('_')+1:],
            [],
            [],
            [],
            collection,
            tier,
            recipe
        )



# def replace_glossary(item = None):
#     print ("model > replace_glossary is deprecated")
#     if item != None:
#         item = re.sub('Field', 'Outdoor', item)

#     return (item)


class Furniture(object):
    def __init__(self, id, rarity, category, subcategory, size_width, size_height, size_other, comfort_bonus, name_jp, name_en, desc_jp, desc_en, icon, group, interaction, sources):
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

    @classmethod
    def from_data(cls, furniture_id, data):
        print ("model > Furniture class is deprecated, use classes.Funiture > Furniture")

        furniture = data.furniture[furniture_id]
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
        print ("model > FurnitureGroup class is deprecated, use classes.Funiture > FurnitureGroup")

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
