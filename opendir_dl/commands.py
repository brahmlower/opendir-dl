import os
from prettytable import PrettyTable
from opendir_dl.utils import DatabaseWrapper
from opendir_dl.utils import RemoteFile
from opendir_dl.utils import SearchEngine
from opendir_dl.utils import PageCrawler
from opendir_dl.utils import DownloadManager
from opendir_dl.utils import is_url

def command_help(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl help` is called
    """
    self_path = os.path.realpath(__file__)
    cur_dir = "/".join(self_path.split("/")[:-1])
    rfile = open(cur_dir + "/help.txt", 'r')
    print rfile.read()
    rfile.close()

def command_index(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl index` is called
    """
    db_wrapper = DatabaseWrapper.from_default()
    crawler = PageCrawler(db_wrapper.db_conn, input_values)
    crawler.quick = "quick" in input_flags
    crawler.reindex = input_options.get("reindex", None)
    crawler.crawl()

def command_search(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl search` is called
    """
    db_wrapper = DatabaseWrapper.from_unknown(input_options.get('db', None))

    # Define our search engine and configure it per the provided parameters
    search = SearchEngine(db_wrapper.db_conn, input_values)
    search.exclusive = "inclusive" not in input_flags
    # This is all output related stuff
    output_table = PrettyTable(['ID', 'Name', 'URL'])
    output_table.padding_width = 1
    output_table.align = 'l'
    for i in search.query():
        output_table.add_row([i.pkid, i.name, i.url])
    print output_table

def command_download(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl download` is called
    """
    db_wrapper = DatabaseWrapper.from_unknown(input_options.get('db', None))

    # This is a really hacky way of implementing the --search flag
    if "search" in input_flags:
        search = SearchEngine(db_wrapper.db_conn, input_values)
        search.exclusive = "inclusive" not in input_flags
        input_values = []
        for i in search.query():
            input_values.append(i.pkid)

    dlman = DownloadManager(db_wrapper, input_values)
    dlman.start()
