from dataclasses import replace
import os
import re
import traceback
import argparse

import wiki

from data import load_data
from model import Character
#import shared.functions
from shared.CompareImages import compare_images

args = None
map_wikiname_id = {}
galleries = []



class Gallery(object):
    def __init__(self, root_dir, dirname, character_wikiname, variant_origin:str, is_diorama, is_exported, description, files, exclude_files = []):
        self.root_dir = root_dir
        self.dirname = dirname
        self.character_wikiname = character_wikiname
        self.variant_origin = variant_origin
        self.is_diorama = is_diorama
        self.is_exported = is_exported
        self.description = description
        self.files = files
        self.exclude_files = exclude_files

    @property
    def character_dir_path(self):
        return os.path.join(self.root_dir, self.dirname)

    
    
    @property
    def wikitext(self):
        self.exclude_files = compare_images(self.files, self.character_dir_path)
        wikitext = self.generate_gallery_wikitext(self.files, self.exclude_files, self.character_wikiname, self.description)
        #S2 is a second set of usually same faces for a sprite variant (no mask/hat etc), 
        #so display as a separate gallery within same section, or merge if first section has few images
        if(os.path.exists(self.character_dir_path+"_S2")):
            s2_path = self.character_dir_path+"_S2"
            s2_files = self.scan_files(s2_path)
            s2_exclude_files = compare_images(s2_files, s2_path)
            self.exclude_files += s2_exclude_files

            if len(self.files) > 2: wikitext += self.generate_gallery_wikitext(s2_files, s2_exclude_files, None, None) #append second gallery
            else: wikitext = self.generate_gallery_wikitext(self.files + s2_files, self.character_wikiname, self.description) #redo gallery merged
        
        return wikitext


    @classmethod
    def from_data(cls, export_catalog, root_dir, character_dir):
        character_dir_path = os.path.join(root_dir, character_dir)
        character_wikiname = ')' in character_dir and character_dir[:character_dir.rfind(')')+1] or character_dir
        character_wikiname = re.sub('_diorama$', '', character_wikiname).replace('_', ' ')
        variant_origin = ' (' in character_wikiname and character_wikiname[:character_wikiname.find(' (')] or character_wikiname
        is_diorama = character_dir.endswith("diorama")
        is_exported = (is_diorama or f"{character_dir}_diorama" not in export_catalog) and not character_dir.endswith("S2")    

        files = Gallery.scan_files(character_dir_path)
        
        return cls(
            root_dir,
            character_dir,
            character_wikiname,
            variant_origin,
            is_diorama,
            is_exported,
            None,
            files
        )
    

    def scan_files(dir):
        return [x for x in os.listdir(dir) if x.endswith(".png")]


    def generate_gallery_wikitext(cls, files: list, exclude_files: list, title, description = None):
        wikitext = ""

        gallery_list = [x for x in files if x not in exclude_files]

        if title is not None: wikitext += f"=={title}==\n"
        if description is not None and description != '': wikitext += description+"\n"

        if exclude_files: wikitext += "\n".join([f"<!-- {x} intentionally excluded as a duplicate of another sprite -->" for x in exclude_files]) + "\n"
        #print(wikitext)
        wikitext += "<gallery>\n" + "\n".join(gallery_list) + "\n</gallery>\n"

        return wikitext



def scan_directory_for_galleries(root_dir):
    global galleries

    export_catalog =  os.listdir(root_dir)

    for character_dir in export_catalog:
        galleries.append(Gallery.from_data(export_catalog, root_dir, character_dir))



def generate_page_wikitext(export_galleries):
    global galleries

    wiki_categories = ["Characters galleries"] #, f"{variant_origin} sprites"]

    #print(f"Export galleries: {[x.dirname for x in export_galleries]}")

    wikitext = '=Sprites=\n'
    for gallery in export_galleries:
        wikitext +=  gallery.wikitext

    wikitext += "=Video=\n{{CharacterVideoGallery}}\n"
    
    wikitext += "\n{{CharacterAdditionalGallery|"+export_galleries[0].variant_origin+" images}}"
    wikitext += "\n{{CharacterGallerySeo|"+",".join([x.character_wikiname for x in export_galleries])+"}}"
    wikitext += "\n" + "\n".join([f"[[Category:{x}]]" for x in wiki_categories])

    return wikitext



def upload_files(export_galleries):
    assert wiki.site != None
    global args

    for gallery in export_galleries:
        page_list = wiki.page_list(f"File:{gallery.character_wikiname}")
        wiki_categories = ["Character sprites", f"{gallery.variant_origin} images"]
        wiki_text = "\n".join([f"[[Category:{x}]]" for x in wiki_categories])

        comment = f"Sprite for {gallery.character_wikiname}"
    
        for file in [x for x in gallery.files if f"File:{x}" not in page_list and x not in gallery.exclude_files]:
            print (f"Uploading {file}")
            path = os.path.join(args['gallery_dir'], gallery.dirname, file)
            wiki.upload(path, file, comment, wiki_text)



def get_character_data():
    global args, map_wikiname_id

    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])

    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character['Id'], data)
            map_wikiname_id[character.wiki_name] = character.id
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()

        # if args['character_id'] is not None and character['Id'] not in args['character_id']:
        #     continue

        if args['character_wikiname'] is not None and character.wiki_name not in args['character_wikiname']:
            continue
    



def generate():
    global args, map_wikiname_id, galleries

    get_character_data()
    scan_directory_for_galleries(args['gallery_dir'])

    export_list = args['character_wikiname'] or map_wikiname_id.keys()

    for character_wikiname in export_list:
        character_wikiname = character_wikiname.replace('_',' ').strip()
        variant_origin = '(' in character_wikiname and character_wikiname[:character_wikiname.find(' (')] or character_wikiname
        export_galleries = [x for x in galleries if x.variant_origin == variant_origin and x.is_exported]

        #print(f"Export galleries: {[x.character_wikiname for x in export_galleries]}")
        if not export_galleries:
            print(f"No sprite export galleries found for {character_wikiname}")
            continue

        gallery_self = next(x for x in export_galleries if x.character_wikiname == character_wikiname)
        gallery_alt = [x for x in export_galleries if x.character_wikiname != character_wikiname and x.character_wikiname in map_wikiname_id.keys() ]
        gallery_npc = [x for x in export_galleries if x.character_wikiname != character_wikiname and x.character_wikiname not in map_wikiname_id.keys() ]

        # print(f"gallery_self {gallery_self}")
        # print(f"gallery_alt {gallery_alt}")
        # print(f"gallery_npc {gallery_npc}")
        
        export_galleries= [gallery_self] + gallery_alt + gallery_npc
        print(f"Sorted galleries for {character_wikiname}: {[x.character_wikiname for x in export_galleries]}")

        wikitext = generate_page_wikitext(export_galleries)
        
        if args['wiki'] != None and wiki.site != None: 
            upload_files(export_galleries)

            wikipath = character_wikiname + '/gallery'

            if args['wiki_section'] != None:
                #print(f"Updating section {args['wiki_section']} of {wikipath}")
                wiki.update_section(wikipath, args['wiki_section'], wikitext)
            elif not wiki.page_exists(wikipath, wikitext):
                print(f'Publishing {wikipath}')
                wiki.publish(wikipath, wikitext, f'Generated character gallery page')

        
        with open(os.path.join(args['outdir'], f'{character_wikiname}.txt'), 'w', encoding="utf8") as f:           
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


    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    if args['character_wikiname']:
        for name in args['character_wikiname']: name = name.replace('_',' ').strip()

    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
