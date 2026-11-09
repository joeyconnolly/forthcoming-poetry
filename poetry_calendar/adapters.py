"""Adapters return facts and diagnostics, never mutate storage or render HTML."""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .model import clean, make_record

@dataclass
class Result:
    records:list=field(default_factory=list)
    warnings:list=field(default_factory=list)
    candidates:int=0
    excluded:int=0
    complete:bool=True

    def warn(self,url,reason):
        self.complete=False
        self.warnings.append({'url':url,'reason':str(reason) or type(reason).__name__})

def soup(html): return BeautifulSoup(html,'html.parser')

def bloodaxe(config,fetch,today):
    result=Result()
    for url in config['sources']:
        doc=soup(fetch.get(url)); forms=doc.select('form:has(h4)')
        if not forms: result.warn(url,'No expected publication forms; empty result requires review')
        for form in forms:
            result.candidates+=1
            try:
                title=form.h4.get_text(' ',strip=True); author=form.select_one('p strong').get_text(' ',strip=True)
                text=form.get_text(' ',strip=True)
                date=re.search(r'Publication Date:\s*(\d{1,2}\s+\w+\s+\d{4})',text)[1]
                link=urljoin(url,form.select_one('a[href*="/ecs/product/"]')['href'])
                isbn=re.findall(r'ISBN:\s*(\d{13})',text)
                subtitle=form.h4.find_next_sibling('p').get_text(' ',strip=True)
                if subtitle.startswith('Publication Date'): subtitle=''
                result.records.append(make_record(config['id'],title,author,date,link,{'url':url,'text':f'{author}; {title}; Publication Date: {date}'},isbns=isbn,subtitle=subtitle))
            except (AttributeError,TypeError,ValueError,KeyError) as e: result.warn(url,f'Malformed publication card: {e}')
    return result

def ninearches(config,fetch,today):
    result=Result(); index=config['sources'][0]; doc=soup(fetch.get(index))
    # Read year headings in document order; no hard-coded future year or title limit.
    year=None; candidates={}
    for node in doc.find_all(['h2','a']):
        if node.name=='h2':
            m=re.search(r'Poetry Publications:\s*(\d{4})',node.get_text(' ',strip=True))
            year=int(m[1]) if m else None
        elif year is not None and year>=today.year and '/publications/poetry-collections/' in node.get('href',''):
            url=urljoin(index,node['href']); label=clean(node.get_text(' ',strip=True))
            if label and url.rstrip('/')!=index.rstrip('/'): candidates.setdefault(url,[]).append(label)
    if not candidates: result.warn(index,'No current/future year titles found; verify catalogue year headings')
    for url,labels in candidates.items():
        result.candidates+=1
        try:
            detail=soup(fetch.get(url)); text=detail.get_text(' ',strip=True)
            m=re.search(r'Publication date:\s*(\d{1,2}\s*(?:st|nd|rd|th)?\s+\w+\s+\d{4}|\w+\s+\d{4})',text,re.I)
            if not m: raise ValueError('Publication date missing')
            if re.search(r'CBV:\s*Creative writing|DCF:\s*(?:Writing|Literary|Criticism)|guide to (?:writing|poetry)',text,re.I):
                result.excluded+=1; continue
            if not re.search(r'DCF:\s*Poetry Collections|poetry anthology',text,re.I):
                raise ValueError('Poetry classification needs review')
            title=labels[0]; author=labels[1] if len(labels)>1 else ''
            if author==title: raise ValueError('Contributor not separated from title')
            result.records.append(make_record(config['id'],title,author,m[1],url,{'url':url,'text':f'{title}; {author}; Publication date: {m[1]}; DCF: Poetry Collections'},isbns=re.findall(r'ISBN:\s*(\d{13})',text)))
        except Exception as e: result.warn(url,e)
    return result

