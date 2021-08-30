from blogger_scrapper.blog import Blogsite


class Scrapper:

    def __init__(self, site, feed="atom"):
        """ TODO: add docs

        :param site:
        :type site:
        :param feed:
        :type feed:
        """
        if not site:
            raise ValueError("No site URL has been provided")

        self.site = Blogsite(site, feed=feed)
        self.feed = self.site.blog_feed
