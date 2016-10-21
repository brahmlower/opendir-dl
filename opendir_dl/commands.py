import os
import yaml
import appdirs
from prettytable import PrettyTable
from opendir_dl.databasing import database_opener
from opendir_dl.utils import SearchEngine
from opendir_dl.utils import PageCrawler
from opendir_dl.utils import DownloadManager

def help(*args):#input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl help` is called
    """
    self_path = os.path.realpath(__file__)
    cur_dir = "/".join(self_path.split("/")[:-1])
    rfile = open(cur_dir + "/help.txt", 'r')
    print rfile.read()
    rfile.close()

def database(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl db` is called
    """
    config_path = appdirs.user_data_dir('opendir-dl') + "/config.yml"
    config_stream = open(config_path, 'r')
    config = yaml.load(config_stream)
    config_stream.close()

    if "delete" in input_options.keys():
        target = input_options['delete']
        if target == "default":
            raise ValueError("Invalid database name- cannot delete default database.")
        if target not in config['databases'].keys():
            raise ValueError("Invalid database name- no database exists with that name.")
        config['databases'].pop(target, None)
        wfile = open(config_path, 'w')
        yaml.dump(config, wfile, default_flow_style=False)
        wfile.close()
        return

    if len(input_values) > 0:
        # We're creating a new database
        config_stream = open(config_path, 'r+')
        config = yaml.load(config_stream)
        disallowed_db_names = ['default']
        db_name = input_values[0]
        # Validate the name for the new database
        if db_name in disallowed_db_names:
            raise ValueError("Invalid database name- cannot be in disallowed database name list.")
        if len(db_name.split()) > 1:
            raise ValueError("Invalid database name- cannot contain whitespace.")
        if db_name in config['databases'].keys():
            raise ValueError("Invalid database name- database with that name already exists.")
        # Set the database type and resource
        if 'type' in input_options.keys() and 'resource' not in input_options.keys():
            # If we're specifying the type, we *must* specify the resource
            raise ValueError("Must provide resource when specifying a database type")
        db_type = input_options.get('type', 'filesystem')
        if db_type not in ['filesystem', 'url', 'alias']:
            raise ValueError("Database type must be one of: url, filesystem, alias")
        db_resource = input_options.get('resource', db_name + ".db")
        if db_type == "alias" and db_resource not in config['databases'].keys():
            raise ValueError("Cannot create alias to database- no database named '%s'." % db_resource)
        # Save the new configuration
        config['databases'][db_name] = {'type': db_type, 'resource': db_resource}
        wfile = open(config_path, 'w')
        yaml.dump(config, wfile, default_flow_style=False)
        wfile.close()
        return

    config_stream = open(config_path)
    config = yaml.load(config_stream)
    output_table = PrettyTable(['Name', 'Type', 'Resource'])
    output_table.padding_width = 1
    output_table.align = 'l'
    for i in config['databases']:
        output_table.add_row([i, config['databases'][i]['type'], config['databases'][i]['resource']])
    print output_table

def index(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl index` is called
    """
    #db_wrapper = DatabaseWrapper.from_unknown(input_options.get('db', None))
    db_wrapper = database_opener(input_options.get('db', None))

    crawler = PageCrawler(db_wrapper.db_conn, input_values)
    crawler.quick = "quick" in input_flags
    crawler.reindex = input_options.get("reindex", None)
    crawler.crawl()

def search(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl search` is called
    """
    db_wrapper = database_opener(input_options.get('db', None))

    # Define our search engine and configure it per the provided parameters
    search = SearchEngine(db_wrapper.db_conn, input_values)
    search.exclusive = "inclusive" not in input_flags
    # This is all output related stuff
    output_table = PrettyTable(['ID', 'Name', 'URL', 'Last Indexed'])
    output_table.padding_width = 1
    output_table.align = 'l'
    for i in search.query():
        output_table.add_row([i.pkid, i.name, i.url, i.last_indexed])
    print output_table

def download(input_values, input_flags, input_options): #pylint: disable=unused-argument
    """Function run when `opendir-dl download` is called
    """
    db_wrapper = database_opener(input_options.get('db', None))

    # This is a really hacky way of implementing the --search flag
    if "search" in input_flags:
        search = SearchEngine(db_wrapper.db_conn, input_values)
        search.exclusive = "inclusive" not in input_flags
        input_values = []
        for i in search.query():
            input_values.append(i.pkid)

    dlman = DownloadManager(db_wrapper, input_values)
    dlman.no_index = "no-index" in input_flags
    dlman.start()
