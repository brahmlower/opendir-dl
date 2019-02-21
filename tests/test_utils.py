import os
import sys
import tempfile
import unittest
from urllib.parse import urlparse
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
        self.assertEqual(filename, parsed_filename)

    def test_urlencoded_name(self):
        filename = "file%20name.txt"
        url = "http://localhost/%s" % filename
        parsed_filename = opendir_dl.utils.url_to_filename(url)
        self.assertEqual("file name.txt", parsed_filename)

    def test_implicit_filename(self):
        url = "http://localhost/"
        parsed_filename = opendir_dl.utils.url_to_filename(url)
        self.assertEqual("index.html", parsed_filename)

    def test_parsed_url(self):
        url = "http://localhost/path/filename.txt"
        parsed_url = urlparse(url)
        parsed_filename = opendir_dl.utils.url_to_filename(parsed_url)
        self.assertEqual("filename.txt", parsed_filename)

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
        self.assertEqual(head.url, url)
        self.assertEqual(head.status, int(head_dict['status']))
        self.assertEqual(head.content_type, head_dict['content-type'])
        self.assertEqual(head.content_length, int(head_dict['content-length']))
        self.assertTrue(isinstance(head.last_modified, datetime))
        self.assertTrue(isinstance(head.last_indexed, datetime))

    def test_no_dict(self):
        url = "http://example.com/dir/"
        head_dict = {}
        head = opendir_dl.utils.HttpHead(url, head_dict)
        self.assertTrue(isinstance(head, opendir_dl.utils.HttpHead))
        self.assertEqual(head.url, url)
        self.assertEqual(head.status, 0)
        self.assertEqual(head.content_type, '')
        self.assertEqual(head.content_length, 0)
        self.assertEqual(head.last_modified, None)
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

    # def test_socket_error(self):
    #     url = "http://unlikely.address.local:12345/"
    #     #with self.assertRaises(ValueError) as context:
    #     opendir_dl.utils.HttpHead.from_url(url)
    #     #expected_error = "No results found for index '{}' in database '{}'.".format(target_index, db_path)
    #     #self.assertEqual(str(context.exception), expected_error)
    #     self.assertTrue(False)

class ParseUrlsTest(unittest.TestCase):
    """Tests opendir_dl.utils.url_to_domain
    """
    def test_empty_text(self):
        url = "http://localhost/"
        html = ""
        url_list = opendir_dl.utils.parse_urls(url, html)
        self.assertTrue(isinstance(url_list, list))
        self.assertEqual(len(url_list), 0)

    def test_single_link(self):
        url = "http://localhost/"
        html = "<html><a href=\"link\">link</a></html>"
        url_list = opendir_dl.utils.parse_urls(url, html)
        self.assertTrue(isinstance(url_list, list))
        self.assertEqual(len(url_list), 1)
        self.assertEqual(url_list[0], "http://localhost/link")

    def test_no_clean_links(self):
        url = "http://localhost/"
        html = "<html><a href=\"#\">link</a></html>"
        url_list = opendir_dl.utils.parse_urls(url, html)
        self.assertTrue(isinstance(url_list, list))
        self.assertEqual(len(url_list), 0)

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
    # The following function has been commented out because the property url_triage_bucked has
    # been refactored out while implementing threads

    # def test_clean_index_items(self):
    #     with ThreadedHTTPServer("localhost", 8000) as server:
    #         db_url = "%stest_resources/test_sqlite3.db" % server.url
    #         db = opendir_dl.databasing.database_opener(self.config, db_url)
    #     index_items = ["http://localhost/", 10, "3"]
    #     crawler = opendir_dl.utils.PageCrawler(db, index_items)

    #     self.assertEqual(len(crawler.url_triage_bucket), 3)
    #     # TODO: This will need to check that the URL for items 10 and 3 match those items in the database
    #     for i in crawler.url_triage_bucket:
    #         self.assertTrue(opendir_dl.utils.is_url(i))

    def test_default_triage_method(self):
        db = opendir_dl.databasing.DatabaseWrapper('')
        db.connect()
        crawler = opendir_dl.utils.PageCrawler(db, ["http://localhost/"])
        self.assertFalse(crawler.quick)
        self.assertEqual(crawler.__dict__['_triage_method'], crawler.triage_standard)

    def test_change_triage_method(self):
        db = opendir_dl.databasing.DatabaseWrapper('')
        db.connect()
        crawler = opendir_dl.utils.PageCrawler(db, ["http://localhost/"])
        crawler.quick = True
        self.assertTrue(crawler.quick)
        self.assertEqual(crawler.__dict__['_triage_method'], crawler.triage_quick)
        crawler.quick = False
        self.assertFalse(crawler.quick)
        self.assertEqual(crawler.__dict__['_triage_method'], crawler.triage_standard)

class SearchEngineTest(unittest.TestCase):
    def test_query(self):
        self_path = os.path.realpath(__file__)
        cur_dir = "/".join(self_path.split("/")[:-1])
        db_path = cur_dir + '/test_resources/test_sqlite3.db'
        db = opendir_dl.databasing.DatabaseWrapper.from_fs(db_path)
        search = opendir_dl.utils.SearchEngine(db, ['example'])
        self.assertTrue(len(search.filters), 1)
        results = search.query()
        self.assertEqual(len(results), 1)

    def test_exclusivity(self):
        search = opendir_dl.utils.SearchEngine()
        # Tests that the exclusive is True by default
        self.assertTrue(search.exclusive)
        self.assertEqual(search.__dict__['_exclusivity'], sqlalchemy.and_)
        # Sets exclusive to False and tests everything was tested as expected
        search.exclusive = False
        self.assertFalse(search.exclusive)
        self.assertEqual(search.__dict__['_exclusivity'], sqlalchemy.or_)
        # Sets exclusive back to True and tests everything was set back to normal
        search.exclusive = True
        self.assertTrue(search.exclusive)
        self.assertEqual(search.__dict__['_exclusivity'], sqlalchemy.and_)

    def test_db_missing(self):
        search = opendir_dl.utils.SearchEngine()
        search.add_filter("test")
        with self.assertRaises(ValueError) as context:
            search.query()

class HttpGetTest(unittest.TestCase):
    def test_localhost(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            response = opendir_dl.utils.http_get(server.url)
        self.assertEqual(response[0]["status"], '200')

class DownloadManagerTest(TestWithConfig):
    def test_nonexistant_index(self):
        target_index = 404
        db_path = "test_resources/test_sqlite3.db"
        db_wrapper = opendir_dl.databasing.database_opener(self.config, db_path)
        dl_man = opendir_dl.utils.DownloadManager(db_wrapper, target_index)
        with self.assertRaises(ValueError) as context:
            dl_man.download_id(target_index)
        expected_error = "No results found for index '{}' in database '{}'.".format(target_index, db_path)
        self.assertEqual(str(context.exception), expected_error)

class FormatTagListTest(unittest.TestCase):
    def test_empty_list(self):
        result = opendir_dl.utils.format_tags([])
        self.assertEqual(result, "")

    def test_single_item(self):
        tag = opendir_dl.models.Tags(name="test")
        result = opendir_dl.utils.format_tags([tag])
        self.assertEqual(result, tag.name)

    def test_multiple_items(self):
        tag1 = opendir_dl.models.Tags(name="test1")
        tag2 = opendir_dl.models.Tags(name="test2")
        result = opendir_dl.utils.format_tags([tag1, tag2])
        self.assertEqual(result, "{} {}".format(tag1.name, tag2.name))
