from blogger_scrapper.blog import Blogsite


class Scrapper:

    def __init__(self, site, feed="atom", output_format="json", plain_text=False):
        if not site:
            raise ValueError("No site URL has been provided")

        self._populate_site(site, feed, plain_text)

    def _populate_site(self, site, feed, plain_text):
        self.target = Blogsite(site, feed, plain_text)
