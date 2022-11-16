import traceback

from pywikiapi import Site, ApiError
#import wikitextparser as wtp

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