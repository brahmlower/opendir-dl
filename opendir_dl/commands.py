import os
import yaml
import appdirs
from prettytable import PrettyTable
from opendir_dl.databasing import database_opener
from opendir_dl.utils import SearchEngine
from opendir_dl.utils import PageCrawler
from opendir_dl.utils import DownloadManager
from opendir_dl.utils import create_table

class BaseCommand(object):
    def __init__(self):
        self.config = None
        self.options = {}
        self.flags = []
        self.values = []
        self.db_wrapper = None

    def has_flag(self, flag_name):
        return flag_name in self.flags

    def db_connected(self):
        return self.db_wrapper != None

    def db_connect(self):
        if self.db_connected():
            raise ValueError
        resource = self.options.get('db', None)
        self.db_wrapper = database_opener(resource)

    def db_disconnect(self):
        if not self.db_connected():
            raise ValueError
        self.db_wrapper.close()
        self.db_wrapper = None

    def run(self):
        pass # pragma: no cover

class DownloadCommand(BaseCommand):
    valid_options = ["db"]#{"db": [type_url, type_id, type_filesystem, type_dbname]}
    valid_flags = ["no-index"]

    def run(self):
        # Prepare the database connection
        if not self.db_connected():
            self.db_connect()
        # Make the download manager, configure it, start it
        dlman = DownloadManager(self.db_wrapper, self.values)
        dlman.no_index = self.has_flag("no-index")
        dlman.start()

class IndexCommand(BaseCommand):
    valid_options = ["db"]#{"db": [type_url, type_id, type_filesystem, type_dbname]}
    valid_flags = ["quick"]

    def run(self):
        # Prepare the database connection
        if not self.db_connected():
            self.db_connect()
        # Make the crawler, configure it, start it
        crawler = PageCrawler(self.db_wrapper.db_conn, self.values)
        crawler.quick = self.has_flag("quick")
        crawler.crawl()

class SearchCommand(BaseCommand):
    valid_options = ["db"]#{"db": [type_url, type_id, type_filesystem, type_dbname]}
    valid_flags = ["inclusive"]

    def run(self):
        # Prepare the database connection
        if not self.db_connected():
            self.db_connect()
        search = SearchEngine(self.db_wrapper.db_conn, self.values)
        search.exclusive = self.has_flag("inclusive")
        results = search.query()
        columns = ["ID", "Name", "URL", "Last Indexed"]
        print create_table(results, columns)

class HelpCommand(BaseCommand):
    valid_options = {}
    valid_flags = []

    def read_helpfile(self):
        current_directory = os.path.abspath(os.path.join(__file__, os.pardir))
        helpfile_path = os.path.join(current_directory, "help.txt")
        with open(helpfile_path, 'r') as rfile:
            return rfile.read()

    def run(self):
        print self.read_helpfile()

class DatabaseCommand(BaseCommand):
    valid_options = {}
    valid_flags = []

    def create_database(self):
        disallowed_db_names = ['default']
        db_name = self.values[0]
        # Validate the name for the new database
        if db_name in disallowed_db_names:
            message = "Invalid database name- cannot be in disallowed database name list."
            raise ValueError(message)
        if len(db_name.split()) > 1:
            message = "Invalid database name- cannot contain whitespace."
            raise ValueError(message)
        if db_name in self.config.databases.keys():
            message = "Invalid database name- database with that name already exists."
            raise ValueError(message)
        # Set the database type and resource
        if 'type' in self.options.keys() and 'resource' not in self.options.keys():
            # If we're specifying the type, we *must* specify the resource
            message = "Must provide resource when specifying a database type."
            raise ValueError(message)
        db_type = self.options.get('type', 'filesystem')
        if db_type not in ['filesystem', 'url', 'alias']:
            message = "Database type must be one of: url, filesystem, alias."
            raise ValueError(message)
        db_resource = self.options.get('resource', db_name + ".db")
        if db_type == "alias" and db_resource not in self.config.databases.keys():
            message = "Cannot create alias to database- no database named '%s'." % db_resource
            raise ValueError(message)
        # Save the new configuration
        self.config.databases[db_name] = {'type': db_type, 'resource': db_resource}
        self.config.save()

    def delete_database(self):
        # TODO: This won't delete the actual database file
        target = self.options['delete']
        if target == "default":
            message = "Invalid database name- cannot delete default database."
            raise ValueError(message)
        if target not in self.config.databases.keys():
            message = "Invalid database name- no database exists with that name."
            raise ValueError(message)
        self.config.databases.pop(target, None)
        self.config.save()

    def list_databases(self):
        output_table = PrettyTable(['Name', 'Type', 'Resource'])
        output_table.padding_width = 1
        output_table.align = 'l'
        for i in self.config.databases:
            row = [i, self.config.databases[i]['type'], self.config.databases[i]['resource']]
            output_table.add_row(row)
        print output_table

    def run(self):
        if len(self.values) > 0:
            return self.create_database()
        if self.options.get("delete", False):
            return self.delete_database()
        self.list_databases()

