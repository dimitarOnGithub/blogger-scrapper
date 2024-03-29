import warnings
from concurrent.futures.process import ProcessPoolExecutor
from ctypes import Union
from datetime import datetime
from multiprocessing import Manager
from time import sleep
from bs4.element import Tag
import urllib3
from urllib3.exceptions import NewConnectionError
from bs4 import BeautifulSoup
import re
import codecs


class Blogsite:

    def __init__(self, site, feed="atom"):
        """ Constructor for the Blogsite object to be used as a high-level interface for working with the site's
        content. This constructor initializes the Feed class which provides access to the blog articles.

        :param site: URL of the Blogger site.
        :type site: str
        :param feed: Type of the feed, defaulting to 'atom'.
        :type feed: str
        """
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
                                self._encoding = _split_tag
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
                                self._encoding = tag
                        except LookupError:
                            continue
                else:
                    self._encoding = "UTF-8"
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
            self.blog_feed = Feed(self.rss_link, "rss", site_encoding=self._encoding)
        elif feed == "rss" and self.rss_link is None:
            warnings.warn(f"Couldn't find the preferred feed 'RSS', falling back to 'Atom'")
            self.blog_feed = Feed(self.atom_link, "atom", site_encoding=self._encoding)
        else:
            if feed == "atom":
                self.blog_feed = Feed(self.atom_link, "atom", site_encoding=self._encoding)
            else:
                self.blog_feed = Feed(self.rss_link, "rss", site_encoding=self._encoding)

    def __str__(self):
        return f"<Blogsite url='{self.canonical_url}'>"

    def __repr__(self):
        return f"Blogsite('{self.canonical_url}')"


