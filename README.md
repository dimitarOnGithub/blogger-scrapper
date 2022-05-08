# blogger-scrapper

Scrapper is a small Python package for scrapping (scraping) content (articles, authors and comments*) from the Google's Blogger platform via their Atom/RSS feed. The package export supports JSON, SQL or XML formats.

\* RSS feeds do not provide comments so those will not be scrapped if the Scrapper object is initialized with the 'feed="rss"' parameter.

# Usage

The simplest and most straightforward way of using the Scrapper would be to simply initialize it by providing the domain name to the Blogger website as a parameter with no additional parameters, and then running its 'scrap()' method which will obtain all content via Atom and generate the export in JSON format.

```python
>>> import blogger_scrapper
>>> scrapper = blogger_scrapper.Scrapper('foobar.blogspot.com')
>>> scrapper
<blogger_scrapper.scrapper.Scrapper object at 0x7f817e1f8ac0>
>>> scrapper.scrap()
```

Upon invoking the *scrap()* method, a JSON file wih the data will be created in the output/ directory at root level in the project structure.

You can also change the export type upon initializing the object, to do that provide the additional *export_type* parameter and specify what sort of an export should be used (json, xml, sql).

# Going deeper

If you're keen on browing the content of a website instead of scrapping it, you can instead refer to the various objects within the package responsible for handling the data from the website.

## Working with the data

The *Blogsite* object is mostly just a high-level interface for working with the website, it establishes the connection to the website and verifies that the expected feed is available for collection. Once the initial checks have been completed, it initializes the *Feed* class that does all the work.

The *Feed* class provides access to the content of the site via its *fetch_first*, *fetch_all*, *get_all_authors* and *get_all_comments* methods. It's recommended to initialize this class via the *Blogsite* object as that's the one retrieving the actual Atom feed URL and passing it onto the Feed object.

```python
>>> scrapper.site
Blogsite('foobar.blogspot.com')
>>> scrapper.feed
Feed('https://foobar.blogspot.com/feeds/posts/default', 'atom', site_encoding='UTF-8')
```

The *get_all_authors* and *get_all_comments* methods will require you to provide it a list of articles already collected from the feed, this is to avoid overloading the website with calls made to it.

## Article viewing

Once we have access to the *Feed* object, we can refer to its methods to view the various content retrieved from the site. All articles exist as objects of the *BlogArticle* class, which grants you the access to various data, such as unique ID on the site, author and publishing information:
```python
>>> article = feed.fetch_first()
>>> article.article_id
8279894121456130630
>>> article.author
BlogAuthor('Winter')
>>> article.published_date
datetime.datetime(2021, 5, 6, 17, 51, 0, 1000, tzinfo=datetime.timezone(datetime.timedelta(seconds=10800)))
>>> article.feed_link
'https://www.blogger.com/feeds/1234567890/posts/default/1234567890'
>>> article.blog_link
'https://foobar.blogspot.com/2021/05/blog-post.html'
>>> article.
article.article_id        article.blog_link         article.content           article.last_edited_date  article.title
article.author            article.comments          article.feed_link         article.published_date 
```

## Authors viewing

The users' names have been edited for the sake of their own privacy.

```python
>>> articles = feed.fetch_all()
>>> authors = feed.get_all_authors(articles)
>>> authors
[BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited> '), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>'), BlogAuthor('<edited>')]
```

The *BlogAuthor* class provides you with the data about each collected author, whether that's the author of the article or of any of the comments.
```python
>>> author = article.author
>>> author
BlogAuthor('Winter')
>>> author.
author.author_id  author.email      author.image_src  author.name       author.uri        
```

## Comments viewing

The *BlogComment* class holds the data for each comment retrieved from the website, along with backref to the article it has been posted to and its author.

```python
>>> comments = scrapper.feed.get_all_comments(articles)
>>> len(comments)
101
>>> comment = comments[0]
>>> comment.
comment.article_backref    comment.comment_id         comment.last_updated_date  
comment.author             comment.content            comment.published_date     
>>> comment.article_backref
7163000079208924147
>>> comment.author
BlogAuthor('Anonymous')
>>> comment.published_date
datetime.datetime(2012, 5, 19, 13, 52, 37, 331000, tzinfo=datetime.timezone(datetime.timedelta(seconds=10800)))
```

# Exporting

If you're scrapping a site without any additional parameters provided to the Scrapper class, all the data in the provided JSON export will be as-is within the program in terms of attributes naming. The same remains true for SQL and XML exports.

## JSON

