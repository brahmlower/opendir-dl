import os
import sys
import shutil
import appdirs
import tempfile
import unittest
from urlparse import urlparse
from datetime import datetime
import sqlalchemy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opendir_dl'))
import opendir_dl
from . import ThreadedHTTPServer
from . import TestWithConfig

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

    def test_implicit_filename(self):
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

class PageCrawlerTest(TestWithConfig):
    def test_clean_index_items(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            db_url = "%stest_resources/test_sqlite3.db" % server.url
            db = opendir_dl.databasing.database_opener(self.config, db_url)
        index_items = ["http://localhost/", 10, "3"]
        crawler = opendir_dl.utils.PageCrawler(db, index_items)
        self.assertEquals(len(crawler.url_triage_bucket), 3)
        # TODO: This will need to check that the URL for items 10 and 3 match those items in the database
        for i in crawler.url_triage_bucket:
            self.assertTrue(opendir_dl.utils.is_url(i))

    def test_default_triage_method(self):
        db = opendir_dl.databasing.DatabaseWrapper('')
        db.connect()
        crawler = opendir_dl.utils.PageCrawler(db, ["http://localhost/"])
        self.assertFalse(crawler.quick)
        self.assertEquals(crawler.__dict__['_triage_method'], crawler.triage_standard)

    def test_change_triage_method(self):
        db = opendir_dl.databasing.DatabaseWrapper('')
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
        db = opendir_dl.databasing.DatabaseWrapper.from_fs(db_path)
        search = opendir_dl.utils.SearchEngine(db, ['example'])
        self.assertTrue(len(search.filters), 1)
        results = search.query()
        self.assertEquals(len(results), 1)

    def test_exclusivity(self):
        search = opendir_dl.utils.SearchEngine()
        # Tests that the exclusive is True by default
        self.assertTrue(search.exclusive)
        self.assertEquals(search.__dict__['_exclusivity'], sqlalchemy.and_)
        # Sets exclusive to False and tests everything was tested as expected
        search.exclusive = False
        self.assertFalse(search.exclusive)
        self.assertEquals(search.__dict__['_exclusivity'], sqlalchemy.or_)
        # Sets exclusive back to True and tests everything was set back to normal
        search.exclusive = True
        self.assertTrue(search.exclusive)
        self.assertEquals(search.__dict__['_exclusivity'], sqlalchemy.and_)

    def test_db_missing(self):
        search = opendir_dl.utils.SearchEngine()
        search.add_filter("test")
        with self.assertRaises(ValueError) as context:
            search.query()

class HttpGetTest(unittest.TestCase):
    def test_localhost(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            response = opendir_dl.utils.http_get(server.url)
        self.assertEquals(response[0]["status"], '200')

class MakeDirPTest(unittest.TestCase):
    def test_make_missing_path(self):
        path = "mkdirp1/missing/path"
        opendir_dl.utils.mkdir_p(path)
        self.assertTrue(os.path.exists(path))
        shutil.rmtree('mkdirp1')

    def test_make_partially_missing_path(self):
        path = "mkdirp2/path"
        opendir_dl.utils.mkdir_p(path)
        self.assertTrue(os.path.exists(path))
        new_path = path + "/new_dir"
        opendir_dl.utils.mkdir_p(new_path)
        self.assertTrue(os.path.exists(new_path))
        shutil.rmtree('mkdirp2')

    def test_make_existing_path(self):
        path = "mkdirp3/path/"
        opendir_dl.utils.mkdir_p(path)
        self.assertTrue(os.path.exists(path))
        opendir_dl.utils.mkdir_p(path)
        self.assertTrue(os.path.exists(path))
        shutil.rmtree('mkdirp3')
