import json
import unittest
from datetime import date
from poetry_calendar.picador import listing,book,collect

BASE='https://www.panmacmillan.com'
INDEX=BASE+'/genres/fiction/poetry'
URL=BASE+'/authors/a/book/9781037404177'
def html(*nodes):return '<script type="application/ld+json">'+json.dumps({'@graph':list(nodes)})+'</script>'
def detail(**changes):
    b={'@type':'Book','name':'Poèmes','url':URL,'isbn':'9781037404177','author':[{'name':'A Poète'}],
       'datePublished':'2027-01-21','publisher':{'name':'Picador'},'genre':['Poetry / poems'],
       'bookFormat':'https://schema.org/Paperback','workExample':[]}
    return {**b,**changes}
def catalogue(items):return html({'@type':'ItemList','name':'Poetry','itemListElement':[{'item':i} for i in items]})
class Fetch:
    def __init__(self,pages):self.pages=pages;self.visited=[]
    def get(self,url):self.visited.append(url);return self.pages[url]
class PicadorTests(unittest.TestCase):
    def run_source(self,item,extras=None):
        fetch=Fetch({INDEX:catalogue([item]),URL:html(item),**(extras or {})})
        return collect({'id':'picador','sources':[INDEX]},fetch,date(2026,11,9)),fetch
    def test_public_pagination_and_unicode(self):
        item=detail(); page2=INDEX+'/2'
        fetch=Fetch({INDEX:catalogue([item])+f'<a href="{page2}">2</a>',page2:catalogue([detail(datePublished='2025-01-01')]),URL:html(item)})
        r=collect({'id':'picador','sources':[INDEX]},fetch,date(2026,11,9))
        self.assertEqual(r.records[0]['title'],'Poèmes');self.assertIn(page2,fetch.visited)
        self.assertEqual(r.records[0]['date']['start'],'2027-01-21')
    def test_excludes_other_imprint_and_poet_novel(self):
        for changes in ({'publisher':{'name':'Pan'}},{'genre':['Historical fiction']}):
            r,_=self.run_source(detail(**changes));self.assertFalse(r.records)
    def test_earlier_edition_holds_reissue(self):
        variant=BASE+'/authors/a/book/9781037404184'
        item=detail(workExample=[{'url':variant}])
        r,_=self.run_source(item,{variant:html(detail(url=variant,datePublished='2020-01-01'))})
        self.assertFalse(r.records);self.assertTrue(any('Earlier edition' in w['reason'] for w in r.warnings))
    def test_missing_edition_cannot_admit_unchecked_reissue(self):
        r,_=self.run_source(detail(workExample=[{'url':BASE+'/missing'}]))
        self.assertFalse(r.records)
    def test_same_day_ebook_does_not_duplicate_print(self):
        variant=BASE+'/authors/a/book/9781037404184'
        r,_=self.run_source(detail(workExample=[{'url':variant}]),{variant:html(detail(url=variant,bookFormat='https://schema.org/EBook'))})
        self.assertEqual(len(r.records),1)
    def test_missing_book_date_cannot_use_article_date(self):
        item=detail();del item['datePublished']
        with self.assertRaises(ValueError):book(html({'@type':'WebPage','datePublished':'2027-01-01'},item),URL)
    def test_changed_empty_listing_is_not_success(self):
        with self.assertRaises(ValueError):listing('<p>Loading...</p>',INDEX)
    def test_primary_book_does_not_read_recommendation(self):
        with self.assertRaises(ValueError):book(html({'@type':'ItemList','itemListElement':[{'item':detail()}]}),URL)
