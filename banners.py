import collections
import os
import re
import json
import traceback
import argparse
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from data import load_data, load_season_data, BlueArchiveData
from model import Character
from classes.Banner import Banner, BannerImage
import wiki

IGNORE_ID = {
	'jp':
		[
			50001, #Cherino banner 2021-03-07~2021-04-29, didn't happen
		],
	'gl':
		[]
	}

UNIQUE_LOBBY_IMAGE_BANNER_ID = {
	'jp': [],
	'gl': [
		90050127,
		90050129,
		90050136,
		]
}

EXPORT_CAT = ['PickupGacha', 'LimitedGacha', 'FesGacha', ] #'SelectPickupGacha'


args = {}
data:BlueArchiveData
regional_data = {}
known_lobby_banners_jp = {}
prodnotice_events_jp = []
banner_names = {}
characters = {}



def find_notice_for_character(character_name):
	global prodnotice_events_jp
	
	#print(f"Looking for relevant notice of {character_name}")

	STRIP_CHARS = "★123「」、,（）()"
	translation_table = str.maketrans('', '', STRIP_CHARS)
	def str_normalize(str):
		#return str.strip(STRIP_CHARS).replace('（','(').replace('）',')').replace('、',',')
		return str.translate(translation_table)
		
	earliest_notice = None
	for notice in prodnotice_events_jp:
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
	global args, data, regional_data, characters, known_lobby_banners_jp, known_lobby_banners_gl, prodnotice_events_jp, banner_names
	
	data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

	regional_data['jp'] = load_season_data(args['data_primary'])
	regional_data['gl'] = load_season_data(args['data_secondary']) 

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
	known_banners_files = {
		'jp': Path(os.path.join(args['bannerwatch'], 'known_lobby_banners_jp.json')), 
		'gl': Path(os.path.join(args['bannerwatch'], 'known_lobby_banners_gl.json'))
		}
	for region in ['jp', 'gl']:
		known_banners_file = known_banners_files[region]
		if known_banners_file.exists():
			with open(known_banners_file, "r", encoding="utf-8") as f:
				if region == 'jp':
					known_lobby_banners_jp = {x['LinkedLobbyBannerId']:x for x in json.load(f) if 'LinkedLobbyBannerId' in x}
				else:
					known_lobby_banners_gl = {key:x for key, x in json.load(f).items()}

	known_events_file = Path(os.path.join(args['bannerwatch'], 'known_events.json'))
	if known_events_file.exists():
		with open(known_events_file, "r", encoding="utf-8") as f:
			prodnotice_events_jp = json.load(f)

	banner_names_file = Path(os.path.join(args['translation'], 'banner_names.json'))
	if banner_names_file.exists():
		with open(banner_names_file, "r", encoding="utf-8") as f:
			banner_names = json.load(f)



