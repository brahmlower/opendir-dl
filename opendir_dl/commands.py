import sqlalchemy
from prettytable import PrettyTable
from opendir_dl.databasing import database_opener
from opendir_dl.utils import SearchEngine
from opendir_dl.utils import PageCrawler
from opendir_dl.utils import DownloadManager
from opendir_dl.utils import create_table
from opendir_dl.models import Tags
from opendir_dl.models import FileIndex

class BaseCommand(object):
    def __init__(self):
        self.config = None
        self.arguments = {}
        self.db_wrapper = None

    def has_flag(self, flag_name):
        # This pretty much just wraps the self.arguments dict, but it's useful
        # in that we don't have to deail with the flag tracking implementation at all
        return self.arguments.get("--{}".format(flag_name)) is True

    def get_option(self, option_name):
        return self.arguments.get("--{}".format(option_name))

    def get_argument(self, argument_name):
        return self.arguments.get("<{}>".format(argument_name))

    def db_connected(self):
        return self.db_wrapper is not None

    def db_connect(self):
        if self.db_connected():
            raise ValueError("Database already connected")
        if not self.config:
            raise ValueError("No valid configuration has been set")

        # Get the target database value from the arguments, or use the default
        resource = "default"
        if self.arguments is not None and self.get_option("db") is not None:
            resource = self.get_option("db")
        # Opend the referenced database
        self.db_wrapper = database_opener(self.config, resource)

    def db_disconnect(self):
        if not self.db_connected():
            raise ValueError
        self.db_wrapper.close()
        self.db_wrapper = None

    def run(self):
        pass # pragma: no cover

# Version command

class VersionCommand(BaseCommand):
    def run(self):
        print "opendir-dl 0.0.0"

# Tagging related commands

class TagListCommand(BaseCommand):
    def run(self):
        if not self.db_connected():
            self.db_connect()
        # Just list the tags we have
        results = self.db_wrapper.db_conn.query(Tags).all()
        for i in results:
            print i.name, len(i.indexes)

class TagCreateCommand(BaseCommand):
    def run(self):
        if not self.db_connected():
            self.db_connect()
        for i in self.get_argument("name"):
            new_tag = Tags(name=i)
            self.db_wrapper.db_conn.add(new_tag)
        self.db_wrapper.db_conn.commit()

class TagDeleteCommand(BaseCommand):
    def run(self):
        if not self.db_connected():
            self.db_connect()
        raise ValueError("Not implemented yet! +1")

class TagUpdateCommand(BaseCommand):
    def run(self):
        if not self.db_connected():
            self.db_connect()
        provided_index = self.get_argument("index")
        provided_tag_name = self.get_argument("name")
        # Get the tag
        tag = self.db_wrapper.db_conn.query(Tags).filter(Tags.name.like(provided_tag_name)).one()
        # Get the file index
        #index_pkid = self.options['update']
        file_index = self.db_wrapper.db_conn.query(FileIndex).get(provided_index)
        file_index.tags.append(tag)
        self.db_wrapper.db_conn.commit()

class DownloadCommand(BaseCommand):
    """Download:
    Usage:
      opendir-dl download <id> (--no-index)
        Description:
                Downloads the specified resource.

        Flags:
                --search        Execute search first using all provided flags,
                                options and values, and then download all of
                                the results.

                --no-index      Specifies that the downloaded file will not be
                                indexed if it hasn't been already, and will not
                                but updated if it has already been indexed.

        Options:
                --db [file|url|db profile|'all']
                        This specifies the database to be used while executing
                        the command. The provided value can be a URL, a file
                        path, or a database profile. URLs and file paths must
                        point to a valid opendir-dl sqlite3 database file.
                        Valid database profiles's are explained in the Database
                        section. The 'all' database alias is respected here.

        Examples:
                $ opendir-dl download --db all 4

                This will download the file referenced by the file entry with
                the ID 4 in each of the attached databases. This is a useless
                thing to do, but it illustrates that you can download a file by
                its ID, and that you can reference all databases at once.
    """
    valid_options = ["db"]#{"db": [type_url, type_id, type_filesystem, type_dbname]}
    valid_flags = ["no-index"]

    def run(self):
        # Prepare the database connection
        if not self.db_connected():
            self.db_connect()
        # Make the download manager, configure it, start it
        values = self.get_argument("index")
        print values
        dlman = DownloadManager(self.db_wrapper, values)
        dlman.no_index = self.has_flag("no-index")
        dlman.start()

