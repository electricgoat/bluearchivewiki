import traceback

from pywikiapi import Site, ApiError
import wikitextparser as wtp
import re

WIKI_API = 'https://bluearchive.wiki/w/api.php'

site = None
stored_auth = [None, None]



def init(args):
    global site
    global stored_auth

    try:
        stored_auth = args['wiki']
        site = Site(WIKI_API)
        site.login(stored_auth[0], stored_auth[1])
        print(f'Logged in to wiki, token {site.token()}')

    except ApiError as error:
        if error.message == 'Login failed':
            print (f"Login failed, retrying")
            reauthenticate()
        else:
            print(f'Wiki API error: {error}')
            traceback.print_exc()



def reauthenticate():
    global site
    global stored_auth

    print (f"Reauthenticating with {stored_auth}")
    try:
        site.login(stored_auth[0], stored_auth[1])
        print(f'Logged in to wiki, token {site.token()}')

    except ApiError as error:
        if error.message == 'Call failed':
            print (f"Call failed, retrying")
            reauthenticate()
        if error.message == 'Login failed':
            print (f"Login failed, check credentials")
            exit()



def page_exists(page, wikitext = None):
    global site

    try:
        text = site('parse', page=page, prop='wikitext')
        if wikitext == None:
            print (f"Found wiki page {text['parse']['title']}")
            return True
        elif wikitext == text['parse']['wikitext']:
            print (f"Found wiki page {text['parse']['title']}, no changes")
            return True
        else:
            return False
    except ApiError as error:
        if error.data['code'] == 'missingtitle':
            print (f"Page {page} not found")
            return False
        else:
            print (f"Unknown error {error}, retrying")
            page_exists(page)
        


def page_list(match, srnamespace = '*'): #TODO namespaces lookup https://www.mediawiki.org/wiki/Manual:Namespace
    global site
    page_list = []

    try: 
        for r in site.query(list='search', srsearch=match, srlimit=400, srprop='isfilematch', srnamespace = srnamespace):
            for page in r['search']:
                page_list.append(page['title'].replace(' ', '_'))
    except ApiError as error:
        if error.message == 'Call failed':
            print (f"Call failed, retrying")
            page_list(match)
        # elif error.data['code'] == 'fileexists-no-change':
        #     print (f"{error.data['info']}")
        #     return True
        else:
            print (f"Unknown error {error}")

    #print(f"Fetched {len(page_list)} pages that match {match}")
    return page_list



def category_members(cmtitle, cmnamespace = '*'):
    global site
    page_list = []

    if not cmtitle.startswith('Category:'): cmtitle = 'Category:' + cmtitle

    try: 
        for r in site.query(list='categorymembers', cmtitle=cmtitle, cmtype='page|subcat|file', cmlimit=200, cmprop='title', cmnamespace = cmnamespace):
            for page in r['categorymembers']:
                page_list.append(page['title'].replace(' ', '_'))
    except ApiError as error:
        if error.message == 'Call failed':
            print (f"Call failed, retrying")
            category_members(cmtitle, cmnamespace)
        # elif error.data['code'] == 'fileexists-no-change':
        #     print (f"{error.data['info']}")
        #     return True
        else:
            print (f"Unknown error {error}")

    #print(f"Fetched {len(page_list)} pages that match {match}")
    return page_list



def update_template(page_name, template_name, wikitext):
    template_old = None
    template_new = None

    text = site('parse', page=page_name, prop='wikitext')
    print (f"Updating wiki page {text['parse']['title']}")

    wikitext_old = wtp.parse(text['parse']['wikitext'])
    for template in wikitext_old.templates:
        if template.name.strip() == template_name: 
            template_old = str(template)
            #print (f'Old template text is {template_old}')
            break

    wikitext_new = wtp.parse(wikitext)
    for template in wikitext_new.templates:
        if template.name.strip() == template_name: 
            template_new = str(template)
            #print (f'New template text is {template_new}')
            break

    if template_new == None:
        print (f'Unable to find new template data')
        return

    if template_old == None:
        print (f'Unable to find old template data')
        return

    if template_new == template_old:
        print (f'...no changes in {template_name} for {page_name}')
    else:
        publish(page_name, text['parse']['wikitext'].replace(template_old, template_new), summary=f'Updated {template_name} template data')



