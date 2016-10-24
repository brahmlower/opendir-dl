from opendir_dl import commands

class ParseInput(object):
    available_flags = ["inclusive", "quick", "quiet", "search", "no-index"]
    available_options = ["depth", "db", "delete", "type", "resource"]
    available_commands = {
        "help": commands.HelpCommand,
        "index": commands.IndexCommand,
        "search": commands.SearchCommand,
        "download": commands.DownloadCommand,
        "database": commands.DatabaseCommand}

    def __init__(self):
        """Default values for the types of input

        Defaults here are sane, so providing a fresh instance of ParseInput
        will not break anything. The default command is set to 'help' allowing
        us to run `opendir-dl` and get the help menu.
        """
        self.command = self.available_commands["help"]
        self.flags = []
        self.options = {}
        self.command_values = []

    def instantiate_command(self):
        instance = self.command()
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

    def set_command(self, command):
        if self.available_commands.get(command, None):
            self.command = self.available_commands[command]
        else:
            message = "No such command '%s'. Run 'help' for available commands." % command
            raise ValueError(message)

    @classmethod
    def from_list(cls, input_list):
        """Create an instance of ParseInput with clean data
        """
        clean_input = cls()
        # Assign command, return if none specified
        if len(input_list) == 0:
            return clean_input
        clean_input.set_command(input_list.pop(0))
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

def main(raw_user_in):
    """The main function for handling any provided input

    Consider the following two examples

        user@debian:~$ opendir-dl index --quiet http://localhost:8000/

        >>> import opendir_dl
        >>> opendir_dl.main(["index", "--quiet", "http://localhost:8000/"])

    The the first example is run from the commandline, where the second example
    is run from a python shell. the result of these two examples is the same.
    """
    user_in = ParseInput.from_list(raw_user_in)
    command_instance = user_in.instantiate_command()
    command_instance.run()