class IndexCommand(BaseCommand):
    """Index:
        Description:
                The index operation will crawl in index the referenced webpage.
                References to pages can be urls, as well as database indexes,
                where the URL associated with that index will be re-indexed.

        Flags:
                --quick         Changes the indexing method such that HEAD
                                requests are not made for each possible file.
                                This results in a quicker index, but less data
                                gathered for each possible file.

                --quiet         Do not print output while executing commands.
                                This will still print any command results.

        Options:
                --depth [int]   This is the maximum page depth to travel while
                                indexing sites. This is to prevent recursive
                                directories from filling the index database.
                                The default value is 50.

                --db [file|url|db profile|'all']
                                This specifies the database to be used while
                                executing the command. The provided value can
                                be a URL, a file path, or a database profile.
                                URLs and file paths must point to a valid
                                opendir-dl sqlite3 database file. Valid
                                database profiles's are explained in the
                                Database section. The 'all' database alias is
                                respected here.

        Examples:
                $ opendir-dl index http://localhost:8000/

                This is the most basic form of index, where all newly
                discovered files are indexed within the default database. This
                will use the full index method where each potential file is
                queried with a HTTP HEAD request.

                $ opendir-dl index --db my_indexes http://localhost:8000/

                Here a nondefault database profile is specified. This command
                assumes there is a database profile called 'my_indexes'. All
                new indexes will be added to that database rather than the
                default database.

                $ opendir-dl index --quick http://remotehost/somepath/

                Some sites are slower, and because the default index method
                makes a HEAD request for each possible file, the web server may
                go slower than we would like. Providing the quick flag
                indicates that we should not make full HEAD requests and just
                take an educated guess at the filetypes. This is considerably
                quicker, but may be less accurate.
    """

    valid_options = ["db"]#{"db": [type_url, type_id, type_filesystem, type_dbname]}
    valid_flags = ["quick"]

    def run(self):
        # Prepare the database connection
        if not self.db_connected():
            self.db_connect()
        # Make the crawler, configure it, start it
        resource = self.get_argument("resource")
        crawler = PageCrawler(self.db_wrapper.db_conn, resource)
        crawler.quick = self.has_flag("quick")
        crawler.run()

class SearchCommand(BaseCommand):
    """Search:
        Description:
                This command provides search functionality within the specified
                database.

        Flags:
                --inclusive     Changes a search to include all results
                                matching any of the provided search terms.
                                Search is exclusive by default.

        Options:
                --db [file|url|db profile|'all']
                        This specifies the database to be used while executing
                        the command. The provided value can be a URL, a file
                        path, or a database profile. URLs and file paths must
                        point to a valid opendir-dl sqlite3 database file.
                        Valid database profiles's are explained in the Database
                        section. The 'all' database alias is respected here.

                --rawsql [sql string]
                        This lets the user provide their own crafted sql string
                        to be passed to the sqlite3 engine. Note that this is
                        intended to be used for read only purposes, but there
                        is nothing preventing write operations from running. Be
                        extremely careful using this option.

        Examples:
                <none>
    """

    valid_options = ["db"]#{"db": [type_url, type_id, type_filesystem, type_dbname]}
    valid_flags = ["inclusive"]

    def run(self):
        # Prepare the database connection
        if not self.db_connected():
            self.db_connect()
        if self.has_flag("rawsql"):
            rawsql = sqlalchemy.text(' '.join(self.get_argument("terms")))
            results = self.db_wrapper.db_conn.execute(rawsql)
            print create_table(results)
        else:
            terms = self.get_argument("terms")
            search = SearchEngine(self.db_wrapper.db_conn, terms)
            search.exclusive = self.has_flag("inclusive")
            results = search.query()
            columns = ["ID", "Name", "Last Indexed", "Tags"]
            print create_table(results, columns)

# Database commands

class DatabaseListCommand(BaseCommand):
    def run(self):
        output_table = PrettyTable(['Name', 'Type', 'Resource'])
        output_table.padding_width = 1
        output_table.align = 'l'
        for i in self.config.databases:
            row = [i, self.config.databases[i]['type'], self.config.databases[i]['resource']]
            output_table.add_row(row)
        print output_table

class DatabaseCreateCommand(BaseCommand):
    def run(self):
        disallowed_db_names = ['default']
        db_name = self.get_argument("name")[0]
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
        if self.get_option('type') and not self.get_option('resource'):
            # If we're specifying the type, we *must* specify the resource
            message = "Must provide resource when specifying a database type."
            raise ValueError(message)
        db_type = self.get_option('type')
        if not db_type:
            db_type = 'filesystem'
        if db_type not in ['filesystem', 'url', 'alias']:
            message = "Database type must be one of: 'url', 'filesystem', 'alias'. Got type '{}'.".format(db_type)
            raise ValueError(message)
        db_resource = self.get_option('resource')
        if not db_resource:
            db_resource = "{}.db".format(db_name)
        if db_type == "alias" and db_resource not in self.config.databases.keys():
            message = "Cannot create alias to database- no database named '%s'." % db_resource
            raise ValueError(message)
        # Save the new configuration
        self.config.databases[db_name] = {'type': db_type, 'resource': db_resource}
        self.config.save()

