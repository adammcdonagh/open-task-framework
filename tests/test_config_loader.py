# pylint: skip-file
# ruff: noqa
import json
import os
import random
from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time
from jinja2.exceptions import UndefinedError
from pytest_shell import fs

from opentaskpy.config.loader import ConfigLoader

GLOBAL_VARIABLES: str | None = None

RANDOM = random.randint(10000, 99999)


@pytest.fixture(scope="function")
def write_dummy_variables_file(tmpdir):
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

    # Unset any environment variables overrides
    if "OTF_VARIABLES_FILE" in os.environ:
        del os.environ["OTF_VARIABLES_FILE"]


def test_load_variables(tmpdir):
    # Ensure something satisfies the file lookup plugin
    fs.create_files(
        [
            {
                "/tmp/variable_lookup.txt": {
                    "content": "hello",
                }
            },
        ]
    )

    assert ConfigLoader("test/cfg") is not None


def test_load_variables_file_override(tmpdir):
    # Write a different variables file. Load it, and verify the variable matches
    json_obj = {
        "CUSTOM_VARS_FILE": "{{ XYZ }}1",
        "XYZ": "ABC",
    }

    fs.create_files(
        [
            {f"{tmpdir}/custom_vars_file.json.j2": {"content": json.dumps(json_obj)}},
        ]
    )

    # Set environment variable to point to the new variables file
    os.environ["OTF_VARIABLES_FILE"] = f"{tmpdir}/custom_vars_file.json.j2"

    assert ConfigLoader("test/cfg") is not None

    # Verify the variable is loaded correctly
    assert ConfigLoader("test/cfg").get_global_variables()["CUSTOM_VARS_FILE"] == "ABC1"

    # Delete the file and verify that we get an exception thrown
    os.remove(f"{tmpdir}/custom_vars_file.json.j2")
    with pytest.raises(FileNotFoundError):
        ConfigLoader("test/cfg")


def test_load_task_definition(write_dummy_variables_file, tmpdir):
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


def test_load_new_variables_from_task_def(write_dummy_variables_file, tmpdir):
    config_loader = ConfigLoader(tmpdir)

    # Create a task definition file (this isn't valid, but it proves if the evaluation of variables works)
    fs.create_files(
        [
            {
                f"{tmpdir}/task.json": {
                    "content": (
                        '{"test_var": "{{ test }}", "my_new_var": "{{ NEW_VARIABLE }}",'
                        ' "variables": {"NEW_VARIABLE": "NEW_VALUE"}}'
                    )
                }
            },
            {
                f"{tmpdir}/task1.json.j2": {
                    "content": (
                        '{"test_var": "{{ test }}","my_new_var": "{{ NEW_VARIABLE }}",'
                        ' "variables": {"NEW_VARIABLE": "NEW_VALUE"}}'
                    )
                },
            },
        ]
    )

    expected_task_definition = {
        "test_var": "test123456",
        "my_new_var": "NEW_VALUE",
        "variables": {"NEW_VARIABLE": "NEW_VALUE"},
    }

    # Test that the task definition is loaded correctly
    assert config_loader.load_task_definition("task") == expected_task_definition
    # task1 should fail because it's a jinja template and we don't support setting
    # variables in jinja templates
    config_loader = ConfigLoader(tmpdir)
    # Expect a jinja2 UndefinedError
    with pytest.raises(UndefinedError):
        config_loader.load_task_definition("task1")


def test_custom_plugin(tmpdir):
    # Create a JSON file with some test variables in it
    fs.create_files(
        [
            {
                f"{tmpdir}/variables.json.j2": {
                    "content": '{"test": "{{ lookup(\'test_plugin\') }}"}'
                }
            },
        ]
    )
    # Symlink test/cfg/plugins to tmpdir/plugins
    os.symlink(
        os.path.join(os.path.dirname(__file__), "../test/cfg", "plugins"),
        f"{tmpdir}/plugins",
    )

    # Test that the global variables are loaded correctly
    config_loader = ConfigLoader(tmpdir)

    assert config_loader.get_global_variables() == {"test": "hello"}


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
        "SOME_VARIABLE7": (
            "{{ SOME_VARIABLE8 }}{{ SOME_VARIABLE2 }}{{ SOME_VARIABLE3 }}"
        ),
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


def test_resolve_lookups_in_task_definition(tmpdir):
    json_obj = {"test": "{{ SOME_VARIABLE }}", "SOME_VARIABLE": "test1234"}

    # Create a JSON file with some test variables in it
    fs.create_files(
        [
            {f"{tmpdir}/variables.json.j2": {"content": json.dumps(json_obj)}},
        ]
    )

    # Test that the global variables are loaded correctly
    config_loader = ConfigLoader(tmpdir)

    # Now create a task definition file
    task_def = {
        "name": "test",
        "description": "{{ lookup('file', path='" + str(tmpdir) + "/lookup.txt') }}",
    }

    # Create a JSON file for the task definition
    fs.create_files(
        [
            {f"{tmpdir}/transfers/task_def.json": {"content": json.dumps(task_def)}},
            {f"{tmpdir}/lookup.txt": {"content": "FILE_LOOKUP_SUCCESS"}},
        ]
    )

    # Test that the global variables are loaded correctly
    config_loader = ConfigLoader(tmpdir)
    config_loader.get_global_variables()

    # Load the task definition
    task_def = config_loader.load_task_definition("task_def")
    # Check that the description has been resolved
    assert task_def["description"] == "FILE_LOOKUP_SUCCESS"


