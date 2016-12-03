import os
import sys
import md5
import unittest
import appdirs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opendir_dl'))
import opendir_dl
from . import ThreadedHTTPServer
from . import TestWithConfig

"""
Just makes sure the code doesn't throw exceptions. Code cleanup required before
proper unit tests can be written.
"""

class BaseCommandTest(TestWithConfig):
    def test_flags(self):
        instance = opendir_dl.commands.BaseCommand()
        instance.flags = ["example"]
        self.assertTrue(instance.has_flag("example"))
        self.assertFalse(instance.has_flag("not-there"))

    def test_database_interaction(self):
        instance = opendir_dl.commands.BaseCommand()
        instance.config = self.config
        self.assertFalse(instance.db_connected())
        instance.db_connect()
        self.assertTrue(instance.db_connected())
        instance.db_disconnect()
        self.assertFalse(instance.db_connected())

class CommandHelpTest(TestWithConfig):
    def test_no_args(self):
        instance = opendir_dl.commands.HelpCommand()
        instance.config = self.config
        instance.run()

class CommandIndexTest(TestWithConfig):
    def test_no_args(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            instance = opendir_dl.commands.IndexCommand()
            instance.config = self.config
            instance.values = [server.url]
            instance.run()

    def test_quick_index(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            instance = opendir_dl.commands.IndexCommand()
            instance.config = self.config
            instance.values = [server.url]
            instance.flags = ["quick"]
            instance.run()

    def test_index_404status(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            url = "%s/test_resources/missing_file.txt" % server.url
            instance = opendir_dl.commands.IndexCommand()
            instance.config = self.config
            instance.values = [url]
            instance.run()

class CommandDatabaseTest(TestWithConfig):
    def test_list(self):
        instance = opendir_dl.commands.DatabaseCommand()
        instance.config = self.config
        instance.run()

    def test_create_and_delete_database(self):
        # Create a database to be deleted
        instance1 = opendir_dl.commands.DatabaseCommand()
        instance1.config = self.config
        instance1.values = ["test1"]
        instance1.run()
        # Delete the database we just made
        instance2 = opendir_dl.commands.DatabaseCommand()
        instance2.config = self.config
        instance2.options["delete"] = "test1"
        instance2.run()

    def test_attempt_delete_default(self):
        instance = opendir_dl.commands.DatabaseCommand()
        instance.config = self.config
        instance.options["delete"] = "default"
        with self.assertRaises(ValueError) as context:
            instance.run()

    def test_attempt_bad_type(self):
        instance = opendir_dl.commands.DatabaseCommand()
        instance.config = self.config
        instance.options["type"] = "notavalidtype"
        instance.options["resource"] = "default"
        instance.values = ["test2"]
        with self.assertRaises(ValueError) as context:
            instance.run()
        expected_error = "Database type must be one of: url, filesystem, alias."
        self.assertEqual(str(context.exception), expected_error)

    def test_incomplete_alias(self):
        resource = "nonreal_database"
        expected_error = "Cannot create alias to database- no database named '%s'." % resource
        instance = opendir_dl.commands.DatabaseCommand()
        instance.config = self.config
        instance.options["type"] = "alias"
        instance.options["resource"] = resource
        instance.values = ["alias_name"]
        with self.assertRaises(ValueError) as context:
            instance.run()
        self.assertEqual(str(context.exception), expected_error)

class CommandSearchTest(TestWithConfig):
    def test_no_args(self):
        instance = opendir_dl.commands.SearchCommand()
        instance.config = self.config
        instance.options["db"] = "test_resources/test_sqlite3.db"
        instance.run()

class CommandDownloadTest(TestWithConfig):
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
            instance = opendir_dl.commands.DownloadCommand()
            instance.config = self.config
            instance.values = ["%stest_resources/test_sqlite3.db" % server.url]
            instance.run()
            # Make sure the file was actually downloaded
            self.assert_file_exists("test_sqlite3.db")
            # Make sure the two files are exactly the same
            self.assert_files_match("test_sqlite3.db", "test_resources/test_sqlite3.db")
            os.remove("test_sqlite3.db")

    def test_no_index(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            # Download the file
            instance = opendir_dl.commands.DownloadCommand()
            instance.config = self.config
            instance.values = ["%stest_resources/example_file.txt" % server.url]
            instance.flags = ['no-index']
            instance.run()
            # Make sure the file was actually downloaded
            self.assert_file_exists("example_file.txt")
            # Make sure the two files are exactly the same
            self.assert_files_match("example_file.txt", "test_resources/example_file.txt")
            os.remove("example_file.txt")
            # Check our database to make sure an index wasn't created
            db_wrapper = opendir_dl.databasing.DatabaseWrapper.from_default(self.config)
            search = opendir_dl.utils.SearchEngine(db_wrapper.db_conn, ["example_file.txt"])
            num_results = len(search.query())
            self.assertEqual(num_results, 0)

    def test_bad_status(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            # This references path test_resources/test_404_head.txt which does not exist (causing status 404)
            instance = opendir_dl.commands.DownloadCommand()
            instance.config = self.config
            instance.values = [13]
            instance.options["db"] = "%stest_resources/test_sqlite3.db" % server.url
            instance.run()
            # Make sure the file was not created
            self.assertFalse(os.path.exists("test_404_head.txt"))

    #def test_search(self):
    #    with ThreadedHTTPServer("localhost", 8000) as server:
    #        instance = opendir_dl.commands.DownloadCommand()
    #        instance.config = self.config
    #        instance.values = ["example_file"]
    #        instance.flags = ["search"]
    #        instance.options["db"] = "%stest_resources/test_sqlite3.db" % server.url
    #        instance.run()
    #        self.assertTrue(os.path.exists("example_file.txt"))
    #        os.remove("example_file.txt")
