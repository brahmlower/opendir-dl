import urllib
import tempfile
from datetime import datetime
import httplib2
from bs4 import BeautifulSoup
import sqlalchemy
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import DateTime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

MODELBASE = declarative_base()

class RemoteFile(MODELBASE):
    """This represents a remote file
    """
    __tablename__ = "remotefile"
    pkid = Column(Integer, primary_key=True)
    url = Column(String)
    name = Column(String)
    domain = Column(String)
    last_indexed = Column(DateTime)
    content_type = Column(String)
    last_modified = Column(DateTime)
    content_length = Column(Integer)

class PageCrawler(object):
    def __init__(self, db_conn, input_urls):
        """Prepare the PageCrawler

        Required initial values are a database connection to save file entries
        to as well as a list of URLs to search. This list can contain any
        number of URLs.
        """
        self.db_conn = db_conn
        self._quick = False
        self._triage_method = self.triage_standard
        self.reindex = None
        if not isinstance(input_urls, list):
            raise ValueError

        self.url_triage_bucket = input_urls
        self.index_urls = []
        self.file_heads = []

    @property
    def quick(self):
        """Wrapper around bool which sets the triage method

        Setting quick to True will also set the triage_method to triage_quick,
        thus changing the method we triage new URLs. That method results in
        fewer head requests, thus speading the indexing processs. Cool huh!!
        """
        return self._quick

    @quick.setter
    def quick(self, value):
        self._quick = value
        if self._quick:
            self._triage_method = self.triage_quick
        else:
            self._triage_method = self.triage_standard

    def crawl(self):
        """Watches the URL lists and delegates work to threads
        """
        while len(self.url_triage_bucket) + len(self.index_urls) + len(self.file_heads) > 0:
            self._triage_method()

            while len(self.index_urls) > 0:
                url = self.index_urls.pop(0)
                response = http_get(url)
                self.url_triage_bucket += parse_urls(url, response[1])

            self.save_heads()

    def triage_standard(self):
        """Handles the URLs that are dumpped into self.url_triage_bucket
        """
        while len(self.url_triage_bucket) > 0:
            # Continue popping URLs from the bucket until the bucket is empty
            url = self.url_triage_bucket.pop(0)
            # Get the head information about the URL. This will be necessary
            # for deciding what to do with the resource (crawl it/database it)
            head = HttpHead.from_url(url)
            if head.status != '200':
                continue
            if head.is_html() and not head.last_modified:
                # If the content type is "text/html", and does not have a
                # "last-modified" date, then it's a page we want to crawl. If
                # the page has a "last-modified" date, it is a static file
                # rather than one that was generated as part of the directory.
                # Append the url to the index_urls list for another method to
                # handle.
                self.index_urls.append(url)
            else:
                # The content type indicates it is some sort of file, so we
                # should add it to the database. Here we're attaching the URL
                # to the dictionary containing the head request data. The key
                # is prefixed with "oddl_" to prevent any collision with data
                # that may already be in the dictionary (unlikely, but just
                # in case)
                self.file_heads.append(head)

    def triage_quick(self):
        """Triages URLs without making HEAD requests
        """
        while len(self.url_triage_bucket) > 0:
            url = self.url_triage_bucket.pop(0)
            if url[-1] == "/":
                # We think this might be another directory index to look at
                self.index_urls.append(url)
            else:
                # This might be just a file, don't get any information about
                # it and just add the data we have about it to the file_heads
                head = HttpHead(url, {})
                self.file_heads.append(head)

    def save_heads(self):
        """Saves file entries that are queued up in self.file_heads

        This will remove each entry in file_heads and save it to the database.
        """
        while len(self.file_heads) > 0:
            # For each head entry, pop it from the list, clean the values
            # associated with it (domain/name/last_modified), and then make the
            # RemoteFile object.
            head = self.file_heads.pop(0)
            self.db_conn.add(head.as_remotefile())
            print "Found file: %s" % head.url
        # Now that the looping has finished, commit our new objects to the
        # database. TODO: Depending how how the database session works,
        # threading *might* cause a lot of problems here...
        self.db_conn.commit()

