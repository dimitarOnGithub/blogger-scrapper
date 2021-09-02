import warnings


class BlogArticleMapping:

    _blog_article_attributes = [
        "article_id",
        "title",
        "content",
        "author",
        "published_date",
        "last_edited_date",
        "blog_link",
        "feed_link",
        "comments"
    ]

    def __init__(self, **kwargs):
        """ Constructor for the BlogArticle mapping - provided keyword arguments must match the attributes of the
        BlogArticle class in the blog module. Value of the keywords will be the name of the field when export is
        performed by scrapped, eg:

        If article_id is provided with value 'unique_article_number', when scrapper is performing the export of data,
        the field, that on Blogger is called 'article_id', will be called 'unique_article_number' in the export.
        """
        for attribute in self._blog_article_attributes:
            setattr(self, attribute, attribute)

        for attr_name, mapping_name in kwargs.items():
            if attr_name in self._blog_article_attributes:
                setattr(self, attr_name, mapping_name)
            else:
                warnings.warn(f"Unknown keyword argument: '{attr_name}'; provided arguments must match attributes of "
                              f"the BlogArticle class")

    def get_mapping(self, attr_name):
        """ Method to return the mapping value of the provided `attr_name` parameter, eg:

        get_mapping('title') -> self.title = 'name' -> returned value is 'name'

        If the provided `attr_name` parameter doesn't match an existing attribute, None is returned.

        :param attr_name: Attribute name to look for.
        :type attr_name: str
        :return: The mapping value of the attribute.
        :rtype: str
        """
        if hasattr(self, attr_name):
            return getattr(self, attr_name)
        else:
            warnings.warn(f"Unknown attribute name: '{attr_name}'")
            return None


class BlogAuthorMapping:

    _blog_author_attributes = [
        "author_id",
        "name",
        "uri",
        "email",
        "image_src"
    ]

    def __init__(self, **kwargs):
        """ Constructor for the BlogAuthor mapping - provided keyword arguments must match the attributes of the
        BlogAuthor class in the blog module. Value of the keywords will be the name of the field when export is
        performed by scrapped, eg:

        If name is provided with value 'username', when scrapper is performing the export of data, the field, that on
        Blogger is called 'name', will be called 'username' in the export.
        """
        for attribute in self._blog_author_attributes:
            setattr(self, attribute, attribute)

        for attr_name, mapping_name in kwargs.items():
            if attr_name in self._blog_author_attributes:
                setattr(self, attr_name, mapping_name)
            else:
                warnings.warn(f"Unknown keyword argument: '{attr_name}'; provided arguments must match attributes of "
                              f"the BlogAuthor class")

    def get_mapping(self, attr_name):
        """ Method to return the mapping value of the provided `attr_name` parameter, eg:

        get_mapping('title') -> self.title = 'name' -> returned value is 'name'

        If the provided `attr_name` parameter doesn't match an existing attribute, None is returned.

        :param attr_name: Attribute name to look for.
        :type attr_name: str
        :return: The mapping value of the attribute.
        :rtype: str
        """
        if hasattr(self, attr_name):
            return getattr(self, attr_name)
        else:
            warnings.warn(f"Unknown attribute name: '{attr_name}'")
            return None


class BlogCommentMapping:

    _blog_comment_attributes = [
        "comment_id",
        "content",
        "published_date",
        "last_updated_date",
        "author"
    ]

    def __init__(self, **kwargs):
        """ Constructor for the BlogComment mapping - provided keyword arguments must match the attributes of the
        BlogComment class in the blog module. Value of the keywords will be the name of the field when export is
        performed by scrapped, eg:
        
        If content is provided with value 'body', when scrapper is performing the export of data, the field, that on
        Blogger is called 'content', will be called 'body' in the export.
        """
        for attribute in self._blog_comment_attributes:
            setattr(self, attribute, attribute)

        for attr_name, mapping_name in kwargs.items():
            if attr_name in self._blog_comment_attributes:
                setattr(self, attr_name, mapping_name)
            else:
                warnings.warn(f"Unknown keyword argument: '{attr_name}'; provided arguments must match attributes of "
                              f"the BlogComment class")

    def get_mapping(self, attr_name):
        """ Method to return the mapping value of the provided `attr_name` parameter, eg:

        get_mapping('content') -> self.content = 'body' -> returned value is 'body'

        If the provided `attr_name` parameter doesn't match an existing attribute, None is returned.

        :param attr_name: Attribute name to look for.
        :type attr_name: str
        :return: The mapping value of the attribute.
        :rtype: str
        """
        if hasattr(self, attr_name):
            return getattr(self, attr_name)
        else:
            warnings.warn(f"Unknown attribute name: '{attr_name}'")
            return None
