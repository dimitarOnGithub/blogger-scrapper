from blogger_scrapper.export import SqlExport, FileExport
from blogger_scrapper.blog import Blogsite


class Scrapper:

    def __init__(self, site, feed="atom", export_type="json"):
        """ Constructor for the scrapper; this class initializes the BlogSite sub-class and that in turn initializes the
        blog Feed class. This class provides the high level access to all the functionality.

        :param site: URL of the Blogger site to be scrapped.
        :type site: str
        :param feed: Choice of which feed to attempt for the scrapping - atom or rss
        :type feed: str
        """
        if not site:
            raise ValueError("No site URL has been provided")

        if export_type not in ['json', 'xml', 'sql']:
            raise ValueError(f"Unknown export_type provided - '{export_type}'; available formats are 'json', 'xml', "
                             f"'sql'")

        self.site = Blogsite(site, feed=feed)
        self.feed = self.site.blog_feed
        self.export_type = export_type

    def scrap(self):
        """ High level method that takes care of collecting all data from the site and then exporting it.

        """
        articles = self.feed.fetch_all()
        authors = self.feed.get_all_authors(articles)
        comments = self.feed.get_all_comments(articles)
        if self.export_type == 'sql':
            sql_export = SqlExport(articles, authors, comments)
            sql_export.do_export()
        elif self.export_type == 'json':
            json_export = FileExport(articles, authors, comments, 'json', self.feed.site_encoding)
            json_export.do_export()
        else:
            xml_export = FileExport(articles, authors, comments, 'xml', self.feed.site_encoding)
            xml_export.do_export()
