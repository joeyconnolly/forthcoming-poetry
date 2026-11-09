import copy
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from poetry_calendar.imports import import_csv,load_imported,merge_imported,isbn
from poetry_calendar.model import make_record
from poetry_calendar.pipeline import atomic_json,load_state,reconcile,effective_records
from poetry_calendar.adapters import Result

TODAY=date(2026,11,9)
NOW='2026-11-09T08:00:00+00:00'
P={'id':'picador','name':'Picador','enabled':False,'sources':['https://example.org/books'],'coverage':'test'}
URL='https://example.org/language-animal'
HEADER=['Title','Author','Publisher','Publication date','ISBN','Source URL']
ROW=['Language Animal','Susannah Dickey','Picador','15 April 2027','9781037423321',URL]

class ImportTests(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).resolve().parents[1]/'work';scratch.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=scratch);self.root=Path(self.tmp.name)
        self.assertTrue(self.root.resolve().is_relative_to(scratch.resolve()))
        self.addCleanup(self.tmp.cleanup)
        atomic_json(self.root/'config/publishers.json',[P,{**P,'id':'other','name':'Other Press'}])
        atomic_json(self.root/'config/overrides.json',{})
        self.state={'schema_version':1,'records':[],'sources':{}}
        atomic_json(self.root/'data/state.json',self.state)
        self.csv=self.root/'titles.csv'
    def write(self,rows,header=HEADER,delimiter=','):
        with self.csv.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f,delimiter=delimiter);w.writerow(header);w.writerows(rows)
    def automatic(self):
        r=make_record('picador','Language Animal','Susannah Dickey','1 April 2027',URL,{'url':URL,'text':'publisher'},isbns=['9781037423321'])
        reconcile(self.state,P,Result(records=[r]),NOW,TODAY);atomic_json(self.root/'data/state.json',self.state)
        return r
    def test_new_import_bom_unicode_and_repeat_are_idempotent(self):
        row=['Poèmes','Éva Example','picador','Spring 2028','',URL]
        self.write([row]);self.assertEqual(import_csv(self.root,self.csv),{'added':1,'updated':0,'unchanged':0})
        before=(self.root/'data/imported.json').read_bytes()
        self.assertEqual(import_csv(self.root,self.csv),{'added':0,'updated':0,'unchanged':1})
        self.assertEqual(before,(self.root/'data/imported.json').read_bytes())
        self.assertEqual(load_imported(self.root)['records'][0]['title'],'Poèmes')
    def test_uploaded_date_wins_after_subsequent_collection(self):
        raw=self.automatic();self.write([ROW]);self.assertEqual(import_csv(self.root,self.csv)['updated'],1)
        raw['date']['start']='2027-06-01';raw['date']['end']='2027-06-01';raw['date']['label']='1 June 2027'
        reconcile(self.state,P,Result(records=[raw]),NOW,TODAY)
        before=copy.deepcopy(self.state)
        result=effective_records(self.state,{},TODAY,load_imported(self.root)['records'])
        self.assertEqual(len(result),1);self.assertEqual(result[0]['date']['start'],'2027-04-15')
        self.assertEqual(self.state,before)
    def test_new_manual_title_later_discovered_automatically_is_one_book(self):
        self.write([ROW]);import_csv(self.root,self.csv);self.automatic()
        self.assertEqual(len(merge_imported(self.state['records'],load_imported(self.root)['records'])),1)
    def test_isbn_match_can_correct_title_author_and_source(self):
        self.automatic();row=ROW.copy();row[0]='Corrected Title';row[1]='Corrected Author';row[5]='https://example.org/new-source'
        self.write([row]);import_csv(self.root,self.csv)
        result=merge_imported(self.state['records'],load_imported(self.root)['records'])
        self.assertEqual(len(result),1);self.assertEqual(result[0]['title'],'Corrected Title')
    def test_title_author_match_without_isbn_and_different_url(self):
        self.automatic();row=ROW.copy();row[0]='LANGUAGE ANIMAL';row[4]='';row[5]='https://example.org/another-source'
        self.write([row]);self.assertEqual(import_csv(self.root,self.csv)['updated'],1)
        self.assertEqual(len(merge_imported(self.state['records'],load_imported(self.root)['records'])),1)
    def test_corrected_reimport_joins_through_original_automatic_record(self):
        self.automatic();row=ROW.copy();row[4]='';row[5]='https://example.org/first-upload'
        self.write([row]);import_csv(self.root,self.csv)
        row=ROW.copy();row[0]='Corrected title';row[5]='https://example.org/second-upload'
        self.write([row]);self.assertEqual(import_csv(self.root,self.csv)['updated'],1)
        stored=load_imported(self.root)['records'];self.assertEqual(len(stored),1);self.assertEqual(stored[0]['title'],'Corrected title')
    def test_different_publishers_do_not_merge(self):
        self.automatic();row=ROW.copy();row[2]='Other Press';self.write([row]);self.assertEqual(import_csv(self.root,self.csv)['added'],1)
        self.assertEqual(len(merge_imported(self.state['records'],load_imported(self.root)['records'])),2)
    def test_last_row_and_latest_upload_win_with_history(self):
        second=ROW.copy();second[3]='May 2027';self.write([ROW,second]);import_csv(self.root,self.csv)
        self.assertEqual(len(load_imported(self.root)['records']),1)
        second[3]='June 2027';self.write([second]);self.assertEqual(import_csv(self.root,self.csv)['updated'],1)
        r=load_imported(self.root)['records'][0];self.assertEqual(r['date']['label'],'June 2027');self.assertTrue(r['history'])
    def test_invalid_row_rolls_back_entire_file(self):
        self.write([ROW]);import_csv(self.root,self.csv);before=(self.root/'data/imported.json').read_bytes()
        good=ROW.copy();good[3]='May 2027';bad=ROW.copy();bad[3]='31 February 2027'
        self.write([good,bad])
        with self.assertRaisesRegex(ValueError,'CSV row 3'):import_csv(self.root,self.csv)
        self.assertEqual(before,(self.root/'data/imported.json').read_bytes())
        self.assertFalse((self.root/'data/.update.lock').exists())
    def test_dry_run_saves_nothing(self):
        self.write([ROW]);self.assertEqual(import_csv(self.root,self.csv,dry_run=True)['added'],1)
        self.assertFalse((self.root/'data/imported.json').exists())
    def test_ambiguous_shared_url_is_not_silently_merged(self):
        r=self.automatic();other=copy.deepcopy(r);other.update(id='other-book',title='Different Book',isbns=[])
        self.state['records'].append(other);atomic_json(self.root/'data/state.json',self.state);self.write([ROW])
        with self.assertRaisesRegex(ValueError,'Ambiguous duplicate'):import_csv(self.root,self.csv)
        self.assertFalse((self.root/'data/imported.json').exists())
    def test_unknown_publisher_bad_isbn_unsafe_url_rejected(self):
        for index,value in [(2,'Unregistered Press'),(4,'9781037423322'),(5,'javascript:alert(1)')]:
            row=ROW.copy();row[index]=value;self.write([row])
            with self.assertRaises(ValueError):import_csv(self.root,self.csv)
    def test_isbn10_normalises_to_13(self):
        self.assertEqual(isbn('0-306-40615-2'),'9780306406157')
    def test_semicolon_csv_and_contributor_roles(self):
        self.write([ROW+['Éva Translator; Another Translator','An Editor']],HEADER+['Translator','Editor'],delimiter=';')
        import_csv(self.root,self.csv);people=load_imported(self.root)['records'][0]['contributors']
        self.assertEqual([p['role'] for p in people],['author','translator','translator','editor'])
    def test_missing_headers_and_empty_rows_fail_cleanly(self):
        self.write([ROW[:2]],HEADER[:2])
        with self.assertRaisesRegex(ValueError,'Required columns'):import_csv(self.root,self.csv)
        self.write([])
        with self.assertRaisesRegex(ValueError,'no title rows'):import_csv(self.root,self.csv)
    def test_cli_import_rebuilds_and_dry_run_does_not(self):
        project=Path(__file__).resolve().parents[1]
        shutil.copytree(project/'site',self.root/'site');self.write([ROW])
        command=[sys.executable,'-m','poetry_calendar','import-csv',str(self.csv),'--root',str(self.root)]
        result=subprocess.run(command+['--dry-run'],cwd=project,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertFalse((self.root/'dist/index.html').exists())
        result=subprocess.run(command,cwd=project,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Language Animal',(self.root/'dist/index.html').read_text(encoding='utf-8'))
