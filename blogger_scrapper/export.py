import warnings
from datetime import datetime
from pathlib import Path

from blogger_scrapper import BlogArticleMapping, BlogAuthorMapping, BlogCommentMapping, BlogArticle, BlogAuthor, \
    BlogComment
import sqlite3
import json


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
        """ The export method for the SqlExport class - generates the output file, related tables and inserts all the
        collected data.

        """
        output_dir = Path('output')
        if not Path.exists(output_dir) or not Path.is_dir(output_dir):
            output_dir = Path(f"output-tmp-{datetime.now().strftime('%d%m%Y-%H%M%S%f')}")
            warnings.warn(f"Default output/ directory doesn't exist or is not a directory, creating a temporary new "
                          f"directory called {output_dir.name}")
            Path.mkdir(output_dir, exist_ok=True)
        conn = sqlite3.connect(f"{output_dir}/sql_export-{datetime.now().strftime('%d%m%Y-%H%M%S')}.db")
        articles_table_create_query = (f"CREATE TABLE {self.articles_table_name} ("
                                       f"{self.articles_map.get_mapping('article_id')} VARCHAR(255),"
                                       f"{self.articles_map.get_mapping('title')} VARCHAR(255) NOT NULL,"
                                       f"{self.articles_map.get_mapping('content')} TEXT NOT NULL,"
                                       f"{self.articles_map.get_mapping('author')} VARCHAR(255) NOT NULL,"
                                       f"{self.articles_map.get_mapping('published_date')} DATETIME NOT NULL,"
                                       f"{self.articles_map.get_mapping('last_edited_date')} DATETIME NOT NULL,"
                                       f"{self.articles_map.get_mapping('blog_link')} VARCHAR(255),"
                                       f"{self.articles_map.get_mapping('feed_link')} VARCHAR(255)"
                                       f");")
        authors_table_create_query = (f"CREATE TABLE {self.authors_table_name} ("
                                      f"{self.authors_map.get_mapping('author_id')} VARCHAR(255),"
                                      f"{self.authors_map.get_mapping('name')} VARCHAR(255) NOT NULL,"
                                      f"{self.authors_map.get_mapping('uri')} VARCHAR(255),"
                                      f"{self.authors_map.get_mapping('email')} VARCHAR(255),"
                                      f"{self.authors_map.get_mapping('image_src')} VARCHAR(255)"
                                      f");")
        comments_table_create_query = (f"CREATE TABLE {self.comments_table_name} ("
                                       f"{self.comments_map.get_mapping('comment_id')} VARCHAR(255),"
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
        articles_for_insertion = []
        for article in self.all_articles:
            article_data = (
                f"{article.article_id}",
                f"{article.title}",
                f"{article.content}",
                f"{article.author.author_id}",
                f"{article.published_date}",
                f"{article.last_edited_date}",
                f"{article.blog_link}",
                f"{article.feed_link}"
            )
            articles_for_insertion.append(article_data)
        cursor.executemany(f"INSERT INTO {self.articles_table_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           articles_for_insertion)

        # Generate authors insert query:
        authors_for_insertion = []
        for author in self.all_authors:
            author_data = (
                f"{author.author_id}",
                f"{author.name}",
                f"{author.uri}",
                f"{author.email}",
                f"{author.image_src}"
            )
            authors_for_insertion.append(author_data)
        cursor.executemany(f"INSERT INTO {self.authors_table_name} VALUES (?, ?, ?, ?, ?)", authors_for_insertion)

        # Generate comments insert query:
        comments_for_insertion = []
        for comment in self.all_comments:
            comment_data = (
                f"{comment.comment_id}",
                f"{comment.content}",
                f"{comment.published_date}",
                f"{comment.last_updated_date}",
                f"{comment.author.author_id}"
            )
            comments_for_insertion.append(comment_data)
        cursor.executemany(f"INSERT INTO {self.comments_table_name} VALUES (?, ?, ?, ?, ?)", comments_for_insertion)

        # Generate articles-comments relationship
        arts_comms_for_insertion = []
        for article in self.all_articles:
            if len(article.comments) > 0:
                for comment in article.comments:
                    arts_comms_data = (
                        f"{article.article_id}",
                        f"{comment.comment_id}"
                    )
                    arts_comms_for_insertion.append(arts_comms_data)
        cursor.executemany(f"INSERT INTO {self.articles_table_name}_{self.comments_table_name} VALUES "
                           f"(?, ?)", arts_comms_for_insertion)
        conn.commit()


class JsonExport:

    def __init__(self, all_articles_list, all_authors_list, all_comments_list, encoding):
        self.all_articles = all_articles_list  # type: list[BlogArticle]
        self.all_authors = all_authors_list  # type: list[BlogAuthor]
        self.all_comments = all_comments_list  # type: list[BlogComment]
        self.encoding = encoding

    def do_export(self, export_of="all"):
        """ The export method for the JsonExport class - generates the output file and write all the collected data.
        Optional parameter `export_of` could be provided if instead of dumping all data, only specific subsection of it
        is required (only articles, authors or comments).

        :param export_of: Optional parameter to define the scope of the export.
        :type export_of: str
        """
        if export_of not in ['all', 'authors', 'comments']:
            raise ValueError(f"Provided 'export_of' parameter value must match one of - all, authors, comments")

        output_dir = Path('output')
        if not Path.exists(output_dir) or not Path.is_dir(output_dir):
            output_dir = Path(f"output-tmp-{datetime.now().strftime('%d%m%Y-%H%M%S%f')}")
            warnings.warn(f"Default output/ directory doesn't exist or is not a directory, creating a temporary new "
                          f"directory called {output_dir.name}")
            Path.mkdir(output_dir, exist_ok=True)

        if export_of == "all":
            data_dict = {
                'articles': {},
                'authors': {},
                'comments': {}
            }
            i = 0
            for article in self.all_articles:
                articles = data_dict.get('articles')
                i += 1
                articles[f"article-{i}"] = {
                    'id': article.article_id,
                    'title': article.title,
                    'content': article.content,
                    'author': f"{article.author.author_id}-{article.author.name}",
                    'published_date': article.published_date.isoformat(),
                    'last_edited_date': article.last_edited_date.isoformat(),
                    'blog_link': article.blog_link,
                    'feed_link': article.feed_link,
                    'comments': {}
                }
                if len(article.comments) > 0:
                    comments = data_dict.get('articles').get(f'article-{i}').get('comments')
                    c = 0
                    for comment in article.comments:
                        c += 1
                        comments[f"comment-{c}"] = {
                            'id': comment.comment_id,
                            'content': comment.content,
                            'published_date': comment.published_date.isoformat(),
                            'last_edited_date': comment.last_updated_date.isoformat(),
                            'author': f"{comment.author.author_id}-{comment.author.name}",
                            'article_ref': comment.article_backref
                        }

            i = 0
            for author in self.all_authors:
                authors = data_dict.get('authors')
                i += 1
                authors[f"author-{i}"] = {
                    'id': author.author_id,
                    'uri': author.uri,
                    'name': author.name,
                    'email': author.email,
                    'image_src': author.image_src
                }

            i = 0
            for comment in self.all_comments:
                comments = data_dict.get('comments')
                i += 1
                comments[f"comment-{i}"] = {
                    'id': comment.comment_id,
                    'content': comment.content,
                    'published_date': comment.published_date.isoformat(),
                    'last_edited_date': comment.last_updated_date.isoformat(),
                    'author': f"{comment.author.author_id}-{comment.author.name}",
                    'article_ref': comment.article_backref
                }

        elif export_of == "articles":
            data_dict = {}
            i = 0
            for article in self.all_articles:
                i += 1
                data_dict[f"article-{i}"] = {
                    'id': article.article_id,
                    'title': article.title,
                    'content': article.content,
                    'author': f"{article.author.author_id}-{article.author.name}",
                    'published_date': article.published_date.isoformat(),
                    'last_edited_date': article.last_edited_date.isoformat(),
                    'blog_link': article.blog_link,
                    'feed_link': article.feed_link,
                    'comments': {}
                }
                if len(article.comments) > 0:
                    comments = data_dict.get('articles').get(f'{article}-{i}').get('comments')
                    c = 0
                    for comment in article.comments:
                        c += 1
                        comments[f"comment-{c}"] = {
                            'id': comment.comment_id,
                            'content': comment.content,
                            'published_date': comment.published_date.isoformat(),
                            'last_edited_date': comment.last_updated_date.isoformat(),
                            'author': f"{comment.author.author_id}-{comment.author.name}",
                            'article_ref': comment.article_backref
                        }

        elif export_of == "authors":
            data_dict = {}
            i = 0
            for author in self.all_authors:
                i += 1
                data_dict[f"author-{i}"] = {
                    'id': author.author_id,
                    'uri': author.uri,
                    'name': author.name,
                    'email': author.email,
                    'image_src': author.image_src
                }

        else:
            data_dict = {}
            i = 0
            for comment in self.all_comments:
                i += 1
                data_dict[f"comment-{i}"] = {
                    'id': comment.comment_id,
                    'content': comment.content,
                    'published_date': comment.published_date.isoformat(),
                    'last_edited_date': comment.last_updated_date.isoformat(),
                    'author': f"{comment.author.author_id}-{comment.author.name}",
                    'article_ref': comment.article_backref
                }

        with open(f"{output_dir}/json_export-{datetime.now().strftime('%d%m%Y-%H%M%S')}.json", "w+",
                  encoding=self.encoding) as f:
            f.write(json.dumps(data_dict, indent=4, ensure_ascii=False))