def shearsman(config,fetch,today):
    result=Result(); index=config['sources'][0]; doc=soup(fetch.get(index)); urls=set()
    for a in doc.select('a[href]'):
        m=re.search(r'/(\d{4})-titles--date-order',a['href'])
        if m and int(m[1])>=today.year: urls.add(urljoin(index,a['href']))
    if not urls: result.warn(index,'No current/future annual catalogues discovered')
    for url in sorted(urls):
        try: page=soup(fetch.get(url))
        except Exception as e: result.warn(url,e); continue
        rows=[r for r in page.select('.dmRespRow') if r.select_one('h4') and re.search(r'Published\s+',r.get_text(' ',strip=True))]
        # Responsive wrappers can contain several rows. Only actual title rows qualify.
        rows=[r for r in rows if len(r.select('h4'))==1]
        if not rows: result.warn(url,'No expected dated title rows')
        for row in rows:
            result.candidates+=1
            try:
                heading=row.h4; chunks=[clean(t) for t in heading.stripped_strings if clean(t)]
                if len(chunks)<2: raise ValueError('Cannot separate author and title')
                author=chunks[0]; title=' '.join(chunks[1:]); text=row.get_text(' ',strip=True)
                if re.search(r'^Shearsman\s+\d|^Shearsman Magazine',title,re.I) or re.search(r'This is a memoir|essays and criticism|critical study',text,re.I):
                    result.excluded+=1; continue
                if re.search(r'\bnovel\b|\bnovella\b|\bprose poems?\b',text,re.I):
                    raise ValueError(f'Hybrid/prose classification requires review: {title}')
                if re.search(r'second edition|reissue|first published in',text,re.I) and not re.search(r'Translated from|Poem texts translated',text,re.I):
                    raise ValueError('Reissue or edition requires editorial review')
                date_match=re.search(r'Published\s+((?:\d{1,2}\s+)?(?:[A-Za-z]+\s+)?\d{4}(?:[;, .]*(?:exact )?[Dd]ate\s+tbc\.?)?)',text)
                if not date_match: raise ValueError('No recognised publication statement')
                # Some publisher buy-buttons link to a different book. Attribute the
                # exact factual catalogue row rather than trusting an unverified shop link.
                source=url+'#'+row.get('id','')
                result.records.append(make_record(config['id'],title,author,date_match[1],source,{'url':source,'text':f'{author}; {title}; Published {date_match[1]}'},isbns=re.findall(r'ISBN\s+(\d{13})',text)))
            except Exception as e: result.warn(url,e)
    return result

def seren(config,fetch,today):
    result=Result(); url=config['sources'][0]; seen=set()
    while url:
        if url in seen: result.warn(url,'Pagination loop'); break
        seen.add(url); doc=soup(fetch.get(url)); cards=doc.select('.book-panel')
        if not cards and not re.search(r'no (?:books|products|results)',doc.get_text(' ',strip=True),re.I): result.warn(url,'No expected catalogue cards or explicit empty state')
        for card in cards:
            result.candidates+=1
            try:
                a=card.select_one('h4 a'); title=a.get_text(' ',strip=True); link=urljoin(url,a['href'])
                author=card.select_one('.name').get_text(' ',strip=True)
                detail=soup(fetch.get(link)); text=detail.get_text(' ',strip=True)
                categories=[a.get_text(' ',strip=True).lower() for a in detail.select('a[href*="/books/"]')]
                # Product taxonomy must be local, not the navigation's Poetry link.
                facts=detail.select_one('.book-info') or detail.select_one('.summary')
                facts_text=facts.get_text(' ',strip=True) if facts else ''
                genre=re.search(r'(?:Category|Categories|Genre):?\s*([^\n]+)',detail.get_text('\n',strip=True),re.I)
                # A date can exclude an already-published book even if its genre is ambiguous.
                m=re.search(r'(?:Publication [Dd]ate|Published):?\s*((?:\d{1,2}\s+)?\w+\s+\d{4}|\w+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{4})',text)
                if m:
                    from .model import parse_date
                    d=parse_date(m[1])
                    if d['end'] and d['end']<today.isoformat(): result.excluded+=1; continue
                if genre and re.search(r'fiction|crime|biography|history',genre[1],re.I): result.excluded+=1; continue
                if genre and not re.search(r'poetry',genre[1],re.I): raise ValueError('Catalogue category does not establish poetry genre')
                if not genre: raise ValueError('Product genre not identified; cannot infer poetry from navigation')
                if not m: raise ValueError('Publication date missing')
                result.records.append(make_record(config['id'],title,author,m[1],link,{'url':link,'text':f'{title}; {author}; {m[0]}; {genre[0]}'}))
            except Exception as e: result.warn(url,e)
        nxt=doc.select_one('a.next.page-numbers, a[rel="next"]'); url=urljoin(url,nxt['href']) if nxt else None
    return result

