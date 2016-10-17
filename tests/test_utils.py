import os
import appdirs
import tempfile
import unittest
from urlparse import urlparse
from datetime import datetime
import sqlalchemy
import opendir_dl
from . import ThreadedHTTPServer

class IsUrlTest(unittest.TestCase):
    """Tests opendir_dl.utils.is_url
    """
    def test_valid_http(self):
        url = "http://localhost:9000/"
        self.assertTrue(opendir_dl.utils.is_url(url))

    def test_valid_https(self):
        url = "https://example.com/"
        self.assertTrue(opendir_dl.utils.is_url(url))

    def test_valid_http_unicode(self):
        url = u'http://localhost:9000/'
        self.assertTrue(opendir_dl.utils.is_url(url))

    def test_invalid_ftp(self):
        url = "ftp://localhost:9000/"
        self.assertTrue(opendir_dl.utils.is_url(url))

    def test_invalid_unknown(self):
        url = ":/12/363p"
        self.assertFalse(opendir_dl.utils.is_url(url))

    def test_non_string(self):
        url = 1235
        self.assertFalse(opendir_dl.utils.is_url(url))

class UrlToFilenameTest(unittest.TestCase):
    """Tests opendir_dl.utils.url_to_filename
    """
    def test_normal_name(self):
        filename = "filename.txt"
        url = "http://localhost/%s" % filename
        parsed_filename = opendir_dl.utils.url_to_filename(url)
        self.assertEquals(filename, parsed_filename)

    def test_urlencoded_name(self):
        filename = "file%20name.txt"
        url = "http://localhost/%s" % filename
        parsed_filename = opendir_dl.utils.url_to_filename(url)
        self.assertEquals("file name.txt", parsed_filename)

    def test_implicite_filename(self):
        url = "http://localhost/"
        parsed_filename = opendir_dl.utils.url_to_filename(url)
        self.assertEquals("index.html", parsed_filename)

    def test_parsed_url(self):
        url = "http://localhost/path/filename.txt"
        parsed_url = urlparse(url)
        parsed_filename = opendir_dl.utils.url_to_filename(parsed_url)
        self.assertEquals("filename.txt", parsed_filename)

class HttpHeadTest(unittest.TestCase):
    """Tests opendir_dl.utils.HttpHead
    """
    def test_normal_head(self):
        url = "http://example.com/dir/"
        head_dict = {"status": '200', "content-type": 'text/plain',
                     "content-length": '500',
                     "last-modified": "Mon, 16 Jan 2006 16:30:19 GMT"}
        head = opendir_dl.utils.HttpHead(url, head_dict)
        self.assertTrue(isinstance(head, opendir_dl.utils.HttpHead))
        self.assertEquals(head.url, url)
        self.assertEquals(head.status, int(head_dict['status']))
        self.assertEquals(head.content_type, head_dict['content-type'])
        self.assertEquals(head.content_length, int(head_dict['content-length']))
        self.assertTrue(isinstance(head.last_modified, datetime))
        self.assertTrue(isinstance(head.last_indexed, datetime))

    def test_no_dict(self):
        url = "http://example.com/dir/"
        head_dict = {}
        head = opendir_dl.utils.HttpHead(url, head_dict)
        self.assertTrue(isinstance(head, opendir_dl.utils.HttpHead))
        self.assertEquals(head.url, url)
        self.assertEquals(head.status, 0)
        self.assertEquals(head.content_type, '')
        self.assertEquals(head.content_length, 0)
        self.assertEquals(head.last_modified, None)
        self.assertTrue(isinstance(head.last_indexed, datetime))

    def test_html_content_type(self):
        url = "http://example.com/dir/"
        head_dict = {"status": '200', "content-type": 'text/html some info',
                     "content-length": '500',
                     "last-modified": "Mon, 16 Jan 2006 16:30:19 GMT"}
        head = opendir_dl.utils.HttpHead(url, head_dict)
        self.assertTrue(isinstance(head, opendir_dl.utils.HttpHead))
        self.assertTrue(head.is_html())

    def test_as_fileindex(self):
        url = "http://example.com/dir/"
        head_dict = {"status": '200', "content-type": 'text/html some info',
                     "content-length": '500',
                     "last-modified": "Mon, 16 Jan 2006 16:30:19 GMT"}
        head = opendir_dl.utils.HttpHead(url, head_dict)
        self.assertTrue(isinstance(head, opendir_dl.utils.HttpHead))
        self.assertTrue(isinstance(head.as_fileindex(), opendir_dl.utils.FileIndex))

class ParseUrlsTest(unittest.TestCase):
    """Tests opendir_dl.utils.url_to_domain
    """
    def test_empty_text(self):
        url = "http://localhost/"
        html = ""
        url_list = opendir_dl.utils.parse_urls(url, html)
        self.assertTrue(isinstance(url_list, list))
        self.assertEquals(len(url_list), 0)

    def test_single_link(self):
        url = "http://localhost/"
        html = "<html><a href=\"link\">link</a></html>"
        url_list = opendir_dl.utils.parse_urls(url, html)
        self.assertTrue(isinstance(url_list, list))
        self.assertEquals(len(url_list), 1)
        self.assertEquals(url_list[0], "http://localhost/link")

    def test_no_clean_links(self):
        url = "http://localhost/"
        html = "<html><a href=\"#\">link</a></html>"
        url_list = opendir_dl.utils.parse_urls(url, html)
        self.assertTrue(isinstance(url_list, list))
        self.assertEquals(len(url_list), 0)