def test_default_date_variable_resolution(tmpdir):
    # Test that the default date variable is resolved correctly
    json_obj = {
        "YYYY": "{{ now().strftime('%Y') }}",
        "MM": "{{ now().strftime('%m') }}",
        "DD": "{{ now().strftime('%d') }}",
        "UTC_DD": "{{ utc_now().strftime('%d') }}",
        "MONTH_SHORT": "{{ now().strftime('%b') }}",
        "DAY_SHORT": "{{ now().strftime('%a') }}",
        "PREV_DD": "{{ (now()|delta_days(-1)).strftime('%d') }}",
        "PREV_UTC_DD": "{{ (utc_now()|delta_days(-1)).strftime('%d') }}",
        "PREV_MM": "{{ (now()|delta_days(-1)).strftime('%m') }}",
        "PREV_YYYY": "{{ (now()|delta_days(-1)).strftime('%Y') }}",
    }

    # Create a JSON file with some test variables in it
    fs.create_files(
        [
            {f"{tmpdir}/variables.json.j2": {"content": json.dumps(json_obj)}},
        ]
    )

    config_loader = ConfigLoader(tmpdir)
    config_loader.get_global_variables()

    # Check that the date variables are resolved correctly
    assert config_loader.get_global_variables()["YYYY"] == datetime.now().strftime("%Y")
    assert config_loader.get_global_variables()["MM"] == datetime.now().strftime("%m")
    assert config_loader.get_global_variables()["DD"] == datetime.now().strftime("%d")
    assert config_loader.get_global_variables()["UTC_DD"] == datetime.now(
        tz=UTC
    ).strftime("%d")
    assert config_loader.get_global_variables()[
        "MONTH_SHORT"
    ] == datetime.now().strftime("%b")
    assert config_loader.get_global_variables()["DAY_SHORT"] == datetime.now().strftime(
        "%a"
    )

    # Get datetime for yesterday
    yesterday = datetime.now() - timedelta(days=1)
    assert config_loader.get_global_variables()["PREV_YYYY"] == yesterday.strftime("%Y")
    assert config_loader.get_global_variables()["PREV_MM"] == yesterday.strftime("%m")
    assert config_loader.get_global_variables()["PREV_DD"] == yesterday.strftime("%d")

    # Play around with the current time. Set it to a GMT time before the clocks change
    # Change the time to before BST starts
    initial_datetime = datetime(
        year=2024,
        month=3,
        day=31,
        hour=0,
        minute=59,
        second=59,
    )

    # Set an environment variable so that the current timezone is set to GMT0BST
    os.environ["TZ"] = "GMT0BST,M3.5.0/1,M10.5.0/2"

    with freeze_time(initial_datetime) as frozen_datetime:
        assert frozen_datetime() == initial_datetime

        config_loader = ConfigLoader(tmpdir)
        # At this point, "yesterday" should be 30th March 2024
        assert config_loader.get_global_variables()["PREV_DD"] == "30"

        frozen_datetime.tick()
        # Now we should be in BST, the previous day should still be 30th March 2024
        config_loader = ConfigLoader(tmpdir)
        assert config_loader.get_global_variables()["PREV_DD"] == "30"

        # Now jump to the next day at 00:59:59 again
        frozen_datetime.tick(delta=timedelta(seconds=-1, days=1))
        # This should now return 31st March 2024
        config_loader = ConfigLoader(tmpdir)
        assert config_loader.get_global_variables()["PREV_DD"] == "31"

        # Tick and check that the date is still correct
        frozen_datetime.tick()
        config_loader = ConfigLoader(tmpdir)
        assert config_loader.get_global_variables()["PREV_DD"] == "31"

    # Replicate the above test but with PREV_UTC_DD instead
    initial_datetime = datetime(
        year=2024,
        month=3,
        day=31,
        hour=0,
        minute=59,
        second=59,
    )

    with freeze_time(initial_datetime) as frozen_datetime:
        assert frozen_datetime() == initial_datetime

        config_loader = ConfigLoader(tmpdir)
        # At this point, "yesterday" should be 30th March 2024
        assert config_loader.get_global_variables()["PREV_UTC_DD"] == "30"

        frozen_datetime.tick()
        # Now we should be in BST, but we're looking at UTC the previous day should still be 30th March 2024
        config_loader = ConfigLoader(tmpdir)
        assert config_loader.get_global_variables()["PREV_UTC_DD"] == "30"

        # Now jump to the next day at 00:59:59 again
        frozen_datetime.tick(delta=timedelta(seconds=-1, days=1))
        # This should now return 31st March 2024
        config_loader = ConfigLoader(tmpdir)
        assert config_loader.get_global_variables()["PREV_UTC_DD"] == "31"

        # Tick and check that the date is still correct
        frozen_datetime.tick()
        config_loader = ConfigLoader(tmpdir)
        assert config_loader.get_global_variables()["PREV_UTC_DD"] == "31"


