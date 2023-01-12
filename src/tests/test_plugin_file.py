import unittest
import os
from opentaskpy.plugins.lookup.file import run
from tests.file_helper import write_test_file


class FilePluginTest(unittest.TestCase):
    def test_file_plugin_missing_path(self):
        with self.assertRaises(Exception) as ex:
            run()

        self.assertEqual(str(ex.exception), "Missing kwarg: 'path' while trying to run lookup plugin 'file'")

    def test_file_plugin_file_not_found(self):
        with self.assertRaises(FileNotFoundError) as ex:
            run(path="/tmp/does_not_exist.txt")

        self.assertEqual(
            str(ex.exception), "File /tmp/does_not_exist.txt does not exist while trying to run lookup plugin 'file'"
        )

    def test_file_plugin(self):
        # Run test with a valid variable file, and ensure it's read and contains that value
        file_name = "/tmp/test.variable.txt"
        content = "test1234"
        write_test_file(file_name, content)
        result = run(path=file_name)
        self.assertEqual(result, content)

    def tearDown(self):
        # Remove /tmp/test.variable.txt if it exists
        if os.path.isfile("/tmp/test.variable.txt"):
            os.remove("/tmp/test.variable.txt")