class Feed:

    def __init__(self, url, feed_type, site_encoding="UTF-8"):
        """ Constructor for the Feed object used to work with the Blogger site.

        :param url: URL to the feed.
        :type url: str
        :param feed_type: Type of the feed - RSS or atom
        :type feed_type: str
        :param site_encoding: Optional encoding type to use when scrapping the articles and comments.
        :type site_encoding: str
        """
        if feed_type.lower() != "rss" and feed_type.lower() != "atom":
            raise ValueError(f"Provided '{feed_type}' is neither an Atom feed, nor an RSS feed")

        self.url = url
        self.feed_type = feed_type
        self.site_encoding = site_encoding
        self.total_results = 0
        self.pages = {}
        self._lock = Manager().Lock()
        self._all_fetched_articles = []
        _http = urllib3.PoolManager()
        try:
            _conn = _http.request("GET", self.url)
        except NewConnectionError:
            raise ConnectionError(f"Failed to load '{self.feed_type}' at '{self.url}'")

        _feed_data = BeautifulSoup(_conn.data.decode(self.site_encoding), features="lxml")
        try:
            _start_index = int(_feed_data.find('opensearch:startindex').text)
            self.total_results = int(_feed_data.find('opensearch:totalresults').text)
            _items_per_page = int(_feed_data.find('opensearch:itemsperpage').text)
            _page_number = 0
            while _start_index + _items_per_page < self.total_results + _items_per_page:
                _page_number += 1
                if _start_index + _items_per_page < self.total_results:
                    _expected_articles = _items_per_page
                else:
                    _expected_articles = self.total_results - _start_index
                if self.feed_type == "rss":
                    _page_url = f"{self.url}&start-index={_start_index}&max-results={_items_per_page}"
                    page = FeedPage(page_number=_page_number, page_type=self.feed_type,
                                    url=_page_url, encoding=self.site_encoding,
                                    articles_num=_expected_articles)
                    self.pages[_page_number] = page
                elif self.feed_type == "atom":
                    _page_url = f"{self.url}?start-index={_start_index}&max-results={_items_per_page}"
                    page = FeedPage(page_number=_page_number, page_type=self.feed_type,
                                    url=_page_url, encoding=self.site_encoding,
                                    articles_num=_expected_articles)
                    self.pages[_page_number] = page
                _start_index = _start_index + _items_per_page
        except ValueError:
            warnings.warn(f"Failed to obtain Feed information for feed at '{self.url}'")

    def fetch_first(self, page_number=1):
        """ Method fetches the first article for the provided `page_number` parameter.

        :param page_number: Optional page number to retrieve the first article from.
        :type page_number: int
        :return: BlogArticle object, either BlogRSSArticle or BlogAtomArticle
        :rtype: Union[BlogRSSArticle, BlogAtomArticle]
        """
        page = self.pages.get(page_number)
        if page:
            http = urllib3.PoolManager()
            try:
                content = http.request("GET", page.url)
            except NewConnectionError:
                raise RuntimeError(f"Failed to fetch all articles for page number '{page_number}'")
            soup = BeautifulSoup(content.data.decode(self.site_encoding), features="lxml")
            if self.feed_type == "rss":
                first_article = soup.find("item")
                blog_article = BlogRSSArticle(article_tag=first_article)
            else:
                first_article = soup.find("entry")
                blog_article = BlogAtomArticle(article_tag=first_article, encoding=self.site_encoding)
            return blog_article
        else:
            warnings.warn(f"Couldn't find page number '{page_number}' in the feed pages")
            return None

    def fetch_all(self, page_number=None):
        """ Method fetches all articles from all FeedPage objects saved in the self.pages attribute. If the optional
        parameter `page_number` has been provided, the method will instead fetch all articles only for that specified
        page.

        :param page_number: Optional page number to retrieve the first article from.
        :type page_number: int
        :return: List of BlogArticle objects, either BlogRSSArticle or BlogAtomArticle
        :rtype: list[BlogRSSArticle or BlogAtomArticle]
        """
        all_articles = []
        if page_number is None:
            with ProcessPoolExecutor(max_workers=10) as executor:
                for page, articles in zip(self.pages.values(), executor.map(self._fetch_articles, self.pages.values())):
                    if len(articles) != page.expected_number_of_articles:
                        warnings.warn(f"Couldn't successfully obtain the expected number of articles for page number "
                                      f"{page.number}")
                    self._save_articles(articles)
        else:
            page = self.pages.get(page_number)
            if page is None:
                warnings.warn(f"Couldn't find page number '{page_number}' in the feed pages")
                return None
            returned_articles = self._fetch_articles(page)
            if len(returned_articles) != page.expected_number_of_articles:
                warnings.warn(f"Couldn't successfully obtain the expected number of articles for page number "
                              f"{page.number}")
            self._save_articles(self._fetch_articles(page))
        all_articles = self._all_fetched_articles.copy()
        self._all_fetched_articles = []
        return all_articles

    def _fetch_articles(self, page):
        """ Hidden (private) method used to fetch articles for the provided `page` parameter.

        :param page: The page object from which to collect data.
        :type page: FeedPage
        :return: List of all articles.
        :rtype: list[BlogRSSArticle, BlogAtomArticle]
        """
        http = urllib3.PoolManager()
        while True:
            try:
                attempt = 1
                content = http.request("GET", page.url)
                if content.status != 200 and attempt <= 3:
                    warnings.warn(f"Caught {content.status} error while attempting to retrieve content for page "
                                  f"'{page.number}', sleeping for 5 seconds and retrying - Attempt {attempt}/3")
                    sleep(5)
                else:
                    break
            except NewConnectionError:
                raise RuntimeError(f"Failed to fetch all articles for page number '{page.number}'")
        soup = BeautifulSoup(content.data.decode(self.site_encoding), features="lxml")
        articles_list = []
        if self.feed_type == "rss":
            all_articles = soup.find_all("item")
            for article in all_articles:
                _rtcl = BlogRSSArticle(article_tag=article)
                articles_list.append(_rtcl)
        else:
            all_articles = soup.find_all("entry")
            for article in all_articles:
                _rtcl = BlogAtomArticle(article_tag=article, encoding=self.site_encoding)
                articles_list.append(_rtcl)
        return articles_list

    def _save_articles(self, next_batch):
        """ Hidden (private) method that utilizes multiprocessing.Manager.Lock() for when this class' 'fetch_all' method
        is invoked; just making sure that all executor works in the 'fetch_all' method will be manipulating the
        temporary `self._all_fetched_articles` list in a safe manner.

        :param next_batch: List of the BlogArticle objects to save.
        :type next_batch: list[BlogRSSArticles, BlogAtomArticle]
        :return: Nothing
        :rtype: None
        """
        with self._lock:
            self._all_fetched_articles.extend(next_batch)
        return

    def get_all_authors(self, articles_list):
        """ Method to obtain all unique authors from the provided `articles_list`, this includes all authors of comments
        for the articles.

        :param articles_list:
        :type articles_list: list[BlogRSSArticle, BlogAtomArticle]
        :return: List of all authors.
        :rtype: list[BlogAuthor]
        """
        authors_set = set()
        for article in articles_list:
            authors_set.add(article.author)
            if len(article.comments) > 0:
                for comm in article.comments:
                    authors_set.add(comm.author)
        return list(authors_set)

    def get_all_comments(self, articles_list):
        """ Method to obtain all comments from the provided `articles_list`.

        :param articles_list:
        :type articles_list: list[BlogRSSArticle, BlogAtomArticle]
        :return: List of all comments.
        :rtype: list[BlogComment]
        """
        if self.feed_type == "rss":
            warnings.warn(f"Feed type is 'RSS', cannot retrieve comments info")
            return []
        else:
            comments_set = set()
            for article in articles_list:
                if len(article.comments) > 0:
                    for art_comm in article.comments:
                        comments_set.add(art_comm)
            return list(comments_set)

    def __str__(self):
        return (f"<Feed url='{self.url}', feed_type='{self.feed_type}', total_articles={self.total_results}, "
                f"total_pages={len(self.pages)}>")

    def __repr__(self):
        return f"Feed('{self.url}', '{self.feed_type}', site_encoding='{self.site_encoding}')"


