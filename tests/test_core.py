import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from poetry_calendar.model import parse_date,make_record,forthcoming,sort_key
from poetry_calendar.pipeline import reconcile,effective_records,atomic_json,load_state,load_registry,update_lock
from poetry_calendar.adapters import Result,bloodaxe,ninearches,shearsman,seren,gallery,gallery_feeds

TODAY=date(2026,11,9)
NOW='2026-11-09T08:17:00+00:00'
P={'id':'test','sources':['https://example.org/catalogue'],'coverage':'test'}
def record(title='One',url='https://example.org/one',d='18 March 2027'):
    return make_record('test',title,'A Poet',d,url,{'url':url,'text':d})
def state(): return {'schema_version':1,'records':[],'sources':{}}

class Dates(unittest.TestCase):
    def test_precision_and_boundaries(self):
        self.assertEqual(parse_date('March 2027')['end'],'2027-03-31')
        self.assertEqual(parse_date('Winter 2027')['end'],'2028-02-29')
        self.assertEqual(parse_date('19 th March 2027')['start'],'2027-03-19')
        self.assertEqual(parse_date('November 4, 2026')['start'],'2026-11-04')
        self.assertFalse(forthcoming(record(d='9 November 2026'),TODAY))
        self.assertTrue(forthcoming(record(d='November 2026'),TODAY))
        self.assertTrue(forthcoming(record(d='Date TBC'),TODAY))
        self.assertIsNone(parse_date('Date TBC')['start'])
        self.assertEqual(parse_date('2027; exact date tbc.')['precision'],'year')
    def test_invalid_dates(self):
        for raw in ['31 February 2027','tomorrow','announced today','2027-25-01','']:
            with self.assertRaises(ValueError): parse_date(raw)
    def test_sorting(self):
        records=[record(d='Date TBC'),record(d='2027'),record(d='December 2027'),record(d='Spring 2027')]
        self.assertEqual([r['date']['precision'] for r in sorted(records,key=sort_key)],['season','month','year','unknown'])

class Reconciliation(unittest.TestCase):
    def test_repeat_is_content_idempotent(self):
        s=state(); reconcile(s,P,Result(records=[record()]),NOW,TODAY); before=copy.deepcopy(s)
        reconcile(s,P,Result(records=[record()]),NOW,TODAY)
        self.assertEqual(s,before)
    def test_failure_preserves_records(self):
        s=state(); reconcile(s,P,Result(records=[record()]),NOW,TODAY); before=copy.deepcopy(s['records'])
        failed=Result(); failed.warn(P['sources'][0],'timeout'); reconcile(s,P,failed,NOW,TODAY)
        self.assertEqual(s['records'],before); self.assertEqual(s['sources']['test']['status'],'failed')
    def test_suspicious_empty_preserves_last_good(self):
        s=state(); rs=[record(str(n),f'https://example.org/{n}') for n in range(4)]
        reconcile(s,P,Result(records=rs),NOW,TODAY); before=copy.deepcopy(s['records'])
        reconcile(s,P,Result(),NOW,TODAY)
        self.assertEqual(s['records'],before); self.assertNotEqual(s['sources']['test']['status'],'ok')
    def test_alias_dedup_and_publisher_isolation(self):
        s=state(); reconcile(s,P,Result(records=[record(),record(url='https://example.org/ebook')]),NOW,TODAY)
        self.assertEqual(len(s['records']),1)
        other=record(); other['publisher_id']='other'; other['id']='other'
        reconcile(s,{**P,'id':'other'},Result(records=[other]),NOW,TODAY)
        self.assertEqual(len(s['records']),2)
    def test_conflict_retains_previous(self):
        s=state(); reconcile(s,P,Result(records=[record()]),NOW,TODAY)
        reconcile(s,P,Result(records=[record(),record(d='19 March 2027')]),NOW,TODAY)
        self.assertEqual(s['records'][0]['date']['label'],'18 March 2027')
        self.assertEqual(s['sources']['test']['status'],'partial')
    def test_date_change_retains_identity_and_history(self):
        s=state(); reconcile(s,P,Result(records=[record()]),NOW,TODAY); rid=s['records'][0]['id']
        reconcile(s,P,Result(records=[record(d='21 April 2027')]),NOW,TODAY)
        self.assertEqual(s['records'][0]['id'],rid); self.assertEqual(len(s['records'][0]['history']),1)
    def test_missing_records_require_repeated_complete_checks(self):
        s=state(); reconcile(s,P,Result(records=[record()]),NOW,TODAY)
        for day in (9,10,11): reconcile(s,P,Result(),NOW,date(2026,11,day))
        self.assertEqual(s['records'][0]['record_status'],'uncertain')
    def test_same_day_retries_do_not_age_missing_records(self):
        s=state(); reconcile(s,P,Result(records=[record()]),NOW,TODAY)
        for _ in range(3): reconcile(s,P,Result(),NOW,TODAY)
        self.assertEqual(s['records'][0]['missing_checks'],1)
        self.assertEqual(s['records'][0]['record_status'],'active')
    def test_auditable_override_survives_collection(self):
        s=state(); reconcile(s,P,Result(records=[record()]),NOW,TODAY); rid=s['records'][0]['id']
        overrides={rid:{'reason':'Official correction','evidence_url':'https://example.org/one','set':{'date':'April 2027'}}}
        reconcile(s,P,Result(records=[record()]),NOW,TODAY)
        self.assertEqual(effective_records(s,overrides,TODAY)[0]['date']['precision'],'month')
        self.assertEqual(s['records'][0]['date']['precision'],'day')
    def test_unknown_override_rejected(self):
        with self.assertRaises(ValueError): effective_records(state(),{'missing':{}},TODAY)
    def test_state_lock_and_atomic_roundtrip(self):
        scratch=Path(__file__).resolve().parents[1]/'work'; scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            root=Path(tmp); atomic_json(root/'data/state.json',state()); self.assertEqual(load_state(root),state())
            with update_lock(root):
                with self.assertRaises(RuntimeError):
                    with update_lock(root): pass

