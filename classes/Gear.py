import itertools
import operator

from shared.functions import replace_statnames


class Gear(object):
    def __init__(self, name_en, name_jp, desc_en, desc_jp, icon, tiers, tier1_desc, tier2_desc, effect_data, unlock_level):
        self.name_en = name_en
        self.name_jp = name_jp
        self.desc_en = desc_en
        self.desc_jp = desc_jp
        self.icon = icon
        self.tiers = tiers
        self.tier1_desc = tier1_desc
        self.tier2_desc = tier2_desc
        self.effect_data = effect_data
        self.unlock_level = unlock_level


    @classmethod
    def from_data(cls, character_id, data):
        gear_tiers_data = [entry for entry in data.gear.values() if entry['CharacterId'] == character_id]
        # if not gear:
        #     raise KeyError(character_id)

        tiers = [GearTier.from_data(tier, data) for tier in sorted(gear_tiers_data, key=operator.itemgetter('Tier'))]
        unlock_level = tiers[0].unlock_favor

        
        stat_bonus_text = []
        for index,stat_type in enumerate(tiers[0].stats['stat_type']):
            stat_bonus_text.append(stat_type + " by {{SkillValue|" + str(tiers[0].stats['stat_value'][index]) + "}}")

        tier1_desc = "Increase " + (" and ".join(stat_bonus_text))
        tier2_desc = 'Normal Skill changes to '

        effect_data = {'stat_name': tiers[0].stats['stat_type'][0], 'amount_base': str(tiers[0].stats['stat_value'][0])}

        if 'NameEn' not in data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]: print (f"Missing Unique Gear translation, LocalizeEtcId {data.gear[(character_id , 1)]['LocalizeEtcId']}")

        return cls(
            'NameEn' in data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]] and data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['NameEn'] or None,
            data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['NameJp'],
            'DescriptionEn' in data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]] and '<p>' + data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['DescriptionEn'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>' or None,
            '<p>' + data.etc_localization[data.gear[(character_id , 1)]["LocalizeEtcId"]]['DescriptionJp'].replace("\n\n",'</p><p>').replace("\n",'<br>') + '</p>',
            data.gear[(character_id , 1)]['Icon'].rsplit('/', 1)[-1],
            tiers,
            tier1_desc,
            tier2_desc,
            effect_data,
            unlock_level,
        )


class GearTier(object):
    def __init__(self, tier, unlock_favor, materials, stats):
        self.tier = tier
        self.unlock_favor = unlock_favor
        self.materials = materials
        self.stats = stats

    @classmethod
    def from_data(cls, tier, data):
        return cls(
            tier['Tier'],
            tier['OpenFavorLevel'],
            tier['Tier']>1 and list(get_recipe_materials(data.gear[(tier['CharacterId'], tier['Tier']-1)]['RecipeId'], data)) or None,
            {'stat_type':replace_statnames(tier['StatType']), 'stat_value':tier['MaxStatValue']}
        )


def get_recipe_materials(recipe_id, data):
    if recipe_id not in data.recipes:
        return
    recipe = data.recipes[recipe_id]
    #if recipe['RecipeType'] != 'EquipmentTierUp':
    #    return

    ingredients = data.recipes_ingredients[recipe['RecipeIngredientId']]
    ingredients = itertools.chain(
        zip(ingredients['IngredientParcelType'], ingredients['IngredientId'], ingredients['IngredientAmount']),
        zip(ingredients['CostParcelType'], ingredients['CostId'], ingredients['CostAmount'])
    )
    for type_, id, amount in ingredients:
        if type_ == 'Item':
            #yield data.etc_localization[data.items[id]['LocalizeEtcId']]['NameEn'], data.items[id]['Icon'].rsplit('/', 1)[-1], amount
            yield data.etc_localization[data.items[id]['LocalizeEtcId']]['NameEn'], amount
        elif type_ == 'Currency':
            #yield data.translated_currencies[id]['NameEn'], data.currencies[id]['Icon'].rsplit('/', 1)[-1], amount
            yield data.translated_currencies[id]['NameEn'], amount
