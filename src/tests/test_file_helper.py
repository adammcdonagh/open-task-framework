import unittest
import os
from tests.file_helper import write_test_file, list_test_files


class FileHelperTest(unittest.TestCase):
    def test_write_test_file_with_content(self):
        file_name = "/tmp/test.txt"
        content = "test1234"
        write_test_file(file_name, content)
        with open(file_name, "r") as f:
            self.assertEqual(f.read(), content)

    def test_write_test_file_with_length(self):
        file_name = "/tmp/test.txt"
        length = 100
        write_test_file(file_name, length=length)
        with open(file_name, "r") as f:
            self.assertEqual(len(f.read()), length)

    def test_list_test_files(self):
        file_name = "/tmp/test.txt"
        content = "test1234"
        write_test_file(file_name, content)
        list = list_test_files("/tmp", "test.txt", ",")
        self.assertEqual(list, file_name)

        # Do the same but with a regex
        list = list_test_files("/tmp", "test.*", ",")
        self.assertEqual(list, file_name)

    def tearDown(self):
        os.remove("/tmp/test.txt")
