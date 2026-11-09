"""Durable CSV uploads layered over, never overwritten by, collected observations."""
import copy
import csv
import json
import re
from datetime import datetime, timezone
from .model import canonical_url, clean, key, make_record

def load_imported(root):
    path=root/'data/imported.json'
    if not path.exists():return {'schema_version':1,'records':[]}
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version')!=1 or not isinstance(data.get('records'),list):
        raise ValueError('Unsupported imported-data schema')
    return data

def isbn(value):
    value=re.sub(r'[\s-]','',value).upper()
    if not value:return ''
    if re.fullmatch(r'\d{9}[\dX]',value):
        if sum((10-i)*(10 if c=='X' else int(c)) for i,c in enumerate(value))%11:
            raise ValueError('Invalid ISBN-10 checksum')
        stem='978'+value[:9]
        return stem+str((-sum(int(c)*(1 if i%2==0 else 3) for i,c in enumerate(stem)))%10)
    if re.fullmatch(r'97[89]\d{10}',value) and sum(int(c)*(1 if i%2==0 else 3) for i,c in enumerate(value))%10==0:
        return value
    raise ValueError('ISBN must be a valid ISBN-10 or ISBN-13 (or blank)')

def identity(record):
    people=[p['name'] for p in record['contributors'] if p['role']=='author']
    if not people:people=[p['name'] for p in record['contributors']]
    return key(record['title']),tuple(sorted(key(p) for p in people))

def matches(record,others):
    same=[x for x in others if x['publisher_id']==record['publisher_id']]
    known=set(record.get('matched_auto_ids',[]))
    numbers=set(record.get('isbns',[]))
    strong=[x for x in same if x['id'] in known or bool(known.intersection(x.get('matched_auto_ids',[]))) or
            canonical_url(x['source_url'])==canonical_url(record['source_url']) or
            bool(numbers.intersection(x.get('isbns',[])))]
    found=strong or [x for x in same if identity(x)==identity(record)]
    if len({identity(x) for x in found})>1:
        raise ValueError(f"Ambiguous duplicate for {record['title']!r}; source URL/ISBN matches different books")
    return found

def merge_imported(automatic,uploaded):
    """Uploaded values win, including dates, even after later automated refreshes."""
    result=copy.deepcopy(automatic)
    for item in uploaded:
        ids={r['id'] for r in matches(item,result)}
        result=[r for r in result if r['id'] not in ids]
        result.append(copy.deepcopy(item))
    return result

ALIASES={'title':'title','author':'author','authors':'author','publisher':'publisher',
    'publication date':'date','date':'date','isbn':'isbn','source url':'url','url':'url',
    'translator':'translator','translators':'translator','editor':'editor','editors':'editor'}
REQUIRED={'title','author','publisher','date','url'}

def read_csv(path,registry):
    names={}
    for publisher in registry:
        for name in [publisher['id'],publisher['name']]:
            names.setdefault(key(name),set()).add(publisher['id'])
    rows=[]
    with path.open(encoding='utf-8-sig',newline='') as handle:
        sample=handle.read(8192);handle.seek(0)
        try:dialect=csv.Sniffer().sniff(sample,delimiters=',;\t')
        except csv.Error:dialect=csv.excel
        reader=csv.DictReader(handle,dialect=dialect)
        if not reader.fieldnames:raise ValueError('CSV is empty; a header row is required')
        headers={}
        for header in reader.fieldnames:
            field=ALIASES.get(clean(header).lower().replace('_',' '))
            if field:
                if field in headers.values():raise ValueError('Duplicate CSV column: '+header)
                headers[header]=field
        if REQUIRED-set(headers.values()):
            raise ValueError('Required columns: Title, Author, Publisher, Publication date, Source URL; ISBN is optional')
        for row in reader:
            if not any(v for v in row.values()):continue
            line=reader.line_num
            try:
                if None in row or any(v is None for v in row.values()):raise ValueError('Wrong number of CSV columns')
                fields={field:clean(row[header]) for header,field in headers.items()}
                if any(not fields[x] for x in REQUIRED):raise ValueError('Required cells cannot be blank (use Date TBC for an unknown date)')
                ids=names.get(key(fields['publisher']),set())
                if len(ids)!=1:raise ValueError('Unknown or ambiguous publisher; use an ID or display name from config/publishers.json')
                people=[]
                for field,role in [('author','author'),('translator','translator'),('editor','editor')]:
                    people.extend({'name':clean(name),'role':role} for name in fields.get(field,'').split(';') if clean(name))
                number=isbn(fields.get('isbn',''))
                r=make_record(next(iter(ids)),fields['title'],people[0]['name'],fields['date'],fields['url'],
                    {'url':canonical_url(fields['url']),'text':'User-supplied CSV bibliographic record'},
                    contributors=people,isbns=[number] if number else [],source_kind='csv_import',source_label='CSV import — takes priority over automatic sources')
                r['id']='import-'+r['id']
                rows.append((line,r))
            except (ValueError,KeyError,IndexError) as e:raise ValueError(f'CSV row {line}: {e}') from e
    if not rows:raise ValueError('CSV has no title rows')
    return rows

FIELDS=('publisher_id','title','contributors','date','source_url','isbns')
def import_csv(root,path,dry_run=False):
    from .pipeline import load_registry,load_state,update_lock,atomic_json
    with update_lock(root):
        rows=read_csv(path,load_registry(root)); data=load_imported(root)
        automatic=load_state(root)['records'];original={r['id']:copy.deepcopy(r) for r in data['records']}
        touched=set(); auto_matches=set(); now=datetime.now(timezone.utc).isoformat(timespec='seconds')
        for line,r in rows:
            try:
                r['matched_auto_ids']=sorted(x['id'] for x in matches(r,automatic))
                prior=matches(r,data['records'])
                if len(prior)>1:raise ValueError('Multiple uploaded records match; resolve imported.json before updating')
                if prior:
                    old=prior[0];r['id']=old['id'];r['matched_auto_ids']=sorted(set(r['matched_auto_ids'])|set(old.get('matched_auto_ids',[])))
                found=matches(r,automatic)
                r['matched_auto_ids']=sorted(set(r.get('matched_auto_ids',[]))|{x['id'] for x in found})
                if found:auto_matches.add(r['id'])
                r.update(first_seen_at=prior[0]['first_seen_at'] if prior else now,last_seen_at=now,last_verified_at=now,
                    imported_at=now,missing_checks=0,history=prior[0].get('history',[]) if prior else [])
                if prior:
                    old=prior[0]
                    if all(old.get(k)==r.get(k) for k in FIELDS) and old.get('matched_auto_ids',[])==r['matched_auto_ids']:
                        r=copy.deepcopy(old)
                    else:r['history']=r['history']+[{'observed_at':now,'previous':{k:old.get(k) for k in FIELDS}}]
                data['records']=[x for x in data['records'] if x['id']!=r['id']]+[r]
                touched.add(r['id'])
            except ValueError as e:raise ValueError(f'CSV row {line}: {e}') from e
        # Validate the final merged view before committing any changes.
        merge_imported(automatic,data['records'])
        summary={'added':0,'updated':0,'unchanged':0}
        for r in data['records']:
            if r['id'] not in touched:continue
            old=original.get(r['id'])
            if old==r:summary['unchanged']+=1
            elif old or r['id'] in auto_matches:summary['updated']+=1
            else:summary['added']+=1
        data['records'].sort(key=lambda r:r['id'])
        if not dry_run and (summary['added'] or summary['updated']):atomic_json(root/'data/imported.json',data)
        return summary
