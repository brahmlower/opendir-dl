# opendir-dl

This is an indexer and downloader for open directories.

Examples of how this is used:
```
sudo pip install .
./opendir-dl index http://somesite.com
```

Installation can be done in a virtual environment, but the `opendir-dl` executable assumes the python path /usr/bin/python, which will cause the file to run outside of the virtual environment. That line can be changed for testing.

You can test this on local directories by hosting a folder via pythons SimpleHTTPServer
```
python -m SimpleHTTPServer &
./opendir-dl index http://localhost:8000/
```

Working Examples:
```
opendir-dl index http://www.google.com

opendir-dl search png

opendir-dl search png jpg

opendir-dl search --inclusive png jpg

opendir-dl search --urlsearch png
```


Planned examples (some may already be working, but I'm too lazy to properly update this):
```
opendir-dl index http://www.google.com

opendir-dl download http://www.google.com

opendir-dl search "game of thrones"

opendir-dl search --type "iso"

opendir-dl search --size 1gb-5gb --site example.com
```

Library testing can be done by installing the package and importing it in idle:
```
import opendir_dl
opendir_dl.main(['list', 'of', 'arguments'])
opendir_dl.index("http://opendir.com/")
```