class FeedPage:

    def __init__(self, page_number, url, page_type, encoding, articles_num):
        self.number = page_number
        self.url = url
        self.page_type = page_type
        self.encoding = encoding
        self.expected_number_of_articles = articles_num

    def get_next_page(self):
        """ Method to try and get the URL for the next iteration of the feed. Only applicable for 'Atom' feeds.

        :return: URL to the next page.
        :rtype: str
        """
        next_page_url = None
        http = urllib3.PoolManager()
        try:
            content = http.request("GET", self.url)
        except NewConnectionError:
            return next_page_url
        soup = BeautifulSoup(content.data.decode(self.encoding), features="lxml")
        _links = soup.find_all('link')
        for link in _links:
            if link.has_attr('rel') and 'next' in link.get('rel'):
                next_page_url = link.get('href')
        return next_page_url

    def get_previous_page(self):
        """ Method to try and get the URL for the previous iteration of the feed. Only applicable for 'Atom' feeds.

        :return: URL to the previous page.
        :rtype: str
        """
        previous_page_url = None
        http = urllib3.PoolManager()
        try:
            content = http.request("GET", self.url)
        except NewConnectionError:
            return previous_page_url
        soup = BeautifulSoup(content.data.decode(self.encoding), features="lxml")
        _links = soup.find_all('link')
        for link in _links:
            if link.has_attr('rel') and 'previous' in link.get('rel'):
                previous_page_url = link.get('href')
        return previous_page_url

    def __str__(self):
        return f"<FeedPage url='{self.url}', page_number='{self.number}', page_type='{self.page_type}'>"

    def __repr__(self):
        return f"FeedPage({self.number}, '{self.url}', '{self.page_type}', '{self.encoding}')"


