class MemoryLobby(object):
    def __init__(self, image, bgm_id, unlock_level, lobby_id_list = []):
        self.image = image
        self.bgm_id = bgm_id
        self.unlock_level = unlock_level
        self.lobby_id_list = lobby_id_list


    @classmethod
    def from_data(cls, character_id, data):
        lobby_id_list = [x['Id'] for x in data.memory_lobby.values() if x['CharacterId'] == character_id]
        try: 
            lobby_data = data.memory_lobby[lobby_id_list[0]]
        except KeyError: return cls( None, None, 1, [] )
        except IndexError: return cls( None, None, 1, [] )

        unlock_level = None
        for favor_reward in data.favor_rewards:
            if favor_reward[0] == character_id:
                if 'MemoryLobby' in data.favor_rewards[(character_id , favor_reward[1])]['RewardParcelType']: unlock_level = data.favor_rewards[(character_id , favor_reward[1])]['FavorRank']
        
        return cls(
            lobby_data['RewardTextureName'][lobby_data['RewardTextureName'].rfind('/')+1:],
            lobby_data['BGMId'],
            unlock_level,
            lobby_id_list
        )
