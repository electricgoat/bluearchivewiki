import collections
import os
import re
import json
import traceback
import argparse
from datetime import datetime
from pathlib import Path

from data import load_data, load_season_data
from model import Character
import wiki


class BannerImage:
    def __init__(self, src_filename:str|None, src_dir:str|Path, wikinames:list[str]):
        self.src_filename = src_filename
        self.src_dir = src_dir
        self.wikinames:list[str] = wikinames
    
    @property
    def is_wikinamed(self) -> bool:
        return os.path.exists(os.path.join(self.src_dir, 'wikinamed', self.wikinames[0]))
    
    @property
    def get_file(self) -> Path|None:
        if self.is_wikinamed: return os.path.join(self.src_dir, 'wikinamed', self.wikinames[0])
        if self.src_filename is not None and os.path.exists(os.path.join(self.src_dir, 'banner', self.src_filename)): return os.path.join(self.src_dir, 'banner', self.src_filename)
        return None


class Banner:
    name_jp = ''
    name_en = ''
    featured_characters:list[Character] = []

    image_banner_jp:BannerImage|None = None
    image_lobby_banner_jp:BannerImage|None = None

    #lobby_image_wikiname:str = None
    #image_source:str|None = None
    #image_wikinames:list[str] = []
    rerun_original_id:int|None = None
    prodnotice_data = None

    def __init__(self, banner_data):
        self.id = banner_data.get('Id')
        self.category_type = banner_data.get('CategoryType')
        self.is_legacy = banner_data.get('IsLegacy')
        self.one_gacha_goods_id = banner_data.get('OneGachaGoodsId')
        self.ten_gacha_goods_id = banner_data.get('TenGachaGoodsId')
        self.goods_dev_name = banner_data.get('GoodsDevName', "")
        self.display_tag = banner_data.get('DisplayTag', "None")
        self.display_order = banner_data.get('DisplayOrder', 0)
        self.gacha_banner_path = banner_data.get('GachaBannerPath', "")
        self.video_id = banner_data.get('VideoId', [])
        self.linked_lobby_banner_id = banner_data.get('LinkedRobbyBannerId')
        self.info_character_id = banner_data.get('InfoCharacterId', [])
        self.sale_period_from = self.parse_date(banner_data.get('SalePeriodFrom'))
        self.sale_period_to = self.parse_date(banner_data.get('SalePeriodTo'))
        self.recruit_coin_id = banner_data.get('RecruitCoinId')
        self.recruit_selection_shop_id = banner_data.get('RecruitSellectionShopId')
        self.purchase_cooltime_min = banner_data.get('PurchaseCooltimeMin', 0)
        self.purchase_count_limit = banner_data.get('PurchaseCountLimit', 0)
        self.purchase_count_reset_type = banner_data.get('PurchaseCountResetType', "None")
        self.is_newbie = banner_data.get('IsNewbie', False)
        self.is_select_recruit = banner_data.get('IsSelectRecruit', False)
        self.direct_pay_invisible_token_id = banner_data.get('DirectPayInvisibleTokenId', 0)
        self.direct_pay_android_shop_cash_id = banner_data.get('DirectPayAndroidShopCashId', 0)
        self.direct_pay_apple_shop_cash_id = banner_data.get('DirectPayAppleShopCashId', 0)

    def parse_date(self, date_str):
        if date_str:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return None

    def is_active(self):
        now = datetime.now()
        return self.sale_period_from <= now <= self.sale_period_to if self.sale_period_from and self.sale_period_to else False

    def __repr__(self):
        return f"<Banner ID={self.id}, Category={self.category_type}, Active={self.is_active()}>"



args = None
data = None
season_data = {'jp':None, 'gl':None}
banners:dict[int:Banner] = {}
prodnotice_banners = []
prodnotice_events = []

characters = {}



