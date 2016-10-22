# opendir-dl
[![Build Status](https://travis-ci.org/bplower/opendir-dl.svg?branch=master)](https://travis-ci.org/bplower/opendir-dl)
[![Coverage Status](https://coveralls.io/repos/github/bplower/opendir-dl/badge.svg?branch=master)](https://coveralls.io/github/bplower/opendir-dl?branch=master)

This is an indexer and downloader for open directories.

## Installation
While the project is in development, the best way to install the project is using the vcs support in pip:
```
user@debian:~$ pip install -e git+https://github.com/bplower/opendir-dl#egg=opendir-dl
```

This will make the 'opendir-dl' script available:
```
user@debian:~/opendir-dl$ which opendir-dl
/usr/local/bin/opendir-dl
```

## Usage

Since this project is still a work in progress, please note that not every feature detailed here may be implemented. Features and examples marked with "(planned)" are not implemented, but will be soon. Everything else should be working.

### Index

**Basic index**

This is the normal index. It will collect metadata for each file it indexes using the HEAD HTTP method
```
opendir-dl index http://domain.com/some/path
```

**Quick index**

The quick index will do everything the same as the Basic index except for data collection via the HEAD request
```
opendir-dl index --quick http://domain.com/some/path
```

**Reindex Existing Entries**

If you want to reindex a specific item, you can reference the index ID. Here we're going to get the ID for the file "example_file.txt", and then update our index of it.
```
opendir-dl search example_file.txt
+----+------------------+-------------------------------------------------------+----------------------------+
| ID | Name             | URL                                                   | Last Indexed               |
+----+------------------+-------------------------------------------------------+----------------------------+
| 15 | example_file.txt | http://localhost:8000/test_resources/example_file.txt | 2016-10-16 21:23:35.409316 |
+----+------------------+-------------------------------------------------------+----------------------------+
opendir-dl index 15
opendir-dl search example_file.txt
+----+------------------+-------------------------------------------------------+----------------------------+
| ID | Name             | URL                                                   | Last Indexed               |
+----+------------------+-------------------------------------------------------+----------------------------+
| 15 | example_file.txt | http://localhost:8000/test_resources/example_file.txt | 2016-10-20 16:14:52.431861 |
+----+------------------+-------------------------------------------------------+----------------------------+
```

### Search

**Basic Search**

A normal search will do a substring search on the file names. This search will reatun all files with the string 'png' in the name.
```
opendir-dl search png
```

**Multi String Search**

Providing multiple search terms will execute an exclusive search, meaning it will return entires whose names contain all phrases. In this case, you will only get files with names that contain both 'png' and 'jpg'.
```
opendir-dl search png jpg
```

**Inclusive Search**

You can provide the inclusive flag to specify that the search should entries that match any of the terms provided. In this case, you will receive files containing at least one of 'png' and 'jpg'.
```
opendir-dl search --inclusive png jpg
```

**URL Search**

You may need to search the URL field rather than the name field. In this case, we're searching for any file whose URL contains the string 'iso/'.
```
opendir-dl search --urlsearch iso/
```

**Searching Non-Default Database**

You may want to specify a database to search, other than the default database. The `--db` option works with several types of sources.

Non-default file path
```
opendir-dl search --db /home/user/example.db png
```

Database hosted via http
```
opendir-dl search --db http://example.com/path/example.db iso
```

Named database caches (planned)
```
opendir-dl search --db billsdb jpg
```

### Cached Databases

**Cache Creation** (planned)

A remote database can be registered by providing the url to the file, and an alias for the database. This will keep a local copy of the database, which can then be referenced by that alias. The alias *must* be a single word, and may not be the word `all`. The reserved word `all` will reference all cached databases while using the `cachedb` command.
```
opendir-dl cachedb http://example.com/path/example.db billsdb
```

We can now search this database using the following command
```
opendir-dl search --db billsdb iso
```

**Cached Database Status** (planned)

We can check the status of our cache of the database. This will tell you if the remote file has been modified since your cache was created.
```
opendir-dl cachedb --status billsdb
```
**Updating Cached Databases** (planned)

The cached database can be updated using the `--update` option.
```
opendir-dl cachedb --update billsdb
```

If you have many caches and just want to update all of them using the `all` alias.
```
opendir-dl cachedb --update all
```

**Removing Cached Databases** (planned)

A cached database can be removed with the `--delete` option.
```
opendir-dl cachedb --delete billsdb
```

Deleting all cached databases can be done using the `all` alias.
```
opendir-dl cachedb --delete all
```

### Download

**Standard Download**

A normal download like this will not only download the file to the local directory, but will also index the file, so you may search for it in the future. If a file is already indexed, its URL can be referenced by the entries ID. There is no limit to the number of identifiers that my be provided.

Download by URL
```
opendir-dl download http://example.com/path/somefile.jpg
```

Download by ID
```
opendir-dl download 25
```

Providing multiple resource identifiers
```
opendir-dl download 26 90 http://example.com/path/someotherfile.iso 15
```

**Downloading from Non-Default Databases**

A file can be downloaded from non-default databases by providing the `--db` option. This will download the file associated with the ID 12 in that database, not your default database.
```
opendir-dl download --db http://example.com/path/bill.db 12
```

It is worth noting that there is no point in providing the `--db` option while specifying a URL to download. In the following example, the new index entry for somesite.com would be added to the temporary file containing the database retrieved from example.com. The temporary file is deleted once the script is complete, so the newly created index is lost.
```
opendir-dl download --db http://example.com/path/bill.db http://somesite.com/file.iso
```

**Download Search Results**

You've crafted your search to find the exact files you want, so now it's time to download all of them. This can be done by providing the same parameters to the download command, in addition to the flag `--search`. Lets say you would like to download all files returned in the following search.
```
opendir-dl search --db billsdb --inclusive jpg iso
```

You can do so by changing the command from search to download, and then providing the `--search` flag.
```
opendir-dl download --search --db billsdb --inclusive jpg iso
```

## For Developers

The library can be used by importing `opendir_dl`. Here we are effectively running `opendir-dl search png`.
```python
>>> import opendir_dl
>>> opendir_dl.main(['search', 'png'])
```

You can directly run commands without having to go through the input parsing process. This example is effectively the same as the one just above.
```python
>>> import opendir_dl
>>> opendir_dl.commands.search(['png'])
```
