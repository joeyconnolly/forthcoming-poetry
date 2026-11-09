import unittest
from poetry_calendar.batch_one import catalogue_poetry,announcement

class BatchOneTests(unittest.TestCase):
    def test_catalogue_poetry_is_separated_from_adjacent_fiction(self):
        pages=['Spring 2027\nThe Fisher King by Rebecca Tamás\nA Novel by A Novelist',
            '28 January 2027, 112 pages\nDC (Poetry)\nFlapped paperback\nPrint: 9781804273166\nEbook: 9781804273173\nThe Fisher King\nRebecca Tamás\nDescription\n28 January 2027, 140 pages\nContemporary fiction (FBA)\nPrint: 9781804272961\nEbook: 9781804272978\nA Novel\nA Novelist']
        result=catalogue_poetry(pages,'fitzcarraldo','https://example.org/catalogue.pdf')
        self.assertEqual(len(result.records),1)
        self.assertEqual(result.records[0]['contributors'][0]['name'],'Rebecca Tamás')
        self.assertEqual(result.records[0]['date']['start'],'2027-01-28')
        self.assertEqual(result.records[0]['isbns'],['9781804273166'])
    def test_unknown_catalogue_layout_warns(self):
        result=catalogue_poetry(['DC (Poetry)\nUnexpected layout'],'fitzcarraldo','https://example.org/catalogue.pdf')
        self.assertFalse(result.records);self.assertTrue(result.warnings)
    def test_title_must_match_contents(self):
        result=catalogue_poetry(['28 January 2027, 112 pages\nDC (Poetry)\nPrint: 9781804273166\nEbook: 9781804273173\nWrong Title\nA Person'],'fitzcarraldo','https://example.org/catalogue.pdf')
        self.assertFalse(result.records);self.assertTrue(result.warnings)
    def test_announcement_preserves_season_and_translation_roles(self):
        html='<div class="entry-content"><p>Our collections: <em>A Book</em> by A Poet, and <em>A Translation</em> by A Translator.</p><p>The collections will publish in spring 2027.</p><a href="https://example.org/doi/book/9781807811938">A Book is available to preorder</a><a href="https://example.org/doi/book/9781807811648">A Translation is available to preorder</a></div>'
        result=announcement(html,'pavilion','https://example.org/announcement',{'9781807811648':[{'name':'An Original Poet','role':'author'},{'name':'A Translator','role':'translator'}]})
        self.assertEqual(len(result.records),2)
        self.assertEqual(result.records[0]['date']['precision'],'season')
        self.assertEqual(result.records[1]['contributors'][1]['role'],'translator')
        self.assertEqual(result.records[0]['evidence']['url'],'https://example.org/announcement')
    def test_article_timestamp_is_not_release_date(self):
        with self.assertRaises(ValueError):announcement('<div class="entry-content"><p>Posted October 2026</p></div>','pavilion','https://example.org/announcement')
