# pylint: skip-file
import os
import random
from copy import deepcopy

import pytest
from pytest_shell import fs

from opentaskpy import exceptions
from opentaskpy.taskhandlers import transfer
from tests.fixtures.ssh_clients import *  # noqa: F403

os.environ["OTF_NO_LOG"] = "1"
os.environ["OTF_LOG_LEVEL"] = "DEBUG"


local_test_dir = "/tmp/local_tests"

# Create a task definition
local_task_definition = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": ".*taskhandler.*\\.txt",
        "protocol": {"name": "local"},
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
            "mode": "0644",
        },
    ],
}

local_file_watch_task_no_error_definition = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": ".*nofileexists.*\\.txt",
        "fileWatch": {"timeout": 1},
        "error": False,
        "protocol": {"name": "local"},
    },
}

local_with_fin_task_definition = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": ".*taskhandler.fin.*\\.txt",
        "protocol": {"name": "local"},
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "flags": {
                "fullPath": f"{local_test_dir}/dest/sftp_with_fin.fin",
            },
            "protocol": {"name": "local"},
        },
    ],
}

# PCA delete
local_pca_delete_task_definition_1 = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": "pca_delete\\.txt",
        "protocol": {"name": "local"},
        "postCopyAction": {
            "action": "delete",
        },
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ],
}

# PCA move
local_pca_move_task_definition_1 = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": "pca_move\\.txt",
        "protocol": {"name": "local"},
        "postCopyAction": {
            "action": "move",
            "destination": f"{local_test_dir}/archive",
        },
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ],
}

local_pca_move_task_definition_2 = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": "pca_move_2\\.txt",
        "protocol": {"name": "local"},
        "postCopyAction": {
            "action": "move",
            "destination": f"{local_test_dir}/archive/",
        },
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ],
}

local_pca_invalid_move_task_definition = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": "pca_move_3\\.txt",
        "protocol": {"name": "local"},
        "postCopyAction": {
            "action": "move",
            "destination": f"{local_test_dir}/archive/pca_move_bad.txt",
        },
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ],
}

local_pca_invalid_move_dir_task_definition = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": "pca_move_4\\.txt",
        "protocol": {"name": "local"},
        "postCopyAction": {
            "action": "move",
            "destination": "/etc/passwd",
        },
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ],
}

local_pca_rename_task_definition_1 = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": "pca_rename_1\\.txt",
        "protocol": {"name": "local"},
        "postCopyAction": {
            "action": "rename",
            "destination": f"{local_test_dir}/archive/",
            "pattern": "rename",
            "sub": "renamed",
        },
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ],
}

local_pca_rename_many_task_definition_1 = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": "pca_rename_many.*\\.txt",
        "protocol": {"name": "local"},
        "postCopyAction": {
            "action": "rename",
            "destination": f"{local_test_dir}/archive/",
            "pattern": "rename",
            "sub": "renamed",
        },
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ],
}


local_destination_file_rename = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": "dest_rename.*taskhandler.*\\.txt",
        "protocol": {"name": "local"},
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "rename": {
                "pattern": "t(askha)ndler",
                "sub": "T\\1NDLER",
            },
            "protocol": {"name": "local"},
        },
    ],
}

fail_invalid_protocol_task_definition = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": ".*taskhandler.*\\.txt",
        "protocol": {"name": "nonexistent"},
    },
}

local_multi_protocol_task_definition = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": ".*taskhandler.*\\.txt",
        "protocol": {"name": "local"},
    },
    "destination": [
        {
            "hostname": "172.16.0.12",
            "directory": "/tmp/testFiles/dest",
            "protocol": {"name": "ssh", "credentials": {"username": "application"}},
        },
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ],
}


@pytest.fixture(scope="session")
def setup_local_test_dir():
    os.makedirs(f"{local_test_dir}/src", exist_ok=True)
    os.makedirs(f"{local_test_dir}/dest", exist_ok=True)
    os.makedirs(f"{local_test_dir}/archive", exist_ok=True)

    return local_test_dir