class FixtureFetcher:
    def __init__(self,files): self.files=files
    def get(self,url): return self.files[url]

class Adapters(unittest.TestCase):
    def fixture(self,name): return (Path(__file__).parent/'fixtures'/name).read_text(encoding='utf-8')
    def test_bloodaxe_facts_and_formats(self):
        r=bloodaxe(P,FixtureFetcher({P['sources'][0]:self.fixture('bloodaxe.html')}),TODAY)
        self.assertEqual(r.records[0]['title'],'To No Place'); self.assertEqual(len(r.records[0]['isbns']),2)
        self.assertEqual(r.records[0]['date']['start'],'2027-02-12')
    def test_bloodaxe_changed_markup_not_empty_success(self):
        r=bloodaxe(P,FixtureFetcher({P['sources'][0]:'<html>Maintenance</html>'}),TODAY)
        self.assertFalse(r.complete)
    def test_ninearches_ordinal_and_classification(self):
        index='<h2>Poetry Publications: 2026</h2><a href="/publications/poetry-collections/cherry">Cherry Blossom at Nightbreak</a><a href="/publications/poetry-collections/cherry">Rishi Dastidar</a>'
        r=ninearches(P,FixtureFetcher({P['sources'][0]:index,'https://example.org/publications/poetry-collections/cherry':self.fixture('ninearches.html')}),TODAY)
        self.assertTrue(r.complete); self.assertEqual(r.records[0]['date']['start'],'2026-03-19')
    def test_shearsman_month_and_periodical_exclusion(self):
        index='<a href="/2027-titles--date-order">2027</a>'
        r=shearsman(P,FixtureFetcher({P['sources'][0]:index,'https://example.org/2027-titles--date-order':self.fixture('shearsman.html')}),TODAY)
        self.assertEqual(r.records[0]['title'],'Year of the Labyrinth'); self.assertEqual(r.records[0]['date']['precision'],'month'); self.assertEqual(r.excluded,1)
        self.assertTrue(r.records[0]['source_url'].endswith('#1971402284'))
    def test_seren_past_forthcoming_label_excluded(self):
        index='<div class="book-panel"><h4><a href="/book/example">Hunting the Pembrokeshire Murderer</a></h4><p class="name">S.J. Matchett</p></div>'
        r=seren(P,FixtureFetcher({P['sources'][0]:index,'https://example.org/book/example':self.fixture('seren.html')}),TODAY)
        self.assertTrue(r.complete); self.assertEqual(r.excluded,1)
    def test_gallery_uppercase_date_and_truncation(self):
        index='<ul class="products"><li class="product"><a class="woocommerce-LoopProduct-link" href="/product/daylight">Book</a></li></ul><div class="woocommerce-pagination"><a class="next" href="?page=2">Next</a></div>'
        r=gallery({**P,'max_pages':1},FixtureFetcher({P['sources'][0]:index,'https://example.org/product/daylight':self.fixture('gallery.html')}),TODAY)
        self.assertEqual(r.records[0]['date']['start'],'2026-09-24'); self.assertFalse(r.complete)
    def test_gallery_feed_uses_book_date_not_feed_date(self):
        feed='<rss><channel><item><title>Daylight Mystery</title><link>https://example.org/product/daylight</link><pubDate>Mon, 01 Jan 2030 00:00:00 GMT</pubDate></item></channel></rss>'
        detail=self.fixture('gallery.html')+'<span class="posted_in"><a>Poetry</a></span>'
        r=gallery_feeds(P,FixtureFetcher({P['sources'][0]:feed,'https://example.org/product/daylight':detail}),TODAY)
        self.assertEqual(r.records[0]['date']['start'],'2026-09-24'); self.assertFalse(r.complete)

if __name__=='__main__': unittest.main()