class BlogArticle:

    def __init__(self, article_id, title, content, author, published_date, last_edited_date=None,
                 blog_link=None, feed_link=None, comments_list=None):
        """ Parent class of the possible blog article objects - BlogRSSArticle and BlogAtomArticle. Children objects
        initialize this object after they've performed their own initialization via their respective way (direct
        assigning of parameters versus provision of a Tag object for the child object to scan on its own).

        :param article_id: Unique Blogger-generated ID for the article.
        :type article_id: int
        :param title: Title of the article.
        :type title: str
        :param content: Content of the article.
        :type content: str
        :param author: Author of the comment, ideally an instance of the BlogAuthor class. If a string is provided
                    instead, the constructor will initialize a basic BlogAuthor object, setting the provided string as
                    a username of the author.
        :type author: Union[BlogAuthor, str]
        :param published_date: Ideally a Datetime object of when the article was posted, timezone awareness encouraged,
                            but if a simple string is provided instead, it will be probed for the known feed date
                            formats; if none match, current date and time will be set.
        :type published_date: Union[datetime, str]
        :param last_edited_date: Ideally a Datetime object of when the article was last updated, timezone awareness
                            encouraged, but if a simple string is provided instead, it will be probed for the known feed
                            date formats; if none match, current date and time will be set.
                            If none has been provided, will be left as None.
                            Optional parameter.
        :type last_edited_date: Union[datetime, str, None]
        :param blog_link: Link to the article in the blog as-is. Optional parameter.
        :type blog_link: str
        :param feed_link: Link to the article in the feed. Atom-only. Optional parameter.
        :type feed_link: str
        :param comments_list: List of comments that have been added to this specific article, all entries in the list
                    are instances of the BlogComment object. Empty list will be generated if no comments are present.
        :type comments_list: list[BlogComment]
        """
        if article_id is None or published_date is None or title is None or content is None or author is None:
            raise ValueError(f"You must provide the necessary attributes - article_id, published_date, title, content "
                             f"and author")

        self.article_id = article_id  # type: int
        self.title = title  # type: str
        self.content = content  # type: str

        if isinstance(author, str):
            self.author = BlogAuthor(name=author, uri="", author_id=-1, email="dummy-email@dummy.com", image_src="")
        elif isinstance(author, BlogAuthor):
            self.author = author  # type: BlogAuthor
        else:
            raise ValueError(f"Provided 'author' parameter is neither a str, nor an instance of BlogAuthor")
        if isinstance(published_date, str):
            try:
                # ISO format is the usual Atom date format
                self.published_date = datetime.fromisoformat(published_date)
            except ValueError:
                pass
            try:
                # Thu, 06 May 2021 14:51:00 +0000 is an example RSS article Published date format
                self.published_date = datetime.strptime(published_date, '%a, %d %b %Y %H:%M:%S %z')
            except ValueError:
                self.published_date = datetime.now()
        elif isinstance(published_date, datetime):
            self.published_date = published_date  # type: datetime
        else:
            raise ValueError(f"Provided 'published_date' parameter is neither a str, nor an instance of datetime")

        if last_edited_date:
            if isinstance(last_edited_date, str):
                try:
                    # ISO format is the usual Atom date format
                    self.last_edited_date = datetime.fromisoformat(last_edited_date)
                except ValueError:
                    pass
                try:
                    # Thu, 06 May 2021 14:51:00 +0000 is an example RSS article Published date format
                    self.last_edited_date = datetime.strptime(last_edited_date, '%a, %d %b %Y %H:%M:%S %z')
                except ValueError:
                    self.last_edited_date = datetime.now()
            elif isinstance(last_edited_date, datetime):
                self.last_edited_date = last_edited_date  # type: datetime
            else:
                raise ValueError(f"Provided 'last_edited_date' parameter is neither a str, nor an instance of datetime")
        else:
            self.last_edited_date = self.published_date

        if blog_link is not None:
            self.blog_link = blog_link  # type: str
        else:
            self.blog_link = ""
        if feed_link is not None:
            self.feed_link = feed_link  # type: str
        else:
            self.feed_link = ""
        if comments_list is not None:
            self.comments = comments_list  # type: list[BlogComment]
        else:
            self.comments = []

    def __str__(self):
        return (f"<BlogArticle id='{self.article_id}', title='{self.title}', author='{self.author.name}', "
                f"published={self.published_date.strftime('%d/%b/%Y')}>")

    def __repr__(self):
        return f"BlogArticle('{self.article_id}', '{self.title}')"

    def __hash__(self):
        if self.article_id != -1:
            return hash(self.article_id)
        else:
            return hash(self.title + self.published_date.strftime("%Y-%m-%d"))

    def __eq__(self, other):
        if isinstance(other, BlogArticle):
            return self.__hash__() == other.__hash__()
        else:
            return False


