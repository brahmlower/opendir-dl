from sqlalchemy import or_
from sqlalchemy import and_
from opendir_dl.utils import create_database_connection
from opendir_dl.utils import RemoteFile
from opendir_dl.utils import PageCrawler
from prettytable import PrettyTable

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
    crawler = PageCrawler(db_conn, input_values)
    crawler.quick = "quick" in input_flags
    crawler.reindex = input_options.get("reindex", None)
    crawler.crawl()

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
    output_table = PrettyTable(['ID','Name','URL'])
    output_table.padding_width = 1
    for i in results.all():
        output_table.add_row([i.pkid, i.name, i.url])
    print output_table
