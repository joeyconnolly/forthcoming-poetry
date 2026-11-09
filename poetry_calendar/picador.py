"""Public Pan Macmillan poetry catalogue; no internal API access."""
import json
import re
from datetime import date
from urllib.parse import urljoin, urlsplit
from .adapters import Result, soup
from .model import canonical_url, clean, key, make_record

def entities(doc):
    for script in doc.select('script[type="application/ld+json"]'):
        data=json.loads(script.get_text())
        for item in data if isinstance(data,list) else [data]:
            yield from item.get('@graph',[item])

def listing(html,url,name='Poetry'):
    doc=soup(html)
    lists=[x for x in entities(doc) if x.get('@type')=='ItemList' and x.get('name')==name]
    if len(lists)!=1 or not lists[0].get('itemListElement'):
        raise ValueError('Expected populated Poetry catalogue metadata')
    books=[x['item'] for x in lists[0]['itemListElement']]
    if any(x.get('@type')!='Book' for x in books):raise ValueError('Unexpected catalogue item type')
    pages={urljoin(url,a['href']) for a in doc.select('a[href]') if re.fullmatch(r'/genres/fiction/poetry/\d+/?',urlsplit(a['href']).path)}
    return books,pages

def book(html,url):
    doc=soup(html)
    matches=[x for x in entities(doc) if x.get('@type')=='Book' and canonical_url(x.get('url','https://invalid.example/'))==canonical_url(url)]
    if len(matches)!=1:raise ValueError('Expected one primary Book matching requested URL')
    item=matches[0]
    for field in ('name','author','datePublished','isbn','publisher','genre','bookFormat'):
        if not item.get(field):raise ValueError('Missing book field: '+field)
    # ISO day on the Book entity, never the surrounding webpage publication date.
    date.fromisoformat(item['datePublished'])
    if not re.fullmatch(r'\d{13}',str(item['isbn'])):raise ValueError('Invalid ISBN')
    return item

def collect(config,fetch,today):
    result=Result(complete=False); index=config['sources'][0]
    pending=list(config['sources']); seen=set(); candidates={}
    while pending:
        url=pending.pop(0)
        if url in seen:continue
        seen.add(url)
        try:
            items,pages=listing(fetch.get(url),url,'Picador Books' if '/picador/books' in url else 'Poetry')
            pending.extend(sorted(pages-seen))
            for item in items:
                result.candidates+=1
                try:
                    pub=date.fromisoformat(item['datePublished'][:10])
                    if pub>today:candidates[canonical_url(item['url'])]=item
                    else:result.excluded+=1
                except (KeyError,ValueError,TypeError) as e:result.warn(url,'Invalid catalogue book date: '+str(e))
        except Exception as e:result.warn(url,e)
    for url in config.get('recheck_urls',[]):candidates.setdefault(url,None)
    for url in sorted(candidates):
        try:
            item=book(fetch.get(url),url)
            if item['publisher'].get('name')!='Picador':result.excluded+=1;continue
            genres=' '.join(item['genre']).lower()
            if not re.search(r'poetry|poems',genres) or re.search(r'criticism|study guide|writing guide',genres):
                result.excluded+=1;continue
            if item['bookFormat'].rsplit('/',1)[-1] not in ('Paperback','Hardcover'):
                result.excluded+=1;continue
            # Explicit related editions let us reject a later format of a published work.
            earlier=False
            for variant in item.get('workExample',[]):
                other_url=variant.get('url')
                if not other_url or canonical_url(other_url)==canonical_url(url):continue
                other=book(fetch.get(other_url),other_url)
                if key(other['name'])!=key(item['name']):raise ValueError('Related edition title mismatch')
                if date.fromisoformat(other['datePublished'])<date.fromisoformat(item['datePublished']):earlier=True
            if earlier:
                result.warn(url,'Earlier edition exists; later format held as possible reissue');continue
            description=soup(item.get('description','')).get_text(' ',strip=True)
            if re.search(r'\breissue\b|\breissued\b|\banniversary edition\b|\bfirst published\b',description,re.I):
                result.warn(url,'Possible reissue in publisher description; held for review');continue
            authors=item['author'] if isinstance(item['author'],list) else [item['author']]
            contributors=[{'name':clean(a['name']),'role':'author'} for a in authors]
            result.records.append(make_record(config['id'],item['name'],contributors[0]['name'],item['datePublished'],url,
                {'url':url,'text':f"{item['name']}; {'; '.join(a['name'] for a in contributors)}; {item['datePublished']}; ISBN {item['isbn']}; Picador; publisher poetry classification"},
                contributors=contributors,isbns=[item['isbn']],source_label='UK publisher book page'))
        except Exception as e:result.warn(url,e)
    result.warn(index,'Public poetry catalogue pagination, first Picador catalogue page and known future book pages; uncategorised announcements and other editions may be missing')
    return result
