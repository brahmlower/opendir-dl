from opendir_dl import index
from opendir_dl import search

def main(input_list):
    if input_list[0] == "index":
        index(input_list[1])
    elif input_list[0] == "download":
        print "not implemented yet"
    elif input_list[0] == "search":
        search(input_list[1])
