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

    def test_help(self):
        opendir_dl.main(["help"])

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

class CommandMenuTest(unittest.TestCase):
    def test_no_default_set(self):
        command_menu = opendir_dl.CommandMenu()
        target_command_ref = command_menu.get([])
        self.assertEqual(target_command_ref, command_menu.raise_no_default)
        with self.assertRaises(ValueError) as context:
            target_command_ref()
        expected_error = "No default action was set for this command."
        self.assertEqual(str(context.exception), expected_error)

    def test_default_set(self):
        command_menu = opendir_dl.CommandMenu()
        command_menu.set_default(help)
        self.assertEqual(command_menu.default, help)

    def test_register_string_default(self):
        command_menu = opendir_dl.CommandMenu()
        command_menu.register_string("help", None)
        self.assertEqual(command_menu.get(["help"]), None)
        command_menu.register_string("help", help)
        self.assertEqual(command_menu.get(["help"]), help)

    def test_register_string_command(self):
        command_menu = opendir_dl.CommandMenu()
        command_menu.register_string('help', help)
        self.assertTrue(command_menu.commands, {"help": help})

    def test_register_list_not_list(self):
        command_menu = opendir_dl.CommandMenu()
        with self.assertRaises(TypeError) as context:
            command_menu.register_list("this object is not a list", help)
        expected_error = "Value for command_list should be of type 'list'."
        self.assertEqual(str(context.exception), expected_error)

    def test_register_list(self):
        command_menu = opendir_dl.CommandMenu()
        command_menu.register_list(['help'], help)
        self.assertTrue(command_menu.commands, {"help": help})

    def test_get_command(self):
        command_menu = opendir_dl.CommandMenu()
        command_menu.register_list(["help", "tier2"], help)
        target_command_ref = command_menu.get(["help", "tier2"])
        self.assertEqual(target_command_ref, help)

    def test_get_unregistered_command(self):
        value_list = ["missing", "path"]
        command_menu = opendir_dl.CommandMenu()
        with self.assertRaises(ValueError) as context:
            command_menu.get(value_list)
        expected_error = "No command registered with the path '{}'.".format(value_list)
        self.assertEqual(str(context.exception), expected_error)

    def test_register_decorator(self):
        command_menu = opendir_dl.CommandMenu()
        @command_menu.register("foo")
        def foo():
            return "foo"
        self.assertEqual(command_menu.commands.keys(), ["foo"])
        target_command_ref = command_menu.get(["foo"])
        self.assertEqual(target_command_ref(), "foo")

    # def test_register_insuffiecient_information(self):
    #     # Requires refactoring/rephrasing of error thrown at line #45
    #     command_menu = opendir_dl.CommandMenu()
    #     with self.assertRaises(ValueError) as context:
    #         command_menu.register("foo")
    #     expected_error = "Insufficient arguments to register menu path."
    #     self.assertEqual(str(context.exception), expected_error)
