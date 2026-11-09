"""Publisher poetry listings, catalogue facts and official announcements."""
import io
import re
from urllib.parse import urljoin
from pypdf import PdfReader
from .adapters import Result,soup
from .model import make_record,clean,canonical_url,key

def catalogue_poetry(pages,pid,url):
    result=Result()
    # Validate against the catalogue contents list as well as the per-book block.
    contents='\n'.join(pages[:2])
    pattern=r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*,\s*\d+\s+pages\s*\nDC\s*\(Poetry\)(?P<facts>.*?)Print:\s*(\d{13})\s*\nEbook:\s*\d{13}\s*\n([^\n]+)\n([^\n]+)'
    for number,page in enumerate(pages,1):
        markers=len(re.findall(r'DC\s*\(Poetry\)',page))
        matches=list(re.finditer(pattern,page,re.S))
        if markers!=len(matches): result.warn(url+f'#page={number}','Unparsed poetry catalogue entry; layout review needed')
        for m in matches:
            result.candidates+=1
            date,facts,isbn,title,author=m.groups()
            title,author=clean(title),clean(author)
            if f'{title} by {author}' not in clean(contents):
                result.warn(url+f'#page={number}','Catalogue title/contributor not confirmed by contents list');continue
            source=url+f'#page={number}&search={isbn}'
            result.records.append(make_record(pid,title,author,date,source,{'url':source,'text':f'{title}; {author}; {date}; print ISBN {isbn}; DC (Poetry)'},isbns=[isbn],source_label='Publisher catalogue',source_kind='catalogue'))
    return result

def fitzcarraldo(config,fetch,today):
    result=Result(complete=False); index=config['sources'][0]; pending=[index]; seen=set(); links=set()
    while pending:
        url=pending.pop(0)
        if url in seen: continue
        seen.add(url); doc=soup(fetch.get(url)); cards=doc.select('a.publication[href]')
        if not cards: result.warn(url,'No poetry publication cards; check changed layout')
        for a in cards: links.add(canonical_url(urljoin(url,a['href'])))
        for a in doc.select('a[rel=next], a.next'):
            target=urljoin(url,a['href'])
            if '/shop/poetry/' in target:pending.append(target)
    links.update(u for u in config.get('recheck_urls',[]) if '/books/' in u)
    for url in sorted(links):
        result.candidates+=1
        try:
            doc=soup(fetch.get(url)); top=doc.select_one('.details .top')
            title=doc.select_one('h1.book-title').get_text(' ',strip=True)
            author=top.select_one('.author').get_text(' ',strip=True)
            date=re.search(r'Published\s+(\d{1,2}\s+\w+\s+\d{4})',top.get_text(' ',strip=True))
            if not date: raise ValueError('Book publication date missing')
            result.records.append(make_record(config['id'],title,author,date[1],url,{'url':url,'text':f'{title}; {author}; Published {date[1]}; official poetry list'}))
        except Exception as e:result.warn(url,e)
    catalogue_index=config['sources'][1]
    try:
        doc=soup(fetch.get(catalogue_index)); catalogues=[]
        for a in doc.select('a[href]'):
            label=a.get_text(' ',strip=True)
            m=re.fullmatch(r'(Spring|Autumn)\s+(\d{4})\s+Catalogue',label)
            if m and int(m[2])>=today.year and a['href'].lower().endswith('.pdf'):
                catalogues.append((int(m[2]),m[1]=='Autumn',urljoin(catalogue_index,a['href'])))
        if not catalogues:result.warn(catalogue_index,'No current UK catalogue found')
        # The latest catalogue supplements the living poetry list; older books stay in state.
        for _,__,url in sorted(set(catalogues),reverse=True)[:1]:
            reader=PdfReader(io.BytesIO(fetch.get_pdf(url)))
            extra=catalogue_poetry([p.extract_text() for p in reader.pages],config['id'],url)
            result.candidates+=extra.candidates;result.warnings.extend(extra.warnings)
            for record in extra.records:
                match=next((r for r in result.records if key(r['title'])==key(record['title'])),None)
                if not match:result.records.append(record)
                elif match['date']['start']!=record['date']['start']:result.warn(url,'Catalogue date differs from current book page; book-page date retained')
    except Exception as e:result.warn(catalogue_index,e)
    result.warn(index,'Official poetry list plus latest UK catalogue; announcements elsewhere may be missing')
    return result

def announcement(html,pid,url,overrides=None):
    result=Result(complete=False);doc=soup(html);body=doc.select_one('.entry-content')
    if not body:raise ValueError('Announcement content missing')
    intro=body.find('p'); text=body.get_text(' ',strip=True)
    date=re.search(r'collections will publish in\s+((?:spring|summer|autumn|winter)\s+\d{4})',text,re.I)
    if not date:raise ValueError('No explicit shared publication season; requires review')
    titles=intro.find_all('em',recursive=False)
    if not titles:raise ValueError('Announcement title list changed')
    for em in titles:
        result.candidates+=1
        title=em.get_text(' ',strip=True)
        author=re.match(r'\s*by\s+(.+?)(?:,\s*(?:and\s*)?|\.\s*$)',str(em.next_sibling))
        if not author:result.warn(url,f'Contributor missing for {title}');continue
        link=next((a['href'] for a in body.select('a[href]') if '/doi/book/' in a['href'] and a.get_text(' ',strip=True).startswith(title)),None)
        if not link:result.warn(url,f'Book link missing for {title}');continue
        isbn=link.rsplit('/',1)[-1]
        extra={'isbns':[isbn],'source_label':'Publisher announcement; season only'}
        if isbn in (overrides or {}):extra['contributors']=overrides[isbn]
        result.records.append(make_record(pid,title,author[1].strip(),date[1],link,{'url':url,'text':f'{title}; {author[1]}; collections will publish in {date[1]}'},**extra))
    return result

def pavilion(config,fetch,today):
    result=Result(complete=False);index=config['sources'][0];doc=soup(fetch.get(index))
    links=set(config.get('announcement_seeds',[]))|set(config.get('recheck_evidence_urls',[]))
    for a in doc.select('.entry-title a[href]'):
        text=a.get_text(' ',strip=True)
        if re.search(r'pavilion.*collections',text,re.I):
            year=re.search(r'20\d{2}',text)
            if year and int(year[0])>=today.year:links.add(urljoin(index,a['href']))
    if not links:result.warn(index,'No current annual announcements found')
    for url in sorted(links):
        try:
            extra=announcement(fetch.get(url),config['id'],url,config.get('contributor_overrides'))
            result.records.extend(extra.records);result.candidates+=extra.candidates;result.warnings.extend(extra.warnings)
        except Exception as e:result.warn(url,e)
    result.warn(index,'Official annual announcements, checked weekly; book pages currently inaccessible. Seasonal dates retained. Tagged archive discovery is partial.')
    return result
