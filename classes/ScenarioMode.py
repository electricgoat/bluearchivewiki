import re
from shared.functions import hashkey


class ScenarioMode(object):
    def __init__(self, id, volume, chapter, episode, volume_title, chapter_title, episode_title):
        self.id = id
        self.volume = volume
        self.chapter = chapter
        self.episode = episode
        self.volume_title = volume_title
        self.chapter_title = chapter_title
        self.episode_title = episode_title

    @property
    def page(self):
        return self.volume and f"Main Story/{self.volume}/Chapter {self.chapter}/Episode {self.episode}"

    @classmethod
    def from_data(cls, mode_id, data):
        mode = data.scenario_modes.get(mode_id, {})
        volume = main_story_volume(mode)
        if volume is None:
            print(f"WARNING - scenario mode {mode_id} is not a Main Story episode, its story can't be named")
            return cls(mode_id, None, None, None, None, None, None)

        return cls(
            mode_id,
            volume,
            mode['ChapterId'],
            mode['EpisodeId'],
            re.sub(r'^\S+[.:] ', '', title(data, mode, 'Volume', mode['VolumeId'])), #drops the volume's number, "1. ", "Ex. "
            title(data, mode, 'Chapter', mode['VolumeId'], mode['ChapterId']),
            title(data, mode, 'Episode', mode['VolumeId'], mode['ChapterId'], mode['EpisodeId']),
        )


def main_story_volume(mode) -> str|None:
    """The volume of the wiki's Main Story pages a scenario mode is in"""
    match mode.get('ModeType'), mode.get('SubType'):
        case 'Main', 'Series1': return 'Volume F' if mode['VolumeId'] == 100 else f"Volume {mode['VolumeId']}"
        case 'SpecialOperation', 'Series1': return 'Volume EX'
        case 'Main', 'Series2': return f"Act 2/Volume {mode['DisplayVolumeId']}"
        case 'SpecialOperation', 'Series2': return 'Act 2/Volume EX'
    return None


def title(data, mode, part, *ids) -> str:
    """Title of a Main Story volume, chapter or episode, keyed as the client keys it: Main_Chapter_Title_1_3, Main_Chapter_Title_Series2_2_1"""
    series = [] if mode['SubType'] == 'Series1' else [mode['SubType']]
    localized = data.localization.get(hashkey('_'.join([mode['ModeType'], part, 'Title', *series, *map(str, ids)])), {})
    return localized.get('En') or localized.get('Jp', '')
