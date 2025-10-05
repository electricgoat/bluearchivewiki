import os
from datetime import datetime
from pathlib import Path

REGION_TIMEZONE = {'jp':'+09', 'gl':'+09'}

class BannerImage:
    def __init__(self, src_filename:str|None, src_dir:str|Path, wikinames:list[str]):
        self.src_filename = src_filename
        self.src_dir = src_dir
        self.wikinames:list[str] = wikinames
    
    @property
    def is_wikinamed(self) -> bool:
        return len(self.wikinames)>0 and os.path.exists(os.path.join(self.src_dir, self.wikinames[0]))
    
    @property
    def get_file(self) -> Path|None:
        if self.is_wikinamed:
            return Path(os.path.join(self.src_dir, self.wikinames[0]))
        if self.src_filename is not None and os.path.exists(os.path.join(self.src_dir, self.src_filename)):
            return Path(os.path.join(self.src_dir, self.src_filename))
        return None
    
    @property
    def sequence_number(self) -> int|None:
        try:
            return int(self.wikinames[0].split('_')[-1].split('.')[0])
        except:
            return None


class Banner:
    region:str = 'jp'
    name_jp:str = ''
    name_en:str = ''
    name_en_global:str = ''
    name_en_global_rerun:str = ''
    featured_characters = []
    notes = ''

    image_banner:BannerImage|None = None
    image_lobby_banner:BannerImage|None = None

    rerun_original_id:int|None = None
    rerun_cnt:int = 0
    prodnotice_data = None
    crossregion_id = 0

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
        self.sale_period_from = self.parse_date(banner_data.get('SalePeriodFrom') or "2021-02-04 16:00:00")
        self.sale_period_to = self.parse_date(banner_data.get('SalePeriodTo') or "2099-12-31 03:59:59")
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
        self.selectable_gacha_group_id = banner_data.get('SelectAbleGachaGroupId', 0)


    def parse_date(self, date_str):
        if date_str:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return None

    @property
    def is_active(self):
        now = datetime.now()
        return self.sale_period_from <= now <= self.sale_period_to if self.sale_period_from and self.sale_period_to else False
    
    @property
    def is_limited(self):
        return self.category_type in ['LimitedGacha', 'FesGacha']
    
    @property
    def is_rerun(self):
        return self.rerun_original_id is not None
    
    @property
    def wiki_featured_characters(self):
        return [x.wiki_name for x in self.featured_characters]
    
    @property
    def wiki_sale_period_from(self):
        assert self.sale_period_from is not None
        return self.sale_period_from.strftime("%Y-%m-%dT%H:%M") + REGION_TIMEZONE[self.region]

    @property
    def wiki_sale_period_to(self):
        assert self.sale_period_to is not None
        return self.sale_period_to.strftime("%Y-%m-%dT%H:%M") + REGION_TIMEZONE[self.region]
    

    @property
    def wiki_notes(self):
        notes = []
        # if self.category_type == 'FesGacha': 
        #     notes.append('anniversary')
        # if self.category_type == 'LimitedGacha': 
        #     notes.append('Limited')
        # if self.rerun_original_id is not None: 
        #     notes.append('rerun')
        # if (self.sale_period_from and self.sale_period_from > datetime.now()): 
        #     notes.append('future')
        # elif (self.sale_period_to and self.sale_period_to > datetime.now()): 
        #     notes.append('current')

        if self.notes:  notes.append((len(notes)>0 and '\n' or '')+self.notes)
        return notes
    
    @property
    def featured_name(self):
        return ','.join([x.wiki_name for x in self.featured_characters]) if self.featured_characters else 'None'
    
    @property
    def get_name_global(self):
        if self.is_rerun and self.name_en_global_rerun != '':
            return self.name_en_global_rerun
        return self.name_en_global if self.name_en_global else self.name_en if self.name_en else ''
    
    @property
    def bannercode(self):
        code = ','.join([x.wiki_name.replace(' ','_') for x in self.featured_characters]) + '_' 
        if not self.is_rerun:
            code += 'release'
        else:
            code += f'rerun{self.rerun_cnt}'
        return code
    
    @property
    def uid(self):
        return self.region.upper() + '_' + self.bannercode
    
    def __repr__(self):
        return f"<Banner ID={self.id}, Category={self.category_type}, Active={self.is_active}>"