class BlogAuthor:

    def __init__(self, name=None, uri=None, author_id=None, email=None, image_src=None, author_tag=None):
        """ Constructor for the BlogAuthor object. Can either be initialized via the BeautifulSoup Tag object, passed
        to this method via the `author_tag` attribute, or attributed can be assigned directly via the rest of the
        available parameters.

        :param name: Display name of the author as per their Blogger profile
        :type name: str
        :param uri: URI location of the author's profile on the Blogger platform
        :type uri: str
        :param email: E-mail of the author as retrieved from Blogger, almost always noreply@blogger.com
        :type email: str
        :param image_src: Link to the author's selected avatar.
        :type image_src: str
        :param author_tag: BeautifulSoup object of the author, specifically the <author> HTML tags that encapsulate it.
        :type author_tag: bs4.element.Tag
        """
        if author_tag is None and (name is None or uri is None or author_id is None or email is None or
                                   image_src is None):
            raise ValueError(f"You must provide either an author tag object for the blog author or the necessary"
                             f" attributes")

        if author_tag:
            if author_tag.find('name'):
                self.name = author_tag.find('name').text  # type: str
            else:
                self.name = "Anonymous"
            if author_tag.find('uri'):
                self.uri = author_tag.find('uri').text  # type: str
                try:
                    self.author_id = int(self.uri.split("/")[-1])
                except ValueError:
                    self.author_id = -1
            else:
                self.uri = "Dummy-URI"
                self.author_id = -1
            if author_tag.find('email'):
                self.email = author_tag.find('email').text  # type: str
            else:
                self.email = "dummy-email@dummy.com"
            if author_tag.find('gd:image'):
                self.image_src = author_tag.find('gd:image').get('src')  # type: str
            else:
                self.image_src = ""
        else:
            self.name = name  # type: str
            self.uri = uri  # type: str
            self.author_id = author_id  # type: int
            self.email = email  # type: str
            self.image_src = image_src  # type: str

    def __str__(self):
        return f"<BlogAuthor name='{self.name}', author_id={self.author_id}>"

    def __repr__(self):
        return f"BlogAuthor('{self.name}')"

    def __hash__(self):
        if self.author_id != -1:
            return hash(self.author_id)
        else:
            return hash(self.name + self.uri)

    def __eq__(self, other):
        if isinstance(other, BlogAuthor):
            return self.__hash__() == other.__hash__()
        else:
            return False


class BlogComment:

    def __init__(self, comment_id=None, content=None, published_date=None, last_updated_date=None, author=None,
                 article_backref=None, comment_tag=None):
        """ Constructor for the BlogComment object. Can either be initialized via the BeautifulSoup Tag object, when
        passed via the `comment_tag` attribute, or by directly assigning the values.

        :param comment_id: Unique Blogger-generated ID for the comment
        :type comment_id: int
        :param content: Content of the comment, extracted from the <content> tag surrounding the comment body.
        :type content: str
        :param published_date: Datetime object of when the comment was posted, timezone awareness encouraged.
        :type published_date: datetime
        :param last_updated_date: Datetime object of when the comment was last updated, timezone awareness encouraged.
        :type last_updated_date: datetime
        :param author: Author of the comment, instance of the BlogAuthor class.
        :type author: BlogAuthor
        :param article_backref: Backreference ID of the article on which the comment was posted, useful for looking up
                        which article it belongs to.
        :type article_backref: int
        :param comment_tag: BeautifulSoup object of the comment, specifically the <entry> HTML tags that encapsulate it.
        :type comment_tag: bs4.element.Tag
        """
        if comment_tag is None and (comment_id is None or content is None or published_date is None
                                    or last_updated_date is None or author is None or article_backref is None):
            raise ValueError(f"You must provide either a comment tag object for the comment or the necessary"
                             f" attributes")

        if comment_tag:
            if comment_tag.find('id'):
                self.comment_id = int(comment_tag.find('id').text.split("-")[-1])  # type: int
            else:
                self.comment_id = -1
            if comment_tag.find('content'):
                self.content = comment_tag.find('content').text  # type: str
            else:
                self.content = "Dummy Content"
            if comment_tag.find('published'):
                self.published_date = datetime.fromisoformat(comment_tag.find('published').text)  # type: datetime
            else:
                self.published_date = datetime.now()
            if comment_tag.find('updated'):
                self.last_updated_date = datetime.fromisoformat(comment_tag.find('updated').text)  # type: datetime
            else:
                self.last_updated_date = self.published_date
            if comment_tag.find('author'):
                _author = comment_tag.find('author')
                self.author = BlogAuthor(author_tag=_author)
            else:
                self.author = BlogAuthor(name="Anonymous", uri="", author_id=-1, email="dummy-email@dummy.com",
                                         image_src="")
        else:
            self.comment_id = comment_id  # type: int
            self.content = content  # type: str
            self.published_date = published_date  # type: datetime
            self.last_updated_date = last_updated_date  # type: datetime
            self.author = author  # type: BlogAuthor

        if article_backref is None:
            warnings.warn(f"No article backref value has been provided for comment with id '{self.comment_id}', "
                          f"comment will still be saved but no article information will be available for it.")
            self.article_backref = -1
        else:
            self.article_backref = article_backref  # type: int

    def __str__(self):
        return f"<BlogComment id={self.comment_id}, author='{self.author}', backref='{self.article_backref}'"

    def __hash__(self):
        if self.comment_id != -1:
            return hash(self.comment_id)
        else:
            return hash(self.content + self.published_date.strftime("%Y-%m-%d"))

    def __eq__(self, other):
        if isinstance(other, BlogComment):
            return self.__hash__() == other.__hash__()
        else:
            return False


