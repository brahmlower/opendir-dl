import os
import sys
import socket
import threading
import SocketServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
import httplib2
import unittest
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opendir_dl'))
import opendir_dl

class QuietSimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Produces no logging output

    I defined this just to keep the test output pretty
    """
    def log_message(self, *args):
        pass

class ThreadedHTTPServer(object):
    def __init__(self, host, port):
        SocketServer.TCPServer.allow_reuse_address = True
        self.server = SocketServer.TCPServer((host, port), QuietSimpleHTTPRequestHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.url = "http://%s:%d/" % (host, port)

    def start(self):
        self.server_thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

class TestWithConfig(unittest.TestCase):
    def __init__(self, methodName="runTest"):
        super(TestWithConfig, self).__init__(methodName)
        self.config = None
        self.setUp = self.set_up
        self.tearDown = self.tear_down
        self.template_database_path = self.get_path("test_sqlite3.db")
        self.database_path = self.get_path("test_1234_sqlite3.db")

    def get_path(self, filename):
        self_path = os.path.realpath(__file__)
        cur_dir = "/".join(self_path.split("/")[:-1])
        return "{}/test_resources/{}".format(cur_dir, filename)

    def create_database_instance(self):
        shutil.copy(self.template_database_path, self.database_path)

    def delete_database_instance(self):
        os.remove(self.database_path)

    def set_up(self):
        # Open the configuration
        config_path = opendir_dl.get_config_path("config.yml", "opendir-dl-test")
        self.config = opendir_dl.Configuration(config_path = config_path)
        self.create_database_instance()


    def tear_down(self):
        # Delete the test directory
        test_data_dir = os.path.abspath(os.path.join(self.config.config_path, os.pardir))
        shutil.rmtree(test_data_dir)
        self.delete_database_instance()
