import copy
import json
import os
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch,MagicMock
from poetry_calendar.sheets import SheetError,public_records,grid_values,fetch_values,build_sheet,SCOPE
from poetry_calendar.sheet_render import render_sheet

HEADERS=['Title','Author','Publisher','Pub Date','Format','URL to book page (if applicable)','Translator','Notes','Status','Form submitted']
ROW=['A New Book','Éva Poet','A New Publisher','15 April 2027','Translation','https://example.org/book','A Translator','PRIVATE-NOTE-92','Live','PRIVATE-FORM-93']
TODAY=date(2026,11,10)

class SheetsTests(unittest.TestCase):
    def setUp(self):
        self.project=Path(__file__).resolve().parents[1]
        scratch=self.project/'work';scratch.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=scratch);self.root=Path(self.tmp.name)
        self.assertTrue(self.root.resolve().is_relative_to(scratch.resolve()));self.addCleanup(self.tmp.cleanup)
        shutil.copytree(self.project/'site',self.root/'site')
        (self.root/'config').mkdir();(self.root/'config/sheet.json').write_text(json.dumps({'spreadsheet_id':'test','tab':'Current list'}))
    def test_only_live_is_public_and_private_columns_are_discarded(self):
        past=ROW.copy();past[0]='PRIVATE-PAST';past[8]='Past'
        excluded=ROW.copy();excluded[0]='PRIVATE-EXCLUDED';excluded[8]='Excluded'
        blank=ROW.copy();blank[0]='PRIVATE-DRAFT';blank[8]=''
        records,_=public_records([HEADERS,ROW,past,excluded,blank,[]])
        self.assertEqual(len(records),1);data=json.dumps(records)
        for word in ['PRIVATE','notes','submitted']:self.assertNotIn(word,data)
        self.assertEqual(records[0]['translator'],'A Translator')
    def test_live_past_date_is_not_automatically_hidden(self):
        r=ROW.copy();r[3]='1 January 2020'
        records,_=public_records([HEADERS,r]);render_sheet(self.root,TODAY,records)
        self.assertIn('A New Book',(self.root/'public-site/index.html').read_text(encoding='utf-8'))
    def test_no_link_is_plain_text_and_html_is_escaped(self):
        r=ROW.copy();r[0]='<script>bad()</script>';r[5]=''
        records,_=public_records([HEADERS,r]);render_sheet(self.root,TODAY,records)
        output=(self.root/'public-site/index.html').read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;',output);self.assertNotIn('<script>bad()',output);self.assertNotIn('href=""',output)
    def test_projection_has_no_private_data_anywhere_in_artifact(self):
        records,_=public_records([HEADERS,ROW]);render_sheet(self.root,TODAY,records)
        files=list((self.root/'public-site').iterdir());self.assertEqual({p.name for p in files},{'index.html','app.js','style.css','robots.txt'})
        for p in files:
            output=p.read_text(encoding='utf-8')
            for value in ['PRIVATE-NOTE-92','PRIVATE-FORM-93','GOOGLE_SHEETS_CREDENTIALS']:self.assertNotIn(value,output)
    def test_invalid_live_row_fails_before_replacing_output(self):
        output=self.root/'public-site';output.mkdir();(output/'index.html').write_text('LAST GOOD')
        r=ROW.copy();r[3]='31 February 2027'
        with patch('poetry_calendar.sheets.fetch_values',return_value=[HEADERS,r]):
            with self.assertRaisesRegex(SheetError,'Row 2'):build_sheet(self.root,TODAY)
        self.assertEqual((output/'index.html').read_text(),'LAST GOOD')
    def test_unknown_status_and_unsafe_url_fail_without_echoing_values(self):
        for col,value in [(8,'PRIVATE-STATUS'),(5,'javascript:PRIVATE-URL'),(4,'PRIVATE-FORMAT')]:
            r=ROW.copy();r[col]=value
            with self.assertRaises(SheetError) as caught:public_records([HEADERS,r])
            self.assertNotIn(value,str(caught.exception));self.assertIn('Row 2',str(caught.exception))
    def test_duplicate_exact_collapses_but_conflicts_stop_build(self):
        records,count=public_records([HEADERS,ROW,ROW]);self.assertEqual(len(records),1);self.assertEqual(count,1)
        r=ROW.copy();r[3]='16 April 2027'
        with self.assertRaisesRegex(SheetError,'Rows 2 and 3'):public_records([HEADERS,ROW,r])
    def test_header_order_blank_columns_and_case(self):
        indexes=[8,7,0,9,2,4,6,3,5,1]
        headers=[HEADERS[i].upper() for i in indexes]+['','']
        values=[ROW[i] for i in indexes]+['','']
        self.assertEqual(public_records([headers,values])[0][0]['title'],'A New Book')
    def test_missing_header_and_unknown_dates(self):
        with self.assertRaises(SheetError):public_records([HEADERS[:3]])
        for value in ['', 'Date TBC','Spring 2027','2027','April 2027','15/04/2027']:
            r=ROW.copy();r[3]=value;self.assertEqual(len(public_records([HEADERS,r])[0]),1)
    def test_empty_approved_list_is_valid(self):
        self.assertEqual(public_records([HEADERS]),([],0))
    def test_real_date_cell_ignores_locale_and_hyperlink_label(self):
        headers=[{'formattedValue':x} for x in HEADERS]
        cells=[{'formattedValue':x} for x in ROW]
        cells[3]={'formattedValue':'04/15/2027','effectiveValue':{'numberValue':(date(2027,4,15)-date(1899,12,30)).days},'effectiveFormat':{'numberFormat':{'type':'DATE'}}}
        cells[5]={'formattedValue':'Publisher page','hyperlink':'https://example.org/book'}
        payload={'sheets':[{'data':[{'rowData':[{'values':headers},{'values':cells}]}]}]}
        records,_=public_records(grid_values(payload));self.assertEqual(records[0]['date']['start'],'2027-04-15');self.assertEqual(records[0]['url'],'https://example.org/book')
    def test_auth_uses_readonly_scope_and_single_named_tab(self):
        secret={'type':'service_account','token_uri':'https://oauth2.googleapis.com/token'}
        response=MagicMock(status_code=200);response.json.return_value={'sheets':[{'data':[{'rowData':[{'values':[{'formattedValue':x} for x in HEADERS]}]}]}]}
        with patch.dict(os.environ,{'GOOGLE_SHEETS_CREDENTIALS':json.dumps(secret)}),patch('google.oauth2.service_account.Credentials.from_service_account_info') as credentials,patch('google.auth.transport.requests.AuthorizedSession') as session:
            client=session.return_value.__enter__.return_value;client.get.return_value=response
            fetch_values({'spreadsheet_id':'test','tab':'Current list'})
            self.assertEqual(credentials.call_args.kwargs['scopes'],[SCOPE])
            self.assertEqual(client.get.call_args.kwargs['params']['ranges'],"'Current list'!A:Z")
            self.assertFalse(client.post.called);self.assertFalse(client.put.called)
    def test_missing_credentials_and_auth_errors_are_redacted(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(SheetError):fetch_values({'spreadsheet_id':'test','tab':'Current list'})
        with patch.dict(os.environ,{'GOOGLE_SHEETS_CREDENTIALS':'PRIVATE-BROKEN-JSON'}):
            with self.assertRaises(SheetError) as caught:fetch_values({'spreadsheet_id':'test','tab':'Current list'})
            self.assertNotIn('PRIVATE-BROKEN-JSON',str(caught.exception))
    def test_build_ignores_legacy_data_and_requires_no_registry(self):
        (self.root/'data').mkdir();(self.root/'data/state.json').write_text('INVALID LEGACY DATA')
        with patch('poetry_calendar.sheets.fetch_values',return_value=[HEADERS,ROW]):build_sheet(self.root,TODAY)
        self.assertIn('A New Publisher',(self.root/'public-site/index.html').read_text(encoding='utf-8'))