def find_notice_for_character(character_name):
    global prodnotice_events
    
    #print(f"Looking for relevant notice of {character_name}")

    STRIP_CHARS = "★123「」、,（）()"
    translation_table = str.maketrans('', '', STRIP_CHARS)
    def str_normalize(str):
        #return str.strip(STRIP_CHARS).replace('（','(').replace('）',')').replace('、',',')
        return str.translate(translation_table)
        
    earliest_notice = None
    for notice in prodnotice_events:
        for banner_character in notice.get('BannerCharacters', []):
            #print(f'{banner_character} -> {banner_character.strip(STRIP_CHARS)}')
            if str_normalize(character_name) == str_normalize(banner_character):
                if earliest_notice is None or notice['StartDate'] < earliest_notice['StartDate']:
                    earliest_notice = notice
                break  # Exit loop once we find a match in this notice
    
    if earliest_notice:
        #print(f"Found a notice of {character_name}")
        # Find the index of the character in the BannerCharacters list
        character_index = [str_normalize(c) for c in earliest_notice['BannerCharacters']].index(str_normalize(character_name))
        # Get the corresponding BannerNames and DownloadedImages
        corresponding_banner_name = earliest_notice['BannerNames'][character_index]
        corresponding_image = earliest_notice['DownloadedImages'][character_index]
        
        return {
            "NoticeId": earliest_notice['NoticeId'],
            "StartDate": earliest_notice['StartDate'],
            "EndDate": earliest_notice['EndDate'],
            "BannerName": corresponding_banner_name,
            "DownloadedImage": corresponding_image
        }
    else:
        return None


def init_data():
    global args, data, season_data, characters, prodnotice_banners, prodnotice_events
    
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    season_data['jp'] = load_season_data(args['data_primary'])
    season_data['gl'] = load_season_data(args['data_secondary']) 

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':#  not in ['Release', 'Complete']:
            continue

        try:
            character = Character.from_data(character['Id'], data)
            characters[character.id] = character
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue

    
    # Load known banners and notices from ba-nnerwatch
    known_banners_file = Path(os.path.join(args['bannerwatch'], 'known_banners.json'))
    if known_banners_file.exists():
        with open(known_banners_file, "r", encoding="utf-8") as f:
            prodnotice_banners = json.load(f)   

    known_events_file = Path(os.path.join(args['bannerwatch'], 'known_events.json'))
    if known_events_file.exists():
        with open(known_events_file, "r", encoding="utf-8") as f:
            prodnotice_events = json.load(f)


def init_banners(region: str):
    global season_data
    global banners, characters, prodnotice_banners, prodnotice_events

    prodnotice_banners_by_llbid = {x['LinkedLobbyBannerId']:x for x in prodnotice_banners if 'LinkedLobbyBannerId' in x}

    for banner_data in sorted(season_data[region].shop_recruit.values(), key=lambda x: x['SalePeriodFrom']):
        if banner_data['CategoryType'] not in ['PickupGacha', 'LimitedGacha', 'FesGacha']:
            continue
        
        banner = Banner(banner_data)         
        
        banner.prodnotice_data = prodnotice_banners_by_llbid.get(banner.linked_lobby_banner_id)
        banner.featured_characters = [characters[id] for id in banner.info_character_id]
        
        notice = find_notice_for_character(''.join([x.wiki_name_jp for x in banner.featured_characters]))
        if notice is not None: 
            banner.name_jp = notice['BannerName']
            #if banner.image_source is None: banner.image_source = notice['DownloadedImage']

        for prev_banner in banners.values():
            if prev_banner.info_character_id == banner.info_character_id: 
                #print(f"This is a rerun of banner {prev_banner.id}")
                banner.rerun_original_id = prev_banner.id

        #if banner.prodnotice_data is not None:
            #lobby_banner_basename = f"Lobby_Banner_{banner.sale_period_from.strftime('%Y%m%d')}"
            #lobby_banner_prodnotice_name = banner.prodnotice_data.get('FileName', [])[0]

            # if lobby_banner_prodnotice_name.lower().startswith(lobby_banner_basename.lower()):
            #     print(f"Lobby Banner filename as expected: {lobby_banner_prodnotice_name}")
            # else:
            #     print(f"Lobby Banner basename is not as expected: {lobby_banner_basename} / {lobby_banner_prodnotice_name}")
            
            #banner.lobby_image_wikiname = f"{lobby_banner_basename}_{lobby_banner_prodnotice_name.split('_')[-2]}.png"

        banner.image_banner_jp = BannerImage(notice is not None and notice.get('DownloadedImage') or None, args['bannerwatch'], [f"Banner_{region.capitalize()}_{x.wiki_name.replace(' ','_')}.png" for x in banner.featured_characters])    
        


        banners[banner.id] = banner



