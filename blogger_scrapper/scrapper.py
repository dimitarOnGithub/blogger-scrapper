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

        if export_type not in ['json', 'xml', 'sqllite']:
            raise ValueError(f"Unknown export_type provided - '{export_type}'; available formats are 'json', 'xml', "
                             f"'sqllite'.")

        self.site = Blogsite(site, feed=feed)
        self.feed = self.site.blog_feed
        self.export_type = export_type
