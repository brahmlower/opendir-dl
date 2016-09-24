from opendir_dl import index
from opendir_dl import search

def parse_flags(input_list, available_flags):
    flags = []
    for i in input_list:
        if i[0] == "-" and i.strip("-") in available_flags:
            flags.append(i.strip("-"))
    return flags

def remove_flags(input_list):
    clean_input = []
    for i in input_list:
        if i[0] != "-":
            clean_input.append(i)
    return clean_input

def help(*args, **kwargs):
    print "opendir-dl [command] (options) [value]"
    print "Example: opendir-dl index http://localhost:8000/"
    print "Example: opendir-dl search --inclusive png jpg"

def main(input_list):
    flags = ["inclusive", "quiet", "urlsearch"]
    command_dict = {
        "index": index,
        "search": search,
    }
    command_value = input_list.pop(0)
    command = command_dict[command_value]
    input_flags = parse_flags(input_list, flags)
    input_list = remove_flags(input_list)
    command(input_list, input_flags)
