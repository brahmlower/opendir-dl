import os
import errno
import urllib
import tempfile
import urlparse
import datetime
import httplib2
import appdirs
from bs4 import BeautifulSoup
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from opendir_dl.models import MODELBASE
from opendir_dl.models import FileIndex

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
        self.url_triage_bucket = []
        self.index_urls = []
        self.file_heads = []

        self.clean_index_items(input_urls)

    def clean_index_items(self, url_ids):
        for item in url_ids:
            if is_url(item):
                self.url_triage_bucket.append(item)
            elif isinstance(item, int) or item.isdigit():
                index_entry = self.db_conn.query(FileIndex).get(int(item))
                self.url_triage_bucket.append(index_entry.url)

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
            if head.status != 200:
                # TODO: Write a test that triggers this
                print "Index failed (HTTP Error %d) URL: %s" % (head.status, url)
                continue
            if head.is_html() and not head.last_modified:
                # If the content type is "text/html", and does not have a
                # "last-modified" date, then it's a page we want to crawl.
                self.index_urls.append(url)
            else:
                # The content type indicates it is some sort of file, so we
                # should add it to the index database.
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
            # FileIndex object.
            head = self.file_heads.pop(0)
            save_head(self.db_conn, head.as_fileindex(), commit=False)
            print "Found file: %s" % head.url
        # Now that the looping has finished, commit our new objects to the
        # database.
        # TODO: Depending how how the database session works, threading *might*
        # cause a lot of problems here...
        self.db_conn.commit()

class DatabaseWrapper(object):
    default_db = 'default.db'

    def __init__(self, source):
        if not os.path.exists(appdirs.user_data_dir('opendir-dl')):
            #os.mkdir(appdirs.user_data_dir('opendir-dl'))
            mkdir_p(appdirs.user_data_dir('opendir-dl'))
        self.db_conn = None
        self.tempfile = None
        self.source = source

    def query(self, *args, **kwargs):
        # This is meant to be overwritten with a reference to
        # self.db_conn.query that way stuff can just call wrapper.query like
        # normal. This is overwritten with the reference to db_conn.query
        # when the database is connected
        pass

    def is_connected(self):
        """True/False value for if the DatabaseWrapper instance is connected
        """
        return self.db_conn != None

    def connect(self):
        """ Establish the database session given the set values
        """
        database_engine = sqlalchemy.create_engine('sqlite:///%s' % self.source)
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
        source = "%s/%s" % (appdirs.user_data_dir('opendir-dl'), cls.default_db)
        dbw_inst = cls(source)
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
        temp_file = tempfile.NamedTemporaryFile()
        dbw_inst = cls(temp_file.name)
        dbw_inst.tempfile = temp_file
        dbw_inst.tempfile.write(data)
        dbw_inst.tempfile.flush()
        dbw_inst.connect()
        return dbw_inst

    @classmethod
    def from_url(cls, url):
        """ Gets a database session from a URL
        """
        response = http_get(url)
        if response[0]['status'] == '200':
            return cls.from_data(response[1])
        else:
            message = "HTTP GET request failed with error '%s'. Expected '200'." \
                    % response[0]['status']
            raise ValueError(message)

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
        if search_terms != None:
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
        self.filters.append(FileIndex.name.like("%%%s%%" % value))

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

        results = db_conn.query(FileIndex).filter(self._exclusivity(*self.filters))
        return results.all()

class HttpHead(object):
    def __init__(self, url, head_dict):
        self._last_modified = None
        parsed_url = urlparse.urlparse(url)
        self.url = unicode(url)
        self.name = url_to_filename(self.url)
        self.domain = unicode(parsed_url.hostname)
        self.status = int(head_dict.get("status", 0))
        self.content_type = unicode(head_dict.get("content-type", ''))
        self.content_length = int(head_dict.get("content-length", 0))
        self.last_modified = head_dict.get("last-modified", None)
        self.last_indexed = datetime.datetime.utcnow()

    @property
    def last_modified(self):
        return self._last_modified

    @last_modified.setter
    def last_modified(self, value):
        try:
            self._last_modified = datetime.datetime.strptime(value, \
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

    def as_fileindex(self):
        file_entry = FileIndex(url=self.url, domain=self.domain,
                               name=self.name, content_type=self.content_type,
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
    def __init__(self, db_wrapper, download_ids, no_index=False):
        self.db_wrapper = db_wrapper
        self.queue = download_ids
        self.no_index = no_index

    def download_url(self, url):
        # TODO: *BUG* This will make a new file even if the query status is not 200
        filename = url_to_filename(url)
        # Download the file
        response = http_get(url)
        # Save the file
        write_file(filename, response[1])
        # Create an index entry for the file
        if not self.no_index:
            head = HttpHead(url, response[0])
            save_head(self.db_wrapper.db_conn, head.as_fileindex())

    def download_id(self, pkid):
        query = self.db_wrapper.query(FileIndex).get(int(pkid))
        self.download_url(query.url)

    def start(self):
        for item in self.queue:
            if is_url(item):
                self.download_url(item)
            elif isinstance(item, int) or item.isdigit():
                self.download_id(item)

def save_head(db_conn, head, commit=True):
    """Saves FileIndex object to database

    Will save the give FileIndex object (head) to the database referenced by
    session db_conn. This checks to make sure the entry does not already exist
    to prevent duplicate entries. If an existing record exists, it will be
    updated.
    """
    filters = []
    filters.append(FileIndex.name.like("%%%s%%" % head.name))
    filters.append(FileIndex.url.like("%%%s%%" % head.url))
    results = db_conn.query(FileIndex).filter(sqlalchemy.and_(*filters))
    if results.count() < 1:
        # This entry hasn't been seen before. Save the new entry
        db_conn.add(head)
    elif results.count() == 1:
        # The entry already exists, update the records
        old_head = results.first()
        old_head.content_type = head.content_type
        old_head.content_length = head.content_length
        old_head.last_modified = head.last_modified
        old_head.last_indexed = head.last_indexed
        # TODO: The following line should only print when verbose = True
        # print 'Updating pre-existing index'
    else:
        # There are multiple entries
        print "There were multiple entires (this is bad). URL index not saved."
    if commit:
        db_conn.commit()

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

def url_to_filename(url):
    """Parses the filename from the given URL
    """
    if not isinstance(url, urlparse.ParseResult):
        url = urlparse.urlparse(url)
    quoted_filename = url.path.split("/")[-1]
    filename = urllib.unquote(quoted_filename)
    if len(filename) == 0:
        filename = "index.html"
    return filename

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if not (exc.errno == errno.EEXIST and os.path.isdir(path)):
            raise

def write_file(filename, data):
    wfile = open(filename, 'w')
    wfile.write(data)
    wfile.close()

def is_url(candidate):
    try:
        url = urlparse.urlparse(candidate)
        return url.path != '' and url.scheme != '' and url.netloc != ''
    except AttributeError:
        return False
