import warnings
from datetime import datetime
from pathlib import Path

from blogger_scrapper import BlogArticleMapping, BlogAuthorMapping, BlogCommentMapping, BlogArticle, BlogAuthor, \
    BlogComment
import sqlite3


class SqlExport:
    articles_table_name = 'articles'
    authors_table_name = 'authors'
    comments_table_name = 'comments'

    def __init__(self, all_articles_list,
                 all_authors_list,
                 all_comments_list,
                 articles_mapping=BlogArticleMapping(),
                 authors_mapping=BlogAuthorMapping(),
                 comments_mapping=BlogCommentMapping()):
        self.all_articles = all_articles_list  # type: list[BlogArticle]
        self.all_authors = all_authors_list  # type: list[BlogAuthor]
        self.all_comments = all_comments_list  # type: list[BlogComment]
        self.articles_map = articles_mapping
        self.authors_map = authors_mapping
        self.comments_map = comments_mapping

    def name_articles_table(self, name):
        """ Method provides a way to set a custom name for the 'articles' table. Provided `name` parameter must NOT be
        same as the authors or comments tables' names.

        :param name: Name of the articles table for the export.
        :type name: str
        """
        if name != self.authors_table_name and name != self.comments_table_name:
            self.articles_table_name = name
        else:
            raise ValueError(f"Provided '{name}' for the articles table name is already in use by one of the other"
                             f" tables")

    def name_authors_table(self, name):
        """ Method provides a way to set a custom name for the 'authors' table. Provided `name` parameter must NOT be
        same as the articles or comments tables' names.

        :param name: Name of the authors table for the export.
        :type name: str
        """
        if name != self.articles_table_name and name != self.comments_table_name:
            self.authors_table_name = name
        else:
            raise ValueError(f"Provided '{name}' for the authors table name is already in use by one of the other"
                             f" tables")

    def name_comments_table(self, name):
        """ Method provides a way to set a custom name for the 'comments' table. Provided `name` parameter must NOT be
        same as the articles or authors tables' names.

        :param name: Name of the comments table for the export.
        :type name: str
        """
        if name != self.articles_table_name and name != self.authors_table_name:
            self.comments_table_name = name
        else:
            raise ValueError(f"Provided '{name}' for the comments table name is already in use by one of the other"
                             f" tables")

    def do_export(self):
        """ TODO: add docs

        :return:
        :rtype:
        """
        output_dir = Path('output')
        if not Path.exists(output_dir) or not Path.is_dir(output_dir):
            output_dir = Path(f"output-tmp-{datetime.now().strftime('%d%m%Y-%H%M%S%f')}")
            warnings.warn(f"Default output/ directory doesn't exist or is not a directory, creating a temporary new "
                          f"directory called {output_dir.name}")
            Path.mkdir(output_dir, exist_ok=True)
        conn = sqlite3.connect(f"{output_dir}/sql_export-{datetime.now().strftime('%d%m%Y-%H%M%S')}.db")
        articles_table_create_query = (f"CREATE TABLE {self.articles_table_name} ("
                                       f"{self.articles_map.get_mapping('article_id')} integer PRIMARY KEY,"
                                       f"{self.articles_map.get_mapping('title')} VARCHAR(255) NOT NULL,"
                                       f"{self.articles_map.get_mapping('content')} TEXT NOT NULL,"
                                       f"{self.articles_map.get_mapping('author')} integer NOT NULL,"
                                       f"{self.articles_map.get_mapping('published_date')} DATETIME NOT NULL,"
                                       f"{self.articles_map.get_mapping('last_edited_date')} DATETIME NOT NULL,"
                                       f"{self.articles_map.get_mapping('blog_link')} VARCHAR(255),"
                                       f"{self.articles_map.get_mapping('feed_link')} VARCHAR(255)"
                                       f");")
        authors_table_create_query = (f"CREATE TABLE {self.authors_table_name} ("
                                      f"{self.authors_map.get_mapping('author_id')} integer PRIMARY KEY,"
                                      f"{self.authors_map.get_mapping('name')} VARCHAR(255) NOT NULL,"
                                      f"{self.authors_map.get_mapping('uri')} VARCHAR(255),"
                                      f"{self.authors_map.get_mapping('email')} VARCHAR(255),"
                                      f"{self.authors_map.get_mapping('image_src')} VARCHAR(255)"
                                      f");")
        comments_table_create_query = (f"CREATE TABLE {self.comments_table_name} ("
                                       f"{self.comments_map.get_mapping('comment_id')} integer PRIMARY KEY,"
                                       f"{self.comments_map.get_mapping('content')} TEXT NOT NULL,"
                                       f"{self.comments_map.get_mapping('published_date')} DATETIME NOT NULL,"
                                       f"{self.comments_map.get_mapping('last_updated_date')} DATETIME NOT NULL,"
                                       f"{self.comments_map.get_mapping('author')} integer NOT NULL"
                                       f");")
        articles_comments_table_create_query = (f"CREATE TABLE {self.articles_table_name}_{self.comments_table_name} ("
                                                f"{self.articles_map.get_mapping('article_id')} integer NOT NULL,"
                                                f"{self.comments_map.get_mapping('comment_id')} integer NOT NULL"
                                                f");")
        cursor = conn.cursor()
        cursor.execute(articles_table_create_query)
        cursor.execute(authors_table_create_query)
        cursor.execute(comments_table_create_query)
        cursor.execute(articles_comments_table_create_query)

        # Generate articles insert query
        insert_articles_query = (
            f"INSERT INTO {self.articles_table_name} ("
            f"{self.articles_map.get_mapping('article_id')},"
            f"{self.articles_map.get_mapping('title')},"
            f"{self.articles_map.get_mapping('content')},"
            f"{self.articles_map.get_mapping('author')},"
            f"{self.articles_map.get_mapping('published_date')},"
            f"{self.articles_map.get_mapping('last_edited_date')},"
            f"{self.articles_map.get_mapping('blog_link')},"
            f"{self.articles_map.get_mapping('feed_link')}"
            f")"
            f" VALUES "
            f"(")
        for article in self.all_articles:
            insert_articles_query = (f"{insert_articles_query}"
                                     f"{article.article_id}, '{article.title}', '{article.content}', "
                                     f"{article.author.author_id}, {article.published_date}, "
                                     f"{article.last_edited_date}, '{article.blog_link}', '{article.feed_link}'")
        insert_articles_query = f"{insert_articles_query} );"
        cursor.execute(insert_articles_query)

        # Generate authors insert query:
        insert_authors_query = (
            f"INSERT INTO {self.authors_table_name} ("
            f"{self.authors_map.get_mapping('author_id')},"
            f"{self.authors_map.get_mapping('name')},"
            f"{self.authors_map.get_mapping('uri')},"
            f"{self.authors_map.get_mapping('email')},"
            f"{self.authors_map.get_mapping('image_src')}"
            f")"
            f" VALUES "
            f"("
        )
        for author in self.all_authors:
            insert_authors_query = (f"{insert_authors_query}"
                                    f"{author.author_id}, '{author.name}', '{author.uri}', '{author.email}',"
                                    f"'{author.image_src}'")
        insert_authors_query = f"{insert_authors_query} ) ;"
        cursor.execute(insert_authors_query)

        # Generate comments insert query:
        insert_comments_query = (
            f"INSERT INTO {self.comments_table_name} ("
            f"{self.comments_map.get_mapping('comment_id')},"
            f"{self.comments_map.get_mapping('content')},"
            f"{self.comments_map.get_mapping('published_date')},"
            f"{self.comments_map.get_mapping('last_updated_date')},"
            f"{self.comments_map.get_mapping('author')}"
            f")"
            f" VALUES "
            f"("
        )
        for comment in self.all_comments:
            insert_comments_query = (f"{insert_comments_query}"
                                     f"{comment.comment_id}, '{comment.content}', {comment.published_date}, "
                                     f"{comment.last_updated_date}, {comment.author.author_id}")
        insert_comments_query = f"{insert_comments_query} ) ;"
        cursor.execute(insert_comments_query)

