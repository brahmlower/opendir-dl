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

### Index

**Basic index**

This is the normal index. It will collect metadata for each file it indexes using the HEAD HTTP method
```
opendir-dl index http://domain.com/some/path
```

**Quick index** (planned)

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

**Basic search**

A normal search will do a substring search on the file names. This search will reatun all files with the string 'png' in the name.
```
opendir-dl search png
```

**Multi string search**

Providing multiple search terms will execute an exclusive search, meaning it will return entires whose names contain all phrases. In this case, you will only get files with names that contain both 'png' and 'jpg'.
```
opendir-dl search png jpg
```

**Inclusive search**

You can provide the inclusive flag to specify that the search should entries that match any of the terms provided. In this case, you will receive files containing at least one of 'png' and 'jpg'.
```
opendir-dl search --inclusive png jpg
```

**URL Search**

You may need to search the URL field rather than the name field. In this case, we're searching for any file whose URL contains the string 'iso/'.
```
opendir-dl search --urlsearch iso/
```

### Download

This feature hasn't been implemented quite yet. Be patient- it's only day 2 of this project :)

## For developers

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