class BlogRSSArticle(BlogArticle):

    def __init__(self, article_id=None, title=None, content=None, author=None, published_date=None,
                 last_edited_date=None, blog_link=None, article_tag=None):
        """ Child object of the BlogArticle class, specifically aimed at articles retrieved via the RSS stream.

        :param article_id: Unique Blogger-generated ID for the article.
        :type article_id: int
        :param title: Title of the article.
        :type title: str
        :param content: Content of the article.
        :type content: str
        :param author: Author of the comment, ideally an instance of the BlogAuthor class. If a string is provided
                    instead, the constructor will initialize a basic BlogAuthor object, setting the provided string as
                    a username of the author.
        :type author: Union[BlogAuthor, str]
        :param published_date: Ideally a Datetime object of when the article was posted, timezone awareness encouraged,
                            but if a simple string is provided instead, it will be probed for the known feed date
                            formats; if none match, current date and time will be set.
        :type published_date: Union[datetime, str]
        :param last_edited_date: Ideally a Datetime object of when the article was last updated, timezone awareness
                            encouraged, but if a simple string is provided instead, it will be probed for the known feed
                            date formats; if none match, current date and time will be set.
                            If none has been provided, will be left as None.
                            Optional parameter.
        :type last_edited_date: Union[datetime, str, None]
        :param blog_link: Link to the article in the blog as-is. Optional parameter.
        :type blog_link: str
        :param article_tag: BeautifulSoup Tag element of the article, in other words, the <item> HTML tag that surrounds
                            each article entry in the feed.
        :type article_tag: Tag
        """
        if article_tag is None and (article_id is None or title is None or content is None or published_date is None
                                    or author is None):
            raise ValueError(f"You must provide either a feed URL for the blog article or the necessary attributes")

        if article_tag is None:
            super().__init__(article_id, title, content, author, published_date, last_edited_date=last_edited_date,
                             blog_link=blog_link)
        else:
            if not isinstance(article_tag, Tag):
                raise ValueError(f"Provided 'article_tag' is not an instance of the BeautifulSoup's Tag class")
            if article_tag.name != 'item':
                raise ValueError(f"Couldn't verify provided 'article_tag' parameter contains the <item> HTML tag for "
                                 f"an RSS article")

            id = article_tag.find("guid").text.split("-")[-1]
            title = article_tag.find("title").text
            content = article_tag.find("description").text
            _author = article_tag.find("author").text
            _author = _author.split(" ")
            _author_email = _author[0]
            _author_name = re.sub("[()]", "", _author[1])
            author = BlogAuthor(_author_name, "", -1, _author_email, "")
            published_date = article_tag.find("pubdate").text
            updated_date = article_tag.find("atom:updated").text
            super().__init__(id, title, content, author, published_date, last_edited_date=updated_date)

    def __str__(self):
        return (f"<BlogRSSArticle id='{self.article_id}', title='{self.title}', author='{self.author.name}', "
                f"published={self.published_date.strftime('%d/%b/%Y')}>")

    def __repr__(self):
        return f"BlogRSSArticle('{self.article_id}', '{self.title}')"


