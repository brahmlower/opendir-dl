import unittest
import opendir_dl
from . import ThreadedHTTPServer

class TestCommandHelp(unittest.TestCase):
    def test_no_args(self):
        opendir_dl.commands.command_help()

class TestCommandIndex(unittest.TestCase):
    def test_no_args(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            url = "http://localhost:8000/"
            opendir_dl.commands.command_index(["http://localhost:8000/"], [], {})
        finally:
            server.stop()

class TestCommandSearch(unittest.TestCase):
    def test_no_args(self):
        opendir_dl.commands.command_search([], [], {"db": "tests/test_from_data.dat"})

class TestCommandDownload(unittest.TestCase):
    def test_no_args(self):
        server = ThreadedHTTPServer("localhost", 8000)
        server.start()
        try:
            url = "http://localhost:8000/"
            opendir_dl.commands.command_index(["http://localhost:8000/tests/test_from_date.dat"], [], {})
        finally:
            server.stop()