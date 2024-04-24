# pylint: skip-file
# ruff: noqa
import os

import pytest

from opentaskpy import exceptions
from opentaskpy.taskhandlers import execution
from tests.fixtures.ssh_clients import *  # noqa: F403

os.environ["OTF_NO_LOG"] = "1"
os.environ["OTF_LOG_LEVEL"] = "DEBUG"

local_test_dir = "/tmp/local_tests"

# Create a task definition
touch_task_definition = {
    "type": "execution",
    "directory": "/tmp",
    "command": f"touch {local_test_dir}/dest/execution.txt",
    "protocol": {"name": "local"},
}

fail_task_definition = {
    "type": "execution",
    "directory": "/tmp",
    "command": f"test -e {local_test_dir}/src/execution.test.fail.txt",
    "protocol": {"name": "local"},
}

fail_host_task_definition = {
    "type": "execution",
    "directory": "/tmp",
    "command": f"touch {local_test_dir}/dest/execution.invalidhost.txt",
    "protocol": {"name": "local"},
}

fail_invalid_protocol_task_definition = {
    "type": "execution",
    "directory": "/tmp",
    "command": f"touch {local_test_dir}/dest/execution.invalidhost.txt",
    "protocol": {"name": "rubbish"},
}


@pytest.fixture(scope="session")
def setup_local_test_dir():
    os.makedirs(f"{local_test_dir}/src", exist_ok=True)
    os.makedirs(f"{local_test_dir}/dest", exist_ok=True)
    os.makedirs(f"{local_test_dir}/archive", exist_ok=True)

    return local_test_dir


def test_invalid_protocol():
    execution_obj = execution.Execution(
        None, "invalid-protocol", fail_invalid_protocol_task_definition
    )
    # Expect a UnknownProtocolError exception
    with pytest.raises(exceptions.UnknownProtocolError):
        execution_obj._set_remote_handlers()


def test_basic_execution(setup_local_test_dir):
    execution_obj = execution.Execution(None, "df-basic", touch_task_definition)
    execution_obj._set_remote_handlers()

    # Ensure no test files exist already, if so delete them
    if os.path.exists(f"{local_test_dir}/dest/execution.txt"):
        os.remove(f"{local_test_dir}/dest/execution.txt")

    # Validate some things were set as expected
    assert execution_obj.remote_handlers[0].__class__.__name__ == "LocalExecution"

    # Run the execution and expect a true status
    assert execution_obj.run()

    # Check the destination file exists on both hosts
    assert os.path.exists(f"{local_test_dir}/dest/execution.txt")


def test_basic_execution_cmd_failure(setup_local_test_dir):
    execution_obj = execution.Execution(None, "task-fail", fail_task_definition)
    execution_obj._set_remote_handlers()

    # Validate some things were set as expected
    assert execution_obj.remote_handlers[0].__class__.__name__ == "LocalExecution"

    # Run the execution and expect a failure

    assert not execution_obj.run()