def upload_banners():
    for banner in banners.values():
        wikitext = f"[[Category:Pick-up banner images]]\r\n"
        for character in banner.featured_characters: wikitext += f"[[Category:{character.personal_name_en} images]]\r\n"

        if banner.linked_lobby_banner_id == 15:
            continue #Shiroko + Hoshino game opening banner

        if banner.rerun_original_id is not None:
            continue #skip uploading rerun images

        if banner.image_banner_jp.get_file is None:
            print(f"Banner {str(banner.linked_lobby_banner_id)} {', '.join([x.wiki_name for x in banner.featured_characters])} is missing an image.")
            continue

        assert len(banner.image_banner_jp.wikinames[0]), f"Banner wikiname must be set, currently {banner.image_banner_jp.wikinames[0]}"


        if not wiki.page_exists(f"File:{banner.image_banner_jp.wikinames[0]}"):
            #print(f"Uploading file {banner.image_banner_jp.get_file} as {banner.image_banner_jp.wikinames[0]}")
            wiki.upload(banner.image_banner_jp.get_file, banner.image_banner_jp.wikinames[0], 'Pick-up banner image', wikitext)

        if len(banner.image_banner_jp.wikinames)>1:
            for redirname in banner.image_banner_jp.wikinames[1:]:
                print(f"Creating redirect from {redirname} to {banner.image_banner_jp.wikinames[0]}")
                wiki.redirect(f"File:{redirname}", f"File:{banner.image_banner_jp.wikinames[0]}", 'Pick-up banner image redirect for secondary character')




def list_banners():
    print ("============ JP banners ============")
    print_server('jp')
    #print ("============ GL banners ============")
    #print_server('gl')


def print_server(region: str):
    global banners

    now = datetime.now() #does not account for timezone

    for banner in banners.values():
        note = ''
        if (banner.sale_period_from > now): note = 'future'
        elif (banner.sale_period_to > now): note = 'current'

        print (f"{str(banner.category_type).rjust(14, ' ')} {str(banner.linked_lobby_banner_id).ljust(4)} {str(banner.info_character_id).ljust(14)} {', '.join([x.wiki_name for x in banner.featured_characters]).ljust(32)}: {banner.sale_period_from} ~ {banner.sale_period_to} {note.ljust(8)} ", end ="")
        if banner.rerun_original_id is None: 
            print (f"      {banner.image_banner_jp.is_wikinamed and 'wikinamed' or banner.image_banner_jp.get_file} {banner.rerun_original_id is None and banner.image_banner_jp.wikinames or ''}")
        else: print('rerun')

        # if banner.rerun_original_id is None and banner.image_source and banner.image_wikinames:
        #     shutil.copy(os.path.join(args['bannerwatch'], 'banner', banner.image_source), os.path.join(args['bannerwatch'], 'wikinamed', banner.image_wikinames[0]))


def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('event_season',     metavar='event_season', nargs='?', default=None, help='Event season to export')
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-bannerwatch',     metavar='DIR', default='../ba-nnerwatch', help='Path to ba-nnerwatch working dir')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2,   metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki')

    args = vars(parser.parse_args())
    print(args)

    try:

        init_data()
        init_banners('jp')

        if args['wiki'] != None:
            wiki.init(args)
            upload_banners()
        else:
            list_banners()

    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
