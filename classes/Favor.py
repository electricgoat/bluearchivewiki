from shared.functions import replace_statnames


class Favor(object):
    def __init__(self, levels):
        self.levels = levels

    @classmethod
    def from_data(cls, character_id, data):
        levels = {}

        for favor_level in data.favor_levels:
            if favor_level[0] == character_id:
                #print(replace_statnames(data.favor_levels[(character_id , favor_level[1])]['StatType']))
                levels[favor_level[1]] = {'stat_type':replace_statnames(data.favor_levels[(character_id , favor_level[1])]['StatType']), 'stat_value':data.favor_levels[(character_id , favor_level[1])]['StatValue']}  

        return cls(
            levels
        )
