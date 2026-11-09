"""Facts embedded in public Penguin UK pages, with explicit imprint separation."""
import json
import re
from datetime import date
from urllib.parse import urljoin
from .adapters import Result,soup
from .model import canonical_url,clean,make_record

BASE='https://www.penguin.co.uk'

def page_props(html):
    node=soup(html).select_one('script#__NEXT_DATA__')
    if not node:raise ValueError('Public page data missing; layout review needed')
    return json.loads(node.get_text())['props']['pageProps']

def works(value):
    if isinstance(value,dict):
        if value.get('isbn') and value.get('seoFriendlyUrl') and value.get('onSaleDate'):
            yield value
        for item in value.values():yield from works(item)
    elif isinstance(value,list):
        for item in value:yield from works(item)

def discover(html,today):
    props=page_props(html); found=set(); count=0
    # Metadata is already embedded in the ordinary HTML response; no API call.
    for item in works(props):
        path=item['seoFriendlyUrl']
        if not path.startswith('/books/'):continue
        count+=1
        if date.fromisoformat(item['onSaleDate']['date'])>today:
            if not path.rstrip('/').endswith('/'+str(item['isbn'])):path=path.rstrip('/')+'/'+str(item['isbn'])
            found.add(urljoin(BASE,path))
    if not count:raise ValueError('No book metadata in discovery page')
    return found

def primary(html,url):
    p=page_props(html)
    if canonical_url(p.get('canonicalLink','https://invalid.example'))!=canonical_url(url):
        raise ValueError('Primary book URL does not match request')
    for field in ('title','isbn','imprint','publishDate','authors','currentFormat','titleData'):
        if not p.get(field):raise ValueError('Missing book field: '+field)
    if not re.fullmatch(r'\d{13}',str(p['isbn'])):raise ValueError('Invalid ISBN')
    date.fromisoformat(p['publishDate'])
    if p['titleData']['onSaleDate']['date']!=p['publishDate']:raise ValueError('Conflicting book dates')
    return p

def record(p,pid,url):
    genres=p['bookPageData']['books']['booksInfo']['bookGenres'].split(',')
    if 'poetry' not in genres:return None
    if p['currentFormat'] not in ('Paperback','Hardback'):return None
    editions=p['titleData'].get('editions')
    if not editions:raise ValueError('Edition history missing; cannot check reissue')
    for group in editions.values():
        for edition in group:
            if date.fromisoformat(edition['onSaleDate']['date'])<date.fromisoformat(p['publishDate']):
                raise ValueError('Earlier edition exists; possible format reissue held')
    if re.search(r'\breissue[ds]?\b|\banniversary edition\b',soup(p.get('summary','')).get_text(' ',strip=True),re.I):
        raise ValueError('Publisher describes a reissue; held for review')
    roles={'Author':'author','Edited by':'editor','Editor':'editor','Translator':'translator','Translated by':'translator'}
    people=[{'name':clean(a['name']),'role':roles[a['role']]} for a in p['authors'] if a.get('role') in roles]
    if not people:raise ValueError('No supported contributor roles')
    return make_record(pid,p['title'],people[0]['name'],p['publishDate'],url,
        {'url':url,'text':f"{p['title']}; {'; '.join(a['name'] for a in people)}; Published {p['publishDate']}; ISBN {p['isbn']}; {p['imprint']}; poetry"},
        contributors=people,isbns=[p['isbn']],imprint=p['imprint'],source_label='UK publisher book page')

def collect(config,fetch,today):
    result=Result(complete=False); candidates=set(config.get('book_seeds',[])+config.get('recheck_urls',[]))
    for url in config['sources']:
        try:candidates.update(discover(fetch.get(url),today))
        except Exception as e:result.warn(url,e)
    visited=set()
    for url in sorted(candidates):
        if url in visited:continue
        visited.add(url);result.candidates+=1
        try:
            p=primary(fetch.get(url),url)
            if p['imprint'] not in config['imprints']:result.excluded+=1;continue
            if p['currentFormat'] not in ('Paperback','Hardback'):
                print_editions=[x for x in p.get('formats',[]) if x['format'] in ('Paperback','Hardback')]
                if not print_editions:result.excluded+=1;continue
                url=urljoin(BASE,print_editions[0]['url'])
                p=primary(fetch.get(url),url)
                if p['imprint'] not in config['imprints']:raise ValueError('Print edition imprint differs')
            item=record(p,config['id'],url)
            if item:result.records.append(item)
            else:result.excluded+=1
        except Exception as e:result.warn(url,e)
    result.warn(config['sources'][0],'Public curated poetry/author lists and tracked book pages, checked weekly; coming-soon shelves are capped and may omit later announcements. Not complete imprint coverage')
    return result
