import json
import os
import random
import shutil
import unittest

from opentaskpy.config.loader import ConfigLoader
from tests.file_helper import BASE_DIRECTORY, write_test_file

GLOBAL_VARIABLES = None


class ConfigLoaderTest(unittest.TestCase):

    RANDOM = random.randint(10000, 99999)

    @classmethod
    def setUpClass(self):

        self.tearDownClass()
        # This all relies on both the docker containers being set up, as well as the directories existing
        # The easiest way to do this is via VSCode tasks, running the "Create test files" task

        # Create dummy variable file
        write_test_file("/tmp/variable_lookup.txt", content=f"{self.RANDOM}")

        # Check that the dest directory exists, if not then we just fail here
        if not os.path.exists(f"{BASE_DIRECTORY}/ssh_1/dest"):
            raise Exception("Destination directory does not exist. Ensure that setup has been run properly")

        # Delete any existing files in the destination directory
        for file in os.listdir(f"{BASE_DIRECTORY}/ssh_1/src"):
            os.remove(f"{BASE_DIRECTORY}/ssh_1/src/{file}")

    def test_load_task_definition(self):

        # Write a nested variable to the global variables file
        json_obj = {
            "test": "{{ SOME_VARIABLE }}6",
            "SOME_VARIABLE": "{{ SOME_VARIABLE2 }}5",
            "SOME_VARIABLE2": "test1234",
        }

        write_test_file("/tmp/variables.json.j2", content=json.dumps(json_obj))

        # Initialise the task runner
        config_loader = ConfigLoader("/tmp")
        # Create a task definition file (this isn't valid, but it proves if the evaluation of variables works)
        write_test_file("/tmp/task.json", content='{"test": "{{ test }}"}')

        expected_task_definition = {"test": "test123456"}

        # Test that the task definition is loaded correctly
        self.assertEqual(config_loader.load_task_definition("task"), expected_task_definition)

        # Test that a non existent task definition file raises an error
        os.remove("/tmp/task.json")
        with self.assertRaises(FileNotFoundError) as e:
            config_loader.load_task_definition("task")
        self.assertEqual(str(e.exception), "Couldn't find task with name: task")

    def test_load_new_variables_from_task_def(self):

        # Write a nested variable to the global variables file
        json_obj = {
            "test": "{{ SOME_VARIABLE }}6",
            "SOME_VARIABLE": "{{ SOME_VARIABLE2 }}5",
            "SOME_VARIABLE2": "test1234",
        }

        write_test_file("/tmp/variables.json.j2", content=json.dumps(json_obj))

        config_loader = ConfigLoader("/tmp")

        # Create a task definition file (this isn't valid, but it proves if the evaluation of variables works)
        write_test_file("/tmp/task.json", content='{"test": "{{ test }}", "variables": {"NEW_VARIABLE": "NEW_VALUE"}}')

        expected_task_definition = {"test": "test123456", "variables": {"NEW_VARIABLE": "NEW_VALUE"}}

        # Test that the task definition is loaded correctly
        self.assertEqual(config_loader.load_task_definition("task"), expected_task_definition)

    def test_load_global_variables(self):

        # Create a JSON file with some test variables in it
        write_test_file("/tmp/variables.json", content='{"test": "test1234"}')

        # Test that the global variables are loaded correctly
        config_loader = ConfigLoader("/tmp")

        self.assertEqual(config_loader.get_global_variables(), {"test": "test1234"})
        os.remove("/tmp/variables.json")

        # Load a .json.j2 file to check that works
        write_test_file("/tmp/variables.json.j2", content='{"test": "test1234"}')
        config_loader = ConfigLoader("/tmp")

        self.assertEqual(config_loader.get_global_variables(), {"test": "test1234"})
        os.remove("/tmp/variables.json.j2")

        # Try loading a .json file that doesn't exist
        # Check this raise a FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            config_loader = ConfigLoader("/tmp")

        # Create several files all in the same place, and ensure they all get
        # merged into one JSON object
        # Make several sub directories for various configs
        os.mkdir("/tmp/variables1")
        os.mkdir("/tmp/variables2")
        os.mkdir("/tmp/variables3")

        write_test_file("/tmp/variables1/variables.json", content='{"test": "test1234"}')
        write_test_file("/tmp/variables2/variables.json", content='{"test2": "test5678"}')
        write_test_file("/tmp/variables3/variables.json", content='{"test3": "test9012"}')

        config_loader = ConfigLoader("/tmp")
        self.assertEqual(
            config_loader.get_global_variables(), {"test": "test1234", "test2": "test5678", "test3": "test9012"}
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
        config_loader = ConfigLoader("/tmp")

        self.assertEqual(config_loader.get_global_variables(), json_resolved)

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
        config_loader = ConfigLoader("/tmp")

        self.assertEqual(config_loader.get_global_variables(), json_resolved)

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
        # Verify an exception with appropriate text is thrown
        with self.assertRaises(Exception) as e:
            config_loader = ConfigLoader("/tmp")

        self.assertEqual(str(e.exception), "Reached max depth of recursive template evaluation")

    @classmethod
    def tearDownClass(self):

        to_remove = [
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
