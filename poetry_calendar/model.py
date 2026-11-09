from __future__ import annotations
import calendar
import hashlib
import re
import unicodedata
from datetime import date, datetime
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

SCHEMA_VERSION = 1

def today_uk():
    return datetime.now(ZoneInfo('Europe/London')).date()

def clean(value):
    return re.sub(r'\s+', ' ', str(value)).strip(' \u200b\ufeff')

def canonical_url(url):
    p = urlsplit(url)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Source URL must be an ordinary HTTP(S) URL')
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip('/') or '/', p.query, p.fragment))

def key(value):
    return re.sub(r'[^\w]+', ' ', unicodedata.normalize('NFKC', value).casefold()).strip()

def parse_date(raw):
    """Display precision is independent of internal range bounds; never invent a day."""
    original = clean(raw)
    text = re.sub(r'(\d)\s*(st|nd|rd|th)\b', r'\1', original, flags=re.I)
    text = re.sub(r'^(Publication date|Date published|Published)\s*:?\s*', '', text, flags=re.I)
    status = 'provisional' if re.search(r'provisional|approx|tbc|tbd', text, re.I) else 'publisher_stated'
    for fmt in ('%d %B %Y', '%d %b %Y', '%B %d, %Y', '%Y-%m-%d', '%d/%m/%Y', '%d.%m.%Y'):
        try:
            d = datetime.strptime(text, fmt).date()
            return dict(raw=original, precision='day', status=status, start=d.isoformat(), end=d.isoformat(), label=f'{d.day} {d:%B %Y}')
        except ValueError:
            pass
    for fmt in ('%B %Y', '%b %Y'):
        try:
            d = datetime.strptime(text, fmt).date()
            end = d.replace(day=calendar.monthrange(d.year, d.month)[1])
            return dict(raw=original, precision='month', status=status, start=d.isoformat(), end=end.isoformat(), label=f'{d:%B %Y}')
        except ValueError:
            pass
    m = re.fullmatch(r'(Spring|Summer|Autumn|Fall|Winter)\s+(\d{4})(?:,?\s+provisional)?', text, re.I)
    if m:
        season, year = m[1].lower(), int(m[2])
        start_month, end_month = {'spring':(3,5),'summer':(6,8),'autumn':(9,11),'fall':(9,11),'winter':(12,2)}[season]
        end_year = year + (season == 'winter')
        return dict(raw=original, precision='season', status='provisional', start=date(year,start_month,1).isoformat(), end=date(end_year,end_month,calendar.monthrange(end_year,end_month)[1]).isoformat(), label=f'{season.title()} {year}, provisional')
    m = re.fullmatch(r'(\d{4})(?:[;, .]*(?:exact )?date\s+tbc\.?)?', text, re.I)
    if m:
        year=int(m[1])
        return dict(raw=original, precision='year', status='provisional', start=f'{year}-01-01',end=f'{year}-12-31',label=f'{year}, date TBC')
    if re.fullmatch(r'(?:date\s+)?(?:tbc|tbd|forthcoming|coming soon)',text,re.I):
        return dict(raw=original,precision='unknown',status='provisional',start=None,end=None,label='Date TBC')
    raise ValueError(f'Unrecognised publication date: {original}')

def forthcoming(record, today):
    if record.get('record_status') != 'active':
        return False
    d=record['date']
    if d['end'] is None:
        return record.get('explicit_forthcoming',False)
    end=date.fromisoformat(d['end'])
    return end > today if d['precision']=='day' else end >= today

def sort_key(record):
    d=record['date']
    return (d['precision'] in ('unknown','year'), d['start'] or '9999', key(record['title']), record['publisher_id'])

def make_record(publisher_id, title, author, raw_date, source_url, evidence, **extra):
    title, author = clean(title), clean(author)
    if not title or not author:
        raise ValueError('Missing title or contributor')
    source_url=canonical_url(source_url)
    identity=publisher_id+'|'+source_url
    record=dict(id=hashlib.sha256(identity.encode()).hexdigest()[:20],publisher_id=publisher_id,title=title,
                contributors=[{'name':author,'role':'author'}],date=parse_date(raw_date),source_url=source_url,
                evidence=evidence,record_status='active',explicit_forthcoming=True)
    record.update(extra)
    return record

def content_identity(record):
    return (record['publisher_id'],key(record['title']),tuple(key(x['name']) for x in record['contributors']))
