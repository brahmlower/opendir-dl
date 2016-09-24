#!/usr/bin/python
import urllib
import datetime
import httplib2
from sqlalchemy import or_
from sqlalchemy import and_
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import DateTime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from bs4 import BeautifulSoup

ModelBase = declarative_base()

def create_database_connection(database_path=''):
    """Returns a database session for the specified database"""
    database_engine = create_engine('sqlite:///' + database_path)
    ModelBase.metadata.create_all(database_engine)
    ModelBase.metadata.bind = database_engine
    database_session = sessionmaker(bind=database_engine)
    return database_session()

def url_to_domain(url):
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
    content_length = head_response['content-length']
    content_type = head_response['content-type']
    last_modified = datetime.datetime.strptime(head_response['last-modified'], "%a, %d %b %Y %H:%M:%S GMT")
    return RemoteFile( \
        url = url,
        domain = domain, \
        name = file_name, \
        content_type = content_type, \
        content_length = content_length, \
        last_modified = last_modified, \
        last_indexed = datetime.datetime.utcnow())

def get_url_head(http_session, url):
    head_response = http_session.request(url, 'HEAD')
    return head_response[0]

class RemoteFile(ModelBase):
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

def crawl_page(db_conn, target_url, rec_depth = 50):
    print "Crawling page: %s" % target_url
    domain = url_to_domain(target_url)
    http_session = httplib2.Http()
    html = http_session.request(target_url)[1]
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all('a', href=True):
        url = target_url + a['href']
        url_head = get_url_head(http_session, url)
        if url_head["content-type"].startswith("text/html"):
            # This is an html page, and should be crawled, not indexed
            crawl_page(db_conn, url, rec_depth - 1)
        else:
            file_name = urllib.unquote(a['href'])
            url_entry = create_remotefile(domain, url, file_name, url_head)
            db_conn.add(url_entry)

def index(input_url, input_flags):
    print "flags:", input_flags
    db_conn = create_database_connection("sqlite3.db")
    crawl_page(db_conn, input_url)
    db_conn.commit()

def search(input_terms, input_flags):
    search_property = "name"
    if "urlsearch" in input_flags:
        search_property = "url"

    exclusive = True
    if "inclusive" in input_flags:
        exclusive = False

    db_conn = create_database_connection("sqlite3.db")
    filters = []
    for i in input_terms:
        filters.append(getattr(RemoteFile, search_property).like("%%%s%%" % i))
    if exclusive:
        results = db_conn.query(RemoteFile).filter(and_(*filters))
    else:
        results = db_conn.query(RemoteFile).filter(or_(*filters))
    for i in results.all():
        print i.name, i.url