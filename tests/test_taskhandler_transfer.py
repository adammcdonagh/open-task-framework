import os
import shutil
import subprocess

import pytest
from file_helper import BASE_DIRECTORY, write_test_file
from pytest_shell import fs

from opentaskpy import exceptions
from opentaskpy.taskhandlers import transfer

os.environ["OTF_NO_LOG"] = "1"
os.environ["OTF_LOG_LEVEL"] = "DEBUG"

# Create a task definition
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

# PCA move
scp_pca_move_task_definition_1 = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": "pca_move\\.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        "postCopyAction": {
            "action": "move",
            "destination": "/tmp/testFiles/archive",
        },
    },
    "destination": [
        {
            "hostname": "172.16.0.12",
            "directory": "/tmp/testFiles/dest",
            "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        },
    ],
}

scp_pca_move_task_definition_2 = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": "pca_move_2\\.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        "postCopyAction": {
            "action": "move",
            "destination": "/tmp/testFiles/archive/",
        },
    },
    "destination": [
        {
            "hostname": "172.16.0.12",
            "directory": "/tmp/testFiles/dest",
            "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        },
    ],
}

scp_pca_invalid_move_task_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": "pca_move_3\\.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        "postCopyAction": {
            "action": "move",
            "destination": "/tmp/testFiles/archive/pca_move_bad.txt",
        },
    },
    "destination": [
        {
            "hostname": "172.16.0.12",
            "directory": "/tmp/testFiles/dest",
            "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        },
    ],
}

scp_pca_rename_task_definition_1 = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": "pca_rename_1\\.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        "postCopyAction": {
            "action": "rename",
            "destination": "/tmp/testFiles/archive/",
            "pattern": "rename",
            "sub": "renamed",
        },
    },
    "destination": [
        {
            "hostname": "172.16.0.12",
            "directory": "/tmp/testFiles/dest",
            "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        },
    ],
}

scp_pca_rename_many_task_definition_1 = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": "pca_rename_many.*\\.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        "postCopyAction": {
            "action": "rename",
            "destination": "/tmp/testFiles/archive/",
            "pattern": "rename",
            "sub": "renamed",
        },
    },
    "destination": [
        {
            "hostname": "172.16.0.12",
            "directory": "/tmp/testFiles/dest",
            "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        },
    ],
}

# Proxy task definition
scp_proxy_task_definition = {
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
            "transferType": "proxy",
            "directory": "/tmp/testFiles/dest",
            "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        },
    ],
}

fail_invalid_protocol_task_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": ".*taskhandler.*\\.txt",
        "protocol": {"name": "nonexistent"},
    },
}


@pytest.fixture(scope="session")
def root_dir():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test"
    )


@pytest.fixture(scope="session")
def docker_compose_files(root_dir):
    """Get the docker-compose.yml absolute path."""
    return [
        f"{root_dir}/docker-compose.yml",
    ]


@pytest.fixture(scope="session")
def ssh_1(docker_services):
    docker_services.start("ssh_1")
    port = docker_services.port_for("ssh_1", 22)
    address = f"{docker_services.docker_ip}:{port}"
    return address


@pytest.fixture(scope="session")
def ssh_2(docker_services):
    docker_services.start("ssh_2")
    port = docker_services.port_for("ssh_2", 22)
    address = f"{docker_services.docker_ip}:{port}"
    return address


@pytest.fixture(scope="session")
def test_files(root_dir):
    # Get the root directory of the project

    structure = [
        f"{root_dir}/testFiles/ssh_1/ssh",
        f"{root_dir}/testFiles/ssh_1/src",
        f"{root_dir}/testFiles/ssh_1/dest",
        f"{root_dir}/testFiles/ssh_1/archive",
        f"{root_dir}/testFiles/ssh_2/ssh",
        f"{root_dir}/testFiles/ssh_2/src",
        f"{root_dir}/testFiles/ssh_2/dest",
        f"{root_dir}/testFiles/ssh_2/archive",
    ]
    fs.create_files(structure)


@pytest.fixture(scope="session")
def setup_ssh_keys(docker_services, root_dir, test_files, ssh_1, ssh_2):
    # Run command locally
    # if ssh key dosent exist yet
    ssh_private_key_file = f"{root_dir}/testFiles/id_rsa"
    if not os.path.isfile(ssh_private_key_file):
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-N", "", "-f", ssh_private_key_file]
        ).returncode

        # Copy the file into the ssh directory for each host
        for i in ["1", "2"]:
            shutil.copy(
                ssh_private_key_file, f"{root_dir}/testFiles/ssh_{i}/ssh/id_rsa"
            )
            shutil.copy(
                f"{root_dir}/testFiles/id_rsa.pub",
                f"{root_dir}/testFiles/ssh_{i}/ssh/authorized_keys",
            )

    # Run the docker exec command to create the user
    # Get the current uid for the running process
    uid = str(os.getuid())
    # commands to run
    commands = [
        ("usermod", "-G", "operator", "-a", "application", "-u", uid),
        ("mkdir", "-p", "/home/application/.ssh"),
        ("cp", "/tmp/testFiles/ssh/id_rsa", "/home/application/.ssh"),
        (
            "cp",
            "/tmp/testFiles/ssh/authorized_keys",
            "/home/application/.ssh/authorized_keys",
        ),
        ("chown", "-R", "application", "/home/application/.ssh"),
        ("chmod", "-R", "700", "/home/application/.ssh"),
        ("chown", "-R", "application", "/tmp/testFiles"),
    ]
    for host in ["ssh_1", "ssh_2"]:
        for command in commands:
            docker_services.execute(host, *command)


