# pylint: skip-file
# ruff: noqa
import os
from copy import deepcopy
from datetime import datetime

import pytest
from pytest_shell import fs

from opentaskpy import exceptions
from opentaskpy.taskhandlers import transfer
from tests.fixtures.ssh_clients import *  # noqa: F403, F401

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


scp_task_definition_no_permissions = {
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
            "directory": "/etc",
            "rename": {
                "pattern": ".*taskhandler.*\\.txt",
                "sub": "passwd",
            },
            "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        },
    ],
}

scp_file_watch_task_no_error_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": ".*nofileexists.*\\.txt",
        "fileWatch": {"timeout": 1},
        "error": False,
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    },
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

scp_destination_file_rename = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": "dest_rename.*taskhandler.*\\.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    },
    "destination": [
        {
            "hostname": "172.16.0.12",
            "directory": "/tmp/testFiles/dest",
            "rename": {
                "pattern": "t(askha)ndler",
                "sub": "T\\1NDLER",
            },
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
        None, "invalid-protocol", fail_invalid_protocol_task_definition
    )
    # Expect a UnknownProtocolError exception
    with pytest.raises(exceptions.UnknownProtocolError):
        transfer_obj._set_remote_handlers()

    # Try one with a longer protocol name
    fail_invalid_protocol_task_definition["source"]["protocol"][
        "name"
    ] = "some.module.path.ProtocolClass"
    transfer_obj = transfer.Transfer(
        None, "invalid-protocol", fail_invalid_protocol_task_definition
    )
    # Expect a UnknownProtocolError exception
    with pytest.raises(exceptions.UnknownProtocolError):
        transfer_obj._set_remote_handlers()


def test_remote_handler(setup_ssh_keys):
    # Validate that given a transfer with ssh protocol, that we get a remote handler of type SSH

    transfer_obj = transfer.Transfer(None, "scp-basic", scp_task_definition)

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
    transfer_obj = transfer.Transfer(None, "scp-basic", scp_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test.taskhandler.txt")


def test_scp_basic_key_from_protocol_definition(root_dir, ssh_key_file):
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
    scp_task_definition_copy = deepcopy(scp_task_definition)
    scp_task_definition_copy["source"]["protocol"]["credentials"]["key"] = ssh_key_file
    transfer_obj = transfer.Transfer(None, "scp-basic", scp_task_definition_copy)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test.taskhandler.txt")


def test_scp_basic_create_dest_dir(root_dir, setup_ssh_keys):
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
    scp_task_definition_copy = deepcopy(scp_task_definition)
    scp_task_definition_copy["destination"][0][
        "directory"
    ] = f"/tmp/testFiles/{datetime.now().strftime('%s')}"
    scp_task_definition_copy["destination"][0]["createDirectoryIfNotExists"] = True
    transfer_obj = transfer.Transfer(None, "scp-basic", scp_task_definition_copy)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test.taskhandler.txt")


def test_scp_basic_no_permissions(root_dir, setup_sftp_keys):
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
    transfer_obj = transfer.Transfer(
        None, "scp-basic-no-permissions", scp_task_definition_no_permissions
    )

    # Run the transfer and expect a true status
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()


def test_scp_filewatch_no_error(setup_ssh_keys):
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "scp-no-file-no-error", scp_file_watch_task_no_error_definition
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()


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
    transfer_obj = transfer.Transfer(None, "scp-basic", scp_with_fin_task_definition)

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
    transfer_obj = transfer.Transfer(
        None, "scp-pca-move", scp_pca_move_task_definition_1
    )

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
    transfer_obj = transfer.Transfer(
        None, "scp-pca-move-2", scp_pca_move_task_definition_2
    )

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
        None, "scp-pca-move-invalid", scp_pca_invalid_move_task_definition
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


def test_destination_file_rename(root_dir, setup_ssh_keys):
    # Random number
    import random

    random_no = random.randint(1, 1000)

    # Create the test file
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/ssh_1/src/dest_rename_{random_no}_taskhandler.txt": {
                    "content": "test1234"
                }
            }
        ]
    )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "scp-dest-rename", scp_destination_file_rename
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(
        f"{root_dir}/testFiles/ssh_2/dest/dest_rename_{random_no}_TaskhaNDLER.txt"
    )


def test_pca_rename(root_dir, setup_ssh_keys):
    # Empty the PCA archive directory
    for file in os.listdir(f"{root_dir}/testFiles/ssh_1/archive"):
        os.remove(f"{root_dir}/testFiles/ssh_1/archive/{file}")

    # Create the test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/pca_rename_1.txt": {"content": "test1234"}}]
    )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "scp-pca-rename", scp_pca_rename_task_definition_1
    )

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
        None, "scp-pca-rename-name", scp_pca_rename_many_task_definition_1
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
    transfer_obj = transfer.Transfer(None, "scp-basic", scp_proxy_task_definition)
    local_staging_dir = transfer_obj.local_staging_dir

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test.taskhandler.proxy.txt")

    # Ensure that local files are tidied up
    assert not os.path.exists(local_staging_dir)


def test_invalid_ssh_decryption_direct():
    # Create a transfer object
    scp_task_definition_copy = deepcopy(scp_task_definition)
    scp_task_definition_copy["source"]["encryption"] = {"decrypt": True}
    transfer_obj = transfer.Transfer(None, "scp-basic", scp_task_definition_copy)

    # Expect a DecryptionNotSupportedError exception
    with pytest.raises(exceptions.DecryptionNotSupportedError):
        transfer_obj.run()


def test_invalid_ssh_encryption_direct():
    # Create a transfer object
    scp_task_definition_copy = deepcopy(scp_task_definition)
    scp_task_definition_copy["destination"][0]["encryption"] = {"encrypt": True}
    transfer_obj = transfer.Transfer(None, "scp-basic", scp_task_definition_copy)

    # Expect a EncryptionNotSupportedError exception
    with pytest.raises(exceptions.EncryptionNotSupportedError):
        transfer_obj.run()
