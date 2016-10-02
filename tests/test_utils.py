import tempfile
import unittest
from urlparse import urlparse
from datetime import datetime
import opendir_dl

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

    def test_as_remotefile(self):
        url = "http://example.com/dir/"
        head_dict = {"status": '200', "content-type": 'text/html some info',
            "content-length": '500',
            "last-modified": "Mon, 16 Jan 2006 16:30:19 GMT"}
        head = opendir_dl.utils.HttpHead(url, head_dict)
        self.assertTrue(isinstance(head, opendir_dl.utils.HttpHead))
        self.assertTrue(isinstance(head.as_remotefile(), opendir_dl.utils.RemoteFile))

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

class PageCrawlerTest(unittest.TestCase):
    pass

class DatabaseWrapper(unittest.TestCase):
    pass

class SearchEngineTest(unittest.TestCase):
    pass