def test_override_date_variable_resolution(tmpdir):
    # Test that the default date variable is resolved correctly
    json_obj = {
        "YYYY": "{{ now().strftime('%Y') }}",
        "MM": "{{ now().strftime('%m') }}",
        "DD": "{{ now().strftime('%d') }}",
        "MONTH_SHORT": "{{ now().strftime('%b') }}",
        "DAY_SHORT": "{{ now().strftime('%a') }}",
        "PREV_DD": "{{ (now()|delta_days(-1)).strftime('%d') }}",
        "PREV_MM": "{{ (now()|delta_days(-1)).strftime('%m') }}",
        "PREV_YYYY": "{{ (now()|delta_days(-1)).strftime('%Y') }}",
    }

    # Create a JSON file with some test variables in it
    fs.create_files(
        [
            {f"{tmpdir}/variables.json.j2": {"content": json.dumps(json_obj)}},
        ]
    )

    os.environ["YYYY"] = "1901"
    os.environ["MM"] = "01"
    os.environ["DD"] = "14"

    config_loader = ConfigLoader(tmpdir)
    config_loader.get_global_variables()

    # Unset the variables
    del os.environ["YYYY"]
    del os.environ["MM"]
    del os.environ["DD"]

    # Check that the date variables are resolved correctly
    assert config_loader.get_global_variables()["YYYY"] == "1901"
    assert config_loader.get_global_variables()["MM"] == "01"
    assert config_loader.get_global_variables()["DD"] == "14"


def test_override_task_variables(tmpdir, write_dummy_variables_file):
    config_loader = ConfigLoader(tmpdir)

    # Create a task definition file (this isn't valid, but it proves if the evaluation of variables works)
    fs.create_files(
        [
            {
                f"{tmpdir}/task.json": {
                    "content": (
                        '{"test_var": "{{ test }}", "variables": {"MY_VARIABLE":'
                        ' "value123"}}'
                    )
                }
            }
        ]
    )

    expected_task_definition = {
        "test_var": "test123456",
        "variables": {"MY_VARIABLE": "value123"},
    }

    # Test that the task definition is loaded correctly
    assert config_loader.load_task_definition("task") == expected_task_definition

    # Now override it with an environment variable and load it again
    os.environ["MY_VARIABLE"] = "overridden_value123"

    expected_task_definition = {
        "test_var": "test123456",
        "variables": {"MY_VARIABLE": "overridden_value123"},
    }
    new_task_definition = config_loader.load_task_definition("task")
    del os.environ["MY_VARIABLE"]
    assert new_task_definition == expected_task_definition


def test_override_task_specific_attribute(write_dummy_variables_file, tmpdir):
    # Define a basic scp transfer
    scp_task_definition = {
        "type": "transfer",
        "source": {
            "hostname": "172.16.0.11",
            "directory": "/tmp/testFiles/src",
            "fileRegex": ".*taskhandler.*\\.txt",
            "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        },
        "destination": [
            {
                "hostname": "172.16.0.12",
                "directory": "/tmp/testFiles/dest",
                "protocol": {"name": "ssh", "credentials": {"username": "application"}},
            },
        ],
    }

    # Write the task definition to a file
    fs.create_files(
        [
            {
                f"{tmpdir}/transfers/test-task.json": {
                    "content": json.dumps(scp_task_definition)
                }
            }
        ]
    )

    # Override things
    os.environ["OTF_OVERRIDE_TRANSFER_SOURCE_HOSTNAME"] = "non_existent_host"
    os.environ["OTF_OVERRIDE_TRANSFER_DESTINATION_0_HOSTNAME"] = "non_existent_host2"
    os.environ["OTF_OVERRIDE_TRANSFER_DESTINATION_0_PROTOCOL_CREDENTIALS_USERNAME"] = (
        "my_username"
    )

    # Load the task definition
    config_loader = ConfigLoader(tmpdir)
    task_definition = config_loader.load_task_definition("test-task")

    del os.environ["OTF_OVERRIDE_TRANSFER_SOURCE_HOSTNAME"]
    del os.environ["OTF_OVERRIDE_TRANSFER_DESTINATION_0_HOSTNAME"]
    del os.environ["OTF_OVERRIDE_TRANSFER_DESTINATION_0_PROTOCOL_CREDENTIALS_USERNAME"]

    # Check that the hostname has been overridden
    assert task_definition["source"]["hostname"] == "non_existent_host"
    assert task_definition["destination"][0]["hostname"] == "non_existent_host2"
    assert (
        task_definition["destination"][0]["protocol"]["credentials"]["username"]
        == "my_username"
    )
