from setuptools import setup

setup(
    # Application name:
    name = "opendir_dl",

    # Version number:
    version = "0.0.0",

    # Application author details:
    author = "Brahm Lower",
    author_email = "bplower@gmail.com",

    # License
    license = "",

    # Packages:
    packages = ["opendir_dl"],

    package_data = {'': ['opendir_dl/help.txt']},

    scripts = ['opendir-dl'],

    # Details:
    url = "https://github.com/bplower/opendir-dl",

    # Description:
    description = "This is an indexer and downloader for open directories.",

    # Dependant packages:
    install_requires = [
        "httplib2",
        "sqlalchemy",
        "prettytable",
        "BeautifulSoup4"
    ],
)
