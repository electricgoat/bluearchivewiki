from classes.Gear import get_recipe_materials


class Potential(object):
    def __init__(self, groups):
        self.groups = groups

        self.stat_groups = ['AttackPower', 'MaxHP', 'HealPower']

    @property
    def max_level(self):
        return len(self.groups['AttackPower']['levels'])
    

    @classmethod
    def from_data(cls, character_id, data):

        potential_groups = {x['PotentialStatBonusRateType']:x for x in data.character_potential[character_id]}
        
        for stat_group in potential_groups.values():
            stat_group['levels'] = data.character_potential_stat[stat_group['PotentialStatGroupId']]
            for level in stat_group['levels']:
                level['materials'] = get_recipe_materials(level['RecipeId'], data)
                #print(recipe)

        #print(potential_levels)
        return cls(
            potential_groups
        )
