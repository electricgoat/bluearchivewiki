from dataclasses import replace
import os
import re
import traceback
import argparse
import json
from datetime import datetime

import wiki

from data import load_data
from model import Character
#import shared.functions
from shared.CompareImages import compare_images

args = None
character_map = {}
wikiname_to_devname_map = {}
galleries = []

LEGACY_SPRNAME = ['First version', 'Original version', 'Beta version', 'Unreleased version', 'Unreleased', 'Pre-release design']


class Gallery(object):
    def __init__(self, root_dir, dirname, character_wikiname, is_diorama, is_exported, description, files, exclude_files = None, cargo_template = None):
        self.root_dir = root_dir
        self.dirname = dirname
        self.character_wikiname = character_wikiname
        self.is_diorama = is_diorama
        self.is_exported = is_exported
        self.description = description
        self.files = files
        self.exclude_files = exclude_files
        self.cargo_template = cargo_template


    @property
    def character_dir_path(self):
        return os.path.join(self.root_dir, self.dirname)
    
    @property
    def files_exportable(self):
        if self.exclude_files is None: return self.files
        out = {}
        for path in self.files.keys():
            out[path] = [x for x in self.files[path] if x not in self.exclude_files[path]]
        return out
    
    @property
    def character_name(self):
        return self.character_wikiname.split('(',1)[0].strip()
    
    @property
    def variant(self):
        return '(' in self.character_wikiname and self.character_wikiname[self.character_wikiname.find('(')+1:-1] or ''
    

    def __repr__(self):
        return (f"Gallery(root_dir={self.root_dir!r}, dirname={self.dirname!r}, "
                f"character_wikiname={self.character_wikiname!r}, is_diorama={self.is_diorama}, "
                f"is_exported={self.is_exported}, description={self.description!r}, "
                f"files={list(self.files.keys())}, exclude_files={self.exclude_files!r}, "
                f"cargo_template={self.cargo_template!r})")

    
    def wikitext(self, include_cargo = False, header_level = 2):
        wikitext = f"{'='*header_level}{self.character_wikiname}{'='*header_level}\n"
        if self.description: wikitext += self.description+"\n"
        if include_cargo: 
            wikitext += "{{Sprite\n"
            for field, value in self.cargo_template.items():
                wikitext += f"|{field} = {value}\n"
            wikitext += "}}\n"

        if self.exclude_files == None:
            self.exclude_files = compare_images(self.files)
            if Gallery.flatlist(self.exclude_files): print(f"Excluding from {self.character_wikiname}: {Gallery.flatlist(self.exclude_files)}")

        if len(self.files.keys()) == 1:
            wikitext += self.generate_gallery_wikitext(Gallery.flatlist(self.files_exportable), Gallery.flatlist(self.exclude_files))
        else:
            #S2 is a second set of usually same faces for a sprite variant (no mask/hat etc), 
            #display as a separate gallery within same section, or merge if first section has few images
            first_gallery_size = len(list(self.files_exportable.values())[0])

            if first_gallery_size > 2: 
                wikitext += self.generate_gallery_wikitext(list(self.files_exportable.values())[0], Gallery.flatlist(self.exclude_files)) + self.generate_gallery_wikitext(list(self.files_exportable.values())[1], []) #append second gallery
            else: 
                wikitext += self.generate_gallery_wikitext(Gallery.flatlist(self.files_exportable), Gallery.flatlist(self.exclude_files)) #make gallery merged
        
        return wikitext


    def generate_gallery_wikitext(self, files: list, exclude_files: list):
        wikitext = ""

        if exclude_files: wikitext += "\n".join([f"<!-- {x} intentionally excluded as a duplicate of another sprite -->" for x in exclude_files]) + "\n"
        
        wikitext += "<gallery>\n" + "\n".join(files) + "\n</gallery>\n"

        return wikitext
    

    @classmethod
    def from_data(cls, export_catalog, root_dir, character_dir):
        character_dir_path = os.path.join(root_dir, character_dir)
        character_wikiname = ')' in character_dir and character_dir[:character_dir.rfind(')')+1] or character_dir
        character_wikiname = re.sub('_diorama$', '', character_wikiname).replace('_', ' ')
        is_diorama = character_dir.endswith("diorama")
        is_exported = (is_diorama or f"{character_dir}_diorama" not in export_catalog) and not character_dir.endswith("S2")    

        file_list = Gallery.scan_files(character_dir_path)
        files = {character_dir_path: file_list}
        
        if(os.path.exists(character_dir_path+"_S2")):
            s2_file_list = Gallery.scan_files(character_dir_path+"_S2")
            files[character_dir_path+"_S2"] = s2_file_list
        
        return cls(
            root_dir,
            character_dir,
            character_wikiname,
            is_diorama,
            is_exported,
            None,
            files
        )
    

    @staticmethod
    def scan_files(dir):
        return [x for x in os.listdir(dir) if x.endswith(".png")]
    

    @staticmethod
    def flatlist(data):
        out = []
        for path in data.keys():
            out += data[path]
        return out


