import sqlalchemy
from prettytable import PrettyTable
from opendir_dl.databasing import database_opener
from opendir_dl.utils import SearchEngine
from opendir_dl.utils import PageCrawler
from opendir_dl.utils import DownloadManager
from opendir_dl.utils import create_table
from opendir_dl.utils import format_tags
from opendir_dl.models import Tags
from opendir_dl.models import FileIndex

class BaseCommand(object):
    """
    This is the default BaseCommand docstring
    """
    def __init__(self):
        self.config = None
        self.arguments = None
        self.db_wrapper = None
        if not self.arguments:
            self.arguments = {}

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

    @classmethod
    def factory(cls, func):
        """
        This is a decorator for functions that returns an instance of BaseCommand with the docstring and function overwritten on the run method of the instance.
        """
        # Following line from http://stackoverflow.com/questions/9541025/how-to-copy-a-python-class
        cls_dict = dict(cls.__dict__)
        cls_dict['__doc__'] = func.__doc__
        command = type(func.__name__, (cls,), cls_dict)
        command.run = func
        return command

@BaseCommand.factory
def TagListCommand(self):
    """
Tag List

Tags can be listed using the command 'tag list', which will produce a table of available tags and the number of items associated with that tag.

.. code::

    $ opendir-dl tag list --debug
    +----------+----------------+
    | Tag Name | Num References |
    +----------+----------------+
    | testing  | 1              |
    | butts    | 1              |
    +----------+----------------+

    """
    if not self.db_connected():
        self.db_connect()
    # Just list the tags we have
    results = self.db_wrapper.db_conn.query(Tags).all()
    cleaned_results = []
    for i in results:
        cleaned_results.append([i.name, len(i.indexes)])
    columns = ["Tag Name", "Num References"]
    print create_table(cleaned_results, columns)

@BaseCommand.factory
def TagCreateCommand(self):
    """
Tag Create

The tag can be created but must be a single word that is not already already in use.

.. code::

    $ opendir-dl tag create --debug testing_command

    """
    if not self.db_connected():
        self.db_connect()
    new_tag_name = self.get_argument("name")[0]
    tag = self.db_wrapper.db_conn.query(Tags).filter(Tags.name.like(new_tag_name)).all()
    if len(tag) > 0:
        # This means the tag already exists. Exit
        raise ValueError("Tag with name '{}' already exists!".format(new_tag_name))
    new_tag = Tags(name=new_tag_name)
    self.db_wrapper.db_conn.add(new_tag)
    self.db_wrapper.db_conn.commit()

@BaseCommand.factory
def TagDeleteCommand(self):
    """
Tag Delete

Deleting tags is just as easy as creating tags.

.. code::

    $ opendir-dl tag delete --debug testing_command

    """
    if not self.db_connected():
        self.db_connect()
    tag_name = self.get_argument("name")[0]
    try:
        tag = self.db_wrapper.db_conn.query(Tags).filter(Tags.name.like(tag_name)).one()
    except sqlalchemy.orm.exc.NoResultFound:
        raise ValueError("Tag with name '{}' does not exist.".format(tag_name))
    self.db_wrapper.db_conn.delete(tag)
    self.db_wrapper.db_conn.commit()

@BaseCommand.factory
def TagUpdateCommand(self):
    if not self.db_connected():
        self.db_connect()
    # Get the entry for the file referenced by the provided index
    provided_index = self.get_argument("index")[0]
    file_index = self.db_wrapper.db_conn.query(FileIndex).get(provided_index)
    if not file_index:
        raise ValueError("File index with ID '{}' could not be found.".format(provided_index))
    # Get the tag referenced by the tag name
    provided_tag_name = self.get_argument("name")[0]
    try:
        tag = self.db_wrapper.db_conn.query(Tags).filter(Tags.name.like(provided_tag_name)).one()
    except sqlalchemy.orm.exc.NoResultFound:
        raise ValueError("Tag with name '{}' does not exist.".format(provided_tag_name))
    # Add the tag reference to the file entry
    file_index.tags.append(tag)
    self.db_wrapper.db_conn.commit()

@BaseCommand.factory
def DownloadCommand(self):
    """
Download

Downloads the specified resource.

This will download the file referenced by the file entry with
the ID 4 in each of the attached databases. This is a useless
thing to do, but it illustrates that you can download a file by
its ID, and that you can reference all databases at once.

.. code::

    $ opendir-dl download --debug --db all 4

"""
    # Prepare the database connection
    if not self.db_connected():
        self.db_connect()
    # Make the download manager, configure it, start it
    values = self.get_argument("index")
    print values
    dlman = DownloadManager(self.db_wrapper, values)
    dlman.no_index = self.has_flag("no-index")
    dlman.start()

