import json
import unittest
from datetime import date
from poetry_calendar.penguin import discover,primary,record,collect

URL='https://www.penguin.co.uk/books/471591/saint-serotonin-by-shire-warsan/9781784746223'
def props():
    return {'canonicalLink':URL,'title':'Saint Serotonin','isbn':'9781784746223','imprint':'Chatto & Windus','publishDate':'2027-05-06',
        'currentFormat':'Hardback','authors':[{'name':'Warsan Shire','role':'Author'}],
        'bookPageData':{'books':{'booksInfo':{'bookGenres':'poetry,fiction,plays-poetry'}}},
        'titleData':{'onSaleDate':{'date':'2027-05-06'},'editions':{'Hardback':[{'onSaleDate':{'date':'2027-05-06'}}]}}}
def html(p):return '<script id="__NEXT_DATA__" type="application/json">'+json.dumps({'props':{'pageProps':p}})+'</script>'
class PenguinTests(unittest.TestCase):
    def test_exact_date_imprint_and_unicode_roles(self):
        p=props();p['authors'] += [{'name':'Éva Example','role':'Translator'},{'name':'A Reader','role':'Read by'}]
        r=record(primary(html(p),URL),'chatto',URL)
        self.assertEqual(r['date']['start'],'2027-05-06');self.assertEqual(r['imprint'],'Chatto & Windus')
        self.assertEqual(r['contributors'][-1],{'name':'Éva Example','role':'translator'});self.assertEqual(len(r['contributors']),2)
    def test_poet_biography_does_not_classify_novel(self):
        p=props();p['summary']='A poet writes a novel';p['bookPageData']['books']['booksInfo']['bookGenres']='fiction,literary-fiction'
        self.assertIsNone(record(p,'chatto',URL))
    def test_reissue_held_and_same_day_ebook_allowed(self):
        p=props();p['titleData']['editions']['Ebook']=[{'onSaleDate':{'date':'2027-05-06'}}]
        self.assertIsNotNone(record(p,'chatto',URL))
        p['titleData']['editions']['Ebook'][0]['onSaleDate']['date']='2020-01-01'
        with self.assertRaisesRegex(ValueError,'Earlier edition'):record(p,'chatto',URL)
    def test_primary_url_and_date_must_match(self):
        with self.assertRaises(ValueError):primary(html(props()),URL+'/wrong')
        p=props();p['titleData']['onSaleDate']['date']='2026-05-06'
        with self.assertRaises(ValueError):primary(html(p),URL)
    def test_embedded_shelf_discovery_no_fixed_year(self):
        p={'automatedBookshelfData':{'shelf':{'works':[{'isbn':'9781784746223','seoFriendlyUrl':'/books/471591/saint-serotonin-by-shire-warsan','onSaleDate':{'date':'2030-05-06'}}]}}}
        self.assertEqual(discover(html(p),date(2026,11,9)),{URL})
    def test_empty_discovery_is_not_complete(self):
        with self.assertRaises(ValueError):discover(html({}),date(2026,11,9))
    def test_imprint_is_not_silently_relabelled(self):
        class Fetch:
            def get(self,url):return html(props())
        r=collect({'id':'cape','sources':[URL],'book_seeds':[URL],'imprints':['Jonathan Cape']},Fetch(),date(2026,11,9))
        self.assertFalse(r.records)

