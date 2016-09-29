import tempfile
import unittest
from datetime import datetime
import opendir_dl

class IsUrlTest(unittest.TestCase):
    """Tests cssefserver.CssefServer
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
        self.assertFalse(opendir_dl.utils.is_url(url))

    def test_invalid_unknown(self):
        url = ":/12/363p"
        self.assertFalse(opendir_dl.utils.is_url(url))

class CleanDateModifiedTest(unittest.TestCase):
    def test_valid_date(self):
        date_string = "Mon, 16 Jan 2006 16:30:19 GMT"
        date = opendir_dl.utils.clean_date_modified(date_string)
        self.assertTrue(isinstance(date, datetime))

    def test_invalid_date_value(self):
        # Note that the Day of the week is incorrect here (should be Sun)
        date_string = "Mon, 15 Jan 2006 16:30:19 GMT"
        date = opendir_dl.utils.clean_date_modified(date_string)
        self.assertEquals(date, None)

    def test_invalid_date_format(self):
        # Note that the day of the month and the month name are swapped
        date_string = "Mon, Jan 16 2006 16:30:19 GMT"
        date = opendir_dl.utils.clean_date_modified(date_string)
        self.assertEquals(date, None)

    def test_invalid_date_none(self):
        date_string = None
        date = opendir_dl.utils.clean_date_modified(date_string)
        self.assertEquals(date, None)

class UrlToFilenameTest(unittest.TestCase):
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