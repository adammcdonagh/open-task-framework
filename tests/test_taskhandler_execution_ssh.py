# pylint: skip-file
# ruff: noqa
import os
from copy import deepcopy

import pytest
from pytest_shell import fs

from opentaskpy import exceptions
from opentaskpy.taskhandlers import execution
from tests.fixtures.ssh_clients import *  # noqa: F403

os.environ["OTF_NO_LOG"] = "1"
os.environ["OTF_LOG_LEVEL"] = "DEBUG"

# Create a task definition
touch_task_definition = {
    "type": "execution",
    "hosts": ["172.16.0.11", "172.16.0.12"],
    "directory": "/tmp",
    "command": "touch /tmp/testFiles/dest/execution.txt",
    "protocol": {"name": "ssh", "credentials": {"username": "application"}},
}

fail_task_definition = {
    "type": "execution",
    "hosts": ["172.16.0.11", "172.16.0.12"],
    "directory": "/tmp",
    "command": "test -e /tmp/testFiles/src/execution.test.fail.txt",
    "protocol": {"name": "ssh", "credentials": {"username": "application"}},
}

fail_host_task_definition = {
    "type": "execution",
    "hosts": ["172.16.0.11", "172.16.255.12"],
    "directory": "/tmp",
    "command": "touch /tmp/testFiles/dest/execution.invalidhost.txt",
    "protocol": {"name": "ssh", "credentials": {"username": "application"}},
}

fail_invalid_protocol_task_definition = {
    "type": "execution",
    "hosts": ["172.16.0.11", "172.16.255.12"],
    "directory": "/tmp",
    "command": "touch /tmp/testFiles/dest/execution.invalidhost.txt",
    "protocol": {"name": "rubbish"},
}


def test_invalid_protocol():
    execution_obj = execution.Execution(
        None, "invalid-protocol", fail_invalid_protocol_task_definition
    )
    # Expect a UnknownProtocolError exception
    with pytest.raises(exceptions.UnknownProtocolError):
        execution_obj._set_remote_handlers()


def test_basic_execution(setup_ssh_keys, root_dir):
    execution_obj = execution.Execution(None, "df-basic", touch_task_definition)
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


def test_basic_execution_host_key_validation(setup_ssh_keys, root_dir):
    # Run the above test again, but this time with host key validation
    ssh_validation_task_definition = deepcopy(touch_task_definition)
    ssh_validation_task_definition["protocol"]["hostKeyValidation"] = True

    # Delete the known hosts file if it exists
    user_home = os.path.expanduser("~")
    known_hosts_file = f"{user_home}/.ssh/known_hosts"
    if os.path.exists(known_hosts_file):
        os.remove(known_hosts_file)

    execution_obj = execution.Execution(
        None, "ssh-host-key-validation", ssh_validation_task_definition
    )

    # Run the execution and expect a false status
    assert not execution_obj.run()

    # log a load of blank messages
    for _ in range(10):
        execution_obj.logger.info("")

    # SSH onto the host manually and accept the host key so it's saved to the system known hosts
    cmd = "ssh -o StrictHostKeyChecking=no application@172.16.0.11 echo 'test' && ssh -o StrictHostKeyChecking=no application@172.16.0.12 echo 'test' "
    result = subprocess.run(cmd, shell=True, capture_output=True)
    assert result.returncode == 0

    # Now rerun the execution, but this time it should work
    assert execution_obj.run()

    # Move the known host file elsewhere and pass the new location to the protocol definition
    known_hosts_file = f"{user_home}/.ssh/known_hosts"
    new_known_hosts_file = f"{user_home}/known_hosts.new"
    os.rename(known_hosts_file, new_known_hosts_file)

    ssh_validation_task_definition["protocol"]["knownHostsFile"] = new_known_hosts_file

    execution_obj = execution.Execution(
        None, "ssh-host-key-validation", ssh_validation_task_definition
    )

    # Run the execution and expect a true status
    assert execution_obj.run()


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

    execution_obj = execution.Execution(None, "task-fail", fail_task_definition)
    execution_obj._set_remote_handlers()

    # Validate some things were set as expected
    assert execution_obj.remote_handlers[0].__class__.__name__ == "SSHExecution"

    assert execution_obj.remote_handlers[1].__class__.__name__ == "SSHExecution"

    # Run the execution and expect a failure

    assert not execution_obj.run()


def test_basic_execution_invalid_host(setup_ssh_keys, root_dir):
    execution_obj = execution.Execution(None, "task-fail", fail_host_task_definition)
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
