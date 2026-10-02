import traceback
import time

import pywikiapi
from pywikiapi import ApiError
import requests
import wikitextparser as wtp
import re

WIKI_API = 'https://bluearchive.wiki/w/api.php'
RETRY_DELAYS = [5, 15, 30, 60, 120] #seconds before each retry of a request the wiki failed

site = None
stored_auth = [None, None]



class Site(pywikiapi.Site):
    """pywikiapi's Site, but with retries for random Call failed errors"""

    def request(self, *args, **kwargs):
        for delay in RETRY_DELAYS + [None]:
            try:
                return super().request(*args, **kwargs)
            except ApiError as error: #pywikiapi's 'Call failed', holding a response other than 200 OK, which it can't print
                response = error.data
                failure = f"HTTP {response.status_code} {response.reason}"
                if delay is None or response.status_code < 500 and response.status_code != 429: raise requests.HTTPError(failure, response=response) from None
            except (requests.ConnectionError, requests.Timeout) as error:
                if delay is None: raise
                failure = repr(error)
            print (f"Wiki request failed with {failure}, retrying in {delay} s")
            time.sleep(delay)



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
    assert site is not None
    global stored_auth

    print (f"Reauthenticating with {stored_auth}")
    try:
        site.login(stored_auth[0], stored_auth[1])
        print(f'Logged in to wiki, token {site.token()}')

    except ApiError as error:
        if error.message == 'Login failed':
            print (f"Login failed, check credentials")
            exit()



def page_exists(page, wikitext = None):
    assert site is not None

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
        if error.data['code'] != 'missingtitle': raise
        print (f"Page {page} not found")
        return False



def page_list(match, srnamespace = '*'): #TODO namespaces lookup https://www.mediawiki.org/wiki/Manual:Namespace
    assert site is not None
    page_list = []

    try: 
        for r in site.query(list='search', srsearch=match, srlimit=400, srprop='isfilematch', srnamespace = srnamespace):
            for page in r['search']:
                page_list.append(page['title'].replace(' ', '_'))
    except ApiError as error:
        print (f"Unknown error {error}")

    #print(f"Fetched {len(page_list)} pages that match {match}")
    return page_list



def page_prefix_list(apprefix, apnamespace = 6): #namespace 6 is File:
    assert site is not None
    page_list = []

    try:
        for r in site.query(list='allpages', apprefix=apprefix, apnamespace=apnamespace, aplimit=200, apfilterredir='all'):
            for page in r['allpages']:
                page_list.append(page['title'].replace(' ', '_'))
    except ApiError as error:
        print (f"Unknown error {error}")

    return page_list



def category_members(cmtitle, cmnamespace = '*'):
    assert site is not None
    page_list = []

    if not cmtitle.startswith('Category:'): cmtitle = 'Category:' + cmtitle

    try: 
        for r in site.query(list='categorymembers', cmtitle=cmtitle, cmtype='page|subcat|file', cmlimit=200, cmprop='title', cmnamespace = cmnamespace):
            for page in r['categorymembers']:
                page_list.append(page['title'].replace(' ', '_'))
    except ApiError as error:
        print (f"Unknown error {error}")

    #print(f"Fetched {len(page_list)} pages that match {match}")
    return page_list



def page_links(title, plnamespace = '*'):
    """Titles of all pages linked from the given page (including links coming from transcluded templates)."""
    assert site is not None
    page_list = []

    try:
        for page in site.query_pages(titles=[title], prop='links', pllimit='max', plnamespace=plnamespace):
            for link in page.get('links', []):
                page_list.append(link['title'].replace(' ', '_'))
    except ApiError as error:
        print (f"Unknown error {error}")

    return page_list



def embedded_in(eititle, einamespace = '*'):
    """Titles of all pages transcluding the given page (Bucket registers its queries this way too)."""
    assert site is not None
    page_list = []

    try:
        for r in site.query(list='embeddedin', eititle=eititle, eilimit='max', einamespace=einamespace):
            for page in r['embeddedin']:
                page_list.append(page['title'].replace(' ', '_'))
    except ApiError as error:
        print (f"Unknown error {error}")

    return page_list



def backlinks(bltitle, blnamespace = '*'):
    """Titles of all pages linking to the given page (what links here)."""
    assert site is not None
    page_list = []

    try:
        for r in site.query(list='backlinks', bltitle=bltitle, bllimit='max', blnamespace=blnamespace):
            for page in r['backlinks']:
                page_list.append(page['title'].replace(' ', '_'))
    except ApiError as error:
        print (f"Unknown error {error}")

    return page_list



def bucket(query:str):
    """Rows of a Bucket query, written as the extension's Lua: bucket('raids').select('season').where('server','JP').run()"""
    assert site is not None

    try:
        return site('bucket', query=query)['bucket']
    except TypeError: #Bucket words its errors as a string, which pywikiapi can't read
        print (f"Bucket query failed: {query}")
        return []