@BaseCommand.factory
def IndexCommand(self):
    """
Index

The index operation will crawl in index the referenced webpage.
References to pages can be urls, as well as database indexes,
where the URL associated with that index will be re-indexed.

This is the most basic form of index, where all newly
discovered files are indexed within the default database. This
will use the full index method where each potential file is
queried with a HTTP HEAD request.

.. code::

    $ opendir-dl index --debug http://localhost:8000/

Here a nondefault database profile is specified. This command
assumes there is a database profile called 'my_indexes'. All
new indexes will be added to that database rather than the
default database.

.. code::

    $ opendir-dl index --debug --db my_indexes http://localhost:8000/

Some sites are slower, and because the default index method
makes a HEAD request for each possible file, the web server may
go slower than we would like. Providing the quick flag
indicates that we should not make full HEAD requests and just
take an educated guess at the filetypes. This is considerably
quicker, but may be less accurate.

.. code::

    $ opendir-dl index --debug --quick http://remotehost/somepath/

"""
    # Prepare the database connection
    if not self.db_connected():
        self.db_connect()
    # Make the crawler, configure it, start it
    resource = self.get_argument("resource")
    crawler = PageCrawler(self.db_wrapper.db_conn, resource)
    crawler.quick = self.has_flag("quick")
    crawler.run()

@BaseCommand.factory
def SearchCommand(self):
    """
Search

This command provides search functionality within the specified database.

"""
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
        cleaned_results = []
        for i in results:
            cleaned_results.append([i.pkid, i.name, i.last_indexed, format_tags(i.tags)])
        columns = ["ID", "Name", "Last Indexed", "Tags"]
        print create_table(cleaned_results, columns)

@BaseCommand.factory
def DatabaseListCommand(self):
    """
Database List

Lists available databases and aliases

Simply running the database command with no options or values
will list the available database profiles. With a fresh setup,
there will only be the default database listed.

.. code::

    $ opendir-dl database list --debug
    +---------+------------+------------+
    | Name    | Type       | Resource   |
    +---------+------------+------------+
    | default | filesystem | default.db |
    +---------+------------+------------+

"""
    output_table = PrettyTable(['Name', 'Type', 'Resource'])
    output_table.padding_width = 1
    output_table.align = 'l'
    for i in self.config.databases:
        row = [i, self.config.databases[i]['type'], self.config.databases[i]['resource']]
        output_table.add_row(row)
    print output_table

@BaseCommand.factory
def DatabaseCreateCommand(self):
    """
Database Create

Creating a new database profile can be done by providing the
'resource' option with a reference to the database file,
followed by the name of the database profile. Here we've
created a database with the name 'my_indexes' which points to
the file 'my_indexes.db' within my user directory.

.. code::

    $ opendir-dl database create --debug --resource ~/my_indexes.db my_indexes
    $ opendir-dl database create --debug
    +------------+------------+---------------------------+
    | Name       | Type       | Resource                  |
    +------------+------------+---------------------------+
    | default    | filesystem | default.db                |
    | my_indexes | filesystem | /home/sk4ly/my_indexes.db |
    +------------+------------+---------------------------+

We can also create a database profile to a remote database by
providing an http/https url as the resource, and specifying the
database type as being a 'url'. In this instance we are calling
the profile 'redditdb'.

.. code::

    $ opendir-dl database create --debug --type url --resource http://opendir-dl.com/redditdb/index.db redditdb
    $ opendir-dl database create --debug
    +------------+------------+-----------------------------------------+
    | Name       | Type       | Resource                                |
    +------------+------------+-----------------------------------------+
    | default    | filesystem | default.db                              |
    | redditdb   | url        | http://opendir-dl.com/redditdb/index.db |
    +------------+------------+-----------------------------------------+

Lastly, we can create alias's to other database. I don't know
if this is useful or not, but set the type to 'alias' and the
resource as the name of another database. Here I've created
an alias to the database 'redditdb' simply called 'r'.

.. code::

    $ opendir-dl database create --debug --type alias --resource default example_alias
    $ opendir-dl database create --debug
    +---------------+------------+------------+
    | Name          | Type       | Resource   |
    +---------------+------------+------------+
    | default       | filesystem | default.db |
    | example_alias | alias      | default    |
    +----------------+------------+-----------+

"""

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

@BaseCommand.factory
def DatabaseDeleteCommand(self):
    """
Database delete

Eventually we will want to remove a database. This is acheived
by providing the 'delete' option with the value of the database
you'd like to delete. In this case we've removed the
'my_indexes' database.

.. code::

    $ opendir-dl database create --debug example_db
    $ opendir-dl database delete --debug example_db
    $ opendir-dl database list --debug
    +------------+------------+---------------+
    | Name       | Type       | Resource      |
    +------------+------------+---------------+
    | default    | filesystem | default.db    |
    | example_db | fielsystem | example_db.db |
    +------------+------------+---------------+

"""
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
