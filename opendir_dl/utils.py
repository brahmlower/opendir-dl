import urllib
import datetime
import httplib2
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import DateTime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from bs4 import BeautifulSoup

MODELBASE = declarative_base()

def create_database_connection(database_path=''):
    """Returns a database session for the specified database
    """
    database_engine = create_engine('sqlite:///' + database_path)
    MODELBASE.metadata.create_all(database_engine)
    MODELBASE.metadata.bind = database_engine
    database_session = sessionmaker(bind=database_engine)
    return database_session()

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
    return url[start:end]

def create_remotefile(domain, url, file_name, head_response):
    """ Creates an instance of RemoteFile based on the provided data
    """
    content_length = head_response['content-length']
    content_type = head_response['content-type']
    last_modified = datetime.datetime.strptime(head_response['last-modified'], \
        "%a, %d %b %Y %H:%M:%S GMT")
    return RemoteFile( \
        url=url,
        domain=domain, \
        name=file_name, \
        content_type=content_type, \
        content_length=content_length, \
        last_modified=last_modified, \
        last_indexed=datetime.datetime.utcnow())

def get_url_head(http_session, url):
    """Returns HEAD request data from the provided URL

    The dict is contains keys and values with data provided by the HEAD request
    response from the web server. The request is made using the provided
    http_session
    """
    head_response = http_session.request(url, 'HEAD')
    return head_response[0]

class RemoteFile(MODELBASE):
    """This represents a remote file
    """
    __tablename__ = "remotefile"
    pkid = Column(Integer, primary_key=True)
    domain = Column(String)
    last_indexed = Column(DateTime)
    name = Column(String)
    url = Column(String)
    content_type = Column(String)
    content_length = Column(Integer)
    last_modified = Column(DateTime)

def crawl_page(db_conn, target_url, rec_depth=50):
    """Recursive page crawling function

    This page will look for all href tags in html anchors, and create RemoteFile
    object for any none text/html resources it finds. By default it has a
    maximum depth of 50 instances, but this is not enforced (at this time).
    """
    print "Crawling page: %s" % target_url
    domain = url_to_domain(target_url)
    http_session = httplib2.Http()
    html = http_session.request(target_url)[1]
    soup = BeautifulSoup(html, "lxml")
    for anchor in soup.find_all('a', href=True):
        url = target_url + anchor['href']
        url_head = get_url_head(http_session, url)
        if url_head["content-type"].startswith("text/html"):
            # This is an html page, and should be crawled, not indexed
            crawl_page(db_conn, url, rec_depth - 1)
        else:
            file_name = urllib.unquote(anchor['href'])
            url_entry = create_remotefile(domain, url, file_name, url_head)
            db_conn.add(url_entry)
