from opendir_dl import index

def main(input_list):
    if input_list[0] == "index":
        index(input_list[1])
    elif input_list[0] == "download":
        print "not implemented yet"