class DatabaseWrapper(object):
    default_db_path = 'sqlite3.db'

    def __init__(self, source=None):
        self.db_conn = None
        self.tempfile = None
        if source:
            self.source = source
        else:
            self.source = self.default_db_path

    def query(self, *args, **kwargs):
        # This is meant to be overwritten with a reference to
        # self.db_conn.query that way stuff can just call wrapper.query like
        # normal
        pass

    def is_connected(self):
        """True/False value for if the DatabaseWrapper instance is connected
        """
        return self.db_conn != None

    def connect(self):
        """ Establish the database session given the set values
        """
        database_engine = create_engine('sqlite:///%s' % self.source)
        MODELBASE.metadata.create_all(database_engine)
        MODELBASE.metadata.bind = database_engine
        database_session = sessionmaker(bind=database_engine)
        self.db_conn = database_session()
        setattr(self, 'query', self.db_conn.query)

    @classmethod
    def from_default(cls):
        """Get a default instance of DatabaseWrapper

        This would be used over `DatabaseWrapper()` because this returns an
        object where self.db_conn is already an established database session
        """
        dbw_inst = cls()
        dbw_inst.connect()
        return dbw_inst

    @classmethod
    def from_fs(cls, path):
        """ Gets a database session from a cache of a remote database

        This method will need additional sanitation on the `path` value.
        relative and absolute paths *should* work, but anything referecing `~`
        will need to be expanded first.
        """
        dbw_inst = cls(path)
        dbw_inst.connect()
        return dbw_inst

    @classmethod
    def from_data(cls, data):
        """Get an instance of DatabaseWrapper from the give raw data
        """
        dbw_inst = cls()
        dbw_inst.tempfile = tempfile.NamedTemporaryFile()
        dbw_inst.tempfile.write(data)
        dbw_inst.tempfile.flush()
        dbw_inst.source = dbw_inst.tempfile.name
        dbw_inst.connect()
        return dbw_inst

    @classmethod
    def from_url(cls, url):
        """ Gets a database session from a URL
        """
        http_session = httplib2.Http()
        http_request = http_session.request(url)
        return cls.from_data(http_request[1])

    @classmethod
    def from_unknown(cls, source_string=None):
        """Creates an instance of DatabaseWrapper given an unknown string
        """
        cache_list = [] # TODO: This is a placeholder until cached databases are implemented
        if not source_string:
            # This gets us the default configuration
            return cls.from_default()
        if source_string.startswith("http://"):
            # We were given a URL
            return cls.from_url(source_string)
        elif source_string in cache_list:
            # Load from a cache of remote db
            #return cls.from_cache(source_string)
            pass
        else:
            # We have a fs path
            return cls.from_fs(source_string)

class SearchEngine(object):
    def __init__(self, db_conn=None, search_terms=None):
        self.db_conn = db_conn
        self._exclusivity = sqlalchemy.and_
        self.filters = []
        if not search_terms:
            search_terms = []
        for i in search_terms:
            self.add_filter(i)

    @property
    def exclusive(self):
        return self._exclusivity == sqlalchemy.and_

    @exclusive.setter
    def exclusive(self, value):
        if value:
            self._exclusivity = sqlalchemy.and_
        else:
            self._exclusivity = sqlalchemy.or_

    def add_filter(self, value):
        self.filters.append(RemoteFile.name.like("%%%s%%" % value))

    def query(self, db_conn=None):
        # If the search engine wasn't provided a database, and the query wasn't
        # provided a database, then raise a ValueError. This is a programming
        # problem.
        if not db_conn and not self.db_conn:
            raise ValueError
        # The search engine had a database provided to it and query() wasn't
        # provided with a specific database connection, so we'll default to the
        # one the class was provided with.
        elif not db_conn:
            db_conn = self.db_conn

        results = self.db_conn.query(RemoteFile).filter(self._exclusivity(*self.filters))
        return results.all()

