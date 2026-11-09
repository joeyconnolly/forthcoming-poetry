"""One public distributor feed, shared across registry-driven publishers."""
import csv
import io
import re
from urllib.parse import urlencode
from .adapters import Result
from .model import make_record, key

INDEX='https://inpressbooks.co.uk/pages/whats-new'
REQUIRED={'Title','Authors','Publisher','ISBN','Publication Date','Category','BIC Code','Main Description'}
# Decisions based on the distributor descriptions, 9 November 2026.
HOLDS={
 '9781919370514':'Mixed poems, essays and photographs; hybrid review',
 '9781916751613':'Mixed poems, essays and translation notes; hybrid review',
 '9781067693985':'Expanded second edition; edition review',
 '9781918628128':'Collection first published in 2008; edition review',
 '9781913958763':'Activity and writing-prompt book; scope review',
 '9781915628671':'Children’s poetry classification needs review',
}

def contributors(raw):
    # Only explicit role markers split a contributor string; names stay intact.
    markers=r'(translated by|edited by|foreword by|illustrated by|cover design or artwork by|photographs by)'
    parts=re.split(markers,raw,flags=re.I)
    roles={'translated by':'translator','edited by':'editor','foreword by':'foreword','illustrated by':'illustrator','cover design or artwork by':'cover artist','photographs by':'photographer'}
    people=[]
    if parts[0].strip(' ,'): people.append({'name':parts[0].strip(' ,'),'role':'author'})
    for i in range(1,len(parts),2):
        name=parts[i+1].strip(' ,')
        if name: people.append({'name':name,'role':roles[parts[i].lower()]})
    if not people: raise ValueError('Missing contributors')
    return people

def parse_feed(text,registry,evidence_url):
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if not REQUIRED.issubset(reader.fieldnames or []): raise ValueError('Inpress CSV schema changed or returned a non-CSV response')
    mapping={p['inpress_name']:p['id'] for p in registry if p.get('inpress_name')}
    results={pid:Result(complete=False) for pid in mapping.values()}
    rows=list(reader)
    if not rows: raise ValueError('Inpress returned an empty feed')
    for row in rows:
        pid=mapping.get(row.get('Publisher'))
        if not pid: continue
        result=results[pid]
        if row.get('Category','').strip().lower()!='poetry': continue
        result.candidates+=1
        isbn=row.get('ISBN','').strip()
        url=INDEX+'?'+urlencode({'search':isbn})
        try:
            if not re.fullmatch(r'\d{13}',isbn): raise ValueError('Missing or malformed print ISBN')
            if isbn in HOLDS: raise ValueError(HOLDS[isbn])
            description=row.get('Main Description','')
            if re.search(r'\b(?:second edition|reissue|first published in)\b',description,re.I): raise ValueError('Edition requires review')
            if row.get('BIC Code','').startswith('Y'): raise ValueError('Children’s category requires review')
            people=contributors(row['Authors'])
            record=make_record(pid,row['Title'],people[0]['name'],row['Publication Date'],url,
                {'url':evidence_url,'text':f"Inpress: {row['Title']}; {row['Authors']}; {row['Publication Date']}; ISBN {isbn}; category Poetry"},
                contributors=people,isbns=[isbn],source_label='Inpress listing',source_kind='distributor',territory='UK/Ireland trade listing',format=row.get('Format',''))
            result.records.append(record)
        except (ValueError,KeyError,TypeError) as e: result.warn(url,e)
    for result in results.values():
        result.warnings.append({'url':INDEX,'reason':'Rolling Inpress trade list; not a complete publisher catalogue. Older missing entries are retained.'})
    return results

def load_feed(fetch,registry):
    page=fetch.get(INDEX)
    match=re.search(r'const sheetUrl\s*=\s*"(https://docs\.google\.com/spreadsheets/d/e/[A-Za-z0-9_-]+/pub\?output=csv)"',page)
    if not match: raise ValueError('Inpress public CSV link not found')
    return parse_feed(fetch.get(match[1]),registry,match[1])

def supplement(primary,extra):
    """Publisher observations win; distributor fills gaps without erasing conflicts."""
    for record in extra.records:
        match=next((r for r in primary.records if set(r.get('isbns',[])) & set(record.get('isbns',[])) or key(r['title'])==key(record['title'])),None)
        if match:
            if match['date']['start']!=record['date']['start']: primary.warn(record['source_url'],'Inpress date differs from publisher; publisher date retained')
        else: primary.records.append(record)
    primary.candidates+=extra.candidates
    primary.warnings.extend(extra.warnings)
    primary.complete=False
    return primary