def gallery(config,fetch,today):
    result=Result(); url=config['sources'][0]; pages=set(); products=set()
    while url:
        if url in pages: result.warn(url,'Pagination loop'); break
        if len(pages)>=config.get('max_pages',100): result.warn(url,'Configured page budget reached; catalogue coverage is partial'); break
        pages.add(url)
        try: doc=soup(fetch.get(url))
        except Exception as e: result.warn(url,e); break
        links={urljoin(url,a['href']) for a in doc.select('ul.products li.product a.woocommerce-LoopProduct-link[href]')}
        if not links: result.warn(url,'No expected product cards')
        for link in sorted(links-products):
            products.add(link); result.candidates+=1
            try:
                detail=soup(fetch.get(link)); title=detail.select_one('.et_pb_wc_title h1').get_text(' ',strip=True)
                author=detail.select_one('.et_pb_wc_description h4').get_text(' ',strip=True)
                info=next((x.get_text(' ',strip=True) for x in detail.select('.wb_cptb_content') if 'publication date:' in x.get_text().lower()),'')
                m=re.search(r'Publication date:\s*((?:\d{1,2}\s+)?\w+\s+\d{4})',info,re.I)
                if not m:
                    years=re.findall(r'Year Published:\s*(\d{4})',detail.get_text(' ',strip=True),re.I)
                    if years and all(int(y)<today.year for y in years): result.excluded+=1; continue
                    raise ValueError('No recognised publication date')
                result.records.append(make_record(config['id'],title,author,m[1],link,{'url':link,'text':f'{title}; {author}; Publication date: {m[1]}'},isbns=re.findall(r'\b\d{13}\b',info)))
            except Exception as e: result.warn(link,e)
        nxt=doc.select_one('.woocommerce-pagination a.next[href]'); url=urljoin(url,nxt['href']) if nxt else None
    return result

def gallery_feeds(config,fetch,today):
    """RSS is discovery only; neither feed pubDate nor dc:creator describes a book."""
    result=Result(); links=set()
    for url in config['sources']:
        try:
            root=ET.fromstring(fetch.get(url)); items=root.findall('./channel/item')
            if not items: result.warn(url,'No RSS items; verify feed')
            for item in items:
                canonical=item.findtext('link') or ''
                if '/product/' in canonical: links.add(canonical)
                content=item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or ''
                for a in soup(content).select('a[href]'):
                    if '/product/' in a['href']: links.add(urljoin(url,a['href']))
            result.warn(url,f'Rolling feed: {len(items)} announcements/products processed; older undiscovered records are outside this scope')
        except Exception as e: result.warn(url,e)
    # A future record must still be rechecked after it rolls out of the feed.
    links.update(config.get('recheck_urls',[]))
    for link in sorted(links):
        result.candidates+=1
        try:
            detail=soup(fetch.get(link))
            categories=detail.select_one('.posted_in')
            if not categories: raise ValueError('Product categories missing')
            if not any(a.get_text(' ',strip=True).casefold()=='poetry' for a in categories.select('a')):
                result.excluded+=1; continue
            title=detail.select_one('.et_pb_wc_title h1').get_text(' ',strip=True)
            author=detail.select_one('.et_pb_wc_description h4').get_text(' ',strip=True)
            info=next((x.get_text(' ',strip=True) for x in detail.select('.wb_cptb_content') if re.search(r'publication date:|year published:',x.get_text(),re.I)),'')
            m=re.search(r'Publication date:\s*((?:\d{1,2}\s+)?\w+\s+\d{4})',info,re.I)
            if not m:
                years=re.findall(r'Year Published:\s*(\d{4})',info,re.I)
                if years and all(int(y)<today.year for y in years): result.excluded+=1; continue
                raise ValueError('No recognised book publication date')
            result.records.append(make_record(config['id'],title,author,m[1],link,{'url':link,'text':f'{title}; {author}; Publication date: {m[1]}'}))
        except Exception as e: result.warn(link,e)
    return result

