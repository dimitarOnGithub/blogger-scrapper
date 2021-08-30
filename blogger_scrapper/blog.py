import warnings
from datetime import datetime
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
        else:
            if feed == "atom":
                self.blog_feed = Feed(self.atom_link, "atom")
            else:
                self.blog_feed = Feed(self.rss_link, "rss")


class Feed:

    def __init__(self, url, feed_type):
        """ Constructor for the Feed object used to work with the Blogger site.

        :param url: URL to the feed.
        :type url: str
        :param feed_type: Type of the feed - RSS or atom
        :type feed_type: str
        """
        if feed_type.lower() != "rss" and feed_type.lower() != "atom":
            raise ValueError(f"Provided '{feed_type}' is neither an Atom feed, nor an RSS feed")

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

        self.feed_data = BeautifulSoup(_conn.data, features="lxml")
        try:
            _start_index = int(self.feed_data.find('opensearch:startindex').text)
            _total_results = int(self.feed_data.find('opensearch:totalresults').text)
            _items_per_page = int(self.feed_data.find('opensearch:itemsperpage').text)
            self.total_results = _total_results
            self.results_per_page = _items_per_page
            self.pages = (_total_results // _items_per_page) + 1
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
                          f"so only retrieving the first {self.results_per_page} entries without any comments")

        if feed_type == "atom":
            _links = self.feed_data.find_all('link')
            for link in _links:
                if link.has_attr('rel') and 'next' in link.get('rel'):
                    self.next_page_url = link.get('href')

    def fetch_first(self):
        """ TODO: add docs

        :return:
        :rtype:
        """
        if self.feed_type == "rss":
            first_article = self.feed_data.find("item")
            blog_article = BlogRSSArticle(article_tag=first_article)
        else:
            first_article = self.feed_data.find("entry")
            blog_article = BlogAtomArticle(article_tag=first_article)
        return blog_article

    def fetch_all(self):
        """ TODO: add docs

        :return:
        :rtype:
        """

        # TODO: this should retrieve _ALL_ articles
        articles_list = []
        if self.feed_type == "rss":
            all_articles = self.feed_data.find_all("item")
            for article in all_articles:
                _rtcl = BlogRSSArticle(article_tag=article)
                articles_list.append(_rtcl)
        else:
            all_articles = self.feed_data.find_all("entry")
            for article in all_articles:
                _rtcl = BlogAtomArticle(article_tag=article)
                articles_list.append(_rtcl)
        return articles_list


class BlogArticle:

    def __init__(self, article_id, title, content, author, published_date, last_edited_date=None,
                 blog_link=None, feed_link=None, comments_list=None):
        """ todo: add docs

        :param article_id:
        :type article_id:
        :param title:
        :type title:
        :param content:
        :type content:
        :param author:
        :type author:
        :param published_date:
        :type published_date:
        :param last_edited_date:
        :type last_edited_date:
        :param blog_link:
        :type blog_link:
        :param feed_link:
        :type feed_link:
        :param comments_list:
        :type comments_list:
        """
        if article_id is None or published_date is None or title is None or content is None or author is None:
            raise ValueError(f"You must provide the necessary attributes - article_id, published_date, title, content "
                             f"and author")
        # TODO: rework dates and authors
        self.article_id = article_id
        self.title = title
        self.content = content
        self.author = author
        self.published_date = published_date
        if last_edited_date is not None:
            self.last_edited_date = last_edited_date
        if blog_link is not None:
            self.blog_link = blog_link
        if feed_link is not None:
            self.feed_link = feed_link
        if comments_list is not None:
            self.comments = comments_list
        else:
            self.comments = []