class Npc(object):
    def __init__(self, wiki_name):
        self.wiki_name = wiki_name.replace('_',' ').strip()

    @property
    def personal_name_en(self):
        return self.wiki_name.split('(',1)[0].strip()
    
    @property
    def variant(self):
        if '(' in self.wiki_name and ')' in self.wiki_name:
            return self.wiki_name.split('(', 1)[1].split(')', 1)[0].strip()
        return None



def scan_directory_for_galleries(root_dir):
    global galleries

    export_catalog =  os.listdir(root_dir)

    for character_dir in export_catalog:
        galleries.append(Gallery.from_data(export_catalog, root_dir, character_dir))



def generate_page_wikitext(export_galleries:list[Gallery], include_cargo = False):
    global galleries

    wiki_categories = ["Characters galleries"]

    #print(f"Export galleries: {[x.dirname for x in export_galleries]}")

    wikitext = '{{CharacterTopNav}}\n=Sprites=\n'
    for gallery in export_galleries:
        wikitext +=  gallery.wikitext(include_cargo)

    wikitext += "=Video=\n{{CharacterVideoGallery}}\n"
    
    wikitext += "\n{{CharacterAdditionalGallery|"+export_galleries[0].character_name+" images}}"
    wikitext += "\n{{CharacterGallerySeo|"+",".join([x.character_wikiname for x in export_galleries])+"}}"
    wikitext += "\n" + "\n".join([f"[[Category:{x}]]" for x in wiki_categories])

    return wikitext


# def generate_npc_wikitext(export_galleries:list[Gallery], include_cargo = False):
#     global galleries

#     wikitext = '==Images==\n'
#     for gallery in export_galleries:
#         wikitext +=  gallery.wikitext(include_cargo, header_level=3)

#     wikitext += "\n{{CatHighlightsGallery|"+export_galleries[0].character_name+"}}"

#     return wikitext


def upload_files(export_galleries:list[Gallery]):
    assert wiki.site != None
    global args

    for gallery in export_galleries:
        page_list = wiki.page_list(f"File:{gallery.character_wikiname}")
        wiki_categories = ["Character sprites", f"{gallery.character_name} images"]
        wiki_text = "\n".join([f"[[Category:{x}]]" for x in wiki_categories])

        comment = f"Sprite for {gallery.character_wikiname}"

        for path in gallery.files_exportable.keys():
            for file in [x for x in gallery.files_exportable[path] if (f"File:{x}" not in page_list or args['reupload']) and x not in gallery.exclude_files[path]]:
                print (f"Uploading {file} from {os.path.join(path, file)}")
                #path = os.path.join(args['gallery_dir'], gallery.dirname, file)
                wiki.upload(os.path.join(path, file), file, comment, wiki_text)



def redirect_files(export_galleries:list[Gallery]):
    assert wiki.site != None
    global args

    for gallery in export_galleries:
        page_list = wiki.page_list(f"File:{gallery.character_wikiname}")

        for path in gallery.exclude_files.keys():
            for file in [x for x in gallery.exclude_files[path] if f"File:{x}" not in page_list]:
                print (f"Creating redirect from {file} to {gallery.exclude_files[path][file]}")
                wiki.publish(f"File:{file}", f"#REDIRECT [[File:{gallery.exclude_files[path][file]}]]\n[[Category:Character sprite redirects]]", "Identical sprite redirect")



def get_character_data():
    global args, character_map, wikiname_to_devname_map
    characters = []

    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character['Id'], data)
            characters.append(character)

            if args['character_wikiname'] is not None and character.wiki_name not in args['character_wikiname']:
                continue
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue

        # if args['character_id'] is not None and character['Id'] not in args['character_id']:
        #     continue
    
    for character in characters:
        if character.personal_name_en not in character_map:
            character_map[character.personal_name_en] = []
        character_map[character.personal_name_en].append(character)

    if args['npc']:
        for name in args['character_wikiname']:
            npc = Npc(name)
            if npc.personal_name_en not in character_map:
                character_map[npc.personal_name_en] = []
            character_map[npc.personal_name_en].append(npc)
            

    # Sort character variant into groups, first entry in the one that gets Cargo data in the library
    for key in character_map:
        group = character_map[key]
        
        vanilla_variant = [c for c in group if c.variant is None]
        rest = [c for c in group if c.variant is not None]
        try: rest.sort(key=lambda c: datetime.strptime(c.profile.release_date_jp, "%Y/%m/%d"))
        except: pass
        
        character_map[key] = vanilla_variant + rest

    
    #wikiname_to_devname_map
    sprite_devname_map = {}
    for devname_map in ['./translation/devname_map.json', './translation/devname_map_aux.json']:
        with open(devname_map, encoding="utf8") as f:
            sprite_devname_map.update(json.load(f))

    for devname, char in sprite_devname_map.items():
        wikiname_to_devname_map[char['firstname'] + (char['variant'] is not None and f" ({char['variant']})" or "")] = devname
    



