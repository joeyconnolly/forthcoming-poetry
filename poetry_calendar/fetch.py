"""Bounded public-page requests, robots checks, host throttling and conditional cache."""
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser
import requests

class FetchError(RuntimeError): pass

class Fetcher:
    def __init__(self, allowed_hosts, cache_dir, delay=1.5, max_requests=100):
        self.hosts=set(allowed_hosts)
        self.cache=Path(cache_dir); self.cache.mkdir(parents=True,exist_ok=True)
        self.delay=delay; self.max_requests=max_requests; self.count=0
        self.last={}; self.robots={}; self.memory={}
        self.session=requests.Session()
        self.session.headers['User-Agent']='ForthcomingPoetry/0.1 (weekly public bibliography)'

    def _request(self,url,headers=None):
        for redirect in range(6):
            p=urlsplit(url)
            if p.scheme!='https' or p.hostname not in self.hosts or p.username or p.password:
                raise FetchError('Request outside configured HTTPS publisher hosts')
            if self.count>=self.max_requests: raise FetchError('Publisher request budget reached; partial coverage')
            time.sleep(max(0,self.delay-(time.monotonic()-self.last.get(p.hostname,0))))
            self.count+=1
            try:
                r=self.session.get(url,headers=headers or {},timeout=(10,35),allow_redirects=False)
            except requests.RequestException as e: raise FetchError(str(e)) from e
            finally: self.last[p.hostname]=time.monotonic()
            if r.status_code in (301,302,303,307,308):
                target=urljoin(url,r.headers.get('Location',''))
                if not urlsplit(url).path.endswith('/robots.txt'):
                    self._allowed(target)
                url=target; continue
            if len(r.content)>8_000_000: raise FetchError('Response exceeds 8 MB limit')
            return r
        raise FetchError('Too many redirects')

    def _allowed(self,url):
        p=urlsplit(url); origin=f'{p.scheme}://{p.netloc}'
        if origin not in self.robots:
            r=self._request(origin+'/robots.txt')
            rp=RobotFileParser()
            if r.status_code in (404,410): rp.parse([])
            elif r.status_code==200: rp.parse(r.text.splitlines())
            else: raise FetchError(f'Robots access unresolved: HTTP {r.status_code}')
            self.robots[origin]=rp
        rp=self.robots[origin]
        if not rp.can_fetch('ForthcomingPoetry',url): raise FetchError('Disallowed by publisher robots directives')
        self.delay=max(self.delay,rp.crawl_delay('ForthcomingPoetry') or 0)

    def get(self,url):
        if url in self.memory: return self.memory[url]
        self._allowed(url)
        stem=self.cache/hashlib.sha256(url.encode()).hexdigest()
        meta_path=stem.with_suffix('.json'); body_path=stem.with_suffix('.html')
        meta=json.loads(meta_path.read_text()) if meta_path.exists() and body_path.exists() else {}
        headers={}
        if meta.get('etag'): headers['If-None-Match']=meta['etag']
        if meta.get('modified'): headers['If-Modified-Since']=meta['modified']
        r=self._request(url,headers)
        if r.status_code==304 and body_path.exists(): body=body_path.read_text(encoding='utf-8')
        elif r.status_code==200:
            if not any(t in r.headers.get('Content-Type','') for t in ('text/html','application/rss+xml','application/xml','text/xml')): raise FetchError('Expected HTML or public XML feed')
            r.encoding='utf-8'; body=r.text
            body_path.write_text(body,encoding='utf-8')
            meta_path.write_text(json.dumps({'etag':r.headers.get('ETag'),'modified':r.headers.get('Last-Modified'),'url':url}),encoding='utf-8')
        else: raise FetchError(f'HTTP {r.status_code}: {url}')
        self.memory[url]=body
        return body
