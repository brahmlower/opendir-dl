from sqlalchemy import or_
from sqlalchemy import and_
from opendir_dl.utils import create_database_connection
from opendir_dl.utils import crawl_page
from opendir_dl.utils import RemoteFile

def command_help(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl help` is called
    """
    print "opendir-dl [command] (options) [value]"
    print "Example: opendir-dl index http://localhost:8000/"
    print "Example: opendir-dl search --inclusive png jpg"

def command_index(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl index` is called
    """
    db_conn = create_database_connection("sqlite3.db")
    for url in input_values:
        crawl_page(db_conn, url)
    db_conn.commit()

def command_search(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl search` is called
    """
    search_property = "name"
    if "urlsearch" in input_flags:
        search_property = "url"

    exclusive = True
    if "inclusive" in input_flags:
        exclusive = False

    db_conn = create_database_connection("sqlite3.db")
    filters = []
    for i in input_values:
        filters.append(getattr(RemoteFile, search_property).like("%%%s%%" % i))
    if exclusive:
        results = db_conn.query(RemoteFile).filter(and_(*filters))
    else:
        results = db_conn.query(RemoteFile).filter(or_(*filters))
    for i in results.all():
        print i.name, i.url
