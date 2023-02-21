import json
import os
import random

import pytest
from file_helper import write_test_file
from pytest_shell import fs

from opentaskpy.config.loader import ConfigLoader

GLOBAL_VARIABLES = None

RANDOM = random.randint(10000, 99999)


def test_load_task_definition(tmpdir):
    # Write a nested variable to the global variables file
    json_obj = {
        "test": "{{ SOME_VARIABLE }}6",
        "SOME_VARIABLE": "{{ SOME_VARIABLE2 }}5",
        "SOME_VARIABLE2": "test1234",
    }

    write_test_file(f"{tmpdir}/variables.json.j2", content=json.dumps(json_obj))

    # Initialise the task runner
    config_loader = ConfigLoader(tmpdir)
    # Create a task definition file (this isn't valid, but it proves if the evaluation of variables works)
    fs.create_files([{f"{tmpdir}/task.json": {"content": '{"test": "{{ test }}"}'}}])

    expected_task_definition = {"test": "test123456"}

    # Test that the task definition is loaded correctly
    assert config_loader.load_task_definition("task") == expected_task_definition

    # Test that a non existent task definition file raises an error
    os.remove(f"{tmpdir}/task.json")
    with pytest.raises(FileNotFoundError) as e:
        config_loader.load_task_definition("task")
    assert e.value.args[0] == "Couldn't find task with name: task"


def test_load_new_variables_from_task_def(tmpdir):
    # Write a nested variable to the global variables file
    json_obj = {
        "test": "{{ SOME_VARIABLE }}6",
        "SOME_VARIABLE": "{{ SOME_VARIABLE2 }}5",
        "SOME_VARIABLE2": "test1234",
    }

    fs.create_files(
        [
            {f"{tmpdir}/variables.json.j2": {"content": json.dumps(json_obj)}},
        ]
    )

    config_loader = ConfigLoader(tmpdir)

    # Create a task definition file (this isn't valid, but it proves if the evaluation of variables works)
    fs.create_files(
        [
            {
                f"{tmpdir}/task.json": {
                    "content": '{"test": "{{ test }}", "variables": {"NEW_VARIABLE": "NEW_VALUE"}}'
                }
            }
        ]
    )

    expected_task_definition = {
        "test": "test123456",
        "variables": {"NEW_VARIABLE": "NEW_VALUE"},
    }

    # Test that the task definition is loaded correctly
    assert config_loader.load_task_definition("task") == expected_task_definition


def test_load_global_variables(tmpdir):
    # Create a JSON file with some test variables in it
    fs.create_files(
        [
            {f"{tmpdir}/variables.json": {"content": '{"test": "test1234"}'}},
        ]
    )

    # Test that the global variables are loaded correctly
    config_loader = ConfigLoader(tmpdir)

    assert config_loader.get_global_variables() == {"test": "test1234"}
    os.remove(f"{tmpdir}/variables.json")

    # Load a .json.j2 file to check that works
    fs.create_files(
        [{f"{tmpdir}/variables.json.j2": {"content": '{"test": "test1234"}'}}]
    )

    config_loader = ConfigLoader(tmpdir)

    assert config_loader.get_global_variables() == {"test": "test1234"}
    os.remove(f"{tmpdir}/variables.json.j2")

    # Try loading a .json file that doesn't exist
    # Check this raise a FileNotFoundError
    with pytest.raises(FileNotFoundError):
        config_loader = ConfigLoader(tmpdir)

    # Create several files all in the same place, and ensure they all get
    # merged into one JSON object
    # Make several sub directories for various configs
    os.mkdir(f"{tmpdir}/variables1")
    os.mkdir(f"{tmpdir}/variables2")
    os.mkdir(f"{tmpdir}/variables3")

    fs.create_files(
        [
            {
                f"{tmpdir}/variables1/variables.json": {
                    "content": '{"test": "test1234"}'
                }
            },
            {
                f"{tmpdir}/variables2/variables.json": {
                    "content": '{"test2": "test5678"}'
                }
            },
            {
                f"{tmpdir}/variables3/variables.json": {
                    "content": '{"test3": "test9012"}'
                }
            },
        ]
    )
    config_loader = ConfigLoader(tmpdir)
    assert config_loader.get_global_variables() == {
        "test": "test1234",
        "test2": "test5678",
        "test3": "test9012",
    }


def test_resolve_templated_variables(tmpdir):
    json_obj = {"test": "{{ SOME_VARIABLE }}", "SOME_VARIABLE": "test1234"}
    json_resolved = {"test": "test1234", "SOME_VARIABLE": "test1234"}

    # Create a JSON file with some test variables in it
    fs.create_files(
        [
            {f"{tmpdir}/variables.json.j2": {"content": json.dumps(json_obj)}},
        ]
    )

    # Test that the global variables are loaded correctly
    config_loader = ConfigLoader(tmpdir)

    assert config_loader.get_global_variables() == json_resolved

    # Remove the variables file
    os.remove(f"{tmpdir}/variables.json.j2")

    # Test again, but with a nested variable
    json_obj = {
        "test": "{{ SOME_VARIABLE }}6",
        "SOME_VARIABLE": "{{ SOME_VARIABLE2 }}5",
        "SOME_VARIABLE2": "test1234",
    }

    json_resolved = {
        "test": "test123456",
        "SOME_VARIABLE": "test12345",
        "SOME_VARIABLE2": "test1234",
    }

    # Create a JSON file with some test variables in it
    fs.create_files(
        [
            {f"{tmpdir}/variables.json.j2": {"content": json.dumps(json_obj)}},
        ]
    )

    # Test that the global variables are loaded correctly
    config_loader = ConfigLoader(tmpdir)

    assert config_loader.get_global_variables() == json_resolved

    # Remove the variables file
    os.remove(f"{tmpdir}/variables.json.j2")

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
    fs.create_files(
        [
            {f"{tmpdir}/variables.json.j2": {"content": json.dumps(json_obj)}},
        ]
    )

    # Test that the global variables are loaded correctly
    # Verify an exception with appropriate text is thrown
    with pytest.raises(Exception) as e:
        config_loader = ConfigLoader(tmpdir)

    assert e.value.args[0] == "Reached max depth of recursive template evaluation"
