"""Read the private canonical Sheet; return only explicitly public fields."""
import hashlib
import json
import os
from datetime import date,datetime,timedelta
from urllib.parse import urlsplit
from .model import clean,key,parse_date

SCOPE='https://www.googleapis.com/auth/spreadsheets.readonly'
HEADERS={'title':'title','author':'author','publisher':'publisher','pub date':'date',
    'format':'format','url to book page (if applicable)':'url','translator':'translator','status':'status'}
FORMATS={x.casefold():x for x in ('Single-author collection','Pamphlet','Anthology','Translation','Selected poems','Collected poems')}
class SheetError(ValueError):pass

def normal_header(value):return clean(value).casefold()

def grid_values(payload):
    sheets=payload.get('sheets',[])
    if len(sheets)!=1:raise SheetError('Expected exactly one canonical tab.')
    blocks=sheets[0].get('data',[])
    if len(blocks)!=1 or blocks[0].get('startRow',0)!=0 or blocks[0].get('startColumn',0)!=0:
        raise SheetError('Unexpected canonical tab response.')
    cells=[r.get('values',[]) for r in blocks[0].get('rowData',[])]
    if not cells:raise SheetError('Canonical tab has no header row.')
    headers=[normal_header(c.get('formattedValue','')) for c in cells[0]]
    values=[]
    for number,row in enumerate(cells):
        output=[]
        for column,cell in enumerate(row):
            text=cell.get('formattedValue','')
            header=headers[column] if column<len(headers) else ''
            if number and header=='url to book page (if applicable)' and cell.get('hyperlink'):
                text=cell['hyperlink']
            if number and header=='pub date' and cell.get('effectiveFormat',{}).get('numberFormat',{}).get('type') in ('DATE','DATE_TIME'):
                serial=cell.get('effectiveValue',{}).get('numberValue')
                if serial is not None:
                    try:text=(date(1899,12,30)+timedelta(days=int(serial))).isoformat()
                    except (ValueError,OverflowError,TypeError):raise SheetError(f'Row {number+1}: invalid date cell.') from None
            output.append(text)
        values.append(output)
    return values

def fetch_values(config):
    secret=os.environ.get('GOOGLE_SHEETS_CREDENTIALS','')
    if not secret:raise SheetError('GOOGLE_SHEETS_CREDENTIALS is missing from this build.')
    try:
        from google.oauth2.service_account import Credentials
        from google.auth.transport.requests import AuthorizedSession
        info=json.loads(secret)
        if info.get('type')!='service_account' or info.get('token_uri')!='https://oauth2.googleapis.com/token':
            raise ValueError('Unexpected credential type')
        credentials=Credentials.from_service_account_info(info,scopes=[SCOPE])
    except Exception:raise SheetError('Could not load the service-account credential. Check the repository secret.') from None
    tab=config['tab'].replace("'","''")
    try:
        with AuthorizedSession(credentials,refresh_timeout=30) as session:
            response=session.get('https://sheets.googleapis.com/v4/spreadsheets/'+config['spreadsheet_id'],
                params={'ranges':f"'{tab}'!A:Z",'includeGridData':'true',
                    'fields':'sheets(properties(title),data(startRow,startColumn,rowData(values(formattedValue,hyperlink,effectiveValue,effectiveFormat(numberFormat)))))'},timeout=40)
    except Exception:raise SheetError('Google authentication or Sheet request failed; check access and retry. No source values were logged.') from None
    if response.status_code!=200:
        raise SheetError(f'Google Sheets returned HTTP {response.status_code}. Check the API, Viewer sharing, spreadsheet ID and tab name.')
    try:return grid_values(response.json())
    except SheetError:raise
    except Exception:raise SheetError('Unexpected Google Sheets response; no source values were logged.') from None

def public_records(values):
    if not values:raise SheetError('Canonical tab has no header row.')
    columns={}
    for i,text in enumerate(values[0]):
        field=HEADERS.get(normal_header(text))
        if field:
            if field in columns:raise SheetError('Duplicate required header: '+field)
            columns[field]=i
    missing=set(HEADERS.values())-set(columns)
    if missing:raise SheetError('Missing canonical columns: '+', '.join(sorted(missing)))
    result=[];seen={};duplicates=0
    for number,row in enumerate(values[1:],2):
        cell=lambda field:clean(row[columns[field]]) if columns[field]<len(row) else ''
        status=cell('status').casefold()
        if status in ('','past','excluded'):continue
        if status!='live':raise SheetError(f'Row {number}: unrecognised editorial status.')
        if not cell('title') and not any(
            clean(value) for index, value in enumerate(row) if index != columns['status']
        ):
            continue  # Ignore empty rows with a prefilled Live status.
        for field in ('title','publisher'):
            if not cell(field):raise SheetError(f'Row {number}: missing {field}.')
        try:
            raw_date=cell('date') or 'Date TBC'
            try:d=parse_date(raw_date)
            except ValueError:
                d=parse_date(datetime.strptime(raw_date,'%d/%m/%y').date().isoformat())
        except ValueError:raise SheetError(f'Row {number}: unrecognised Pub Date; use a date, month/year, year or Date TBC.') from None
        fmt=cell('format')
        url=cell('url')
        try:
            u=urlsplit(url)
            if url and (u.scheme not in ('https','http') or not u.hostname or u.username or u.password):raise ValueError()
        except ValueError:raise SheetError(f'Row {number}: invalid book-page URL.') from None
        # Never carry the input row, status, Notes, or Form submitted into output.
        record={'title':cell('title'),'author':cell('author'),'publisher':cell('publisher'),
            'date':d,'format':FORMATS.get(fmt.casefold(),fmt),'url':url,'translator':cell('translator')}
        identity=tuple(key(record[k]) for k in ('title','author','publisher','translator'))
        if identity in seen:
            prior,prior_row=seen[identity]
            if prior!=record:raise SheetError(f'Rows {prior_row} and {number}: conflicting duplicate book entries.')
            duplicates+=1;continue
        seen[identity]=(record,number);result.append(record)
    result.sort(key=lambda r:(r['date']['start'] or '9999',key(r['title']),key(r['publisher'])))
    return result,duplicates

def publisher_id(name):return hashlib.sha256(key(name).encode()).hexdigest()[:12]

def build_sheet(root,today):
    from .sheet_render import render_sheet
    config=json.loads((root/'config/sheet.json').read_text(encoding='utf-8'))
    records,duplicates=public_records(fetch_values(config))
    render_sheet(root,today,records)
    print(f'Sheet build succeeded: {len(records)} public titles, {len({r["publisher"] for r in records})} publishers; {duplicates} identical duplicates collapsed.')


