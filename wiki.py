import traceback

from pywikiapi import Site, ApiError
import wikitextparser as wtp

WIKI_API = 'https://bluearchive.wiki/w/api.php'

site = None



def init(args):
    global site

    try:
        site = Site(WIKI_API)
        site.login(args['wiki'][0], args['wiki'][1])
        print(f'Logged in to wiki, token {site.token()}')

    except Exception as err:
        print(f'Wiki error: {err}')
        traceback.print_exc()



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
        


def page_list(match):
    global site
    page_list = []

    try: 
        for r in site.query(list='search', srwhat='title', srsearch=match, srlimit=200, srprop='isfilematch'):
            for page in r['search']:
                page_list.append(page['title'].replace(' ', '_'))
    except ApiError as error:
        if error.message == 'Call failed':
            print (f"Call failed, retrying")
            page_list(match)
        elif error.data['code'] == 'fileexists-no-change':
            print (f"{error.data['info']}")
            return True
        else:
            print (f"Unknown upload error {error}")

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



def update_section(page_name, section_name, wikitext):
    section_old = None
    section_new = None

    text = site('parse', page=page_name, prop='wikitext')
    print (f"Updating wiki page {text['parse']['title']}")

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

    if section_new == section_old:
        print (f'...no changes in {section_name} section for {page_name}')
    else:
        publish(page_name, text['parse']['wikitext'].replace(section_old, section_new), summary=f'Updated {section_name} section')



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
        else:
            print (f"Unknown publishing error {error}")



def upload(file, name, comment = 'File upload'):
    global site

    f = open(file, "rb")

    try: 
        site(
            action='upload',
            filename=name,
            comment=comment,
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
            upload(file, name)
        elif error.data['code'] == 'fileexists-no-change':
            print (f"{error.data['info']}")
            return True
        else:
            print (f"Unknown upload error {error}")