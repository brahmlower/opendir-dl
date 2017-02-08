import os
import sys
import unittest
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opendir_dl'))
import opendir_dl

# class ParseInputTest(unittest.TestCase):
#     """Tests opendir_dl.utils.is_url
#     """
#     def test_no_values(self):
#         command_menu = opendir_dl.CommandMenu()
#         parsed_input = opendir_dl.ParseInput.from_list(command_menu, [])
#         self.assertEqual(parsed_input.flags, [])
#         self.assertEqual(parsed_input.options, {})
#         self.assertEqual(parsed_input.command, [])
#         self.assertEqual(parsed_input.command_values, [])

#     def test_list_each(self):
#         input_args = ["index", "--quiet", "--depth", 50, "http://localhost/"]
#         command_menu = opendir_dl.CommandMenu()
#         command_menu.register(['index'], opendir_dl.commands.IndexCommand)
#         parsed_input = opendir_dl.ParseInput.from_list(command_menu, input_args)
#         self.assertEqual(parsed_input.flags, ["quiet"])
#         self.assertEqual(parsed_input.options, {"depth": 50})
#         self.assertEqual(parsed_input.command, ["index"])
#         self.assertEqual(parsed_input.command_values, ["http://localhost/"])

#     def test_set_command(self):
#         command_menu = opendir_dl.CommandMenu()
#         command_menu.register(["download"], opendir_dl.commands.DownloadCommand)
#         parsed_input = opendir_dl.ParseInput(command_menu)
#         parsed_input.set_command(["download"])
#         self.assertEqual(parsed_input.command, ["download"])

#     def test_set_nonreal_command(self):
#         command_menu = opendir_dl.CommandMenu()
#         parsed_input = opendir_dl.ParseInput(command_menu)
#         with self.assertRaises(ValueError) as context:
#             parsed_input.set_command(["nonrealcommand"])

#     def test_add_flag(self):
#         command_menu = opendir_dl.CommandMenu()
#         parsed_input = opendir_dl.ParseInput(command_menu)
#         parsed_input.add_flag("quick")
#         self.assertEqual(parsed_input.flags, ["quick"])

#     def test_add_nonreal_flag(self):
#         command_menu = opendir_dl.CommandMenu()
#         parsed_input = opendir_dl.ParseInput(command_menu)
#         with self.assertRaises(ValueError) as context:
#             parsed_input.add_flag("unittest")

#     def test_add_option(self):
#         command_menu = opendir_dl.CommandMenu()
#         parsed_input = opendir_dl.ParseInput(command_menu)
#         parsed_input.add_option("depth", 100)
#         self.assertEqual(parsed_input.options, {"depth": 100})

#     def test_add_nonreal_option(self):
#         command_menu = opendir_dl.CommandMenu()
#         parsed_input = opendir_dl.ParseInput(command_menu)
#         with self.assertRaises(ValueError) as context:
#             parsed_input.add_option("unittest", False)

class MainTest(unittest.TestCase):
    def test_no_args(self):
        opendir_dl.main(["--debug"])

    def test_arg_list(self):
        opendir_dl.main(["search", "--debug", "--inclusive" "test"])

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
