import unittest
import random
import subprocess
from tests.file_helper import write_test_file
import time
import os
import shutil
import threading
import datetime
import json
from opentaskpy import task_run, exceptions


class TransferScriptTest(unittest.TestCase):

    # Create a variable with a random number
    RANDOM = random.randint(10000, 99999)
    FILE_PREFIX = "unittest_task_run"
    BASE_DIRECTORY = "test/testFiles"
    MOVED_FILES_DIR = "archive"
    DELIMITER = ","

    list = None

    @classmethod
    def setUpClass(self):
        # This all relies on both the docker containers being set up, as well as the directories existing
        # The easiest way to do this is via VSCode tasks, running the "Create test files" task

        # Create dummy variable file
        write_test_file("/tmp/variable_lookup.txt", content=f"{self.RANDOM}")

        # Check that the dest directory exists, if not then we just fail here
        if not os.path.exists(f"{self.BASE_DIRECTORY}/ssh_1/dest"):
            raise Exception("Destination directory does not exist. Ensure that setup has been run properly")

        # Delete any existing files in the destination directory
        for file in os.listdir(f"{self.BASE_DIRECTORY}/ssh_1/src"):
            os.remove(f"{self.BASE_DIRECTORY}/ssh_1/src/{file}")

    def test_load_global_variables(self):

        # Create a JSON file with some test variables in it
        write_test_file("/tmp/variables.json", content='{"test": "test1234"}')

        # Test that the global variables are loaded correctly
        task_runner = task_run.TaskRun("test", "/tmp")
        task_runner.load_global_variables()
        self.assertEqual(task_runner.get_global_variables(), {"test": "test1234"})
        os.remove("/tmp/variables.json")

        # Load a .json.j2 file to check that works
        write_test_file("/tmp/variables.json.j2", content='{"test": "test1234"}')
        task_runner = task_run.TaskRun("test", "/tmp")
        task_runner.load_global_variables()
        self.assertEqual(task_runner.get_global_variables(), {"test": "test1234"})
        os.remove("/tmp/variables.json.j2")

        # Try loading a .json file that doesn't exist
        task_runner = task_run.TaskRun("test", "/tmp")
        # Check this raise a FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            task_runner.load_global_variables()

        # Create several files all in the same place, and ensure they all get
        # merged into one JSON object
        # Make several sub directories for various configs
        os.mkdir("/tmp/variables1")
        os.mkdir("/tmp/variables2")
        os.mkdir("/tmp/variables3")

        write_test_file("/tmp/variables1/variables.json", content='{"test": "test1234"}')
        write_test_file("/tmp/variables2/variables.json", content='{"test2": "test5678"}')
        write_test_file("/tmp/variables3/variables.json", content='{"test3": "test9012"}')

        task_runner = task_run.TaskRun("test", "/tmp")
        task_runner.load_global_variables()
        self.assertEqual(
            task_runner.get_global_variables(), {"test": "test1234", "test2": "test5678", "test3": "test9012"}
        )
        # Remove the directories
        os.remove("/tmp/variables1/variables.json")
        os.remove("/tmp/variables2/variables.json")
        os.remove("/tmp/variables3/variables.json")
        os.rmdir("/tmp/variables1")
        os.rmdir("/tmp/variables2")
        os.rmdir("/tmp/variables3")

    def test_resolve_templated_variables(self):

        json_obj = {"test": "{{ SOME_VARIABLE }}", "SOME_VARIABLE": "test1234"}
        json_resolved = {"test": "test1234", "SOME_VARIABLE": "test1234"}

        # Create a JSON file with some test variables in it
        write_test_file("/tmp/variables.json.j2", content=json.dumps(json_obj))

        # Test that the global variables are loaded correctly
        task_runner = task_run.TaskRun("test", "/tmp")
        task_runner.load_global_variables()
        task_runner.resolve_templated_variables()
        self.assertEqual(task_runner.get_global_variables(), json_resolved)

        # Test again, but with a nested variable
        json_obj = {
            "test": "{{ SOME_VARIABLE }}6",
            "SOME_VARIABLE": "{{ SOME_VARIABLE2 }}5",
            "SOME_VARIABLE2": "test1234",
        }

        json_resolved = {"test": "test123456", "SOME_VARIABLE": "test12345", "SOME_VARIABLE2": "test1234"}

        # Create a JSON file with some test variables in it
        write_test_file("/tmp/variables.json.j2", content=json.dumps(json_obj))

        # Test that the global variables are loaded correctly
        task_runner = task_run.TaskRun("test", "/tmp")
        task_runner.load_global_variables()
        task_runner.resolve_templated_variables()
        self.assertEqual(task_runner.get_global_variables(), json_resolved)

        # Final test is to next 6 times, this should error as the limit is 5
        json_obj = {
            "test": "{{ SOME_VARIABLE }}7",
            "SOME_VARIABLE": "{{ SOME_VARIABLE2 }}6",
            "SOME_VARIABLE2": "{{ SOME_VARIABLE3 }}5",
            "SOME_VARIABLE3": "{{ SOME_VARIABLE4 }}4",
            "SOME_VARIABLE4": "{{ SOME_VARIABLE5 }}3",
            "SOME_VARIABLE5": "{{ SOME_VARIABLE6 }}2",
            "SOME_VARIABLE6": "{{ SOME_VARIABLE7 }}1",
            "SOME_VARIABLE7": "{{ SOME_VARIABLE8 }}{{ SOME_VARIABLE2 }}{{ SOME_VARIABLE3 }}",
            "SOME_VARIABLE8": "test1234",
        }

        # Create a JSON file with some test variables in it
        write_test_file("/tmp/variables.json.j2", content=json.dumps(json_obj))

        # Test that the global variables are loaded correctly
        task_runner = task_run.TaskRun("test", "/tmp")
        task_runner.load_global_variables()

        # Verify an exception with appropriate text is thrown
        with self.assertRaises(Exception) as e:
            task_runner.resolve_templated_variables()
        self.assertEqual(str(e.exception), "Reached max depth of recursive template evaluation")

    def test_load_task_definition(self):

        # Write a nested variable to the global variables file
        json_obj = {
            "test": "{{ SOME_VARIABLE }}6",
            "SOME_VARIABLE": "{{ SOME_VARIABLE2 }}5",
            "SOME_VARIABLE2": "test1234",
        }

        write_test_file("/tmp/variables.json.j2", content=json.dumps(json_obj))

        # Initialise the task runner
        task_runner = task_run.TaskRun("test", "/tmp")
        task_runner.load_global_variables()
        task_runner.resolve_templated_variables()

        # Create a task definition file (this isn't valid, but it proves if the evaluation of variables works)
        write_test_file("/tmp/task.json", content='{"test": "{{ test }}"}')

        expected_task_definition = {"test": "test123456"}

        # Test that the task definition is loaded correctly
        task_runner = task_run.TaskRun("task", "/tmp")
        self.assertEqual(task_runner.load_task_definition("/tmp/task.json"), expected_task_definition)

        # Test that a non existent task definition file raises an error
        task_runner = task_run.TaskRun("test", "/tmp")
        os.remove("/tmp/task.json")
        with self.assertRaises(FileNotFoundError) as e:
            task_runner.load_task_definition("/tmp/task.json")
        self.assertEqual(str(e.exception), "[Errno 2] No such file or directory: '/tmp/task.json'")

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
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        self.assertEqual(self.run_task_run("scp-basic")["returncode"], 0)

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

    def test_scp_basic(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

        # Create a test file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        # Use the TaskRun class to trigger the job properly
        task_runner = task_run.TaskRun("scp-basic", "test/cfg")
        self.assertEqual(task_runner.run(), True)

    def test_scp_basic_pull(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

        # Create a test file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        task_runner = task_run.TaskRun("scp-basic-pull", "test/cfg")
        self.assertEqual(task_runner.run(), True)

    def test_scp_basic_pca_delete(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/test1.txt
        # File will be delteted after transfer

        # Create a test file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/test1.txt", content="test1234")

        task_runner = task_run.TaskRun("scp-basic-pca-delete", "test/cfg")
        self.assertEqual(task_runner.run(), True)

        # Verify the file has disappeared
        self.assertFalse(os.path.exists(f"{self.BASE_DIRECTORY}/ssh_1/src/test1.txt"))

    def test_scp_basic_pca_move(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/test2.txt
        # File will be moved after transfer

        # Create a test file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/test2.txt", content="test1234")

        task_runner = task_run.TaskRun("scp-basic-pca-move", "test/cfg")
        self.assertEqual(task_runner.run(), True)

        # Verify the file has disappeared
        self.assertFalse(os.path.exists(f"{self.BASE_DIRECTORY}/ssh_1/src/test2.txt"))

        # Verify the file has been moved
        self.assertTrue(os.path.exists(f"{self.BASE_DIRECTORY}/ssh_1/{self.MOVED_FILES_DIR}/test2.txt"))

    def test_scp_source_file_conditions(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/log\..*\.log
        # File must be >10 bytes and less than 20
        # File must be older than 60 seconds and less than 600

        # Write a 11 byte long file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", content="01234567890")

        # This should fail, because the file is too new
        task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
        with self.assertRaises(exceptions.FilesDoNotMeetConditionsError) as cm:
            task_runner.run()
        self.assertIn("No remote files could be found to transfer", cm.exception.args[0])

        # Modify the file to be older than 1 minute and try again
        os.utime(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", (time.time() - 61, time.time() - 61))

        task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
        self.assertEqual(task_runner.run(), True)

        # Modify the file to be older than 10 minutes and try again
        os.utime(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", (time.time() - 601, time.time() - 601))
        task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
        with self.assertRaises(exceptions.FilesDoNotMeetConditionsError) as cm:
            task_runner.run()
        self.assertIn("No remote files could be found to transfer", cm.exception.args[0])

        # Write a 9 byte long file - we need to change the age again
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", content="012345678")
        os.utime(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", (time.time() - 61, time.time() - 61))

        task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
        with self.assertRaises(exceptions.FilesDoNotMeetConditionsError) as cm:
            task_runner.run()
        self.assertIn("No remote files could be found to transfer", cm.exception.args[0])

        # Write a 21 byte long file - we need to change the age again
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", content="012345678901234567890")
        os.utime(f"{self.BASE_DIRECTORY}/ssh_1/src/log.unittset.log", (time.time() - 61, time.time() - 61))

        task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
        with self.assertRaises(exceptions.FilesDoNotMeetConditionsError) as cm:
            task_runner.run()
        self.assertIn("No remote files could be found to transfer", cm.exception.args[0])

    def test_scp_file_watch(self):

        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/.*\.log
        # File should not exist to start with

        # Create the source file
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/fileWatch.log", content="01234567890")

        # Filewatch configured to wait 15 seconds before giving up. Expect it to fail
        task_runner = task_run.TaskRun("scp-file-watch", "test/cfg")
        with self.assertRaises(exceptions.RemoteFileNotFoundError) as cm:
            task_runner.run()
        self.assertIn("No files found after ", cm.exception.args[0])

        # This time, we run it again, but after 5 seconds, create the file
        # Create a thread that will run write_test_file after 5 seconds
        t = threading.Timer(
            5, write_test_file, [f"{self.BASE_DIRECTORY}/ssh_1/src/fileWatch.txt"], {"content": "01234567890"}
        )
        t.start()
        print("Started thread - Expect file in 5 seconds, starting task-run now...")

        task_runner = task_run.TaskRun("scp-file-watch", "test/cfg")
        self.assertEqual(task_runner.run(), True)

        # Delete the fileWatch.txt and log file
        os.remove(f"{self.BASE_DIRECTORY}/ssh_1/src/fileWatch.txt")
        os.remove(f"{self.BASE_DIRECTORY}/ssh_1/src/fileWatch.log")

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
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log", content="NOT_THE_RIGHT_PATTERN")

        task_runner = task_run.TaskRun("scp-log-watch", "test/cfg")
        with self.assertRaises(exceptions.LogWatchTimeoutError) as cm:
            task_runner.run()
        self.assertIn("No log entry found after ", cm.exception.args[0])

        # This time we run again, but populate the file after 5 seconds
        t = threading.Timer(
            5, write_test_file, [f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log"], {"content": "someText"}
        )
        t.start()
        print("Started thread - Expect file in 5 seconds, starting task-run now...")
        task_runner = task_run.TaskRun("scp-log-watch", "test/cfg")
        self.assertEqual(task_runner.run(), True)

    def test_scp_log_watch_tail(self):
        # Required files for this test:
        # ssh_1 : test/testFiles/ssh_1/src/logYYYYWatch.log
        # File should not exist to start with
        # To succeed, the file should contain the text "someText"
        year = datetime.datetime.now().year

        # Write the matching pattern into the log, but before it runs.. This should
        # make the task fail because the pattern isn't written after the task starts
        write_test_file(f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch1.log", content="someText\n")
        task_runner = task_run.TaskRun("scp-log-watch-tail", "test/cfg")
        with self.assertRaises(exceptions.LogWatchTimeoutError) as cm:
            task_runner.run()
        self.assertIn("No log entry found after ", cm.exception.args[0])

        # This time write the contents after 5 seconds
        t = threading.Timer(
            5,
            write_test_file,
            [f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch1.log"],
            {"content": "someText\n", "mode": "a"},
        )
        t.start()
        print("Started thread - Expect file in 5 seconds, starting task-run now...")
        task_runner = task_run.TaskRun("scp-log-watch-tail", "test/cfg")
        self.assertEqual(task_runner.run(), True)

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

    @classmethod
    def tearDownClass(self):
        # Get the current year
        year = datetime.datetime.now().year

        to_remove = [
            f"{self.BASE_DIRECTORY}/ssh_1/src/fileWatch.log",
            f"{self.BASE_DIRECTORY}/ssh_1/src/fileWatch.txt",
            f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch.log",
            f"{self.BASE_DIRECTORY}/ssh_1/src/log{year}Watch1.log",
            "/tmp/variable_lookup.txt",
            "/tmp/variables1/variables.json",
            "/tmp/variables2/variables.json",
            "/tmp/variables3/variables.json",
            "/tmp/variables.json.j2",
            "/tmp/task.json",
        ]
        for file in to_remove:
            if os.path.exists(file):
                os.remove(file)

        to_remove_dirs = ["/tmp/variables1", "/tmp/variables2", "/tmp/variables3"]
        for dir in to_remove_dirs:
            if os.path.exists(dir):
                shutil.rmtree(dir)
