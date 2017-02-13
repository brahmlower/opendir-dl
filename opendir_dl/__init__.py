import os
import os.path
import inspect
import errno
import yaml
import appdirs
from docopt import docopt
from docopt import DocoptExit
from opendir_dl import commands

class CommandMenu(object):
    def __init__(self):
        self.default = self.raise_no_default
        self.commands = {}
        self.set_default(self.default)

    def set_default(self, obj):
        self.default = obj

    def raise_no_default(self):
        raise ValueError('No default action was set for this command.')

    def keywords(self):
        temp_keywords = self.commands.keys()
        return temp_keywords

    def register(self, command, obj=None, verbose=True):
        if isinstance(command, list) and obj is not None:
            # Register the menu command via the string registration method
            self.register_list(command, obj, verbose)
        elif isinstance(command, str) and obj is not None:
            # Register the menu command via the list registration method
            self.register_string(command, obj, verbose)
        elif obj is None:
            # The register function is being used as a decorator. Define the
            # decoration method, then return it. The decoration method simply
            # calls this registration method again, with the provided command
            # (regardless of string or list) and the object provided to the
            # decorator function.
            def decorator(obj):
                self.register(command, obj, verbose)
                return obj
            return decorator
        else:
            raise ValueError('Insufficient arguments to register menu path.')

    def register_string(self, command, obj, verbose=True):
        if verbose:
            print "[INFO] Registering command '{}' to function {}".format(command, obj)
        if self.commands.get(command, False):
            # This means the command has already been registered. In this case,
            # there might be subcommands we don't want to overwrite, so we're just
            # setting the default action here.
            self.commands[command].set_default(obj)
        else:
            # This command hasn't been registered yet, so we can just create a
            # new instance of CommandMenu and make the association
            new_commandmenu = CommandMenu()
            new_commandmenu.set_default(obj)
            self.commands[command] = new_commandmenu

    def register_list(self, command_list, obj, verbose=True):
        if verbose:
            print "[INFO] Registering command '{}' to function {}".format(" ".join(command_list), obj)
        if not isinstance(command_list, list):
            # Make sure we were given a list
            raise TypeError("Value for command_list should be of type 'list'.")
        if len(command_list) == 1:
            # If there is only one command in the list, simply register it by calling self.register
            self.register_string(command_list[0], obj, verbose=False)
        else:
            # There are multiple items in the list, so we need to pass the registration process
            # down to the CommandMenu object associated with the next command in the list. This
            # is a somewhat recursive process.
            command_string = command_list.pop(0)
            if command_string not in self.commands.keys():
                # If this portion of the command hasn't been registered yet, make a new CommandMenu
                # instance and make the association in the commands dict. A default is not set here
                self.commands[command_string] = CommandMenu()
            # Call the list registration for the target CommandMenu instance
            target_command = self.commands[command_string]
            target_command.register_list(command_list, obj, verbose=False)

    def get(self, command_list):
        # Call the default function if no command was provided
        if len(command_list) == 0:
            return self.default
        try:
            command_target = self.commands[command_list[0]]
            return command_target.get(command_list[1:])
        except:
            raise ValueError("No command registered with the path '{}'.".format(command_list))

class Configuration(object):
    def __init__(self, config_path=None):
        self.config_path = config_path
        self.parent_dir = os.path.abspath(os.path.join(self.config_path, os.pardir))
        self.databases = {}
        self.default_database_name = "default"
        self.default_database_filename = "default.db"
        if self.config_path:
            self.open()

    def get_storage_path(self, filename):
        return os.path.join(self.parent_dir, filename)

    def create(self):
        # Make sure the data directory exists
        if not os.path.exists(self.parent_dir):
            mkdir_p(self.parent_dir)
        # Create an entry for the default database if it does not exist
        if self.default_database_name not in self.databases.keys():
            database_dict = {"type":"filesystem", "resource": self.default_database_filename}
            self.databases[self.default_database_name] = database_dict
        # Save a copy of the config if the file does not exist
        if not os.path.exists(self.config_path):
            self.save()

    def open(self, allow_fail=False):
        # TODO: this should also verify the database entries. make sure each one
        # is a dict containing resource and type
        try:
            with open(self.config_path, 'r') as rfile:
                config = yaml.load(rfile)
            self.databases = config['databases']
        except IOError:
            if allow_fail:
                raise
            self.create()
            self.open(allow_fail=True)

    def save(self):
        config_dict = {"databases": self.databases}
        with open(self.config_path, 'w') as wfile:
            yaml.dump(config_dict, wfile, default_flow_style=False)

