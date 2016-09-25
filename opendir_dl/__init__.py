from opendir_dl.commands import command_help
from opendir_dl.commands import command_index
from opendir_dl.commands import command_search

class ParseInput(object):
    available_flags = ["inclusive", "quiet", "urlsearch"]
    available_options = ["depth"]
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

    @classmethod
    def new(cls, input_list):
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
                clean_input.options[handling_option] = val
                handling_option = None
                continue
            # Check if the value is a flag
            if val[0] == "-" and val.strip("-") in cls.available_flags:
                clean_input.flags.append(val.strip("-"))
                continue
            # Check if the value is an option
            if val[0] == "-" and val.strip("-") in cls.available_options:
                handling_option = val.strip("-")
                continue
            # Reach this statement means everything from this index to the end
            # of the list should be treated as command values. We will assume
            # it's all command values. Add it to the list, then break out of
            # the loop
            else:
                clean_input.command_values = input_list[idx:]
                break
        # Return the new parsed input object
        return clean_input

def main(input_list):
    """The main function for handling any provided input

    Consider the following two examples

        user@debian:~$ opendir-dl index --quiet http://localhost:8000/

        >>> import opendir_dl
        >>> opendir_dl.main(["index", "--quiet", "http://localhost:8000/""])

    The the first example is run from the commandline, where the second example
    is run from a python shell. the result of these two examples is the same.
    """
    command_dict = {
        "help": command_help,
        "index": command_index,
        "search": command_search,
    }
    clean_input = ParseInput.new(input_list)
    command = command_dict[clean_input.command]
    input_flags = clean_input.flags
    input_options = clean_input.options
    input_values = clean_input.command_values
    command(input_values, input_flags, input_options)