def test_remote_handler():
    # Validate that given a transfer with local protocol, that we get a remote handler of type local

    transfer_obj = transfer.Transfer(None, "sftp-basic", local_task_definition)

    transfer_obj._set_remote_handlers()

    # Validate some things were set as expected
    assert transfer_obj.source_remote_handler.__class__.__name__ == "LocalTransfer"

    # dest_remote_handler should be an array
    assert isinstance(transfer_obj.dest_remote_handlers, list)
    assert len(transfer_obj.dest_remote_handlers) == 1
    #  of LocalTransfer objects
    assert transfer_obj.dest_remote_handlers[0].__class__.__name__ == "LocalTransfer"


def test_local_non_existent_file(setup_local_test_dir):
    local_task_definition_copy = deepcopy(local_task_definition)
    local_task_definition_copy["source"]["fileRegex"] = ".*nonexistent.*\\.txt"
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "local-non-existent", local_task_definition_copy
    )

    # Run the transfer and expect a FilesDoNotMeetConditionsError exception
    with pytest.raises(exceptions.FilesDoNotMeetConditionsError):
        transfer_obj.run()


def test_local_basic(setup_local_test_dir):
    # Create a test file
    fs.create_files(
        [{f"{local_test_dir}/src/test.taskhandler.txt": {"content": "test1234"}}]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer(None, "local-basic", local_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{local_test_dir}/dest/test.taskhandler.txt")

    # Generate a random number
    random_number = random.randint(1, 1000000)
    # Test transferring to a subdir that doesn't exist, and creating it
    local_task_definition["destination"][0][
        "directory"
    ] = f"/{local_test_dir}/dest/{random_number}"

    transfer_obj = transfer.Transfer(None, "local-basic", local_task_definition)

    # Run the transfer and expect a false status, as we've not asked the directory to be created
    # Expect a RemoteTransferError
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()

    assert not os.path.exists(
        f"{local_test_dir}/dest/{random_number}/test.taskhandler.txt"
    )

    # Check file mode is 644
    assert (
        oct(os.stat(f"{local_test_dir}/dest/test.taskhandler.txt").st_mode)[-3:]
        == "644"
    )

    # Now run again, but ask for the dir to be created

    local_task_definition["destination"][0]["createDirectoryIfNotExists"] = True

    transfer_obj = transfer.Transfer(None, "local-basic", local_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()

    # Check the destination file exists
    assert os.path.exists(f"{local_test_dir}/dest/{random_number}/test.taskhandler.txt")


def test_local_filewatch_no_error():
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "local-no-file-no-error", local_file_watch_task_no_error_definition
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()


def test_local_basic_write_fin(setup_local_test_dir):
    # Delete any fin files that exist
    for file in os.listdir(f"{local_test_dir}/dest"):
        if file.endswith(".fin"):
            os.remove(f"{local_test_dir}/dest/{file}")

    # Create a test file
    fs.create_files(
        [{f"{local_test_dir}/src/test.taskhandler.fin.txt": {"content": "test1234"}}]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "local-basic", local_with_fin_task_definition
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{local_test_dir}/dest/test.taskhandler.fin.txt")

    # Check the fin file exists
    assert os.path.exists(f"{local_test_dir}/dest/sftp_with_fin.fin")


def test_pca_move(setup_local_test_dir):
    # Empty the PCA archive directory
    for file in os.listdir(f"{local_test_dir}/archive"):
        os.remove(f"{local_test_dir}/archive/{file}")

    # Create the test file
    fs.create_files([{f"{local_test_dir}/src/pca_move.txt": {"content": "test1234"}}])
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "local-pca-move", local_pca_move_task_definition_1
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{local_test_dir}/dest/pca_move.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{local_test_dir}/src/pca_move.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{local_test_dir}/archive/pca_move.txt")

    # Create the next test file
    fs.create_files([{f"{local_test_dir}/src/pca_move_2.txt": {"content": "test1234"}}])
    transfer_obj = transfer.Transfer(
        None, "local-pca-move-2", local_pca_move_task_definition_2
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()

    # Check the destination file exists
    assert os.path.exists(f"{local_test_dir}/dest/pca_move_2.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{local_test_dir}/src/pca_move_2.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{local_test_dir}/archive/pca_move_2.txt")

    fs.create_files([{f"{local_test_dir}/src/pca_move_3.txt": {"content": "test1234"}}])
    transfer_obj = transfer.Transfer(
        None, "local-pca-move-invalid", local_pca_invalid_move_task_definition
    )

    # Run the transfer and expect a failure status
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{local_test_dir}/dest/pca_move_3.txt")
    # Check the source file should still exist
    assert os.path.exists(f"{local_test_dir}/src/pca_move_3.txt")

    # Check the source file has not been archived
    assert not os.path.exists(f"{local_test_dir}/archive/pca_move_bad.txt")

    # Finally, try moving to a directory that doesn't exist
    fs.create_files([{f"{local_test_dir}/src/pca_move_4.txt": {"content": "test1234"}}])
    transfer_obj = transfer.Transfer(
        None, "local-pca-move-invalid", local_pca_invalid_move_dir_task_definition
    )
    # Run the transfer and expect a failure status
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{local_test_dir}/dest/pca_move_4.txt")
    # Check the source file should still exist
    assert os.path.exists(f"{local_test_dir}/src/pca_move_4.txt")

    # Check the source file has not been archived
    assert not os.path.exists(
        f"{local_test_dir}/archive/archive_no-exist/pca_move_bad.txt"
    )


def test_pca_delete(setup_local_test_dir):
    # Create the test file
    fs.create_files([{f"{local_test_dir}/src/pca_delete.txt": {"content": "test1234"}}])
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "local-pca-delete", local_pca_delete_task_definition_1
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{local_test_dir}/dest/pca_delete.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{local_test_dir}/src/pca_delete.txt")


def test_destination_file_rename(setup_local_test_dir):
    # Random number
    import random

    random_no = random.randint(1, 1000)

    # Create the test file
    fs.create_files(
        [
            {
                f"{local_test_dir}/src/dest_rename_{random_no}_taskhandler.txt": {
                    "content": "test1234"
                }
            }
        ]
    )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "local-dest-rename", local_destination_file_rename
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(
        f"{local_test_dir}/dest/dest_rename_{random_no}_TaskhaNDLER.txt"
    )


def test_pca_rename(setup_local_test_dir):
    # Empty the PCA archive directory
    for file in os.listdir(f"{local_test_dir}/archive"):
        os.remove(f"{local_test_dir}/archive/{file}")

    # Create the test file
    fs.create_files(
        [{f"{local_test_dir}/src/pca_rename_1.txt": {"content": "test1234"}}]
    )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "local-pca-rename", local_pca_rename_task_definition_1
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{local_test_dir}/dest/pca_rename_1.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{local_test_dir}/src/pca_rename_1.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{local_test_dir}/archive/pca_renamed_1.txt")


def test_pca_rename_many(setup_local_test_dir):
    # Create the test file
    # Empty the PCA archive directory
    for file in os.listdir(f"{local_test_dir}/archive"):
        os.remove(f"{local_test_dir}/archive/{file}")

    # for 1 to 10
    for i in range(1, 10):
        fs.create_files(
            [{f"{local_test_dir}/src/pca_rename_many_{i}.txt": {"content": "test1234"}}]
        )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "local-pca-rename-name", local_pca_rename_many_task_definition_1
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    for i in range(1, 10):
        assert os.path.exists(f"{local_test_dir}/dest/pca_rename_many_{i}.txt")
        # Check the source file no longer exists
        assert not os.path.exists(f"{local_test_dir}/src/pca_rename_many_{i}.txt")

        # Check the source file has been archived
        assert os.path.exists(f"{local_test_dir}/archive/pca_renamed_many_{i}.txt")


def test_local_multi_protocol(
    root_dir, setup_local_test_dir, setup_ssh_keys, setup_sftp_keys
):
    # Create a test file
    fs.create_files(
        [{f"{local_test_dir}/src/test.taskhandler.txt": {"content": "test1234"}}]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "local-multi-protocol", local_multi_protocol_task_definition
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test.taskhandler.txt")
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/test.taskhandler.txt")
    assert os.path.exists(f"{local_test_dir}/dest/test.taskhandler.txt")
