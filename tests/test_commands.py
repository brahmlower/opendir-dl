import os
import unittest
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

class TestCommandSearch(unittest.TestCase):
    def test_no_args(self):
        opendir_dl.commands.search([], [], {"db": "test_resources/sqlite3.db"})

class TestCommandDownload(unittest.TestCase):
    def test_no_args(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            opendir_dl.commands.download(["%stest_resources/sqlite3.db" % server.url], [], {})
            os.remove("sqlite3.db")
        finally:
            server.stop()

    def test_search(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            opendir_dl.commands.download(["example_file"], ["search"], {"db": "%stest_resources/sqlite3.db" % server.url})
            os.remove("example_file.txt")
        finally:
            server.stop()
