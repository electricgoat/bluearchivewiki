class Momotalk(object):
    def __init__(self, levels):
        self.levels = levels

    @classmethod
    def from_data(cls, character_id, data):
        levels = []

        for favor_reward in data.favor_rewards:
            if favor_reward[0] == character_id:
                #print(data.favor_rewards[(character_id , favor_reward[1])])
                levels.append(data.favor_rewards[(character_id , favor_reward[1])])  

        return cls(
            levels
        )
