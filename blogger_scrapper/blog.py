import warnings
from datetime import datetime

import urllib3
from urllib3.exceptions import NewConnectionError
from bs4 import BeautifulSoup
import re
import codecs


class Blogsite:

    def __init__(self, site, feed="atom", plain_text=False):
        self.canonical_url = None
        self._encoding = None
        self.atom_link = None
        self.rss_link = None

        if not isinstance(site, str):
            raise ValueError(f"Provided site argument '{site}' is not a string")

        _http = urllib3.PoolManager()
        try:
            _conn = _http.request("GET", site)
        except NewConnectionError:
            raise ConnectionError(f"Failed to connect to Blogger site at '{site}'")

        if _conn.status != 200:
            # Raise error if the connection isn't OK
            raise ConnectionError(f"Connection to site at '{site}' returned unexpected HTTP code - "
                                  f"{_conn.status}")

        _soup = BeautifulSoup(_conn.data, features="lxml")
        _meta_tags = _soup.find_all('meta')
        self.canonical_url = site

        if 'Content-Type' in _conn.headers:
            # Get the encoding from the headers
            _content_type = _conn.headers.getheaders('Content-Type')[0]
            _charset = _content_type.split("=", 1)[-1]
            try:
                # Verify the retrieved encoding is valid
                if codecs.lookup(_charset):
                    self._encoding = _charset
            except LookupError:
                pass
        if self._encoding is None:
            # If encoding has not been obtained, try with looking it up via the BeautifulSoup object
            for tag in _meta_tags:
                if tag.has_attr('content') and tag.get('content').startswith('text/html'):
                    _tag = tag.get('content').split('=')
                    for _split_tag in _tag:
                        try:
                            if codecs.lookup(_split_tag):
                                self.site_encoding = _split_tag
                        except LookupError:
                            continue
            if self._encoding is None:
                # If encoding has still not been retrieved, finally try with regex
                _charset_tag = re.compile(
                    '<meta\s+content=[\'"]text/html;\s+charset=([a-zA-Z0-9-]+)[\'"].*>')
                _charset_tag_matches = re.findall(_charset_tag, _conn.data.decode())
                if _charset_tag_matches:
                    for tag in _charset_tag_matches:
                        try:
                            if codecs.lookup(tag):
                                self.site_encoding = tag
                        except LookupError:
                            continue
                else:
                    self.site_encoding = "UTF-8"
        _blogger_site = False
        for tag in _meta_tags:
            if tag.has_attr('content') and tag.get('content') == 'blogger':
                _blogger_site = True
        if not _blogger_site:
            _blogger_tag_regex = re.compile('<meta\s+content=[\'"](blogger)[\'"].*>')
            _meta_tag = re.findall(_blogger_tag_regex, _conn.data.decode())
            if not _meta_tag:
                raise ValueError(f"Could not verify provided site at '{site}' is a Blogger site")

        _links = _soup.find_all('link')
        for link in _links:
            if link.has_attr('rel'):
                if link.get('rel')[0] == 'alternate':
                    if link.has_attr('type'):
                        if link.get('type') == 'application/atom+xml':
                            self.atom_link = link.get('href')
                        elif link.get('type') == 'application/rss+xml':
                            self.rss_link = link.get('href')

        if self.atom_link is None and self.rss_link is None:
            raise AttributeError(f"Unable to find neither an Atom feed, nor an RSS feed for '{site}'")
        elif feed == "atom" and self.atom_link is None:
            warnings.warn(f"Couldn't find the preferred feed 'Atom', falling back to 'RSS'")
            self.blog_feed = Feed(self.rss_link, "rss")
        elif feed == "rss" and self.rss_link is None:
            warnings.warn(f"Couldn't find the preferred feed 'RSS', falling back to 'Atom'")
            self.blog_feed = Feed(self.atom_link, "atom")


class Feed:

    def __init__(self, url, feed_type):
        self.url = url
        self.feed_type = feed_type
        self.current_page = 0
        self.pages = 0
        self.total_results = 0
        self.results_per_page = 0
        _http = urllib3.PoolManager()
        try:
            _conn = _http.request("GET", self.url)
        except NewConnectionError:
            raise ConnectionError(f"Failed to load '{self.feed_type}' at '{self.url}'")

        _soup = BeautifulSoup(_conn.data, features="lxml")
        try:
            _start_index = int(_soup.find('opensearch:startindex').text)
            _total_results = int(_soup.find('opensearch:totalresults').text)
            _items_per_page = int(_soup.find('opensearch:itemsperpage').text)
            self.total_results = _total_results
            self.results_per_page = _items_per_page
            self.pages = _total_results // _items_per_page
            if _start_index == 1:
                self.current_page = 1
            elif _start_index - 1 > _items_per_page:
                self.current_page = 2
            else:
                self.current_page = (_start_index // _items_per_page) + 1
        except (AttributeError, ValueError):
            raise RuntimeError(f"Failed to load '{self.feed_type}' at '{self.url}' - couldn't obtain feed items "
                               f"information")

        if feed_type == "rss" and self.pages > 1:
            warnings.warn(f"More than 1 page of results detected for '{self.url}'; RSS feed doesn't allow paginating "
                          f"so only retrieving the first {self.results_per_page} entries")

        if feed_type == "atom":
            _links = _soup.find_all('link')
            for link in _links:
                if link.has_attr('rel') and 'next' in link.get('rel'):
                    self.next_page_url = link.get('href')

    def get_articles(self):
        pass


class BlogArticle:

    def __init__(self, blog_id=None, title=None, content=None, published_date=None, last_updated_date=None, author=None,
                 comments=None, article_url=None):
        if article_url is None and (blog_id is None or title is None or content is None or published_date is None
                                    or author is None):
            raise ValueError(f"You must provide either a feed URL for the blog article or the necessary attributes")

        if article_url:
            _http = urllib3.PoolManager()
            try:
                _conn = _http.request("GET", article_url)
            except NewConnectionError:
                raise ConnectionError(f"Failed to load article at '{article_url}'")
            _soup = BeautifulSoup(_conn.data, features="lxml")
            _article = _soup.find('entry')
            if not _article:
                raise RuntimeError(f"Failed to load article at '{article_url}'")

            if _article.find('id'):
                self.blog_id = _article.find('id').text.split("-")[-1]
            if _article.find('title'):
                self.title = _article.find('title').text
            if _article.find('published'):
                self.published_date = datetime.fromisoformat(_article.find('published').text)
            if _article.find('updated'):
                self.last_updated_date = datetime.fromisoformat(_article.find('updated').text)
            if _article.find('author'):
                _author = _article.find('author')
                self.author = BlogAuthor(_author)
