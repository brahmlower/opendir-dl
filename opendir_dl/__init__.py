from opendir_dl.commands import command_help
from opendir_dl.commands import command_index
from opendir_dl.commands import command_search
from opendir_dl.commands import command_download

class ParseInput(object):
    available_flags = ["inclusive", "quick", "quiet", "search"]
    available_options = ["depth", "db"]
    def __init__(self):
        """Default values for the types of input

        Defaults here are sane, so providing a fresh instance of ParseInput
        will not break anything. The default command is set to 'help' allowing
        us to run `opendir-dl` and get the help menu.
        """
        self.command = "help"
        self.flags = []
        self.options = {}
        self.command_values = []

    def add_flag(self, flag):
        #TODO: Raise error if flag not in available_flags
        #TODO: Define new error to assist with reporting error to user
        if flag not in self.flags:
            self.flags.append(flag)

    def add_option(self, option, value):
        #TODO: Check if option in available_options. Raise error if not
        self.options[option] = value

    @classmethod
    def from_list(cls, input_list):
        """Create an instance of ParseInput with clean data
        """
        clean_input = cls()
        # Assign command, return if none specified
        if len(input_list) == 0:
            return clean_input
        clean_input.command = input_list.pop(0)
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
        >>> opendir_dl.main(["index", "--quiet", "http://localhost:8000/""])

    The the first example is run from the commandline, where the second example
    is run from a python shell. the result of these two examples is the same.
    """
    #TODO: Move this into the parse input so it can detect invalid commands
    command_dict = {
        "help": command_help,
        "index": command_index,
        "search": command_search,
        "download": command_download,
    }
    user_in = ParseInput.from_list(raw_user_in)
    try:
        command = command_dict[user_in.command]
    except KeyError:
        command = command_dict["help"]
    command(user_in.command_values, user_in.flags, user_in.options)
