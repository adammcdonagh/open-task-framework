import datetime
import os
import random
import shutil
import subprocess
import threading
import time
import unittest

from opentaskpy import exceptions, task_run
from tests.file_helper import BASE_DIRECTORY, write_test_file


class TransferScriptTest(unittest.TestCase):

    # Create a variable with a random number
    RANDOM = random.randint(10000, 99999)
    FILE_PREFIX = "unittest_task_run"
    MOVED_FILES_DIR = "archive"
    DELIMITER = ","

    list = None

    @classmethod
    def setUpClass(cls):
        # This all relies on both the docker containers being set up, as well as the directories existing
        # The easiest way to do this is via VSCode tasks, running the "Create test files" task

        # Create dummy variable file
        write_test_file("/tmp/variable_lookup.txt", content=f"{cls.RANDOM}")

        # Check that the dest directory exists, if not then we just fail here
        if not os.path.exists(f"{BASE_DIRECTORY}/ssh_1/dest"):
            raise Exception(
                "Destination directory does not exist. Ensure that setup has been run properly"
            )

        # Delete any existing files in the destination directory
        for file in os.listdir(f"{BASE_DIRECTORY}/ssh_1/src"):
            os.remove(f"{BASE_DIRECTORY}/ssh_1/src/{file}")

    """
    #################
    Tests for the "binary" task runner
    #################
    """

    def test_scp_basic_binary(self):
        # Use the "binary" to trigger the job with command line arguments

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        self.assertEqual(self.run_task_run("scp-basic")["returncode"], 0)

    def test_execution_basic_binary(self):
        # Use the "binary" to trigger the job with command line arguments

        self.assertEqual(self.run_task_run("df")["returncode"], 0)

    def test_batch_basic_binary(self):
        # Use the "binary" to trigger the job with command line arguments

        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        self.assertEqual(self.run_task_run("batch-basic")["returncode"], 0)

    def test_binary_invalid_config_file(self):
        # Use the "binary" to trigger the job with command line arguments

        self.assertEqual(self.run_task_run("scp-basic-non-existent")["returncode"], 1)
        # Check the output indicates that the task could not be found
        self.assertIn(
            "Couldn't find task with name: scp-basic-non-existent",
            self.run_task_run("scp-basic-non-existent")["stderr"],
        )

    def test_binary_invalid_config_directory(self):
        # Use the "binary" to trigger the job with command line arguments

        result = self.run_task_run("scp-basic", config="/tmp/non-existent")
        self.assertEqual(result["returncode"], 1)
        # Check the output indicates that no variables could be loaded
        self.assertIn(
            "Couldn't find any variables",
            result["stderr"],
        )

    """
    #################
    Tests using the Python code directly
    #################
    """

    # Disabled for now. If this runs with others, then it conflicts
    # Test having 2 tasks with the same name throws an error
    # def test_duplicate_task_name(self):
    #     # Create a transfer with the same name as an execution
    #     write_test_file(
    #         "test/cfg/transfers/df.json",
    #         content='{"command": "df", "description": "Test task", "name": "df"}',
    #     )

    #     task_runner = task_run.TaskRun("df", "test/cfg")

    #     # Verify an exception with appropriate text is thrown
    #     with self.assertRaises(DuplicateConfigFileError) as e:
    #         task_runner.run()
    #     self.assertEqual(str(e.exception), "Found more than one task with name: df")

    def test_unknown_task_name(self):

        task_runner = task_run.TaskRun("non-existent", "test/cfg")

        # Verify an exception with appropriate text is thrown
        with self.assertRaises(FileNotFoundError) as e:
            task_runner.run()
        self.assertEqual(str(e.exception), "Couldn't find task with name: non-existent")

    def test_batch_basic(self):

        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        # Use the TaskRun class to trigger the job properly
        task_runner = task_run.TaskRun("batch-basic", "test/cfg")
        self.assertTrue(task_runner.run())

    def test_execution_basic(self):

        # Use the TaskRun class to trigger the job properly
        task_runner = task_run.TaskRun("df", "test/cfg")
        self.assertTrue(task_runner.run())

    def test_execution_fail(self):

        # Use the TaskRun class to trigger the job properly
        task_runner = task_run.TaskRun("fail-command", "test/cfg")
        self.assertFalse(task_runner.run())

    def test_scp_basic(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        # Use the TaskRun class to trigger the job properly
        task_runner = task_run.TaskRun("scp-basic", "test/cfg")
        self.assertTrue(task_runner.run())

    def test_scp_basic_multiple_dests(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        # Use the TaskRun class to trigger the job properly
        task_runner = task_run.TaskRun("scp-basic-multiple-dests", "test/cfg")
        self.assertTrue(task_runner.run())

        # Check the files were copied to all 3 destinations
        self.assertTrue(os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/test.txt"))
        self.assertTrue(os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/test-2.txt"))
        self.assertTrue(os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/test-3.txt"))

    def test_scp_basic_10_files(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

        # Create 10 test files
        for i in range(10):
            write_test_file(
                f"{BASE_DIRECTORY}/ssh_1/src/test{i}.txt", content="test1234"
            )

        # Use the TaskRun class to trigger the job properly
        task_runner = task_run.TaskRun("scp-basic", "test/cfg")
        self.assertTrue(task_runner.run())

        # Check that the files were all transferred
        for i in range(10):
            self.assertTrue(os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/test{i}.txt"))

    def test_scp_basic_pull(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        task_runner = task_run.TaskRun("scp-basic-pull", "test/cfg")
        self.assertTrue(task_runner.run())

    def test_scp_basic_pca_delete(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/test1.txt
        # File will be delteted after transfer

        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test1.txt", content="test1234")

        task_runner = task_run.TaskRun("scp-basic-pca-delete", "test/cfg")
        self.assertTrue(task_runner.run())

        # Verify the file has disappeared
        self.assertFalse(os.path.exists(f"{BASE_DIRECTORY}/ssh_1/src/test1.txt"))

    def test_scp_basic_pca_move(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/test2.txt
        # File will be moved after transfer

        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test2.txt", content="test1234")

        task_runner = task_run.TaskRun("scp-basic-pca-move", "test/cfg")
        self.assertTrue(task_runner.run())

        # Verify the file has disappeared
        self.assertFalse(os.path.exists(f"{BASE_DIRECTORY}/ssh_1/src/test2.txt"))

        # Verify the file has been moved
        self.assertTrue(
            os.path.exists(f"{BASE_DIRECTORY}/ssh_1/{self.MOVED_FILES_DIR}/test2.txt")
        )

    def test_scp_source_file_conditions(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/log\..*\.log
        # File must be >10 bytes and less than 20
        # File must be older than 60 seconds and less than 600

        # Write a 11 byte long file
        write_test_file(
            f"{BASE_DIRECTORY}/ssh_1/src/log.unittset.log", content="01234567890"
        )

        # This should fail, because the file is too new
        task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
        with self.assertRaises(exceptions.FilesDoNotMeetConditionsError) as cm:
            task_runner.run()
        self.assertIn(
            "No remote files could be found to transfer", cm.exception.args[0]
        )

        # Modify the file to be older than 1 minute and try again
        os.utime(
            f"{BASE_DIRECTORY}/ssh_1/src/log.unittset.log",
            (time.time() - 61, time.time() - 61),
        )

        task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
        self.assertTrue(task_runner.run())

        # Modify the file to be older than 10 minutes and try again
        os.utime(
            f"{BASE_DIRECTORY}/ssh_1/src/log.unittset.log",
            (time.time() - 601, time.time() - 601),
        )
        task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
        with self.assertRaises(exceptions.FilesDoNotMeetConditionsError) as cm:
            task_runner.run()
        self.assertIn(
            "No remote files could be found to transfer", cm.exception.args[0]
        )

        # Write a 9 byte long file - we need to change the age again
        write_test_file(
            f"{BASE_DIRECTORY}/ssh_1/src/log.unittset.log", content="012345678"
        )
        os.utime(
            f"{BASE_DIRECTORY}/ssh_1/src/log.unittset.log",
            (time.time() - 61, time.time() - 61),
        )

        task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
        with self.assertRaises(exceptions.FilesDoNotMeetConditionsError) as cm:
            task_runner.run()
        self.assertIn(
            "No remote files could be found to transfer", cm.exception.args[0]
        )

        # Write a 21 byte long file - we need to change the age again
        write_test_file(
            f"{BASE_DIRECTORY}/ssh_1/src/log.unittset.log",
            content="012345678901234567890",
        )
        os.utime(
            f"{BASE_DIRECTORY}/ssh_1/src/log.unittset.log",
            (time.time() - 61, time.time() - 61),
        )

        task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
        with self.assertRaises(exceptions.FilesDoNotMeetConditionsError) as cm:
            task_runner.run()
        self.assertIn(
            "No remote files could be found to transfer", cm.exception.args[0]
        )

    def test_scp_file_watch(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.log
        # File should not exist to start with

        # Create the source file
        write_test_file(
            f"{BASE_DIRECTORY}/ssh_1/src/fileWatch.log", content="01234567890"
        )

        # Filewatch configured to wait 15 seconds before giving up. Expect it to fail
        task_runner = task_run.TaskRun("scp-file-watch", "test/cfg")
        with self.assertRaises(exceptions.RemoteFileNotFoundError) as cm:
            task_runner.run()
        self.assertIn("No files found after ", cm.exception.args[0])

        # This time, we run it again, but after 5 seconds, create the file
        # Create a thread that will run write_test_file after 5 seconds
        t = threading.Timer(
            5,
            write_test_file,
            [f"{BASE_DIRECTORY}/ssh_1/src/fileWatch.txt"],
            {"content": "01234567890"},
        )
        t.start()
        print("Started thread - Expect file in 5 seconds, starting task-run now...")

        task_runner = task_run.TaskRun("scp-file-watch", "test/cfg")
        self.assertTrue(task_runner.run())

        # Delete the fileWatch.txt and log file
        os.remove(f"{BASE_DIRECTORY}/ssh_1/src/fileWatch.txt")
        os.remove(f"{BASE_DIRECTORY}/ssh_1/src/fileWatch.log")

    def test_scp_log_watch(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/logYYYYWatch.log
        # File should not exist to start with
        # To succeed, the file should contain the text "someText"
        year = datetime.datetime.now().year
        # Logwatch will fail if the log file dosent exist
        task_runner = task_run.TaskRun("scp-log-watch", "test/cfg")
        with self.assertRaises(exceptions.LogWatchInitError) as cm:
            task_runner.run()
        self.assertIn("Logwatch init failed", cm.exception.args[0])

        # This time, we run it again with the file created and populated. It should fail because the file dosent contain the expected text
        # Write the file
        write_test_file(
            f"{BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log",
            content="NOT_THE_RIGHT_PATTERN",
        )

        task_runner = task_run.TaskRun("scp-log-watch", "test/cfg")
        with self.assertRaises(exceptions.LogWatchTimeoutError) as cm:
            task_runner.run()
        self.assertIn("No log entry found after ", cm.exception.args[0])

        # This time we run again, but populate the file after 5 seconds
        t = threading.Timer(
            5,
            write_test_file,
            [f"{BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log"],
            {"content": "someText"},
        )
        t.start()
        print("Started thread - Expect file in 5 seconds, starting task-run now...")
        task_runner = task_run.TaskRun("scp-log-watch", "test/cfg")
        self.assertTrue(task_runner.run())

    def test_scp_log_watch_tail(self):
        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/logYYYYWatch.log
        # File should not exist to start with
        # To succeed, the file should contain the text "someText"
        year = datetime.datetime.now().year

        # Write the matching pattern into the log, but before it runs.. This should
        # make the task fail because the pattern isn't written after the task starts
        write_test_file(
            f"{BASE_DIRECTORY}/ssh_1/src/log{year}Watch1.log", content="someText\n"
        )
        task_runner = task_run.TaskRun("scp-log-watch-tail", "test/cfg")
        with self.assertRaises(exceptions.LogWatchTimeoutError) as cm:
            task_runner.run()
        self.assertIn("No log entry found after ", cm.exception.args[0])

        # This time write the contents after 5 seconds
        t = threading.Timer(
            5,
            write_test_file,
            [f"{BASE_DIRECTORY}/ssh_1/src/log{year}Watch1.log"],
            {"content": "someText\n", "mode": "a"},
        )
        t.start()
        print("Started thread - Expect file in 5 seconds, starting task-run now...")
        task_runner = task_run.TaskRun("scp-log-watch-tail", "test/cfg")
        self.assertTrue(task_runner.run())

    def run_task_run(self, task, verbose="2", config="test/cfg"):
        # We need to run the bin/task-run script to test this
        script = "python"
        args = ["src/bin/task-run", "-t", task, "-v", verbose, "-c", config]

        # Run the script
        result = subprocess.run(
            [script] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        # Write stdout and stderr to the console
        print("\n########## STDOUT ##########")
        print(result.stdout.decode("utf-8"))
        # Get the console colour for red

        print("########## STDERR ##########")
        print(f"{result.stderr.decode('utf-8')}")

        return {
            "returncode": result.returncode,
            "stdout": result.stdout.decode("utf-8"),
            "stderr": result.stderr.decode("utf-8"),
        }

    @classmethod
    def tearDownClass(cls):
        # Get the current year
        year = datetime.datetime.now().year

        to_remove = [
            f"{BASE_DIRECTORY}/ssh_1/src/fileWatch.log",
            f"{BASE_DIRECTORY}/ssh_1/src/fileWatch.txt",
            f"{BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log",
            f"{BASE_DIRECTORY}/ssh_1/src/log{year}Watch1.log",
            "/tmp/variable_lookup.txt",
            "test/cfg/transfers/df.json",
        ]
        for file in to_remove:
            if os.path.exists(file):
                os.remove(file)

        to_remove_dirs = ["/tmp/variables1", "/tmp/variables2", "/tmp/variables3"]
        for dir in to_remove_dirs:
            if os.path.exists(dir):
                shutil.rmtree(dir)
