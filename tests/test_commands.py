import os
import md5
import unittest
import appdirs
import opendir_dl
from . import ThreadedHTTPServer

class TestCommandHelp(unittest.TestCase):
    def test_no_args(self):
        opendir_dl.commands.help()

class TestCommandIndex(unittest.TestCase):
    def test_no_args(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            opendir_dl.commands.index([server.url], [], {})
        finally:
            server.stop()

    def test_quick_index(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            opendir_dl.commands.index([server.url], ["quick"], {})
        finally:
            server.stop()

    def test_index_404status(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            url = "%s/test_resources/missing_file.txt" % server.url
            opendir_dl.commands.index([url], [], {})
        finally:
            server.stop()

class TestCommandSearch(unittest.TestCase):
    def test_no_args(self):
        opendir_dl.commands.search([], [], {"db": "test_resources/test_sqlite3.db"})

class TestCommandDownload(unittest.TestCase):
    def assert_file_exists(self, file_path):
        self.assertTrue(os.path.exists(file_path))

    def assert_files_match(self, file_path1, file_path2):
        file_1 = open(file_path1)
        file_2 = open(file_path2)
        md5_1 = md5.new(file_1.read()).digest()
        md5_2 = md5.new(file_2.read()).digest()
        self.assertEqual(md5_1, md5_2)

    def test_no_args(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            opendir_dl.commands.download(["%stest_resources/test_sqlite3.db" % server.url], [], {})
            # Make sure the file was actually downloaded
            self.assert_file_exists("test_sqlite3.db")
            # Make sure the two files are exactly the same
            self.assert_files_match("test_sqlite3.db", "test_resources/test_sqlite3.db")
            os.remove("test_sqlite3.db")
        finally:
            server.stop()

    def test_no_index(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            # Remove the existing database if it exists
            db_path = appdirs.user_data_dir('opendir-dl') + "/default.db"
            os.remove(db_path)
            # Download the file
            opendir_dl.commands.download(["%stest_resources/example_file.txt" % server.url], ['no-index'], {})
            # Make sure the file was actually downloaded
            self.assert_file_exists("example_file.txt")
            # Make sure the two files are exactly the same
            self.assert_files_match("example_file.txt", "test_resources/example_file.txt")
            os.remove("example_file.txt")
            # Check our database to make sure an index wasn't created
            db_wrapper = opendir_dl.utils.DatabaseWrapper.from_default()
            search = opendir_dl.utils.SearchEngine(db_wrapper.db_conn, ["example_file.txt"])
            num_results = len(search.query())
            self.assertEqual(num_results, 0)
        finally:
            server.stop()

    def test_bad_status(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            # This references path test_resources/test_404_head.txt which does not exist (causing status 404)
            opendir_dl.commands.download([13], [], {"db": "%stest_resources/test_sqlite3.db" % server.url})
            # Make sure the file was not created
            self.assertFalse(os.path.exists("test_404_head.txt"))
        finally:
            server.stop()

    def test_search(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            opendir_dl.commands.download(["example_file"], ["search"], {"db": "%stest_resources/test_sqlite3.db" % server.url})
            os.remove("example_file.txt")
        finally:
            server.stop()