class BadAnchorTest(unittest.TestCase):
    def test_good_anchor(self):
        href = "filename.txt"
        is_bad = opendir_dl.utils.bad_anchor(href)
        self.assertFalse(is_bad)

    def test_page_anchor(self):
        href = "#bottom"
        is_bad = opendir_dl.utils.bad_anchor(href)
        self.assertTrue(is_bad)

    def test_sort_anchor(self):
        href = "?C=M;O=A"
        is_bad = opendir_dl.utils.bad_anchor(href)
        self.assertTrue(is_bad)

    def test_leading_slash(self):
        href = "/filename.txt"
        is_bad = opendir_dl.utils.bad_anchor(href)
        self.assertTrue(is_bad)

class DatabaseWrapper(unittest.TestCase):
    def test_provided_source(self):
        db = opendir_dl.utils.DatabaseWrapper("sqlite3.db")
        self.assertEquals(db.source, "sqlite3.db")
        db.connect()
        self.assertTrue(db.is_connected())
        self.assertEquals(str(db.db_conn.bind.url), 'sqlite:///sqlite3.db')

    def test_memory_source(self):
        db = opendir_dl.utils.DatabaseWrapper('')
        self.assertEquals(db.source, '')
        db.connect()
        self.assertTrue(db.is_connected())
        self.assertEquals(str(db.db_conn.bind.url), 'sqlite:///')

    def test_query_reassignment(self):
        db = opendir_dl.utils.DatabaseWrapper('')
        db.connect()
        self.assertTrue(db.is_connected())
        self.assertEquals(db.db_conn.query, db.query)

    def test_from_default(self):
        db = opendir_dl.utils.DatabaseWrapper.from_default()
        self.assertTrue(db.is_connected())
        db_path = appdirs.user_data_dir('opendir-dl') + "/default.db"
        self.assertEquals(str(db.db_conn.bind.url), 'sqlite:///%s' % db_path)

    def test_from_data(self):
        self_path = os.path.realpath(__file__)
        cur_dir = "/".join(self_path.split("/")[:-1])
        rfile = open(cur_dir + '/test_resources/test_sqlite3.db', 'rb')
        data = rfile.read()
        rfile.close()
        db = opendir_dl.utils.DatabaseWrapper.from_data(data)
        self.assertTrue(db.is_connected())
        self.assertEquals(db.query(opendir_dl.utils.FileIndex).count(), 12)

    def test_from_fs(self):
        self_path = os.path.realpath(__file__)
        cur_dir = "/".join(self_path.split("/")[:-1])
        db_path = cur_dir + '/test_resources/test_sqlite3.db'
        db = opendir_dl.utils.DatabaseWrapper.from_fs(db_path)
        self.assertTrue(db.is_connected())
        self.assertEquals(db.query(opendir_dl.utils.FileIndex).count(), 12)

    def test_from_url(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            url = "%stest_resources/test_sqlite3.db" % server.url
            db = opendir_dl.utils.DatabaseWrapper.from_url(url)
        finally:
            # We have to clean up the webserver regardless of any unexpected issues
            server.stop()
        self.assertTrue(db.is_connected())
        self.assertEquals(db.query(opendir_dl.utils.FileIndex).count(), 12)

#     def test_from_unknown(self):
#         pass

class PageCrawlerTest(unittest.TestCase):
    def test_default_triage_method(self):
        db = opendir_dl.utils.DatabaseWrapper('')
        db.connect()
        crawler = opendir_dl.utils.PageCrawler(db, ["http://localhost/"])
        self.assertFalse(crawler.quick)
        self.assertEquals(crawler.__dict__['_triage_method'], crawler.triage_standard)

    def test_change_triage_method(self):
        db = opendir_dl.utils.DatabaseWrapper('')
        db.connect()
        crawler = opendir_dl.utils.PageCrawler(db, ["http://localhost/"])
        crawler.quick = True
        self.assertTrue(crawler.quick)
        self.assertEquals(crawler.__dict__['_triage_method'], crawler.triage_quick)
        crawler.quick = False
        self.assertFalse(crawler.quick)
        self.assertEquals(crawler.__dict__['_triage_method'], crawler.triage_standard)

class SearchEngineTest(unittest.TestCase):
    def test_query(self):
        self_path = os.path.realpath(__file__)
        cur_dir = "/".join(self_path.split("/")[:-1])
        db_path = cur_dir + '/test_resources/test_sqlite3.db'
        db = opendir_dl.utils.DatabaseWrapper.from_fs(db_path)
        search = opendir_dl.utils.SearchEngine(db, ['example'])
        self.assertTrue(len(search.filters), 1)
        results = search.query()
        self.assertEquals(len(results), 1)

    def test_exclusivity(self):
        search = opendir_dl.utils.SearchEngine()
        self.assertTrue(search.exclusive)
        self.assertEquals(search.__dict__['_exclusivity'], sqlalchemy.and_)
        search.exclusive = False
        self.assertFalse(search.exclusive)
        self.assertEquals(search.__dict__['_exclusivity'], sqlalchemy.or_)

    def test_db_missing(self):
        search = opendir_dl.utils.SearchEngine()
        search.add_filter("test")
        with self.assertRaises(ValueError) as context:
            search.query()

class TestHttpGet(unittest.TestCase):
    def test_localhost(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            response = opendir_dl.utils.http_get(server.url)
        finally:
            server.stop()
        self.assertEquals(response[0]["status"], '200')
