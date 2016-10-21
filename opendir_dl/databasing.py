import os
import tempfile
import yaml
import appdirs
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from opendir_dl.utils import http_get
from opendir_dl.utils import is_url
from opendir_dl.utils import mkdir_p
from opendir_dl.models import MODELBASE

class DatabaseWrapper(object):
    default_db = 'default.db'

    def __init__(self, source):
        if not os.path.exists(appdirs.user_data_dir('opendir-dl')):
            mkdir_p(appdirs.user_data_dir('opendir-dl'))
        self.db_conn = None
        self.tempfile = None
        self.source = source

    def query(self, *args, **kwargs):
        # This is meant to be overwritten with a reference to
        # self.db_conn.query that way stuff can just call wrapper.query like
        # normal. This is overwritten with the reference to db_conn.query
        # when the database is connected
        pass

    def is_connected(self):
        """True/False value for if the DatabaseWrapper instance is connected
        """
        return self.db_conn != None

    def connect(self):
        """ Establish the database session given the set values
        """
        database_engine = sqlalchemy.create_engine('sqlite:///%s' % self.source)
        MODELBASE.metadata.create_all(database_engine)
        MODELBASE.metadata.bind = database_engine
        database_session = sessionmaker(bind=database_engine)
        self.db_conn = database_session()
        setattr(self, 'query', self.db_conn.query)

    @classmethod
    def from_default(cls):
        """Get a default instance of DatabaseWrapper

        This would be used over `DatabaseWrapper()` because this returns an
        object where self.db_conn is already an established database session
        """
        source = "%s/%s" % (appdirs.user_data_dir('opendir-dl'), cls.default_db)
        dbw_inst = cls(source)
        dbw_inst.connect()
        return dbw_inst

    @classmethod
    def from_fs(cls, path):
        """ Gets a database session from a cache of a remote database

        This method will need additional sanitation on the `path` value.
        relative and absolute paths *should* work, but anything referecing `~`
        will need to be expanded first.
        """
        dbw_inst = cls(path)
        dbw_inst.connect()
        return dbw_inst

    @classmethod
    def from_data(cls, data):
        """Get an instance of DatabaseWrapper from the give raw data
        """
        temp_file = tempfile.NamedTemporaryFile()
        dbw_inst = cls(temp_file.name)
        dbw_inst.tempfile = temp_file
        dbw_inst.tempfile.write(data)
        dbw_inst.tempfile.flush()
        dbw_inst.connect()
        return dbw_inst

    @classmethod
    def from_url(cls, url):
        """ Gets a database session from a URL
        """
        response = http_get(url)
        if response[0]['status'] == '200':
            return cls.from_data(response[1])
        else:
            message = "HTTP GET request failed with error '%s'. Expected '200'." \
                    % response[0]['status']
            raise ValueError(message)

    @classmethod
    def from_name(cls, name):
        config_path = appdirs.user_data_dir('opendir-dl') + "/config.yml"
        config = yaml.load(open(config_path))
        if not config['databases'].get(name, None):
            raise ValueError
        database_path = appdirs.user_data_dir('opendir-dl') + "/" + \
            config['databases'][name]['resource']
        return cls.from_fs(database_path)

def database_opener(database_string=None):
    """Creates an instance of DatabaseWrapper

    We don't know what resource type the database_string is referencing. It can
    be one of the following:
    * URL
    * filepath (relative/absolute)
    * named database
    * None (resulting in default database)
    """
    # This gets us the default configuration
    if not database_string:
        return DatabaseWrapper.from_default()
    # We were given a URL
    if is_url(database_string):
        return DatabaseWrapper.from_url(database_string)
    # Load from a named database
    config = yaml.load(open(appdirs.user_data_dir('opendir-dl') + "/config.yml"))
    if database_string in config['databases'].keys():
        return DatabaseWrapper.from_name(database_string)
    # It might be a filesystem path
    fs_path = os.path.expandvars(database_string)
    fs_path = os.path.expanduser(fs_path)
    if os.path.exists(fs_path):
        return DatabaseWrapper.from_fs(fs_path)
    raise ValueError("Cannot find database referenced by '%s'." % database_string)