class HttpHead(object):
    def __init__(self, url, head_dict):
        self._last_modified = None
        self.url = url
        self.status = head_dict.get("status", 0)
        self.content_type = head_dict.get("content-type", '')
        self.content_length = head_dict.get("content-length", 0)
        self.last_modified = head_dict.get("last-modified", None)
        self.last_indexed = datetime.utcnow()

    @property
    def last_modified(self):
        return self._last_modified

    @last_modified.setter
    def last_modified(self, value):
        try:
            self._last_modified = datetime.strptime(value, \
                "%a, %d %b %Y %H:%M:%S GMT")
        except ValueError:
            self._last_modified = None
        except TypeError:
            self._last_modified = None

    def is_html(self):
        """Determines if resource is of type "text/html"
        The provided dict should be the HEAD of an http request. It is an html
        page if the HEAD contains the key "content-type" and that value starts
        with "text/html"
        """
        return self.content_type.startswith("text/html")

    def as_remotefile(self):
        file_entry = RemoteFile(url=self.url, domain=url_to_domain(self.url),
                                name=url_to_filename(self.url),
                                content_type=self.content_type,
                                content_length=self.content_length,
                                last_modified=self.last_modified,
                                last_indexed=self.last_indexed)
        return file_entry

    @classmethod
    def from_url(cls, url, http_session=httplib2.Http()):
        """Returns HEAD request data from the provided URL

        The dict is contains keys and values with data provided by the HEAD
        request response from the web server. The request is made using the
        provided http_session
        """
        response = http_session.request(url, 'HEAD')
        return cls(url, response[0])

class DownloadManager(object):
    def __init__(self, db_wrapper, download_ids):
        self.db_wrapper = db_wrapper
        self.download_ids = download_ids

    def download_url(self, url):
        filename = url_to_filename(url)
        # Download the file
        response = http_get(url)
        # Save the file
        write_file(filename, response[1])
        # Create an index entry for the file
        head = HttpHead(url, response[0])
        self.db_wrapper.db_conn.add(head.as_remotefile())
        self.db_wrapper.db_conn.commit()

    def download_id(self, pkid):
        query = self.db_wrapper.query(RemoteFile).get(int(pkid))
        self.download_url(query.url)

    def start(self):
        for item in self.download_ids:
            if is_url(item):
                self.download_url(item)
            elif isinstance(item, int) or item.isdigit():
                self.download_id(item)

def parse_urls(url, html):
    """Gets all useful urls on a page
    """
    print "Searching directory: %s" % url
    url_list = []
    # Parse the html we get from the site and then itterate over all 'a'
    # dom elements that have an href in them.
    soup = BeautifulSoup(html, "lxml")
    for anchor in soup.find_all('a', href=True):
        # Skip this anchor if it's one we should ignore
        if bad_anchor(anchor['href']):
            continue
        # build the full url and add it to the url bucket
        new_url = url + anchor['href']
        url_list.append(new_url)
    return url_list

def http_get(url, http_session=httplib2.Http()):
    """Returns GET request data from the provided URL
    """
    return http_session.request(url)

def bad_anchor(anchor):
    """Determines if the provided anchor is one we want to follow

    I know all the logic here can be compressed into a smaller expression,
    but it's saying expanded just to be more readable. This function will be
    improved eventually anyway.
    """
    static_anchors = ["../", "/", "?C=N;O=D", "?C=M;O=A", "?C=S;O=A",\
        "?C=D;O=A"]
    if anchor in static_anchors:
        return True
    if anchor[0] == "#":
        return True
    if anchor[0] == "/":
        return True
    return False

def url_to_domain(url):
    """Parses the domain name from the given URL
    """
    try:
        # Get the start of the domain name. If a value error is rasied
        # that means there is no protocole prefix and we should assume
        # the domain starts at the first character
        start = url.index("://") + 3
    except ValueError:
        start = 0
    try:
        # Find the end of the domain name. If we can't find the "/", that
        # likely means the url is provided without a URI specified, in
        # which case we should assume the end of the domain is the end
        # of the string
        end = url[start:].index("/") + start
    except ValueError:
        end = len(url)
    return url[start:end].split(":")[0]

def url_to_filename(url):
    """Parses the filename from the given URL
    """
    quoted_filename = url.split("/")[-1]
    filename = urllib.unquote(quoted_filename)
    if len(filename) == 0:
        filename = "index.html"
    return filename

def download_url(db_wrapper, url):
    filename = url_to_filename(url)
    # Download the file
    response = http_get(url)
    # Save the file
    write_file(filename, response[1])
    # Create an index entry for the file
    head = HttpHead(url, response[0])
    db_wrapper.db_conn.add(head.as_remotefile())
    db_wrapper.db_conn.commit()

def write_file(filename, data):
    wfile = open(filename, 'w')
    wfile.write(data)
    wfile.close()

def is_url(candidate):
    # A URL will start with either "http://" or "https://"
    if str(candidate).startswith("http://"):
        return True
    return str(candidate).startswith("https://")