def test_invalid_protocol(setup_ssh_keys):
    transfer_obj = transfer.Transfer(
        "invalid-protocol", fail_invalid_protocol_task_definition
    )
    # Expect a UnknownProtocolError exception
    with pytest.raises(exceptions.UnknownProtocolError):
        transfer_obj._set_remote_handlers()

    # Try one with a longer protocol name
    fail_invalid_protocol_task_definition["source"]["protocol"][
        "name"
    ] = "some.module.path.ProtocolClass"
    transfer_obj = transfer.Transfer(
        "invalid-protocol", fail_invalid_protocol_task_definition
    )
    # Expect a UnknownProtocolError exception
    with pytest.raises(exceptions.UnknownProtocolError):
        transfer_obj._set_remote_handlers()


def test_remote_handler(setup_ssh_keys):
    # Validate that given a transfer with ssh protocol, that we get a remote handler of type SSH

    transfer_obj = transfer.Transfer("scp-basic", scp_task_definition)

    transfer_obj._set_remote_handlers()

    # Validate some things were set as expected
    assert transfer_obj.source_remote_handler.__class__.__name__ == "SSHTransfer"

    # dest_remote_handler should be an array
    assert isinstance(transfer_obj.dest_remote_handlers, list)
    assert len(transfer_obj.dest_remote_handlers) == 1
    #  of SSHTransfer objects
    assert transfer_obj.dest_remote_handlers[0].__class__.__name__ == "SSHTransfer"


def test_scp_basic(setup_ssh_keys):
    # Create a test file
    write_test_file(
        f"{BASE_DIRECTORY}/ssh_1/src/test.taskhandler.txt", content="test1234"
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer("scp-basic", scp_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/test.taskhandler.txt")


def test_pca_move(setup_ssh_keys):
    # Empty the PCA archive directory
    for file in os.listdir(f"{BASE_DIRECTORY}/ssh_1/archive"):
        os.remove(f"{BASE_DIRECTORY}/ssh_1/archive/{file}")

    # Create the test file
    write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/pca_move.txt", content="test1234")
    # Create a transfer object
    transfer_obj = transfer.Transfer("scp-pca-move", scp_pca_move_task_definition_1)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/pca_move.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{BASE_DIRECTORY}/ssh_1/src/pca_move.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{BASE_DIRECTORY}/ssh_1/archive/pca_move.txt")

    # Create the next test file
    write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/pca_move_2.txt", content="test1234")
    transfer_obj = transfer.Transfer("scp-pca-move-2", scp_pca_move_task_definition_2)

    # Run the transfer and expect a true status
    assert transfer_obj.run()

    # Check the destination file exists
    assert os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/pca_move_2.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{BASE_DIRECTORY}/ssh_1/src/pca_move_2.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{BASE_DIRECTORY}/ssh_1/archive/pca_move_2.txt")

    write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/pca_move_3.txt", content="test1234")
    transfer_obj = transfer.Transfer(
        "scp-pca-move-invalid", scp_pca_invalid_move_task_definition
    )

    # Run the transfer and expect a true status
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/pca_move_3.txt")
    # Check the source file should still exist
    assert os.path.exists(f"{BASE_DIRECTORY}/ssh_1/src/pca_move_3.txt")

    # Check the source file has not been archived
    assert not os.path.exists(f"{BASE_DIRECTORY}/ssh_1/archive/pca_move_bad.txt")


def test_pca_rename(setup_ssh_keys):
    # Empty the PCA archive directory
    for file in os.listdir(f"{BASE_DIRECTORY}/ssh_1/archive"):
        os.remove(f"{BASE_DIRECTORY}/ssh_1/archive/{file}")

    # Create the test file
    write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/pca_rename_1.txt", content="test1234")
    # Create a transfer object
    transfer_obj = transfer.Transfer("scp-pca-rename", scp_pca_rename_task_definition_1)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/pca_rename_1.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{BASE_DIRECTORY}/ssh_1/src/pca_rename_1.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{BASE_DIRECTORY}/ssh_1/archive/pca_renamed_1.txt")


def test_pca_rename_many(setup_ssh_keys):
    # Create the test file
    # Empty the PCA archive directory
    for file in os.listdir(f"{BASE_DIRECTORY}/ssh_1/archive"):
        os.remove(f"{BASE_DIRECTORY}/ssh_1/archive/{file}")

    # for 1 to 10
    for i in range(1, 10):
        write_test_file(
            f"{BASE_DIRECTORY}/ssh_1/src/pca_rename_many_{i}.txt", content="test1234"
        )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        "scp-pca-rename-name", scp_pca_rename_many_task_definition_1
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    for i in range(1, 10):
        assert os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/pca_rename_many_{i}.txt")
        # Check the source file no longer exists
        assert not os.path.exists(f"{BASE_DIRECTORY}/ssh_1/src/pca_rename_many_{i}.txt")

        # Check the source file has been archived
        assert os.path.exists(
            f"{BASE_DIRECTORY}/ssh_1/archive/pca_renamed_many_{i}.txt"
        )


def test_scp_proxy(setup_ssh_keys):
    # Create a test file
    write_test_file(
        f"{BASE_DIRECTORY}/ssh_1/src/test.taskhandler.proxy.txt", content="test1234"
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer("scp-basic", scp_proxy_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/test.taskhandler.proxy.txt")


# @classmethod
# def tearDownClass(cls):
#     to_remove = [
#         f"{BASE_DIRECTORY}/ssh_1/src/test.taskhandler.txt",
#         f"{BASE_DIRECTORY}/ssh_2/dest/test.taskhandler.txt",
#         f"{BASE_DIRECTORY}/ssh_1/src/test.taskhandler.proxy.txt",
#         f"{BASE_DIRECTORY}/ssh_2/dest/test.taskhandler.proxy.txt",
#     ]
#     for file in to_remove:
#         if os.path.exists(file):
#             os.remove(file)
