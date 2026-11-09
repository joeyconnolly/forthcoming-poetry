import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from poetry_calendar.fetch import Fetcher,FetchError

class Response:
    def __init__(self,status,text,headers=None):
        self.status_code=status; self.text=text; self.content=text.encode(); self.headers=headers or {'Content-Type':'text/html'}

class FetchSafety(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).resolve().parents[1]/'work'; scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch)
        self.fetch=Fetcher(['example.org'],self.temp.name,delay=0)
    def tearDown(self): self.temp.cleanup()
    def test_robots_denial_prevents_page_request(self):
        with patch.object(self.fetch,'_request',return_value=Response(200,'User-agent: *\nDisallow: /')) as request:
            with self.assertRaises(FetchError): self.fetch.get('https://example.org/book')
            self.assertEqual(request.call_count,1)
    def test_unavailable_robots_is_not_permission(self):
        with patch.object(self.fetch,'_request',return_value=Response(403,'')):
            with self.assertRaises(FetchError): self.fetch.get('https://example.org/book')
    def test_outside_host_blocked_before_network(self):
        with patch.object(self.fetch.session,'get') as get:
            with self.assertRaises(FetchError): self.fetch._request('https://other.example/book')
            get.assert_not_called()
    def test_google_redirect_allowance_does_not_allow_arbitrary_google_hosts(self):
        self.fetch.hosts.add('docs.google.com')
        with patch.object(self.fetch.session,'get') as get:
            for url in ['https://evil.googleusercontent.com/pub/x','https://doc-0k-8s-sheets.googleusercontent.com/private/x','https://docs.google.com.evil.org/pub/x']:
                with self.assertRaises(FetchError):self.fetch._request(url)
            get.assert_not_called()
    def test_cached_body_not_used_to_mask_failure(self):
        url='https://example.org/book'
        with patch.object(self.fetch,'_request',side_effect=[Response(404,''),Response(200,'<h1>Book</h1>')]):
            self.fetch.get(url)
        self.fetch.memory.clear()
        with patch.object(self.fetch,'_request',return_value=Response(500,'')):
            with self.assertRaises(FetchError): self.fetch.get(url)
    def test_not_modified_reuses_verified_cache(self):
        url='https://example.org/book'
        with patch.object(self.fetch,'_request',side_effect=[Response(404,''),Response(200,'<h1>Book</h1>')]):
            self.fetch.get(url)
        self.fetch.memory.clear()
        with patch.object(self.fetch,'_request',return_value=Response(304,'')):
            self.assertEqual(self.fetch.get(url),'<h1>Book</h1>')

if __name__=='__main__': unittest.main()