The generated JSON file in the output/ folder will be similar to:
```json
{
    "articles": {
        "article-1": {
            "id": 1234567890,
            "title": "Foobar",
            "content": "<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. <br /></p>",
            "author": "1234567890-Winter",
            "published_date": "2021-05-06T17:51:00.001000+03:00",
            "last_edited_date": "2021-05-06T17:51:12.015000+03:00",
            "blog_link": "https://foobar.blogspot.com/2021/05/blog-post.html",
            "feed_link": "https://www.blogger.com/feeds/1234567890/posts/default/1234567890",
            "comments": {}
        },
    },
    "authors": {
        "author-1": {
            "id": 1234567890,
            "uri": "http://www.blogger.com/profile/1234567890",
            "name": "Winter",
            "email": "noreply@blogger.com",
            "image_src": "http://3.bp.blogspot.com/-40py0GT39zc/VONo4Ua07kI/AAAAAAAAAYo/xx0G9jFqnhA/s1600/1234567890.jpg"
        }
    },
    "comments": {}
}
```

## XML

Another possible export type is an XML file. That will be generated from a JSON using the built-in function of *dumps* from the json package. Example XML export:
```xml
<?xml version="1.0" encoding="UTF-8" ?>
<root>
    <export type="dict">
        <articles type="dict">
            <article-1 type="dict">
                <id type="int">1234567890</id>
                <title type="str">Foobar</title>
                <content type="str">&lt;p&gt;Lorem ipsum dolor sit amet, consectetur adipiscing elit. &lt;br /&gt;&lt;/p&gt;</content>
                <author type="str">1234567890-Winter</author>
                <published_date type="str">2021-05-06T17:51:00.001000+03:00</published_date>
                <last_edited_date type="str">2021-05-06T17:51:12.015000+03:00</last_edited_date>
                <blog_link type="str">https://foobar.blogspot.com/2021/05/blog-post.html</blog_link>
                <feed_link type="str">https://www.blogger.com/feeds/1234567890/posts/default/1234567890</feed_link>
                <comments type="dict"></comments>
            </article-1>
        </articles>
        <authors type="dict">
            <author-1 type="dict">
                <id type="int">1234567890</id>
                <uri type="str">http://www.blogger.com/profile/1234567890</uri>
                <name type="str">Winter</name>
                <email type="str">noreply@blogger.com</email>
                <image_src type="str">http://3.bp.blogspot.com/-40py0GT39zc/VONo4Ua07kI/AAAAAAAAAYo/xx0G9jFqnhA/s1600/1234567890.jpg</image_src>
            </author-1>
        </authors>
    <comments type="dict"></comments>
    </export>
</root>
```

## SQL

The last and final export export is done via the sqlite3 package and it creates a file-based database in the output/ directory. This export also support custom mapping for the naming of the tables and their columns via the mapping module in this package.

### Mapping

To rename tables, you can refer to the *SqlExport* methods - *name_articles_table*, *name_authors_table* and *name_comments_table*.
```python
>>> from blogger_scrapper.export import SqlExport
>>> articles = scrapper.feed.fetch_all()
>>> authors = feed.get_all_authors(articles)
>>> comments = scrapper.feed.get_all_comments(articles)
>>> sql_export = SqlExport(articles, authors, comments)
>>> sql_export.articles_table_name
'articles'
>>> sql_export.name_articles_table('posts')
>>> sql_export.articles_table_name
'posts'
```

To provide a different naming for the columns, use the *BlogArticleMapping*, *BlogAuthorMapping* and *BlogCommentMapping* classes in the mapping.py module. The provided parameters when initializing the object must match the attributes of their respective data class (*BlogArticle*, *BlogAuthor* and *BlogComment*)
```python
>>> from blogger_scrapper.mapping import BlogArticleMapping
>>> mapping = BlogArticleMapping()
>>> mapping = BlogArticleMapping(article_id='unique_id', title='article_name')
>>> mapping.article_id
'unique_id'
>>> mapping.title
'article_name'
```

What basically happens is that you set 'references' to the attributes of the various classes responsible for handling the data (such as *BlogArticle* and *BlogAuthor*) and upon providing the mapping object to the SqlExport class, it matches those references and uses them when creating the columns.

Now that we have a custom mapping for the *article_id* and *title* columns, we can provide it to the SqlExport object
```python
>>> sql_export = SqlExport(articles, authors, comments, articles_mapping=mapping)
>>> sql_export.do_export()
```

Now, we can create a connection to the file database and see the tables and columns with their respective names as we set them earlier.
```python
>>> import sqlite3
>>> conn = sqlite3.Connection(database="output/sql_export-08052022-125839.db")
>>> cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
>>> cursor.fetchall()
[('posts',), ('authors',), ('comments',), ('articles_comments',)]
>>> cursor.execute("PRAGMA table_info('posts')")
>>> cursor.fetchall()
[(0, 'unique_id', 'VARCHAR(255)', 0, None, 0), (1, 'article_name', 'VARCHAR(255)', 1, None, 0), (2, 'content', 'TEXT', 1, None, 0), (3, 'author', 'VARCHAR(255)', 1, None, 0), (4, 'published_date', 'DATETIME', 1, None, 0), (5, 'last_edited_date', 'DATETIME', 1, None, 0), (6, 'blog_link', 'VARCHAR(255)', 0, None, 0), (7, 'feed_link', 'VARCHAR(255)', 0, None, 0)]
```
