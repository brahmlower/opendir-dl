from setuptools import setup

setup(
    name = "opendir_dl",
    version = "0.1.0",
    author = "Brahm Lower",
    author_email = "bplower@gmail.com",
    license = "",
    python_requires='>=3',
    packages = ["opendir_dl"],
    url = "https://github.com/bplower/opendir-dl",
    description = "This is an indexer and downloader for open directories.",
    install_requires = [
        "docopt",
        "PyYAML",
        "appdirs",
        "httplib2",
        "SQLAlchemy",
        "prettytable",
        "lxml",
        "BeautifulSoup4"
    ],
    entry_points={
        'console_scripts': ['opendir-dl = opendir_dl.__init__:main']
    }
)