def generate():
    global args, character_map, wikiname_to_devname_map, galleries

    get_character_data()
    scan_directory_for_galleries(args['gallery_dir'])

    export_list = args['character_wikiname'] and [x.split('(',1)[0].replace('_',' ').strip() for x in args['character_wikiname']] or character_map.keys()

    for character_name in export_list:
        export_galleries:list[Gallery] = [x for x in galleries if x.character_name == character_name and x.is_exported]

        if not export_galleries:
            print(f"No sprite export galleries found for {character_name}")
            continue
        
        playable_variants = []
        if not args['npc']: playable_variants = [x.wiki_name for x in character_map[character_name]]
 
        #prepare data for cargo template
        for gallery in export_galleries:
            gallery.cargo_template = {
                'Id': wikiname_to_devname_map.get(gallery.character_wikiname, ''),
                'Type': gallery.character_wikiname in playable_variants and 'PC' or 'NPC',
                'CharacterName': gallery.character_name,
                'CharacterVariant': gallery.variant,
                'SpriteNames': ','.join([x.split(')',1)[-1].split('_',1)[-1].replace('.png', '') for x in Gallery.flatlist(gallery.files_exportable)]),
                'Sample': Gallery.flatlist(gallery.files_exportable)[0]
            }
        if os.path.exists(os.path.join(gallery.root_dir, gallery.dirname, 'spoiler.txt')):
            #print(f"Spoiler sprite: {gallery.dirname}")
            gallery.cargo_template['Spoiler'] = 'yes'

        for order, character in enumerate(character_map[character_name]):
            gallery_self = next(x for x in export_galleries if x.character_wikiname == character.wiki_name)
            gallery_alt = [x for pv in playable_variants for x in export_galleries if x.character_wikiname != character.wiki_name and x.character_wikiname == pv]
            gallery_npc =    [x for x in export_galleries if x.character_wikiname != character.wiki_name and x.character_wikiname not in playable_variants and not any(text in x.character_wikiname for text in LEGACY_SPRNAME)]
            gallery_legacy = [x for x in export_galleries if x.character_wikiname != character.wiki_name and x.character_wikiname not in playable_variants and any(text in x.character_wikiname for text in LEGACY_SPRNAME)]

            #print(f"Processing character {character_name} № {order}; variant {character.wiki_name}")
            
            export_galleries= [gallery_self] + gallery_alt + gallery_npc + gallery_legacy
            print(f"Sorted galleries for {character.wiki_name}: {[x.character_wikiname for x in export_galleries]}")

            #wikitext = not args['npc'] and generate_page_wikitext(export_galleries, include_cargo = (order==0)) or generate_npc_wikitext(export_galleries, include_cargo = (order==0))
            wikitext = generate_page_wikitext(export_galleries, include_cargo = (order==0))
            
            if args['wiki'] != None and wiki.site != None: 
                upload_files(export_galleries)
                redirect_files(export_galleries)

                # if not args['npc']:
                wikipath = character.wiki_name + '/gallery'

                if args['wiki_section'] != None:
                    #print(f"Updating section {args['wiki_section']} of {wikipath}")
                    wiki.update_section(wikipath, args['wiki_section'], wikitext)
                elif not wiki.page_exists(wikipath, wikitext) and not args['nogallery']:
                    print(f'Publishing {wikipath}')
                    wiki.publish(wikipath, wikitext, f'Generated character gallery page')
                # else:
                #     wikipath = character.wiki_name

                #     if wiki.page_exists(wikipath):
                #         print(f'Publishing {wikipath}')
                #         wiki.update_section(wikipath, args['wiki_section'] or "Images", wikitext, preserve_trailing_parts=True)

            
            with open(os.path.join(args['outdir'], f'{character.wiki_name}.txt'), 'w', encoding="utf8") as f:           
                f.write(wikitext)
        
            


def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-gallery_dir',      metavar='DIR', default='../ba-spinecharacters/out/', help='Directory with rendered sprites')
    parser.add_argument('-outdir',          metavar='DIR', default='./out/gallery', help='Output directory')
    
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish data to wiki, requires wiki_template to be set')
    parser.add_argument('-wiki_section',  metavar='SECTION NAME', help='Name of a page section to be updated')
    
    #parser.add_argument('-character_id', nargs="*", type=int, metavar='ID', help='Id(s) of a characters to export')
    parser.add_argument('-character_wikiname', nargs="*", type=str, metavar='Wikiname', help='Name(s) of a characters to export')
    parser.add_argument('-npc', action='store_true', help='Treat as an NPC gallery')
    parser.add_argument('-nogallery', action='store_true', help='Don\'t create gallery page')
    parser.add_argument('-reupload', action='store_true', help='Try to reupload files')

    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    if args['character_wikiname']:
        args['character_wikiname'] = [name.replace('_', ' ').strip() for name in args['character_wikiname']]

    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