def get_config_path(file_name, project_name="opendir-dl"):
    return os.path.join(appdirs.user_data_dir(project_name), file_name)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if not (exc.errno == errno.EEXIST and os.path.isdir(path)):
            raise

def walk_menu_path(command_menu, arguments):
    command_list = []
    # While we have a target menu
    while command_menu != None:
        current_menu = command_menu
        command_menu = None
        for i in current_menu.keywords():
            if arguments.get(i):
                command_list.append(i)
                command_menu = current_menu.commands[i]
    return command_list

def print_help(content):
    def decorated_print_help():
        print content
    return decorated_print_help

def main(raw_input_list):
    """OpenDir-DL

    Usage:
        opendir-dl help [options] [command]...
        opendir-dl version [options]
        opendir-dl index [options] [--quick] [--depth=<int>] <resource>...
        opendir-dl search [options] [--inclusive] [--rawsql] <terms>...
        opendir-dl download [options] <index>...
        opendir-dl tag list [options]
        opendir-dl tag create [options] <name>
        opendir-dl tag delete [options] <name>
        opendir-dl tag update [options] <name> <index>
        opendir-dl database list [options]
        opendir-dl database create [options] <name> [--type=<type>] [--resource=<resource>]
        opendir-dl database delete [options] <name>...

    Options:
        -h, --help          Shows this message
        -d, --debug         Run the command in debug mode. This changes the
                            configuration path to use, preventing database polution.
        -v, --verbose       How loud should we be? By default this can be a noisy
                            application.
        -D <db>, --db <db>  This specifies the database to be used while executing
                            the command. The provided value can be a URL, a file
                            path, or a database profile. URLs and file paths must
                            point to a valid opendir-dl sqlite3 database file. Valid
                            database profiles's are explained in the Database section.
    """

    # Parse the user input
    arguments = docopt(main.__doc__, help=False, argv=raw_input_list)
    verbose = arguments.get("--verbose")
    if verbose:
        print arguments

    # Define the available command menu
    command_menu = CommandMenu()
    command_menu.register(['help'], print_help(main.__doc__), verbose=verbose)
    command_menu.register(['index'], commands.IndexCommand, verbose=verbose)
    command_menu.register(['search'], commands.SearchCommand, verbose=verbose)
    command_menu.register(['download'], commands.DownloadCommand, verbose=verbose)
    command_menu.register(['tag', 'list'], commands.TagListCommand, verbose=verbose)
    command_menu.register(['tag', 'create'], commands.TagCreateCommand, verbose=verbose)
    command_menu.register(['tag', 'delete'], commands.TagDeleteCommand, verbose=verbose)
    command_menu.register(['tag', 'update'], commands.TagUpdateCommand, verbose=verbose)
    command_menu.register(['database', 'list'], commands.DatabaseListCommand, verbose=verbose)
    command_menu.register(['database', 'create'], commands.DatabaseCreateCommand, verbose=verbose)
    command_menu.register(['database', 'delete'], commands.DatabaseDeleteCommand, verbose=verbose)
    command_path = walk_menu_path(command_menu, arguments)

    # Build the configuration. If 'debug' is provided as a flag, point the path to a debug data directory.
    config_filepath = get_config_path("config.yml")
    if arguments.get('--debug'):
        config_filepath = get_config_path("config.yml", "opendir-dl-debug")
    config = Configuration(config_path=config_filepath)

    # Get the reference to the command class, instantiate it, and then run it
    target_command_ref = command_menu.get(command_path)
    if inspect.isclass(target_command_ref) and issubclass(target_command_ref, commands.BaseCommand):
        command_instance = target_command_ref()
        command_instance.config = config
        command_instance.arguments = arguments
        command_instance.run()
    else:
        target_command_ref()
