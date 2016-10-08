import unittest
import opendir_dl

class TestParseInput(unittest.TestCase):
    """Tests opendir_dl.utils.is_url
    """
    def test_no_values(self):
        parsed_input = opendir_dl.ParseInput.from_list([])
        self.assertEqual(parsed_input.flags, [])
        self.assertEqual(parsed_input.options, {})
        self.assertEqual(parsed_input.command, "help")
        self.assertEqual(parsed_input.command_values, [])

    def test_unreal_command(self):
        parsed_input = opendir_dl.ParseInput.from_list(["unittest"])
        self.assertEqual(parsed_input.command, "help")

    def test_flag_option_command(self):
        input_args = ["index", "--quiet", "--depth", 50, "http://localhost/"]
        parsed_input = opendir_dl.ParseInput.from_list(input_args)
        self.assertEqual(parsed_input.flags, ["quiet"])
        self.assertEqual(parsed_input.options, {"depth": 50})
        self.assertEqual(parsed_input.command, "index")
        self.assertEqual(parsed_input.command_values, ["http://localhost/"])

    def test_add_flag(self):
        parsed_input = opendir_dl.ParseInput()
        parsed_input.add_flag("quick")
        self.assertEqual(parsed_input.flags, ["quick"])

    def test_add_nonreal_flag(self):
        parsed_input = opendir_dl.ParseInput()
        with self.assertRaises(ValueError) as context:
            parsed_input.add_flag("unittest")

    def test_add_option(self):
        parsed_input = opendir_dl.ParseInput()
        parsed_input.add_option("depth", 100)
        self.assertEqual(parsed_input.options, {"depth": 100})

    def test_add_nonreal_option(self):
        parsed_input = opendir_dl.ParseInput()
        with self.assertRaises(ValueError) as context:
            parsed_input.add_option("unittest", False)
