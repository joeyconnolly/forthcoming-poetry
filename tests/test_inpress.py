import csv,io,unittest
from poetry_calendar.inpress import parse_feed, contributors, supplement
from poetry_calendar.adapters import Result
from poetry_calendar.adapters import faber,catalogue_snapshot
from poetry_calendar.pipeline import reconcile
from datetime import date

class InpressTests(unittest.TestCase):
    def parse(self,**changes):
        row={'Title':'A new collection','Authors':'Zoë Green','Publisher':'Test Press','ISBN':'9781915606747','Publication Date':'26/11/2026','Category':'Poetry','BIC Code':'DCF','Main Description':'New poems','Format':'Paperback'}
        row.update(changes); stream=io.StringIO(); writer=csv.DictWriter(stream,fieldnames=row); writer.writeheader(); writer.writerow(row)
        return parse_feed(stream.getvalue(),[{'id':'test','inpress_name':'Test Press'}],'https://example.org/feed')['test']
    def test_unicode_dates_and_identity(self):
        r=self.parse().records[0]
        self.assertEqual(r['contributors'][0]['name'],'Zoë Green')
        self.assertEqual(r['date']['start'],'2026-11-26')
        self.assertIn('search=9781915606747',r['source_url'])
    def test_invalid_date_held(self):
        r=self.parse(**{'Publication Date':'31/02/2027'})
        self.assertFalse(r.records);self.assertTrue(r.warnings)
    def test_html_rejected(self):
        with self.assertRaises(ValueError):parse_feed('<html>Login</html>',[],'https://example.org')
    def test_roles(self):
        self.assertEqual([p['role'] for p in contributors('Rachel Jeffcoat, cover design or artwork by Amy Louise Evans')],['author','cover artist'])
        self.assertEqual(contributors('Edited by Nathan Evans')[0]['role'],'editor')
    def test_reissue_held(self):
        self.assertFalse(self.parse(**{'Main Description':'First published in 2008'}).records)
    def test_rolling_feed_never_complete(self):
        self.assertFalse(self.parse().complete)
    def test_publisher_wins_conflict_and_no_duplicate(self):
        primary=self.parse();extra=self.parse(**{'Publication Date':'27/11/2026'})
        result=supplement(primary,extra)
        self.assertEqual(len(result.records),1)
        self.assertEqual(result.records[0]['date']['start'],'2026-11-26')
        self.assertTrue(any('differs' in w['reason'] for w in result.warnings))

class ExpansionTests(unittest.TestCase):
    def test_faber_follows_pagination_and_reads_book_date(self):
        index='https://www.faber.co.uk/product-category/poetry/'
        book='https://www.faber.co.uk/product/123-a-book/'
        pages={index:'<a href="'+index+'page/2/">2</a><div class="card-prod">Old title</div>',index+'page/2/':'<div class="card-prod"><a class="card-prod__info-tt" href="'+book+'">A Book</a><div class="card-prod__info-name">A Poet</div><button class="pre-order-listing-trigger">Pre-order</button></div>',book:'<h1>A Book</h1><p>A new collection of poems</p><div class="txt-table-item"><div class="txt-table-item__name">Date Published</div><div class="txt-table-item__txt">19.11.2026</div></div><div class="txt-table-item"><div class="txt-table-item__name">ISBN</div><div class="txt-table-item__txt">9780571401727</div></div>'}
        class Fake:
            def get(self,url):return pages[url]
        result=faber({'id':'faber','sources':[index]},Fake(),date(2026,11,9))
        self.assertEqual(len(result.records),1)
        self.assertEqual(result.records[0]['date']['start'],'2026-11-19')
        self.assertFalse(result.complete)
    def test_snapshot_does_not_claim_fresh_verification(self):
        p={'id':'test','sources':['https://example.org/catalogue'],'coverage':'snapshot','catalogue_records':[{'title':'Selected Poems','author':'A Poet','date':'26 November 2026','url':'https://example.org/catalogue#page=3','evidence':'Page 3','isbn':'9781800175907','checked_at':'2026-11-09T00:00:00+00:00'}]}
        s={'records':[],'sources':{}}
        result=catalogue_snapshot(p,None,date(2026,11,16))
        reconcile(s,p,result,'2026-11-16T00:00:00+00:00',date(2026,11,16))
        self.assertEqual(s['records'][0]['last_verified_at'],'2026-11-09T00:00:00+00:00')
