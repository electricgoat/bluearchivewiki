# import collections
# import re
from shared.functions import replace_glossary

class Emblem(object):
    def __init__(self, id, category, rarity, name, description, text, text_visible:bool, icon_path, emblem_icon_path, emblem_iconbg_path, emblem_bg_path, emblem_icon, check_type, check_param, check_value, raw_data = None):
        self.id = id
        self.category = category
        self._rarity = rarity
        self.name = name
        self.description = description
        self.text = text
        self.text_visible = text_visible
        self.icon_path = icon_path
        self.emblem_icon_path = emblem_icon_path
        self.emblem_iconbg_path = emblem_iconbg_path
        self.emblem_bg_path = emblem_bg_path
        #
        self.emblem_icon = emblem_icon
        #
        self.check_type = check_type
        self.check_param = check_param
        self.check_value = check_value
        self._raw_data = raw_data


    def __repr__ (self):
        return f"Emblem:{self.name}"

    
    @property
    def rarity(self):
        return {
            "N":'0',
            "R":'1',
            "SR":'2',
            "SSR":'3'
        }[self._rarity]
    

    @property
    def icon(self):
        if self.icon_path == '': return ''
        return self.icon_path.rsplit('/',1)[-1] + '.png'
    
    # @property
    # def emblem_icon(self):
    #     if self.emblem_icon_path == '': return ''
    #     return self.emblem_icon_path.rsplit('/',1)[-1] + '.png'
    
    @property
    def emblem_iconbg(self):
        if self.emblem_iconbg_path == '': return ''
        return self.emblem_iconbg_path.rsplit('/',1)[-1] + '.png'
    
    @property
    def emblem_bg(self):
        if self.emblem_bg_path == '': return ''
        return self.emblem_bg_path.rsplit('/',1)[-1] + '.png'


    
    @classmethod
    def from_data(cls, id, data, characters, ext_missing_etc_localization = None, ext_missing_localization = None):
        entry = data.emblem[id]

        name = ''
        description = ''
        text = ''
        emblem_icon = entry['EmblemIconPath'] and entry['EmblemIconPath'].rsplit('/',1)[-1] + '.png' or ''

        if entry['LocalizeEtcId'] > 0:
            etc_localization = data.etc_localization[entry['LocalizeEtcId']]
            if 'NameEn' not in etc_localization and ext_missing_etc_localization: ext_missing_etc_localization.add_entry(etc_localization)
            name = etc_localization.get('NameEn') or etc_localization.get('NameJp', '')
            description = etc_localization.get('DescriptionEn') or etc_localization.get('DescriptionJp', '')

        if entry['LocalizeCodeId'] > 0:
            localization = data.localization[entry['LocalizeCodeId']]
            if 'En' not in localization and ext_missing_localization: ext_missing_localization.add_entry(localization)
            text = localization.get('En') or etc_localization.get('Jp', '')


        if entry['Category'] == "Favor":
            name = characters[entry['EmblemParameter']].full_name_en
            description = f"Reach affection rank {entry['CheckPassCount']} with {characters[entry['EmblemParameter']].wiki_name}"
            emblem_icon = f"Emblem_Icon_Favor_{characters[entry['EmblemParameter']].wiki_name.replace(' ','_')}.png"

        if entry['Category'] == "Boss":
            def bosstext(id):
                return {
                    id:'Unknown, Boss',
                    5: 'Shiro & Kuro, Indoors',
                    8: 'Goz, Oudoors',
                    11: 'Binah, Urban'
                }[id]
            text = bosstext(entry['UseAtLocalizeId'])

        if entry['Category'] == "MainStory" and entry['EmblemParameter']:
            description = description.replace('{0}', str(int(str(entry['EmblemParameter'])[1:3]))).replace('{1}', str(int(str(entry['EmblemParameter'])[3:5])))
        
        if entry['Category'] == "GroupStory" and entry['EmblemParameter']:
            description = description.replace('{0}', str(int(str(entry['EmblemParameter'])[2:4])))


        return cls(
            id = entry['Id'],
            category = entry['Category'],
            rarity = entry['Rarity'],
            name = replace_glossary(name),
            description = replace_glossary(description),
            text = text,
            text_visible = entry['EmblemTextVisible'],
            icon_path = entry['IconPath'],
            emblem_icon_path = entry['EmblemIconPath'],
            emblem_iconbg_path = entry['EmblemIconBGPath'],
            emblem_bg_path = entry['EmblemBGPathJp'],
            #
            emblem_icon = emblem_icon,
            #
            check_type = entry['CheckPassType'],
            check_param = entry['EmblemParameter'],
            check_value = entry['CheckPassCount'],
            raw_data = entry,
        )
