import unittest
import random
import subprocess
from tests.file_helper import write_test_file
import time
import os
import threading
import datetime


class TransferScriptTest(unittest.TestCase):

    # Create a variable with a random number
    RANDOM = random.randint(10000, 99999)
    FILE_PREFIX = "unittest_task_run"
    BASE_DIRECTORY = "test/testFiles"
    MOVED_FILES_DIR = "archive"
    DELIMITER = ","

    list = None

    def setUp(self):
        # This all relies on both the docker containers being set up, as well as the directories existing
        # The easiest way to do this is via VSCode tasks, running the "Create test files" task

        # Check that the dest directory exists, if not then we just fail here
        if not os.path.exists(f"{self.BASE_DIRECTORY}/ssh_1/dest"):
            raise Exception("Destination directory does not exist. Ensure that setup has been run properly")

        self.tearDown()

    def test_scp_basic(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

        # Create a test file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        self.assertEqual(self.run_task_run("scp-basic")["returncode"], 0)

    def test_scp_basic_pca_delete(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.txt
        # File will be delteted after transfer

        # Create a test file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        self.assertEqual(self.run_task_run("scp-basic-pca-delete")["returncode"], 0)

        # Verify the file has disappeared
        self.assertFalse(os.path.exists(f"{self.BASE_DIRECTORY}/ssh_1/src/test.txt"))

    def test_scp_basic_pca_move(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.txt
        # File will be moved after transfer

        # Create a test file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        self.assertEqual(self.run_task_run("scp-basic-pca-move")["returncode"], 0)

        # Verify the file has disappeared
        self.assertFalse(os.path.exists(f"{self.BASE_DIRECTORY}/ssh_1/src/test.txt"))

        # Verify the file has been moved
        self.assertTrue(os.path.exists(f"{self.BASE_DIRECTORY}/ssh_1/{self.MOVED_FILES_DIR}/test.txt"))

    def test_scp_source_file_conditions(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/log\..*\.log
        # File must be >10 bytes and less than 20
        # File must be older than 60 seconds and less than 600

        # Write a 11 byte long file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", content="01234567890")

        # This should fail, because the file is too new
        self.assertEqual(self.run_task_run("scp-source-file-conditions")["returncode"], 1)

        # Modify the file to be older than 1 minute and try again
        os.utime(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", (time.time() - 61, time.time() - 61))
        self.assertEqual(self.run_task_run("scp-source-file-conditions")["returncode"], 0)

        # Modify the file to be older than 10 minutes and try again
        os.utime(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", (time.time() - 601, time.time() - 601))
        self.assertEqual(self.run_task_run("scp-source-file-conditions")["returncode"], 1)

        # Write a 9 byte long file - we need to change the age again
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", content="012345678")
        os.utime(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", (time.time() - 61, time.time() - 61))
        self.assertEqual(self.run_task_run("scp-source-file-conditions")["returncode"], 1)

        # Write a 21 byte long file - we need to change the age again
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", content="012345678901234567890")
        os.utime(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", (time.time() - 61, time.time() - 61))
        self.assertEqual(self.run_task_run("scp-source-file-conditions")["returncode"], 1)

    def test_scp_file_watch(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.log
        # File should not exist to start with

        # Filewatch configured to wait 15 seconds before giving up. Expect it to fail
        self.assertEqual(self.run_task_run("scp-file-watch")["returncode"], 1)

        # This time, we run it again, but after 5 seconds, create the file
        # Create a thread that will run write_test_file after 5 seconds
        t = threading.Timer(
            5, write_test_file, [f"{self.BASE_DIRECTORY}/ssh_1/src/fileWatch.txt"], {"content": "01234567890"}
        )
        t.start()
        print("Started thread - Expect file in 5 seconds, starting task-run now...")

        self.assertEqual(self.run_task_run("scp-file-watch")["returncode"], 0)

        # Delete the fileWatch.txt file
        os.remove(f"{self.BASE_DIRECTORY}/ssh_1/src/fileWatch.txt")

    def test_scp_log_watch(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/logYYYYWatch.log
        # File should not exist to start with
        # To succeed, the file should contain the text "someText"
        year = datetime.datetime.now().year
        # Logwatch will fail if the log file dosent exist
        task_result = self.run_task_run("scp-log-watch")
        self.assertEqual(task_result["returncode"], 1)
        # Ensure the failure reason is due to the log not existing
        self.assertIn(
            f"ERROR — Log file /tmp/testFiles/src/log{year}Watch.log does not exist",
            task_result["stderr"],
        )

        # This time, we run it again with the file created and populated. It should fail because the file dosent contain the expected text
        # Write the file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log", content="NOT_THE_RIGHT_PATTERN")
        task_result = self.run_task_run("scp-log-watch")
        self.assertEqual(task_result["returncode"], 1)
        self.assertIn("ERROR — No log entry found after 15 seconds", task_result["stderr"])

        # This time we run again, but populate the file after 5 seconds
        t = threading.Timer(
            5, write_test_file, [f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log"], {"content": "someText"}
        )
        t.start()
        print("Started thread - Expect file in 5 seconds, starting task-run now...")
        self.assertEqual(self.run_task_run("scp-log-watch")["returncode"], 0)

    def test_scp_log_watch_tail(self):
        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/logYYYYWatch.log
        # File should not exist to start with
        # To succeed, the file should contain the text "someText"
        year = datetime.datetime.now().year

        # Write the matching pattern into the log, but before it runs.. This should
        # make the task fail because the pattern isn't written after the task starts
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log", content="someText\n")
        task_result = self.run_task_run("scp-log-watch-tail")
        self.assertEqual(task_result["returncode"], 1)

        # This time write the contents after 5 seconds
        t = threading.Timer(
            5,
            write_test_file,
            [f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log"],
            {"content": "someText\n", "mode": "a"},
        )
        t.start()
        print("Started thread - Expect file in 5 seconds, starting task-run now...")
        self.assertEqual(self.run_task_run("scp-log-watch-tail")["returncode"], 0)

    def run_task_run(self, task, verbose="2", config="test/cfg"):
        # We need to run the bin/task-run script to test this
        script = "python"
        args = ["src/bin/task-run", "-t", task, "-v", verbose, "-c", config]

        # Run the script
        result = subprocess.run([script] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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

    def tearDown(self):
        # Delete the fileWatch.txt file if it exists
        if os.path.exists(f"{self.BASE_DIRECTORY}/ssh_1/src/fileWatch.txt"):
            os.remove(f"{self.BASE_DIRECTORY}/ssh_1/src/fileWatch.txt")

        # Delete the log*Watch.log file if it exists
        # Get the current year
        year = datetime.datetime.now().year
        if os.path.exists(f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log"):
            os.remove(f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log")
