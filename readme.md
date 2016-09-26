# opendir-dl

This is an indexer and downloader for open directories.

## Installation
Clone the repo, cd into the directory and then do a local pip install
```
user@debian:~$ git clone https://github.com/bplower/opendir-dl.git
user@debian:~$ cd opendir-dl
user@debian:~/opendir-dl$ sudo pip install .
```

The executable itself isn't installed by pip, so you will need to copy it to a location in your path.
```
user@debian:~/opendir-dl$ cp opendir-dl /usr/local/bin/.
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

**Reindex everything** (planned)

This can be used to recheck existing entries. Will execute a HEAD request on each file that is indexed, updating any changed information. This will take an extremely long time
```
opendir-dl index --reindex all
```

**Reindex specific domain** (planned)

The reindex process can be narrowed down to all entries related to a domain
```
opendir-dl index --reindex domain.com
```

**Reindex specific url prefix** (planned)

The reindex process can be narrowed down to all entries starting with a specific URL
```
opendir-dl index --reindex http://domain.com/some/
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

**Standard Download** (planned)

A normal download like this will not only download the file to the local directory, but will also index the file, so you may search for it in the future.
```
opendir-dl download http://example.com/path/somefile.jpg
```

**Specify Output** (planned)

If you are downloading a specific file, you can specify the path or filename.
```
opendir-dl download --output newfile.jpg http://example.com/path/somefile.jpg
```

**Downloading by ID** (planned)

A file can be downloaded by referencing its ID rather than the URL.
```
opendir-dl download --id 12
```

This applies to the non-default databases too.
```
opendir-dl download --id 98 --db billsdb
```

**Download Search Results** (planned)

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