def faber(config,fetch,today):
    result=Result(); pending=[config['sources'][0]]; seen=set(); books={}
    for url in config.get('recheck_urls',[]): books[url]=None
    while pending:
        url=pending.pop(0)
        if url in seen: continue
        seen.add(url)
        doc=soup(fetch.get(url)); cards=doc.select('.card-prod')
        if not cards: result.warn(url,'No expected poetry listing cards')
        for card in cards:
            if not card.select_one('.pre-order-listing-trigger'): continue
            a=card.select_one('a.card-prod__info-tt'); author=card.select_one('.card-prod__info-name')
            if a and author: books[urljoin(url,a['href'])]=(a.get_text(' ',strip=True),author.get_text(' ',strip=True))
        for a in doc.select('a[href]'):
            link=urljoin(url,a['href'])
            if re.fullmatch(r'https://www\.faber\.co\.uk/product-category/poetry/page/\d+/',link) and link not in seen: pending.append(link)
    for url,labels in books.items():
        result.candidates+=1
        try:
            detail=soup(fetch.get(url))
            facts={r.select_one('.txt-table-item__name').get_text(' ',strip=True):r.select_one('.txt-table-item__txt').get_text(' ',strip=True) for r in detail.select('.txt-table-item') if r.select_one('.txt-table-item__name') and r.select_one('.txt-table-item__txt')}
            title=detail.h1.get_text(' ',strip=True)
            if not labels: raise ValueError('Previously listed title missing from pre-order discovery; review required')
            text=detail.get_text(' ',strip=True)
            if re.search(r'diary|deluxe|audiobook|on writing|on difficulty',title,re.I) or facts.get('Format','').lower() in ('ebook','audio','audiobook'):
                result.excluded+=1; continue
            if not re.search(r'collection|anthology|poems|verse|pamphlet',text,re.I): raise ValueError('Poetry classification requires review')
            result.records.append(make_record(config['id'],title,labels[1],facts['Date Published'],url,{'url':url,'text':f"{title}; {labels[1]}; Date Published {facts['Date Published']}"},isbns=[facts['ISBN']]))
        except Exception as e: result.warn(url,e)
    result.warn(config['sources'][0],'Pre-order listings only; unlisted announcements and titles without pre-order markers are outside this scope')
    return result

def catalogue_snapshot(config,fetch,today):
    result=Result(complete=False)
    for item in config['catalogue_records']:
        result.candidates+=1
        result.records.append(make_record(config['id'],item['title'],item['author'],item['date'],item['url'],
            {'url':item['url'],'text':item['evidence']},isbns=[item['isbn']],source_kind='catalogue_snapshot',
            source_label='2026 publisher catalogue',evidence_checked_at=item['checked_at']))
    result.warn(config['sources'][0],'Dated catalogue import; publication changes and newer catalogues are not automatically verified')
    return result

def fitzcarraldo(config,fetch,today):
    from .batch_one import fitzcarraldo as run
    return run(config,fetch,today)

def pavilion(config,fetch,today):
    from .batch_one import pavilion as run
    return run(config,fetch,today)

ADAPTERS={'bloodaxe':bloodaxe,'ninearches':ninearches,'shearsman':shearsman,'seren':seren,'gallery':gallery,'gallery_feeds':gallery_feeds,'faber':faber,'catalogue_snapshot':catalogue_snapshot,'fitzcarraldo':fitzcarraldo,'pavilion':pavilion}
