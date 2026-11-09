"""Public Pan Macmillan poetry catalogue; no internal API access."""
import json
import re
import xml.etree.ElementTree as ET
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
    matches=[x for x in entities(doc) if x.get('@type') in ('Book','Audiobook') and canonical_url(x.get('url','https://invalid.example/'))==canonical_url(url)]
    if len(matches)!=1:raise ValueError('Expected one primary Book matching requested URL')
    item=matches[0]
    for field in ('name','author','datePublished','isbn','publisher','genre','bookFormat'):
        if not item.get(field):raise ValueError('Missing book field: '+field)
    # ISO day on the Book entity, never the surrounding webpage publication date.
    date.fromisoformat(item['datePublished'])
    if not re.fullmatch(r'\d{13}',str(item['isbn'])):raise ValueError('Invalid ISBN')
    return item

def author_books(html):
    lists=[x for x in entities(soup(html)) if x.get('@type')=='ItemList' and x.get('name','').startswith('Books by ')]
    if not lists:raise ValueError('Expected author book list')
    return {canonical_url(x['item']['url']) for group in lists for x in group['itemListElement'] if x['item'].get('@type')=='Book'}

def author_slug(url):
    match=re.fullmatch(r'/authors/([^/]+)/[^/]+/\d+/?',urlsplit(url).path)
    return match[1] if match else None

def sitemap_candidates(xml,authors,today):
    """lastmod is a discovery hint only, never a publication date."""
    root=ET.fromstring(xml)
    if not root.tag.endswith('urlset'):raise ValueError('Expected product URL sitemap')
    found=set()
    for entry in root:
        fields={x.tag.rsplit('}',1)[-1]:x.text for x in entry}
        url=fields.get('loc',''); modified=fields.get('lastmod') or ''
        if author_slug(url) in authors and modified[:10]>=today.isoformat():found.add(canonical_url(url))
    return found

def collect(config,fetch,today):
    result=Result(complete=False); index=config['sources'][0]
    pending=list(config['sources']); seen=set(); candidates={}; authors=set()
    while pending:
        url=pending.pop(0)
        if url in seen:continue
        seen.add(url)
        try:
            items,pages=listing(fetch.get(url),url,'Picador Books' if '/picador/books' in url else 'Poetry')
            pending.extend(sorted(pages-seen))
            for item in items:
                if '/genres/fiction/poetry' in url and author_slug(item.get('url','')):authors.add(author_slug(item['url']))
                result.candidates+=1
                try:
                    pub=date.fromisoformat(item['datePublished'][:10])
                    if pub>today:candidates[canonical_url(item['url'])]=item
                    else:result.excluded+=1
                except (KeyError,ValueError,TypeError) as e:result.warn(url,'Invalid catalogue book date: '+str(e))
        except Exception as e:result.warn(url,e)
    if config.get('sitemap_index'):
        try:
            root=ET.fromstring(fetch.get(config['sitemap_index']))
            maps=[node.text for node in root.iter() if node.tag.endswith('loc') and re.fullmatch(r'/sitemaps/products-\d+\.xml',urlsplit(node.text).path)]
            if not maps:raise ValueError('No public product sitemaps found')
            for url in maps:
                for target in sitemap_candidates(fetch.get(url),authors,today):candidates.setdefault(target,None)
        except Exception as e:result.warn(config['sitemap_index'],e)
    for url in config.get('author_sources',[]):
        try:
            for target in author_books(fetch.get(url)):candidates.setdefault(target,None)
        except Exception as e:result.warn(url,e)
    for url in config.get('recheck_urls',[])+config.get('book_seeds',[]):candidates.setdefault(url,None)
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
    result.warn(index,'Poetry catalogue, first imprint page, tracked authors, sitemap candidates for known poetry authors and known future books; sitemap dates are discovery hints only. Unlisted/new authors may be missing')
    return result