def purge_all(titles, forcelinkupdate = False, attempts = 5, delay = 60):
    """Purge given pages, retrying the ones that were not purged (usually due to purge rate limit) after a delay."""
    failed = purge(titles, forcelinkupdate)

    attempt = 1
    while failed and attempt <= attempts:
        print (f"{len(failed)} pages were not purged (likely rate limited), retrying in {delay}s, attempt {attempt}/{attempts}")
        time.sleep(delay)
        failed = purge(failed, forcelinkupdate)
        attempt += 1

    if failed:
        print (f"Failed to purge {len(failed)} pages: {failed}")
    else:
        print (f"Done")

    return failed



def purge(titles, forcelinkupdate = False):
    """Purge the parser cache of given pages, returns the list of titles that could not be purged."""
    assert site is not None
    failed = []

    titles = list(titles)
    for chunk in [titles[i:i+20] for i in range(0, len(titles), 20)]:
        try:
            result = site('purge', titles=chunk, forcelinkupdate=forcelinkupdate, POST=True)
            for page in result.get('purge', []):
                if page.get('missing') or page.get('invalid'):
                    print (f"Page {page['title']} not found")
                elif page.get('purged'):
                    print (f"Purged {page['title']}")
                else:
                    failed.append(page['title'].replace(' ', '_'))
        except ApiError as error:
            if error.data['code'] == 'badtoken':
                reauthenticate()
                failed += purge(chunk, forcelinkupdate)
            else:
                print (f"Unknown purge error {error}")
                failed += chunk

    return failed



def update_template(page_name, template_name, wikitext):
    assert site is not None
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
    assert site is not None
    section_old = None
    section_new = None
    
    try:
        text = site('parse', page=page_name, prop='wikitext')
        print (f"Updating wiki page {text['parse']['title']}")
    except ApiError as error:
        if error.data['code'] != 'missingtitle': raise
        print (f'Target page {page_name} not found')
        return

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
    assert site is not None
    section_old = None
    section_new = None
    
    text = site('parse', page=page_name, prop='wikitext')
    print (f"Updating wiki page {text['parse']['title']}")

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
    assert site is not None

    try:
        site(
            action='edit',
            title=page_name,
            text=wikitext,
            summary=summary,
            token=site.token()
        )
    except ApiError as error:
        if error.data['code'] == 'badtoken':
            reauthenticate()
            publish(page_name, wikitext, summary)
        else:
            print (f"Unknown publishing error {error}")



def upload(file, name, comment = 'File upload', text = ''):
    """Uploads a file, returns whether the wiki has it afterwards."""
    assert site is not None
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
        return True
    except ApiError as error:
        if error.data['code'] == 'backend-fail-internal':
            print (f"Server failed with {error.data['code']}, retrying")
            return upload(file, name, comment, text)
        elif error.data['code'] == 'badtoken':
            reauthenticate()
            return upload(file, name, comment, text)
        elif error.data['code'] == 'fileexists-no-change':
            print (f"{error.data['info']}")
            return True
        else:
            print (f"Unknown upload error {error}")
            return False


def file_hashes(names):
    """SHA-1 of the file behind each File: page that has one, keyed by page title."""
    hashes = {}

    if site is None: return hashes

    names = list(names)
    for chunk in [names[i:i+50] for i in range(0, len(names), 50)]:
        try:
            for page in site.query_pages(titles=chunk, prop='imageinfo', iiprop='sha1|canonicaltitle'):
                #A redirect without a file of its own reports the file of its target, under the target's title
                for info in page.get('imageinfo', []):
                    if 'sha1' in info and info['canonicaltitle'] == page['title']: hashes[page['title'].replace(' ', '_')] = info['sha1']
        except ApiError as error:
            print (f"Unknown error reading file hashes {error}")

    return hashes


def move(name_old, name_new, summary='Consistent naming', noredirect=True):
    assert site is not None

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
        print (f"Unknown moving error {error}")


def redirect(name_from, name_to, summary='Generated redirect'):
    wikitext = f"#REDIRECT [[{name_to}]]"
    publish(name_from, wikitext, summary)


def redirect_target(page):
    """Title the page redirects to, None if it doesn't exist or isn't a redirect."""
    assert site is not None

    try:
        result = site('query', titles=page, redirects=True)
        for redirect in result['query'].get('redirects', []):
            if redirect['from'].replace(' ', '_') == page.replace(' ', '_'):
                return redirect['to'].replace(' ', '_')
    except ApiError as error:
        print (f"Unknown error {error}")

    return None


def extract_trailing_parts(section):
    #Match {{...}} or [[Category:...]]
    trailing_pattern = re.compile(r'(\{\{[^}]+\}\}|\[\[Category:[^\]]+\]\])\s*$', re.MULTILINE)
    return trailing_pattern.findall(section)