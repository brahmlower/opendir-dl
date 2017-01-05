import os
import os.path
import errno
import yaml
import appdirs
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

    def help_menu(self):
        print self.keywords()

    def keywords(self):
        temp_keywords = self.commands.keys()
        return temp_keywords

    def register(self, command, obj=None):
        if isinstance(command, list) and obj != None:
            # Register the menu command via the string registration method
            self.register_list(command, obj)
        elif isinstance(command, str) and obj != None:
            # Register the menu command via the list registration method
            self.register_string(command, obj)
        elif obj == None:
            # The register function is being used as a decorator. Define the
            # decoration method, then return it. The decoration method simply
            # calls this registration method again, with the provided command
            # (regardless of string or list) and the object provided to the
            # decorator function.
            def decorator(obj):
                self.register(command, obj)
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

class ParseInput(object):
    available_flags = ["debug", "inclusive", "quick", "quiet", "search", "no-index", "create"]
    available_options = ["depth", "db", "delete", "type", "resource", "rawsql", "update"]

    def __init__(self, command_menu):
        """Default values for the types of input

        Defaults here are sane, so providing a fresh instance of ParseInput
        will not break anything. The default command is set to 'help' allowing
        us to run `opendir-dl` and get the help menu.
        """
        self.command_menu = command_menu
        self.command = []
        self.flags = []
        self.options = {}
        self.command_values = []

    def instantiate_command(self, config=None):
        instance = self.command()
        instance.config = config
        instance.flags = self.flags
        instance.options = self.options
        instance.values = self.command_values
        return instance

    def add_flag(self, flag):
        # Make sure that the flag is an actual flag first
        if flag in self.available_flags:
            # Now make sure we haven't already added this flag
            if flag not in self.flags:
                self.flags.append(flag)
        else:
            message = "No such flag '%s'. Run 'help' for available flags." % flag
            raise ValueError(message)

    def add_option(self, option, value):
        if option in self.available_options:
            self.options[option] = value
        else:
            message = "No such option '%s'. Run 'help' for available options." % option
            raise ValueError(message)

    def set_command(self, command_list):
        try:
            self.command_menu.get(command_list)
            self.command = command_list
        except ValueError:
            message = "No such command '%s'. Run 'help' for available commands." % command_list
            raise ValueError(message)

    @classmethod
    def from_list(cls, command_menu, input_list):
        """Create an instance of ParseInput with clean data
        """
        clean_input = cls(command_menu)
        # Assign command, return if none specified
        if len(input_list) == 0:
            return clean_input
        # Checks if the first character of the first input value is a dash
        # which would indicate that the value is an option or flag, and the
        # command has been ommited. This will result in running the help
        # command, but we still want to process any remaining vaules like normal
        if input_list[0][0] != "-":
            clean_input.set_command([input_list.pop(0)])
        # Process options and flags
        # For more information on handling_option, see the first if statement
        # in the for loop
        handling_option = None
        for idx, val in enumerate(input_list):
            # Check if we're in the process of handling an option
            # handling_option value indicates if we're in the process of
            # handling and option, which is an association of a key followed by
            # a value in the immediatly following list item. If handling_option
            # equals None, we are not handling any options, but if it is a
            # string, we are handling the option of that value, meaning we will
            # associate that value with the values we're currently handling
            # within the self.options dictionary
            if handling_option:
                clean_input.add_option(handling_option, val)
                handling_option = None
                continue
            # Check if the value is a flag
            if val[0] == "-" and val.strip("-") in cls.available_flags:
                cleaned_flag = val.strip("-")
                clean_input.add_flag(cleaned_flag)
                continue
            # Check if the value is an option
            if val[0] == "-" and val.strip("-") in cls.available_options:
                handling_option = val.strip("-")
                continue
            # Reaching this statement means everything from this index to the
            # end of the list should be treated as command values. We will
            # assume it's all command values. Add it to the list, then break
            # out of the loop
            else:
                clean_input.command_values = input_list[idx:]
                break
        # Return the new parsed input object
        return clean_input

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

    def open(self):
        # TODO: this should also verify the database entries. make sure each one
        # is a dict containing resource and type
        try:
            with open(self.config_path, 'r') as rfile:
                config = yaml.load(rfile)
            self.databases = config['databases']
        except IOError:
            self.create()
            self.open()

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

def main(raw_input_list):
    """The main function for handling any provided input

    Consider the following two examples

        user@debian:~$ opendir-dl index --quiet http://localhost:8000/

        >>> import opendir_dl
        >>> opendir_dl.main(["index", "--quiet", "http://localhost:8000/"])

    The the first example is run from the commandline, where the second example
    is run from a python shell. the result of these two examples is the same.
    """
    # Define the available command menu
    command_menu = CommandMenu()
    command_menu.register(['help'], commands.HelpCommand)
    command_menu.register(['index'], commands.IndexCommand)
    command_menu.register(['search'], commands.SearchCommand)
    command_menu.register(['download'], commands.DownloadCommand)
    command_menu.register(['database'], commands.DatabaseCommand)
    command_menu.register(['tags'], commands.TagCommand)
    command_menu.set_default(commands.HelpCommand)
    # Parse the user input
    user_in = ParseInput.from_list(command_menu, raw_input_list)
    # Build the configuration. If 'debug' is provided as a flag, point
    # the path to a debug data directory.
    config_filepath = get_config_path("config.yml")
    if "debug" in user_in.flags:
        config_filepath = get_config_path("config.yml", "opendir-dl-debug")
    config = Configuration(config_path=config_filepath)
    # Create and start the command
    #command_instance = user_in.instantiate_command(config=config)
    #command_instance.run()
    # Get the reference to the command class, instantiate it, and then run it
    target_command_ref = command_menu.get(user_in.command)
    command_instance = target_command_ref()
    command_instance.config = config
    command_instance.flags = user_in.flags
    command_instance.options = user_in.options
    command_instance.values = user_in.command_values
    command_instance.run()
