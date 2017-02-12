import os
import sys
import unittest
import shutil
from docopt import DocoptExit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opendir_dl'))
import opendir_dl

class MainTest(unittest.TestCase):
    def test_no_args(self):
        with self.assertRaises(DocoptExit) as context:
            opendir_dl.main(["--debug"])

    def test_arg_list(self):
        opendir_dl.main(["search", "--debug", "--inclusive", "test"])

class MakeDirPTest(unittest.TestCase):
    def test_make_missing_path(self):
        path = "mkdirp1/missing/path"
        opendir_dl.mkdir_p(path)
        self.assertTrue(os.path.exists(path))
        shutil.rmtree('mkdirp1')

    def test_make_partially_missing_path(self):
        path = "mkdirp2/path"
        opendir_dl.mkdir_p(path)
        self.assertTrue(os.path.exists(path))
        new_path = path + "/new_dir"
        opendir_dl.mkdir_p(new_path)
        self.assertTrue(os.path.exists(new_path))
        shutil.rmtree('mkdirp2')

    def test_make_existing_path(self):
        path = "mkdirp3/path/"
        opendir_dl.mkdir_p(path)
        self.assertTrue(os.path.exists(path))
        opendir_dl.mkdir_p(path)
        self.assertTrue(os.path.exists(path))
        shutil.rmtree('mkdirp3')
