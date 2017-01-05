import os
from time import sleep
import errno
import urllib
import urlparse
import datetime
import Queue
import socket
from threading import Thread
from threading import Lock
import httplib2
import appdirs
import sqlalchemy
from bs4 import BeautifulSoup
from prettytable import PrettyTable
from opendir_dl.models import FileIndex

class PageCrawler(object):
    def __init__(self, db_conn, url_targets=None):
        """Prepare the PageCrawler

        Required initial values are a database connection to save file entries
        to as well as a list of URLs to search. This list can contain any
        number of URLs.
        """
        self.db_conn = db_conn
        # Values for triage method
        self._triage_quick = False
        self._triage_method = self.triage_standard
        # FileIndex creation values
        self._fileindex_creator_thread = None
        self._fileindex_heads = Queue.Queue()
        # PageScrapper values
        self.scraper_threads_max = 5
        self._scraper_threads = []
        self._urls_to_scrape = Queue.Queue()
        # Thread exit is used to break all the threads out of their loop
        self._thread_exit = False
        # Thread idle is used to determine when to stop the control loop. When
        # all the threads are idle, and self._urls_to_scrape is empty, then we
        # are out of work to do, and should finish execution.
        self._thread_idle_lock = Lock()
        self._thread_idle = []
        # Adds any provided url targets to a list to be triaged at once the
        # scraper is started
        if url_targets:
            self.url_targets = url_targets

    @property
    def quick(self):
        """Wrapper around boolean which sets the triage method

        Setting quick to True will also set the triage_method to triage_quick,
        thus changing the method we triage new URLs. That method results in
        fewer head requests, thus speading the indexing processs. Cool huh!!
        """
        return self._triage_quick

    @quick.setter
    def quick(self, value):
        self._triage_quick = value
        if self._triage_quick:
            self._triage_method = self.triage_quick
        else:
            self._triage_method = self.triage_standard

    def add_index_targets(self, index_targets):
        for item in index_targets:
            if is_url(item):
                self._triage_method(item)
            elif isinstance(item, int) or item.isdigit():
                index_entry = self.db_conn.query(FileIndex).get(int(item))
                self._triage_method(index_entry.url)

    def fileindex_creator(self):
        # Pull head objects from the queue and save them. Continue until the
        # thread exit flag is set, at which poit
        while not self._thread_exit:
            try:
                head = self._fileindex_heads.get(timeout=.1)
                save_head(self.db_conn, head.as_fileindex())
            except Queue.Empty:
                pass

    def set_idle_status(self, thread_id, status):
        # This is used to set the idle status of threads. This handles the lock
        # acquisition process safely
        self._thread_idle_lock.acquire()
        self._thread_idle[thread_id] = status
        self._thread_idle_lock.release()

    def page_scraper(self, thread_num):
        http_session = httplib2.Http(disable_ssl_certificate_validation=True)
        while not self._thread_exit:
            try:
                target_url = self._urls_to_scrape.get(timeout=.1)
                print "Thread {} got url {}".format(thread_num, target_url)
                # Indicate to the controller that this thread is not idle
                self.set_idle_status(thread_num, False)
                response = http_session.request(target_url)
                new_urls = parse_urls(target_url, response[1])
                for i, e in enumerate(new_urls):
                    if not self._thread_exit:
                        print "Thread {} triaging new url {} of {}.".format(thread_num, i+1, len(new_urls))
                        self._triage_method(e, http_session=http_session)
                    else:
                        break
                self.set_idle_status(thread_num, True)
            except Queue.Empty:
                pass
            except:
                self.set_idle_status(thread_num, True)
                raise

    def run(self):
        """Watches the URL lists and delegates work to threads
        """
        # Triage any initial targets we were giving upon instantiation
        self.add_index_targets(self.url_targets)
        # Start the head saving thread
        self._fileindex_creator_thread = Thread(target=self.fileindex_creator)
        self._fileindex_creator_thread.start()
        # Create all of the threads for scraping pages
        for i in range(self.scraper_threads_max):
            # Here len(self._scraper_threads) is being used to create the ID for
            # the thread that's being created. This thread ID is used to track
            # the position within self._thread_idle, where the thread will update
            # its idle status.
            new_thread_id = len(self._scraper_threads)
            scraper_thread = Thread(target=self.page_scraper, args=(new_thread_id,))
            self._scraper_threads.append(scraper_thread)
            self._thread_idle_lock.acquire()
            self._thread_idle.append(True)
            self._thread_idle_lock.release()
            scraper_thread.start()

        try:
            while sum(self._thread_idle) != self.scraper_threads_max:
                print 'idle: ' + str(self._thread_idle)
                sleep(1)
        except KeyboardInterrupt:
            print "\nWaiting for threads to exit gracefully..."
            self._thread_exit = True

        self._thread_exit = True
        # Join with all the scraper threads
        for i in self._scraper_threads:
            i.join()
        # Wait for the fileindex creator thread to finish
        self._fileindex_creator_thread.join()

    def triage_standard(self, url, http_session=None):
        """Handles the URLs that are dumped into self.url_triage_bucket
        """
        # Get the head information about the URL. This will be necessary
        # for deciding what to do with the resource (crawl it/database it)
        head = HttpHead.from_url(url, http_session)
        if head.status != 200:
            # TODO: Write a test that triggers this
            print "Index failed (HTTP Error %d) URL: %s" % (head.status, url)
        elif head.is_html() and not head.last_modified:
            # If the content type is "text/html", and does not have a
            # "last-modified" date, then it's a page we want to crawl.
            self._urls_to_scrape.put(url)
        else:
            # The content type indicates it is some sort of file, so we
            # should add it to the index database.
            self._fileindex_heads.put(head)

    def triage_quick(self, url, **kwargs):
        """Triages URLs without making HEAD requests
        """
        if url[-1] == "/":
            # We think this might be another directory index to look at
            self._urls_to_scrape.put(url)
        else:
            # This might be just a file, don't get any information about
            # it and just add the data we have about it to the file_heads
            head = HttpHead(url, {})
            self._fileindex_heads.put(head)

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
    def from_url(cls, url, http_session=None):
        """Returns HEAD request data from the provided URL

        The dict is contains keys and values with data provided by the HEAD
        request response from the web server. The request is made using the
        provided http_session
        """
        if not http_session:
            http_session = httplib2.Http(disable_ssl_certificate_validation=True)
        response = None
        while not response:
            try:
                response = http_session.request(url, 'HEAD')
            except socket.error:
                print "Error establishing connection with url: {}".format(url)
        return cls(url, response[0])

