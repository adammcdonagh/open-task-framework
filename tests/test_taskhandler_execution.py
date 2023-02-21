import os

from fixtures.ssh_clients import *  # noqa:F401
from pytest_shell import fs

from opentaskpy import exceptions
from opentaskpy.taskhandlers import execution

os.environ["OTF_NO_LOG"] = "1"
os.environ["OTF_LOG_LEVEL"] = "DEBUG"

# Create a task definition
touch_task_definition = {
    "type": "execution",
    "hosts": ["172.16.0.11", "172.16.0.12"],
    "username": "application",
    "directory": "/tmp",
    "command": "touch /tmp/testFiles/dest/execution.txt",
    "protocol": {"name": "ssh", "credentials": {"username": "application"}},
}

fail_task_definition = {
    "type": "execution",
    "hosts": ["172.16.0.11", "172.16.0.12"],
    "username": "application",
    "directory": "/tmp",
    "command": "test -e /tmp/testFiles/src/execution.test.fail.txt",
    "protocol": {"name": "ssh", "credentials": {"username": "application"}},
}

fail_host_task_definition = {
    "type": "execution",
    "hosts": ["172.16.0.11", "172.16.255.12"],
    "username": "application",
    "directory": "/tmp",
    "command": "touch /tmp/testFiles/dest/execution.invalidhost.txt",
    "protocol": {"name": "ssh", "credentials": {"username": "application"}},
}

fail_invalid_protocol_task_definition = {
    "type": "execution",
    "hosts": ["172.16.0.11", "172.16.255.12"],
    "username": "application",
    "directory": "/tmp",
    "command": "touch /tmp/testFiles/dest/execution.invalidhost.txt",
    "protocol": {"name": "rubbish"},
}


def test_invalid_protocol():
    execution_obj = execution.Execution(
        "invalid-protocol", fail_invalid_protocol_task_definition
    )
    # Expect a UnknownProtocolError exception
    with pytest.raises(exceptions.UnknownProtocolError):
        execution_obj._set_remote_handlers()


def test_basic_execution(setup_ssh_keys, root_dir):
    execution_obj = execution.Execution("df-basic", touch_task_definition)
    execution_obj._set_remote_handlers()

    # Ensure no test files exist already, if so delete them
    if os.path.exists(f"{root_dir}/testFiles/ssh_1/dest/execution.txt"):
        os.remove(f"{root_dir}/testFiles/ssh_1/dest/execution.txt")

    if os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/execution.txt"):
        os.remove(f"{root_dir}/testFiles/ssh_2/dest/execution.txt")

    # Validate some things were set as expected
    assert execution_obj.remote_handlers[0].__class__.__name__ == "SSHExecution"

    assert execution_obj.remote_handlers[1].__class__.__name__ == "SSHExecution"

    # Run the execution and expect a true status
    assert execution_obj.run()

    # Check the destination file exists on both hosts
    assert os.path.exists(f"{root_dir}/testFiles/ssh_1/dest/execution.txt")
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/execution.txt")


def test_basic_execution_cmd_failure(setup_ssh_keys, root_dir):
    # Write a test file to the source directory
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/ssh_1/src/execution.test.fail.txt": {
                    "content": "test1234"
                }
            }
        ]
    )

    execution_obj = execution.Execution("task-fail", fail_task_definition)
    execution_obj._set_remote_handlers()

    # Validate some things were set as expected
    assert execution_obj.remote_handlers[0].__class__.__name__ == "SSHExecution"

    assert execution_obj.remote_handlers[1].__class__.__name__ == "SSHExecution"

    # Run the execution and expect a failure

    assert not execution_obj.run()


def test_basic_execution_invalid_host(setup_ssh_keys, root_dir):
    execution_obj = execution.Execution("task-fail", fail_host_task_definition)
    execution_obj._set_remote_handlers()
    # Remove test files if they exist
    if os.path.exists(f"{root_dir}/testFiles/ssh_1/dest/execution.invalidhost.txt"):
        os.remove(f"{root_dir}/testFiles/ssh_1/dest/execution.invalidhost.txt")

    # Validate some things were set as expected
    assert execution_obj.remote_handlers[0].__class__.__name__ == "SSHExecution"

    assert execution_obj.remote_handlers[1].__class__.__name__ == "SSHExecution"

    assert not execution_obj.run()

    # But the remote file should still have been created on the valid host
    assert os.path.exists(f"{root_dir}/testFiles/ssh_1/dest/execution.invalidhost.txt")

    assert not os.path.exists(
        f"{root_dir}/testFiles/ssh_2/dest/execution.invalidhost.txt"
    )