def init_banners(region: str):
	global data, regional_data
	global characters, known_lobby_banners_jp, known_lobby_banners_gl, banner_names, prodnotice_events_jp

	banners:dict[int,Banner] = {}
	lobby_banner_map = {}
	sameday_sequence_num = 1

	shop_recruit_sorted:list[dict] = sorted(regional_data[region].shop_recruit.values(), key=lambda x: x['SalePeriodFrom'])
	prev_id = 0

	for banner_data in shop_recruit_sorted:
		if banner_data['Id'] in IGNORE_ID[region]:
			#print(f"Skipping banner {banner_data['Id']}: in IGNORE_ID[region]")
			continue
		if banner_data['CategoryType'] not in EXPORT_CAT:
			#print(f"Skipping banner {banner_data['Id']} of category {banner_data['CategoryType']}: not in EXPORT_CAT")
			continue
		
		banner = Banner(banner_data)    
		banner.region = region

		if region == 'jp': 
			banner.prodnotice_data = known_lobby_banners_jp.get(banner.linked_lobby_banner_id)
		elif region == 'gl': 
			banner.prodnotice_data = None
 
		banner.featured_characters = [characters[id] for id in banner.info_character_id]
		if banner_data['CategoryType'] == 'SelectPickupGacha' and banner.selectable_gacha_group_id > 0:
			#print(f"This is a SelectPickupGacha banner")
			select_group = data.gacha_select_pickup_group.get(banner.selectable_gacha_group_id, [])
			banner.featured_characters = [characters[entry['CharacterId']] for entry in select_group]
		
		if banner.featured_name in banner_names:
			banner.name_jp = banner_names[banner.featured_name].get('NameJp', '').strip()
			banner.name_en = banner_names[banner.featured_name].get('NameEn', '').strip()
			banner.name_en_global = banner_names[banner.featured_name].get('NameEnGlobal', '').strip()
			banner.name_en_global_rerun = banner_names[banner.featured_name].get('NameEnGlobalRerun', '').strip()
		
		if region == 'jp': 
			notice = find_notice_for_character(''.join([x.wiki_name_jp for x in banner.featured_characters]))
			if notice is not None and banner.name_jp == '': 
				banner.name_jp = notice['BannerName']
				#if banner.image_source is None: banner.image_source = notice['DownloadedImage']

		banner.notes = banner_names.get(banner.featured_name, {}).get('Notes', '')

		for prev_banner in banners.values():
			if not banner.rerun_original_id and prev_banner.info_character_id == banner.info_character_id: 
				#print(f"This is a rerun of banner {prev_banner.id}")
				banner.rerun_original_id = prev_banner.id
				break


		#
		# Figure out lobby banner image. This is really messy because filenames are known to have typos and some reruns actually update the image.
		#
		assert banner.sale_period_from is not None
		if prev_id > 0 and banners[prev_id].sale_period_from != banner.sale_period_from:
			sameday_sequence_num = 1
		else:
			sameday_sequence_num += 1

		
		if region == 'jp': 
			original_filename = banner.prodnotice_data['FileName'][0] if banner.prodnotice_data and len(banner.prodnotice_data['FileName']) else None
			wiki_filename = f'Lobby_Banner_{banner.sale_period_from.strftime("%Y%m%d")}_{sameday_sequence_num:02}.png'

			# this aims to prevent duplicates of the same image since we have a somewhat reliable mapping of jp prodnotice filenames
			if original_filename is not None:
				original_filename_stripped = original_filename.rsplit('_',1)[0]
				if original_filename_stripped in lobby_banner_map:
					wiki_filename = lobby_banner_map[original_filename_stripped]
					sameday_sequence_num -= 1
				else: #if banner.prodnotice_data is not None and banner.prodnotice_data.get('IsDownloaded') == True:
					lobby_banner_map[original_filename_stripped] = wiki_filename
			banner.image_lobby_banner = BannerImage(original_filename, os.path.join(args['bannerwatch'], 'lobby_banner'), [wiki_filename])

		elif region == 'gl': 
			original_filename = banner.prodnotice_data['filename'] if banner.prodnotice_data and len(banner.prodnotice_data['filename']) else None
			wiki_filename = f'Lobby_Banner_EN_{banner.sale_period_from.strftime("%Y%m%d")}_{sameday_sequence_num:02}.png'

			#this aims to collapse rerun 2+ images to first rerun name
			same_banner_reruns = [x for x in banners.values() if x.rerun_original_id == banner.rerun_original_id and x.id not in UNIQUE_LOBBY_IMAGE_BANNER_ID[region]]
			if banner.is_rerun and len(same_banner_reruns) > 0:
				banner.image_lobby_banner = same_banner_reruns[0].image_lobby_banner
				sameday_sequence_num -= 1
			else:
				banner.image_lobby_banner = BannerImage(original_filename, os.path.join(args['bannerwatch'],'lobby_banner_gl'), [wiki_filename])
		

		if region == 'jp': 
			banner.image_banner = BannerImage(notice is not None and notice.get('DownloadedImage') or None, os.path.join(args['bannerwatch'], 'banner'), [f"Banner_{region.capitalize()}_{x.wiki_name.replace(' ','_')}.png" for x in banner.featured_characters])
		elif region == 'gl':
			banner.image_banner = BannerImage(None, os.path.join(args['bannerwatch'], 'banner_gl'), [f"Banner_{region.upper()}_{x.wiki_name.replace(' ','_')}.png" for x in banner.featured_characters])

		prev_id = banner.id
		banners[banner.id] = banner

	return banners



def write_banner_wikitext(banners, region:str):
	env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
	template = env.get_template('templates/template_banner.txt')

	wikitext_by_year = {}
	wikitext_all = ''
	for banner in banners.values():  
		banner_year = banner.sale_period_from.year if banner.sale_period_from is not None else 0
		if wikitext_by_year.get(banner_year) is None:
			wikitext_by_year[banner_year] = ""

		wikitext_by_year[banner_year] += template.render(region=region, banner=banner)

	for year in wikitext_by_year.keys():
		wikitext_all += wikitext_by_year[year]
		
		with open(os.path.join(args['outdir'], f'_banners_{region}_{year}.txt'), 'w', encoding="utf8") as f:
			f.write("{{BannerTable |\n<onlyinclude>\n" + wikitext_by_year[year] + "</onlyinclude>\n}}\n")


	with open(os.path.join(args['outdir'], f'_banners_{region}.txt'), 'w', encoding="utf8") as f:
		f.write(wikitext_all)