class DownloadManager(object):
    def __init__(self, db_wrapper, download_ids, no_index=False):
        self.db_wrapper = db_wrapper
        self.queue = download_ids
        self.no_index = no_index

    def download_url(self, url):
        filename = url_to_filename(url)
        # Download the file
        http_session = httplib2.Http(disable_ssl_certificate_validation=True)
        response = http_session.request(url)
        head = HttpHead(url, response[0])
        if head.status != 200:
            print "Failed to download file (HTTP Status %d): %s" % (head.status, url)
            return
        # Save the file
        write_file(filename, response[1])
        # Create an index entry for the file
        if not self.no_index:
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

    Will save the given FileIndex object (head) to the database referenced by
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
        print "URL: {}\nNumber of results: {}".format(head.url, results.count())
        print "\nResults:"
        for i in results:
            print i.name, i.url
        return
    if commit:
        db_conn.commit()

def parse_urls(url, html):
    """Gets all useful urls on a page
    """
    #print "Searching directory: %s" % url
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

def http_get(url, http_session=None):
    """Returns GET request data from the provided URL
    """
    if not http_session:
        http_session = httplib2.Http(disable_ssl_certificate_validation=True)
    return http_session.request(url)

def bad_anchor(anchor):
    """Determines if the provided anchor is one we want to follow

    TODO: Add configurables here, so people can add their own expressions
    to filter out.
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
    with open(filename, 'w') as wfile:
        wfile.write(data)
        wfile.close()

def is_url(candidate):
    try:
        url = urlparse.urlparse(candidate)
        return url.path != '' and url.scheme != '' and url.netloc != ''
    except AttributeError:
        return False

def create_table(data, columns=None):
    if isinstance(data, sqlalchemy.engine.ResultProxy):
        output_table = PrettyTable(data.keys())
        for row in data:
            output_table.add_row(row)
    else:
        output_table = PrettyTable(columns)
        for i in data:
            output_table.add_row([i.pkid, i.name, i.last_indexed, format_tags(i.tags)])
    output_table.padding_width = 1
    output_table.align = 'l'
    return output_table.get_string()

def format_tags(tags_list):
    clean_list = []
    for i in tags_list:
        clean_list.append(i.name)
    if clean_list == []:
        return ''
    else:
        return " ".join(clean_list)

def get_config_path(file_name, project_name="opendir-dl"):
    return os.path.join(appdirs.user_data_dir(project_name), file_name)
