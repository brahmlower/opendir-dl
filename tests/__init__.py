import socket
import threading
import SocketServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
import httplib2

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