class DatabaseDeleteCommand(BaseCommand):
    def run(self):
        # TODO: This won't delete the actual database file
        target = self.get_argument("name")
        for i in target:
            if i == "default":
                message = "Invalid database name- cannot delete default database."
                raise ValueError(message)
            if i not in self.config.databases.keys():
                message = "Invalid database name- no database exists with name '{}'.".format(i)
                raise ValueError(message)
            self.config.databases.pop(i, None)
        self.config.save()

# class DatabaseCommand(BaseCommand):
#     """Database:
#         Description:
#                 The database command allows for CRUD opperations on database
#                 profiles. These profiles are meant to make it eaiser to
#                 frequently interract with non-default databases. These profiles
#                 can be referenced from the index, search and download commands.

#         Options:
#                 --type          This specifies the type of database we're
#                                 defining. This should be one of the following
#                                 values: 'filesystem', 'url', or 'alias'.

#                 --resource      This is the resource being referenced by the
#                                 database. Depending on the type, this will be
#                                 either a filesystem path, url or the name of
#                                 another database.

#                 --delete        This will remove a database from the database
#                                 list, and delete the datbase file if possible
#                                 (cannot delete databases of type url).

#         Examples:
#                 $ opendir-dl database
#                 +---------+------------+------------+
#                 | Name    | Type       | Resource   |
#                 +---------+------------+------------+
#                 | default | filesystem | default.db |
#                 +---------+------------+------------+

#                 Simply running the database command with no options or values
#                 will list the available database profiles. With a fresh setup,
#                 there will only be the default database listed.

#                 $ opendir-dl database --resource ~/my_indexes.db my_indexes
#                 $ opendir-dl database
#                 +------------+------------+---------------------------+
#                 | Name       | Type       | Resource                  |
#                 +------------+------------+---------------------------+
#                 | default    | filesystem | default.db                |
#                 | my_indexes | filesystem | /home/sk4ly/my_indexes.db |
#                 +------------+------------+---------------------------+

#                 Creating a new database profile can be done by providing the
#                 'resource' option with a reference to the database file,
#                 followed by the name of the database profile. Here we've
#                 created a database with the name 'my_indexes' which points to
#                 the file 'my_indexes.db' within my user directory.

#                 $ opendir-dl database --type url --resource http://opendir-dl.com/redditdb/index.db redditdb
#                 $ opendir-dl database
#                 +------------+------------+-----------------------------------------+
#                 | Name       | Type       | Resource                                |
#                 +------------+------------+-----------------------------------------+
#                 | default    | filesystem | default.db                              |
#                 | my_indexes | filesystem | /home/sk4ly/my_indexes.db               |
#                 | redditdb   | url        | http://opendir-dl.com/redditdb/index.db |
#                 +------------+------------+-----------------------------------------+

#                 We can also create a database profile to a remote database by
#                 providing an http/https url as the resource, and specifying the
#                 database type as being a 'url'. In this instance we are calling
#                 the profile 'redditdb'.

#                 $ opendir-dl database --type alias --resource redditdb r
#                 $ opendir-dl database
#                 +------------+------------+-----------------------------------------+
#                 | Name       | Type       | Resource                                |
#                 +------------+------------+-----------------------------------------+
#                 | default    | filesystem | default.db                              |
#                 | my_indexes | filesystem | /home/sk4ly/my_indexes.db               |
#                 | redditdb   | url        | http://opendir-dl.com/redditdb/index.db |
#                 | r          | alias      | redditdb                                |
#                 +------------+------------+-----------------------------------------+

#                 Lastly, we can create alias's to other database. I don't know
#                 if this is useful or not, but set the type to 'alias' and the
#                 resource as the name of another database. Here I've created
#                 an alias to the database 'redditdb' simply called 'r'.

#                 $ opendir-dl database --delete my_indexes
#                 $ opendir-dl database
#                 +----------+------------+-----------------------------------------+
#                 | Name     | Type       | Resource                                |
#                 +----------+------------+-----------------------------------------+
#                 | default  | filesystem | default.db                              |
#                 | redditdb | url        | http://opendir-dl.com/redditdb/index.db |
#                 | r        | alias      | redditdb                                |
#                 +----------+------------+-----------------------------------------+

#                 Eventually we will want to remove a database. This is acheived
#                 by providing the 'delete' option with the value of the database
#                 you'd like to delete. In this case we've removed the
#                 'my_indexes' database.
#     """