def upload_image_banners(banners, args):
	for banner in banners.values():
		wikitext = f"[[Category:Pick-up banner images]]\r\n"
		for character in banner.featured_characters: wikitext += f"[[Category:{character.personal_name_en} images]]\r\n"

		if banner.linked_lobby_banner_id == 15:
			continue #Shiroko + Hoshino game opening banner

		if banner.rerun_original_id is not None:
			continue #skip uploading rerun images

		if banner.image_banner.get_file is None:
			print(f"Banner {str(banner.linked_lobby_banner_id)} {', '.join([x.wiki_name for x in banner.featured_characters])} is missing an image.")
			continue

		assert len(banner.image_banner.wikinames[0]), f"Banner wikiname must be set, currently {banner.image_banner.wikinames[0]}"

		if args['banner_id'] is not None and banner.linked_lobby_banner_id not in args['banner_id']:
			continue


		if not wiki.page_exists(f"File:{banner.image_banner.wikinames[0]}"):
			#print(f"Uploading file {banner.image_banner_jp.get_file} as {banner.image_banner_jp.wikinames[0]}")
			wiki.upload(banner.image_banner.get_file, banner.image_banner.wikinames[0], 'Pick-up banner image', wikitext)

		if len(banner.image_banner.wikinames)>1:
			for redirname in banner.image_banner.wikinames[1:]:
				print(f"Creating redirect from {redirname} to {banner.image_banner.wikinames[0]}")
				wiki.redirect(f"File:{redirname}", f"File:{banner.image_banner.wikinames[0]}", 'Pick-up banner image redirect for secondary character')



def print_list(banners, region: str, tail: int = 20):

	print (f"============ {region.upper()} banners ============")

	now = datetime.now() #does not account for timezone

	for banner in list(banners.values())[-tail:]:
		note = ''
		if (banner.sale_period_from > now): note = 'future'
		elif (banner.sale_period_to > now): note = 'current'

		print (f"{str(banner.category_type).rjust(17, ' ')} {str(banner.linked_lobby_banner_id).ljust(4)} {str(banner.info_character_id).ljust(14)} {', '.join([x.wiki_name for x in banner.featured_characters]).ljust(32)}: {banner.sale_period_from} ~ {banner.sale_period_to} {note.ljust(8)} ", end="")
		#if banner.rerun_original_id is None: 
			#print (f"      {banner.image_banner.is_wikinamed and 'wikinamed' or banner.image_banner.get_file} {banner.rerun_original_id is None and banner.image_banner.wikinames or ''}", end ="")
			#pass
		#else: print('rerun', end="")

		print(f"{banner.rerun_original_id and 'rerun' or '     '} ", end="")

		#if banner.image_lobby_banner is not None: print(f"{banner.image_lobby_banner.get_file} {banner.image_lobby_banner.wikinames}", end ="")
		#print(f" {banner.name_jp} | {banner.name_en}", end ="")
		#print(f" {banner.uid}", end="")
		print('')



def write_banner_names(banners:dict[int,Banner], outdir:str):
	outpath = os.path.join(outdir, 'banner_names.json')
	with open(outpath, 'w', encoding='utf-8') as f:
		json.dump({','.join([x.wiki_name for x in banner.featured_characters]): {
			'Characters': [x.wiki_name for x in banner.featured_characters],
			'NameJp': banner.name_jp,
			'NameEn': banner.name_en,
			'NameEnGlobal': banner.name_en_global,
			'NameEnGlobalRerun': banner.name_en_global_rerun,
			'Notes': banner.notes,

		} for banner in banners.values()}, f, ensure_ascii=False, indent=4)
	print(f"Saved banner names to {outpath}")


def bannercode_dict(banners:dict[int,Banner]):
	output = {}
	banners_list = list(banners.values())

	for index, banner in enumerate(banners_list):
		if banner.is_rerun:
			rerun_cnt = 1
			for i in range(0, index):
				if banners_list[i].is_rerun and banners_list[i].rerun_original_id == banner.rerun_original_id:
					rerun_cnt += 1
			banner.rerun_cnt = rerun_cnt	
		output[banner.bannercode] = banner

	return output


def collate_banners(banners_jp:dict[str,Banner], banners_gl:dict[str,Banner]):
	output = {}

	for bannercode, banner_jp in banners_jp.items():
		output[bannercode] = {}
		output[bannercode]['jp'] = banner_jp
		output[bannercode]['gl'] = bannercode in banners_gl and banners_gl[bannercode] or None
		
		if bannercode in banners_gl:
			banner_jp.crossregion_id = banners_gl[bannercode].linked_lobby_banner_id
			banners_gl[bannercode].crossregion_id = banner_jp.linked_lobby_banner_id

		# if bannercode not in banners_gl:
		# 	print(f"Warning: JP bannercode {bannercode} is not in GL list")

	for bannercode, banner_gl in banners_gl.items():
		if bannercode not in output:
			print(f"Warning: GL bannercode {bannercode} is not in JP list")

	return output


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
	parser.add_argument('-banner_id', nargs="*", type=int, metavar='ID', help='Id(s) of a banner to export')

	args = vars(parser.parse_args())
	print(args)

	try:

		init_data()
		banners:dict[int, Banner] = init_banners('jp')
		banners_gl:dict[int, Banner] = init_banners('gl')

		collate_banners(bannercode_dict(banners), bannercode_dict(banners_gl))

		if args['wiki'] != None:
			wiki.init(args)
			upload_image_banners(banners, args)
		else:
			print_list(banners, 'jp')
			print_list(banners_gl, 'gl')
			
		
		write_banner_wikitext(banners, 'jp')
		write_banner_wikitext(banners_gl, 'gl')
		write_banner_names(banners, args['translation'])

	except:
		parser.print_help()
		traceback.print_exc()


if __name__ == '__main__':
	main()