def update_section(page_name:str, section_name:str, wikitext:str, preserve_trailing_parts:bool = False):
    section_old = None
    section_new = None
    
    try:
        text = site('parse', page=page_name, prop='wikitext')
        print (f"Updating wiki page {text['parse']['title']}")
    except ApiError as error:
        if error.message == 'Call failed':
            print (f"Call failed, retrying")
            update_section(page_name, section_name, wikitext)
        elif error.code == 'missingtitle':
            print (f'Target page {page_name} not found')
            return
        else:
            print(error)

    wikitext_old = wtp.parse(text['parse']['wikitext'])
    for section in wikitext_old.sections:
        if  section.title != None and section.title.strip() == section_name: 
            section_old = str(section)
            #print (f'Old section text is {section_old}')
            break

    wikitext_new = wtp.parse(wikitext)
    for section in wikitext_new.sections:
        if section.title != None and section.title.strip() == section_name: 
            section_new = str(section)
            #print (f'New section text is {section_new}')
            break

    if section_new == None:
        print (f'Unable to find new section data')
        return

    if section_old == None:
        print (f'Unable to find old section data')
        return
    
    if preserve_trailing_parts:
        new_trailing_parts = extract_trailing_parts(section_new)
        for old_part in extract_trailing_parts(section_old):
            if old_part not in new_trailing_parts:
                section_new += '\n' + old_part
        section_new += '\n'

    if section_new == section_old:
        print (f'...no changes in {section_name} section for {page_name}')
    else:
        publish(page_name, text['parse']['wikitext'].replace(section_old, section_new), summary=f'Updated {section_name} section')



#This is a bit weird, added to update the first part of character pages which do not have a section heading
def update_section_number(page_name, section_number, wikitext): 
    section_old = None
    section_new = None
    
    try:
        text = site('parse', page=page_name, prop='wikitext')
        print (f"Updating wiki page {text['parse']['title']}")
    except ApiError as error:
        if error.message == 'Call failed':
            print (f"Call failed, retrying")
            update_section(page_name, section_number, wikitext)

    wikitext_old = wtp.parse(text['parse']['wikitext'])
    section_old = str(wikitext_old.sections[section_number])
    #print (f'Old section text is {section_old}')

    wikitext_new = wtp.parse(wikitext)
    section_new = str(wikitext_new.sections[section_number])
    #print (f'New section text is {section_new}')

    if section_new == None:
        print (f'Unable to find new section data')
        return

    if section_old == None:
        print (f'Unable to find old section data')
        return

    if section_new == section_old:
        print (f'...no changes in section №{section_number} for {page_name}')
    else:
        #print(f'Updated section number {section_number}')
        publish(page_name, text['parse']['wikitext'].replace(section_old, section_new), summary=f'Updated section №{section_number}')



def publish(page_name, wikitext, summary='Publishing generated page'):
    global site

    try:
        site(
            action='edit',
            title=page_name,
            text=wikitext,
            summary=summary,
            token=site.token()
        )
    except ApiError as error:
        if error.message == 'Call failed':
            print (f"Call failed, retrying")
            publish(page_name, wikitext, summary)
        elif error.data['code'] == 'badtoken':
            reauthenticate()
            publish(page_name, wikitext, summary)
        else:
            print (f"Unknown publishing error {error}")



def upload(file, name, comment = 'File upload', text = ''):
    global site
    f = open(file, "rb")

    try: 
        site(
            action='upload',
            filename=name,
            comment=comment,
            text=text,
            ignorewarnings=True,
            token=site.token(),
            POST=True,
            EXTRAS={
                'files': {
                    'file': f.read()
                }
            }
        )
    except ApiError as error:
        if error.message == 'Call failed':
            print (f"Call failed, retrying")
            upload(file, name, comment, text)
        elif error.data['code'] == 'backend-fail-internal':
            print (f"Server failed with {error.data['code']}, retrying")
            upload(file, name, comment, text)
        elif error.data['code'] == 'badtoken':
            reauthenticate()
            upload(file, name, comment, text)
        elif error.data['code'] == 'fileexists-no-change':
            print (f"{error.data['info']}")
            return True
        else:
            print (f"Unknown upload error {error}")


def move(name_old, name_new, summary='Consistent naming', noredirect=True):
    global site

    print(f"Moving {name_old} → {name_new}")
    try:
        #get pageid
        pageid = None
        for page in site.query_pages(titles=[name_old]):
            #print(page)
            pageid = page['pageid']

        if pageid:
            site(
                action='move',
                fromid=pageid,
                to=name_new,
                reason=summary,
                movetalk=True,
                movesubpages=True,
                noredirect=noredirect,
                token=site.token(),
                POST=True
            )
    except ApiError as error:
        if error.message == 'Call failed':
            print (f"Call failed, retrying")
            move(name_old, name_new, summary)
        else:
            print (f"Unknown moving error {error}")


def redirect(name_from, name_to, summary='Generated redirect'):
    wikitext = f"#REDIRECT [[{name_to}]]"
    publish(name_from, wikitext, summary)


def extract_trailing_parts(section):
    #Match {{...}} or [[Category:...]]
    trailing_pattern = re.compile(r'(\{\{[^}]+\}\}|\[\[Category:[^\]]+\]\])\s*$', re.MULTILINE)
    return trailing_pattern.findall(section)