class BlogAtomArticle(BlogArticle):

    def __init__(self, article_id=None, title=None, content=None, author=None, published_date=None, article_tag=None,
                 last_edited_date=None, blog_link=None, feed_link=None, comments=None, encoding="UTF-8"):
        """ Child object of the BlogArticle class, specifically aimed at articles retrieved via the Atom stream.

        :param article_id: Unique Blogger-generated ID for the article.
        :type article_id: int
        :param title: Title of the article.
        :type title: str
        :param content: Content of the article.
        :type content: str
        :param author: Author of the comment, ideally an instance of the BlogAuthor class. If a string is provided
                    instead, the constructor will initialize a basic BlogAuthor object, setting the provided string as
                    a username of the author.
        :type author: Union[BlogAuthor, str]
        :param published_date: Ideally a Datetime object of when the article was posted, timezone awareness encouraged,
                            but if a simple string is provided instead, it will be probed for the known feed date
                            formats; if none match, current date and time will be set.
        :type published_date: Union[datetime, str]
        :param last_edited_date: Ideally a Datetime object of when the article was last updated, timezone awareness
                            encouraged, but if a simple string is provided instead, it will be probed for the known feed
                            date formats; if none match, current date and time will be set.
                            If none has been provided, will be left as None.
                            Optional parameter.
        :type last_edited_date: Union[datetime, str, None]
        :param article_tag: BeautifulSoup Tag element of the article, in other words, the <item> HTML tag that surrounds
                            each article entry in the feed.
        :type article_tag: Tag
        :param blog_link: Link to the article in the blog as-is. Optional parameter.
        :type blog_link: str
        :param feed_link: Link to the article in the feed. Atom-only. Optional parameter.
        :type feed_link: str
        :param encoding: Preferred encoding for when collecting and initializing the comments objects, defaulting to
                        "UTF-8".
        :type encoding: str
        """
        if article_tag is None and (article_id is None or title is None or content is None or published_date is None
                                    or author is None):
            raise ValueError(f"You must provide either a feed URL for the blog article or the necessary attributes")

        if article_tag is None:
            super().__init__(article_id, title, content, author, published_date, last_edited_date=last_edited_date,
                             blog_link=blog_link, feed_link=feed_link, comments_list=comments)
        else:
            if not isinstance(article_tag, Tag):
                raise ValueError(f"Provided 'article_tag' is not an instance of the BeautifulSoup's Tag class")
            if article_tag.name != 'entry':
                raise ValueError(f"Couldn't verify provided 'article_tag' parameter contains the <entry> HTML tag for "
                                 f"an Atom article")

            _article = article_tag
            article_id = int(_article.find('id').text.split("-")[-1])
            title = _article.find('title').text
            content = _article.find('content').text
            published_date = datetime.fromisoformat(_article.find('published').text)
            last_updated_date = datetime.fromisoformat(_article.find('updated').text)
            _author = _article.find('author')
            author = BlogAuthor(author_tag=_author)
            _links = _article.find_all('link')
            comments = []
            _feed_url = None
            _blog_url = None
            for link in _links:
                if link.get('rel')[0] == 'replies' and link.get('type') == "application/atom+xml":
                    _comments_url = link.get('href')
                    _http = urllib3.PoolManager()
                    _conn = _http.request("GET", _comments_url)
                    _comments_soup = BeautifulSoup(_conn.data.decode(encoding), features="lxml")
                    _comments_retrieved = _comments_soup.find_all('entry')
                    if len(_comments_retrieved) > 0:
                        for comment in _comments_retrieved:
                            article_comment = BlogComment(comment_tag=comment, article_backref=article_id)
                            comments.append(article_comment)
                elif link.get('rel')[0] == 'self' and link.get('type') == "application/atom+xml":
                    _feed_url = link.get('href')
                elif link.get('rel')[0] == 'alternate' and link.get('type') == "text/html":
                    _blog_url = link.get('href')
            super().__init__(article_id, title, content, author, published_date, last_edited_date=last_updated_date,
                             blog_link=_blog_url, feed_link=_feed_url, comments_list=comments)

    def __str__(self):
        return (f"<BlogAtomArticle id='{self.article_id}', title='{self.title}', author='{self.author.name}', "
                f"published={self.published_date.strftime('%d/%b/%Y')}>")

    def __repr__(self):
        return f"BlogAtomArticle('{self.article_id}', '{self.title}')"
