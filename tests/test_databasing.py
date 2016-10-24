import os
import sys
import unittest
import appdirs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opendir_dl'))
import opendir_dl
from . import ThreadedHTTPServer

class DatabaseWrapperTest(unittest.TestCase):
    def test_provided_source(self):
        db = opendir_dl.databasing.DatabaseWrapper("sqlite3.db")
        self.assertEquals(db.source, "sqlite3.db")
        db.connect()
        self.assertTrue(db.is_connected())
        self.assertEquals(str(db.db_conn.bind.url), 'sqlite:///sqlite3.db')

    def test_memory_source(self):
        db = opendir_dl.databasing.DatabaseWrapper('')
        self.assertEquals(db.source, '')
        db.connect()
        self.assertTrue(db.is_connected())
        self.assertEquals(str(db.db_conn.bind.url), 'sqlite:///')

    def test_query_reassignment(self):
        db = opendir_dl.databasing.DatabaseWrapper('')
        db.connect()
        self.assertTrue(db.is_connected())
        self.assertEquals(db.db_conn.query, db.query)

    def test_from_default(self):
        db = opendir_dl.databasing.DatabaseWrapper.from_default()
        self.assertTrue(db.is_connected())
        db_path = appdirs.user_data_dir('opendir-dl') + "/default.db"
        self.assertEquals(str(db.db_conn.bind.url), 'sqlite:///%s' % db_path)

    def test_from_data(self):
        # TODO: Automatically count the entries in the database, that way I don't have to update these tests EVERY TIME I UPDATE THE DATABASE
        self_path = os.path.realpath(__file__)
        cur_dir = "/".join(self_path.split("/")[:-1])
        with open(cur_dir + '/test_resources/test_sqlite3.db', 'rb') as rfile:
            data = rfile.read()
        db = opendir_dl.databasing.DatabaseWrapper.from_data(data)
        self.assertTrue(db.is_connected())
        self.assertEquals(db.query(opendir_dl.models.FileIndex).count(), 14)

    def test_from_fs(self):
        self_path = os.path.realpath(__file__)
        cur_dir = "/".join(self_path.split("/")[:-1])
        db_path = cur_dir + '/test_resources/test_sqlite3.db'
        db = opendir_dl.databasing.DatabaseWrapper.from_fs(db_path)
        self.assertTrue(db.is_connected())
        self.assertEquals(db.query(opendir_dl.models.FileIndex).count(), 14)

    def test_from_url(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            url = "%stest_resources/test_sqlite3.db" % server.url
            db = opendir_dl.databasing.DatabaseWrapper.from_url(url)
        self.assertTrue(db.is_connected())
        self.assertEquals(db.query(opendir_dl.models.FileIndex).count(), 14)

    def test_from_404_url(self):
        expected_error = "HTTP GET request failed with error '404'. Expected '200'."
        with self.assertRaises(ValueError) as context:
            with ThreadedHTTPServer("localhost", 8000) as server:
                url = "%stest_resources/test_missing_sqlite3.db" % server.url
                db = opendir_dl.databasing.DatabaseWrapper.from_url(url)
        self.assertEqual(str(context.exception), expected_error)

class DatabaseOpenerTest(unittest.TestCase):
    def test_provided_none(self):
        db_wrapper = opendir_dl.databasing.database_opener()
        self.assertTrue(db_wrapper.is_connected())

    def test_provided_url(self):
        with ThreadedHTTPServer("localhost", 8000) as server:
            db_url = "http://localhost:8000/test_resources/test_sqlite3.db"
            db_wrapper = opendir_dl.databasing.database_opener(db_url)
        self.assertTrue(db_wrapper.is_connected())

    def test_provided_filesystem(self):
        db_path = "test_resources/test_sqlite3.db"
        db_wrapper = opendir_dl.databasing.database_opener(db_path)
        self.assertTrue(db_wrapper.is_connected())

    def test_provided_named_db(self):
        db_name = "secondary"
        instance = opendir_dl.commands.DatabaseCommand()
        instance.values = [db_name]
        instance.run()
        db_wrapper = opendir_dl.databasing.database_opener(db_name)
        self.assertTrue(db_wrapper.is_connected())
        #opendir_dl.commands.DatabaseCommand([db_name], [], {"delete": db_name})

    def tests_not_matching(self):
        provided_string = "abc_doesnt-match a database"
        with self.assertRaises(ValueError) as context:
            opendir_dl.databasing.database_opener(provided_string)
