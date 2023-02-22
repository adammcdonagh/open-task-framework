import os

import pytest
from fixtures.ssh_clients import *  # noqa:F401
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

scp_with_fin_task_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": ".*taskhandler.fin.*\\.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    },
    "destination": [
        {
            "hostname": "172.16.0.12",
            "directory": "/tmp/testFiles/dest",
            "flags": {
                "fullPath": "/tmp/testFiles/dest/scp_with_fin.fin",
            },
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
        "fileRegex": ".*taskhandler.proxy\\.txt",
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


def test_invalid_protocol():
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


def test_scp_basic(root_dir, setup_ssh_keys):
    # Create a test file
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/ssh_1/src/test.taskhandler.txt": {
                    "content": "test1234"
                }
            }
        ]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer("scp-basic", scp_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test.taskhandler.txt")


def test_scp_basic_write_fin(root_dir, setup_ssh_keys):
    # Delete any fin files that exist
    for file in os.listdir(f"{root_dir}/testFiles/ssh_2/dest"):
        if file.endswith(".fin"):
            os.remove(f"{root_dir}/testFiles/ssh_2/dest/{file}")

    # Create a test file
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/ssh_1/src/test.taskhandler.fin.txt": {
                    "content": "test1234"
                }
            }
        ]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer("scp-basic", scp_with_fin_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test.taskhandler.fin.txt")

    # Check the fin file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/scp_with_fin.fin")


def test_pca_move(root_dir, setup_ssh_keys):
    # Empty the PCA archive directory
    for file in os.listdir(f"{root_dir}/testFiles/ssh_1/archive"):
        os.remove(f"{root_dir}/testFiles/ssh_1/archive/{file}")

    # Create the test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/pca_move.txt": {"content": "test1234"}}]
    )
    # Create a transfer object
    transfer_obj = transfer.Transfer("scp-pca-move", scp_pca_move_task_definition_1)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/pca_move.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{root_dir}/testFiles/ssh_1/src/pca_move.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{root_dir}/testFiles/ssh_1/archive/pca_move.txt")

    # Create the next test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/pca_move_2.txt": {"content": "test1234"}}]
    )
    transfer_obj = transfer.Transfer("scp-pca-move-2", scp_pca_move_task_definition_2)

    # Run the transfer and expect a true status
    assert transfer_obj.run()

    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/pca_move_2.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{root_dir}/testFiles/ssh_1/src/pca_move_2.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{root_dir}/testFiles/ssh_1/archive/pca_move_2.txt")

    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/pca_move_3.txt": {"content": "test1234"}}]
    )
    transfer_obj = transfer.Transfer(
        "scp-pca-move-invalid", scp_pca_invalid_move_task_definition
    )

    # Run the transfer and expect a true status
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/pca_move_3.txt")
    # Check the source file should still exist
    assert os.path.exists(f"{root_dir}/testFiles/ssh_1/src/pca_move_3.txt")

    # Check the source file has not been archived
    assert not os.path.exists(f"{root_dir}/testFiles/ssh_1/archive/pca_move_bad.txt")


def test_pca_rename(root_dir, setup_ssh_keys):
    # Empty the PCA archive directory
    for file in os.listdir(f"{root_dir}/testFiles/ssh_1/archive"):
        os.remove(f"{root_dir}/testFiles/ssh_1/archive/{file}")

    # Create the test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/pca_rename_1.txt": {"content": "test1234"}}]
    )
    # Create a transfer object
    transfer_obj = transfer.Transfer("scp-pca-rename", scp_pca_rename_task_definition_1)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/pca_rename_1.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{root_dir}/testFiles/ssh_1/src/pca_rename_1.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{root_dir}/testFiles/ssh_1/archive/pca_renamed_1.txt")


def test_pca_rename_many(root_dir, setup_ssh_keys):
    # Create the test file
    # Empty the PCA archive directory
    for file in os.listdir(f"{root_dir}/testFiles/ssh_1/archive"):
        os.remove(f"{root_dir}/testFiles/ssh_1/archive/{file}")

    # for 1 to 10
    for i in range(1, 10):
        fs.create_files(
            [
                {
                    f"{root_dir}/testFiles/ssh_1/src/pca_rename_many_{i}.txt": {
                        "content": "test1234"
                    }
                }
            ]
        )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        "scp-pca-rename-name", scp_pca_rename_many_task_definition_1
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    for i in range(1, 10):
        assert os.path.exists(
            f"{root_dir}/testFiles/ssh_2/dest/pca_rename_many_{i}.txt"
        )
        # Check the source file no longer exists
        assert not os.path.exists(
            f"{root_dir}/testFiles/ssh_1/src/pca_rename_many_{i}.txt"
        )

        # Check the source file has been archived
        assert os.path.exists(
            f"{root_dir}/testFiles/ssh_1/archive/pca_renamed_many_{i}.txt"
        )


def test_scp_proxy(root_dir, setup_ssh_keys):
    # Create a test file
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/ssh_1/src/test.taskhandler.proxy.txt": {
                    "content": "test1234"
                }
            }
        ]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer("scp-basic", scp_proxy_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test.taskhandler.proxy.txt")
