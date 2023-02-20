import grp
import os
import shutil
import time
import unittest

from file_helper import list_test_files, write_test_file

from opentaskpy.remotehandlers.scripts import transfer as transfer


class TransferScriptTest(unittest.TestCase):
    FILE_PREFIX = "unittest_testfile"
    BASE_DIRECTORY = "/tmp"
    FILE_CONTENT = "test1234"
    MOVED_FILES_DIR = "/tmp/test_move_files"
    DELIMITER = ","

    list = None

    # Setup, create a random list of files in /tmp to test with
    def setUp(self):
        # Ensure cleanup was run before starting
        self.tearDown()

        # Write 10 random files to /tmp
        for i in range(10):
            write_test_file(
                f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}",
                content=self.FILE_CONTENT,
            )

        self.list = list_test_files(
            self.BASE_DIRECTORY, f"{self.FILE_PREFIX}_.*", delimiter=self.DELIMITER
        )

        # If directory doesn't exist, create it
        if not os.path.exists(self.MOVED_FILES_DIR):
            os.mkdir(self.MOVED_FILES_DIR)

    def test_list_files_no_details(self):
        # Expect a list of 10 files
        list = transfer.list_files(
            f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_.*", False
        )
        self.assertEqual(len(list), 10)

        # Check that the list of files returned is the same as the list of files we created
        for i in range(10):
            self.assertIn(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}", list)

        # Expect nothing to be returned
        list = transfer.list_files(
            f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_qwhuidhqwduihqd", False
        )
        self.assertEqual(len(list), 0)

        # Try a more specific regex
        list = transfer.list_files(
            f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_.*[0-9]", False
        )
        self.assertEqual(len(list), 10)

        # Try again but with character classes
        list = transfer.list_files(
            f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_\\d+", False
        )
        self.assertEqual(len(list), 10)

    def test_list_files_details(self):
        # Expect a list of 10 files
        list = transfer.list_files(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_.*", True)
        self.assertEqual(len(list), 10)

        # Check that the list of files returned is the same as the list of files we created
        for i in range(10):
            self.assertIn(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}", list)
            # Get that value from the list
            file = list[f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}"]

            # Check that the file is a dict
            self.assertIsInstance(file, dict)

            # Check that the dict has the keys we expect
            self.assertIn("size", file)
            self.assertIn("modified_time", file)

            # Check that the size is as expected
            self.assertEqual(file["size"], len(self.FILE_CONTENT))

            # Check the modified time is within 1 second of now
            self.assertLessEqual(file["modified_time"], time.time())
            self.assertGreaterEqual(file["modified_time"], time.time() - 1)

    def test_move_files_basic(self):
        transfer.move_files(
            self.list, ",", self.MOVED_FILES_DIR, False, None, None, None, None, None
        )

        # Check that the files were moved
        for i in range(10):
            self.assertFalse(
                os.path.exists(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}")
            )
            self.assertTrue(
                os.path.exists(f"{self.MOVED_FILES_DIR}/{self.FILE_PREFIX}_{i}")
            )

    def test_move_files_create_dest_dir_1(self):
        # Try moving to a directory that doesn't exist without asking to create one and expect an error
        with self.assertRaises(FileNotFoundError):
            transfer.move_files(
                self.list,
                self.DELIMITER,
                f"{self.MOVED_FILES_DIR}/non_existent_directory",
                False,
                None,
                None,
                None,
                None,
                None,
            )

        # Now move to a directory that doesn't exist and ask to create it
        transfer.move_files(
            self.list,
            self.DELIMITER,
            f"{self.MOVED_FILES_DIR}/created_directory",
            True,
            None,
            None,
            None,
            None,
            None,
        )
        # Check that the files were moved
        for i in range(10):
            self.assertFalse(
                os.path.exists(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}")
            )
            self.assertTrue(
                os.path.exists(
                    f"{self.MOVED_FILES_DIR}/created_directory/{self.FILE_PREFIX}_{i}"
                )
            )

    def test_move_files_create_dest_dir_2(self):
        # Move the files in there again, now that the directory exists, this should still work
        transfer.move_files(
            self.list,
            self.DELIMITER,
            f"{self.BASE_DIRECTORY}/created_directory",
            True,
            None,
            None,
            None,
            None,
            None,
        )
        # Check that the files were moved
        for i in range(10):
            self.assertFalse(
                os.path.exists(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}")
            )
            self.assertTrue(
                os.path.exists(
                    f"{self.BASE_DIRECTORY}/created_directory/{self.FILE_PREFIX}_{i}"
                )
            )

        # Remove the created directory
        shutil.rmtree(f"{self.BASE_DIRECTORY}/created_directory")

    def test_move_files_rename(self):
        transfer.move_files(
            self.list,
            self.DELIMITER,
            self.MOVED_FILES_DIR,
            False,
            None,
            None,
            None,
            f"({self.FILE_PREFIX})_(.*)",
            r"\1_renamed_\2",
        )

        # Check that the files were moved
        for i in range(10):
            self.assertFalse(
                os.path.exists(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}")
            )
            self.assertTrue(
                os.path.exists(f"{self.MOVED_FILES_DIR}/{self.FILE_PREFIX}_renamed_{i}")
            )

    def test_move_files_set_owner(self):
        # Determine if the current user is root or not
        is_root = os.getuid() == 0

        # Try setting the owner. This should fail because you cannot change the owner of a file unless you are root
        if not is_root:
            with self.assertRaises(PermissionError):
                transfer.move_files(
                    self.list,
                    self.DELIMITER,
                    self.MOVED_FILES_DIR,
                    False,
                    "root",
                    None,
                    None,
                    None,
                    None,
                )

            # Check that the files were not moved
            for i in range(10):
                self.assertTrue(
                    os.path.exists(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}")
                )
                self.assertFalse(
                    os.path.exists(f"{self.MOVED_FILES_DIR}/{self.FILE_PREFIX}_{i}")
                )

        # Now try setting the owner to the current user - Doesn't really make sense, but should work without throwing an exception
        transfer.move_files(
            self.list,
            self.DELIMITER,
            self.MOVED_FILES_DIR,
            False,
            os.environ.get("USER"),
            None,
            None,
            None,
            None,
        )

        # Check the files moved
        for i in range(10):
            self.assertFalse(
                os.path.exists(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}")
            )
            self.assertTrue(
                os.path.exists(f"{self.MOVED_FILES_DIR}/{self.FILE_PREFIX}_{i}")
            )

    def test_move_files_set_group(self):
        is_root = os.getuid() == 0

        # Try setting the group. This should fail because you cannot change the group of a file if you're not a member of it
        if not is_root:
            with self.assertRaises(PermissionError):
                transfer.move_files(
                    self.list,
                    self.DELIMITER,
                    self.MOVED_FILES_DIR,
                    False,
                    None,
                    "root",
                    None,
                    None,
                    None,
                )

            # Check that the files were not moved
            for i in range(10):
                self.assertTrue(
                    os.path.exists(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}")
                )
                self.assertFalse(
                    os.path.exists(f"{self.MOVED_FILES_DIR}/{self.FILE_PREFIX}_{i}")
                )

            # Now try setting the group to one of the secondary groups of the current user
            groups = os.getgrouplist(os.environ.get("USER"), os.getgid())

            # Convert group ID to name
            groups = [grp.getgrgid(group).gr_name for group in groups]

            transfer.move_files(
                self.list,
                self.DELIMITER,
                self.MOVED_FILES_DIR,
                False,
                None,
                groups[0],
                None,
                None,
                None,
            )

            # Check the files moved
            for i in range(10):
                self.assertFalse(
                    os.path.exists(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}")
                )
                self.assertTrue(
                    os.path.exists(f"{self.MOVED_FILES_DIR}/{self.FILE_PREFIX}_{i}")
                )

            # Check the group was set correctly
            for i in range(10):
                file_group = os.stat(
                    f"{self.MOVED_FILES_DIR}/{self.FILE_PREFIX}_{i}"
                ).st_gid
                # Convert group ID to name
                file_group = grp.getgrgid(file_group).gr_name

                self.assertEqual(groups[0], file_group)

    def test_delete_files(self):
        transfer.delete_files(self.list, self.DELIMITER)

        # Check that the files were moved
        for i in range(10):
            self.assertFalse(
                os.path.exists(f"{self.BASE_DIRECTORY}/{self.FILE_PREFIX}_{i}")
            )

    # Cleanup
    def tearDown(self):
        # Delete the files we created
        list = list_test_files(
            self.BASE_DIRECTORY, f"{self.FILE_PREFIX}_.*", delimiter=self.DELIMITER
        )
        if list:
            for file in list.split(self.DELIMITER):
                os.remove(file)

        # Cleanup, remove the directory we created, if it exists
        if os.path.exists(self.MOVED_FILES_DIR):
            shutil.rmtree(self.MOVED_FILES_DIR)
