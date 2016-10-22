import os
import sys
import md5
import unittest
import appdirs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opendir_dl'))
import opendir_dl
from . import ThreadedHTTPServer

"""
Just makes sure the code doesn't throw exceptions. Code cleanup required before
proper unit tests can be written.
"""

class CommandHelpTest(unittest.TestCase):
    def test_no_args(self):
        opendir_dl.commands.help()

class CommandIndexTest(unittest.TestCase):
    def test_no_args(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            opendir_dl.commands.index([server.url], [], {})

    def test_quick_index(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            opendir_dl.commands.index([server.url], ["quick"], {})

    def test_index_404status(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            url = "%s/test_resources/missing_file.txt" % server.url
            opendir_dl.commands.index([url], [], {})

class CommandDatabaseTest(unittest.TestCase):
    def test_list(self):
        opendir_dl.commands.database([], [], {})

    def test_create_and_delete_database(self):
        opendir_dl.commands.database(["test1"], [], {})
        opendir_dl.commands.database([], [], {"delete": "test1"})

    def test_attempt_delete_default(self):
        with self.assertRaises(ValueError) as context:
            opendir_dl.commands.database([], [], {"delete": "default"})

    def test_attempt_bad_type(self):
        expected_error = "Database type must be one of: url, filesystem, alias"
        with self.assertRaises(ValueError) as context:
            opendir_dl.commands.database(["test2"], [], {"type": "notavalidtype", "resource": "default"})
        self.assertEqual(str(context.exception), expected_error)

    def test_incomplete_alias(self):
        alias_name = "alias_name"
        resource_database = "nonreal_database"
        expected_error = "Cannot create alias to database- no database named '%s'." % resource_database
        with self.assertRaises(ValueError) as context:
            opendir_dl.commands.database([alias_name], [], {"type": "alias", "resource": resource_database})
        self.assertEqual(str(context.exception), expected_error)

class CommandSearchTest(unittest.TestCase):
    def test_no_args(self):
        opendir_dl.commands.search([], [], {"db": "test_resources/test_sqlite3.db"})

class CommandDownloadTest(unittest.TestCase):
    def assert_file_exists(self, file_path):
        self.assertTrue(os.path.exists(file_path))

    def assert_files_match(self, file_path1, file_path2):
        file_1 = open(file_path1)
        file_2 = open(file_path2)
        md5_1 = md5.new(file_1.read()).digest()
        md5_2 = md5.new(file_2.read()).digest()
        self.assertEqual(md5_1, md5_2)

    def test_no_args(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            opendir_dl.commands.download(["%stest_resources/test_sqlite3.db" % server.url], [], {})
            # Make sure the file was actually downloaded
            self.assert_file_exists("test_sqlite3.db")
            # Make sure the two files are exactly the same
            self.assert_files_match("test_sqlite3.db", "test_resources/test_sqlite3.db")
            os.remove("test_sqlite3.db")

    def test_no_index(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
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
            db_wrapper = opendir_dl.databasing.DatabaseWrapper.from_default()
            search = opendir_dl.utils.SearchEngine(db_wrapper.db_conn, ["example_file.txt"])
            num_results = len(search.query())
            self.assertEqual(num_results, 0)

    def test_bad_status(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            # This references path test_resources/test_404_head.txt which does not exist (causing status 404)
            opendir_dl.commands.download([13], [], {"db": "%stest_resources/test_sqlite3.db" % server.url})
            # Make sure the file was not created
            self.assertFalse(os.path.exists("test_404_head.txt"))

    def test_search(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            opendir_dl.commands.download(["example_file"], ["search"], {"db": "%stest_resources/test_sqlite3.db" % server.url})
            os.remove("example_file.txt")