class BlogAuthor:

    def __init__(self, name=None, uri=None, email=None, image_src=None, author_tag=None):
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
        if author_tag is None and (name is None or uri is None or email is None or image_src is None):
            raise ValueError(f"You must provide either an author tag object for the blog author or the necessary"
                             f" attributes")

        if author_tag:
            if author_tag.find('name'):
                self.name = author_tag.find('name').text
            if author_tag.find('uri'):
                self.uri = author_tag.find('uri').text
            if author_tag.find('email'):
                self.email = author_tag.find('email').text
            if author_tag.find('gd:image'):
                self.image_src = author_tag.find('gd:image').get('src')
        else:
            self.name = name
            self.uri = uri
            self.email = email
            self.image_src = image_src


class BlogComment:

    def __init__(self, comment_id=None, content=None, published_date=None, last_updated_date=None, author=None,
                 article_backref=None, comment_tag=None):
        """ Constructor for the BlogComment object. Can either be initialized via the BeautifulSoup Tag object, when
        passed via the `comment_tag` attribute, or by directly assigning the values.

        :param comment_id: Unique Blogger-generated ID for the comment
        :type comment_id: str
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
        :type article_backref: str
        :param comment_tag: BeautifulSoup object of the comment, specifically the <entry> HTML tags that encapsulate it.
        :type comment_tag: bs4.element.Tag
        """
        if comment_tag is None and (comment_id is None or content is None or published_date is None
                                    or last_updated_date is None or author is None or article_backref is None):
            raise ValueError(f"You must provide either a comment tag object for the comment or the necessary"
                             f" attributes")

        # TODO: Add logic to simply assign empty values to non-critical attributes
        if comment_tag:
            if comment_tag.find('id'):
                self.comment_id = comment_tag.find('id').text.split("-")[-1]
            if comment_tag.find('content'):
                self.content = comment_tag.find('content').text
            if comment_tag.find('published'):
                self.published_date = datetime.fromisoformat(comment_tag.find('published').text)
            if comment_tag.find('updated'):
                self.last_updated_date = datetime.fromisoformat(comment_tag.find('updated').text)
            if comment_tag.find('author'):
                _author = comment_tag.find('author')
                self.author = BlogAuthor(author_tag=_author)
        else:
            self.comment_id = comment_id
            self.content = content
            self.published_date = published_date
            self.last_updated_date = last_updated_date
            self.author = author

        if article_backref is None:
            warnings.warn(f"No article backref value has been provided for comment with id '{self.comment_id}', "
                          f"comment will still be saved but no article information will be available for it.")
        else:
            self.article_backref = article_backref


class BlogRSSArticle(BlogArticle):

    def __init__(self, article_id=None, title=None, content=None,  author=None, published_date=None,
                 last_edited_date=None, blog_link=None, article_tag=None):
        """ TODO: add docs

        :param article_id:
        :type article_id:
        :param title:
        :type title:
        :param content:
        :type content:
        :param author:
        :type author:
        :param published_date:
        :type published_date:
        :param last_edited_date:
        :type last_edited_date:
        :param blog_link:
        :type blog_link:
        :param article_tag:
        :type article_tag:
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
            author = BlogAuthor(_author_name, "", _author_email, "")
            published_date = article_tag.find("pubdate").text
            updated_date = article_tag.find("atom:updated").text
            super().__init__(id, title, content, author, published_date, last_edited_date=updated_date)


class BlogAtomArticle(BlogArticle):

    def __init__(self, article_id=None, title=None, content=None,  author=None, published_date=None, article_tag=None,
                 last_edited_date=None, blog_link=None, feed_link=None, comments=None):
        """ TODO: add docs

        :param article_id:
        :type article_id:
        :param title:
        :type title:
        :param content:
        :type content:
        :param author:
        :type author:
        :param published_date:
        :type published_date:
        :param article_tag:
        :type article_tag:
        :param last_edited_date:
        :type last_edited_date:
        :param blog_link:
        :type blog_link:
        :param feed_link:
        :type feed_link:
        :param comments:
        :type comments:
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
            article_id = _article.find('id').text.split("-")[-1]
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
                    _comments_soup = BeautifulSoup(_conn.data, features="lxml")
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
