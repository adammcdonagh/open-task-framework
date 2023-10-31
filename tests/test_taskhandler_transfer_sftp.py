# pylint: skip-file
import os
import random

import pytest
from pytest_shell import fs

from opentaskpy import exceptions
from opentaskpy.taskhandlers import transfer
from tests.fixtures.ssh_clients import *  # noqa: F403

os.environ["OTF_NO_LOG"] = "1"
os.environ["OTF_LOG_LEVEL"] = "DEBUG"

# Create a task definition
sftp_task_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": ".*taskhandler.*\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}

# Non existent source directory
sftp_task_non_existent_source_dir_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src/nonexistentdir",
        "fileRegex": ".*taskhandler.*\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}


sftp_task_definition_no_permissions = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": ".*taskhandler.*\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/etc",
            "rename": {
                "pattern": ".*taskhandler.*\\.txt",
                "sub": "passwd",
            },
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}

sftp_file_watch_task_no_error_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": ".*nofileexists.*\\.txt",
        "fileWatch": {"timeout": 1},
        "error": False,
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
    },
}

sftp_with_fin_task_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": ".*taskhandler.fin.*\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "flags": {
                "fullPath": "/home/application/testFiles/dest/sftp_with_fin.fin",
            },
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}

# PCA move
sftp_pca_move_task_definition_1 = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": "pca_move\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        "postCopyAction": {
            "action": "move",
            "destination": "/home/application/testFiles/archive",
        },
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}

sftp_pca_move_task_definition_2 = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": "pca_move_2\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        "postCopyAction": {
            "action": "move",
            "destination": "/home/application/testFiles/archive/",
        },
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}

sftp_pca_delete_task_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": "pca_delete\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        "postCopyAction": {"action": "delete"},
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}


sftp_pca_invalid_move_task_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": "pca_move_3\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        "postCopyAction": {
            "action": "move",
            "destination": "/home/application/testFiles/archive/pca_move_bad.txt",
        },
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}

sftp_pca_rename_task_definition_1 = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": "pca_rename_1\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        "postCopyAction": {
            "action": "rename",
            "destination": "/home/application/testFiles/archive/",
            "pattern": "rename",
            "sub": "renamed",
        },
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}

sftp_pca_rename_many_task_definition_1 = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": "pca_rename_many.*\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        "postCopyAction": {
            "action": "rename",
            "destination": "/home/application/testFiles/archive/",
            "pattern": "rename",
            "sub": "renamed",
        },
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}

# Proxy task definition
sftp_proxy_task_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": ".*taskhandler.proxy\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "transferType": "proxy",
            "directory": "/home/application/testFiles/dest",
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}


sftp_destination_file_rename = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": "dest_rename.*taskhandler.*\\.txt",
        "protocol": {"name": "sftp", "credentials": {"username": "application"}},
    },
    "destination": [
        {
            "hostname": "172.16.0.22",
            "directory": "/home/application/testFiles/dest",
            "rename": {
                "pattern": "t(askha)ndler",
                "sub": "T\\1NDLER",
            },
            "protocol": {"name": "sftp", "credentials": {"username": "application"}},
        },
    ],
}

fail_invalid_protocol_task_definition = {
    "type": "transfer",
    "source": {
        "hostname": "172.16.0.21",
        "directory": "/home/application/testFiles/src",
        "fileRegex": ".*taskhandler.*\\.txt",
        "protocol": {"name": "nonexistent"},
    },
}


def test_remote_handler(setup_sftp_keys):
    # Validate that given a transfer with sftp protocol, that we get a remote handler of type SFTP

    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition)

    transfer_obj._set_remote_handlers()

    # Validate some things were set as expected
    assert transfer_obj.source_remote_handler.__class__.__name__ == "SFTPTransfer"

    # dest_remote_handler should be an array
    assert isinstance(transfer_obj.dest_remote_handlers, list)
    assert len(transfer_obj.dest_remote_handlers) == 1
    #  of SFTPTransfer objects
    assert transfer_obj.dest_remote_handlers[0].__class__.__name__ == "SFTPTransfer"


def test_sftp_basic(root_dir, setup_sftp_keys):
    # Create a test file
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/sftp_1/src/test.taskhandler.txt": {
                    "content": "test1234"
                }
            }
        ]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/test.taskhandler.txt")

    # Generate a random number
    random_number = random.randint(1, 1000000)
    # Test transferring to a subdir that doesn't exist, and creating it
    sftp_task_definition["destination"][0][
        "directory"
    ] = f"/home/application/testFiles/dest/{random_number}"

    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition)

    # Run the transfer and expect a false status, as we've not asked the directory to be created
    # Expect a RemoteTransferError
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()

    assert not os.path.exists(
        f"{root_dir}/testFiles/sftp_2/dest/{random_number}/test.taskhandler.txt"
    )

    # Now run again, but ask for the dir to be created

    sftp_task_definition["destination"][0]["createDirectoryIfNotExists"] = True

    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()

    # Check the destination file exists
    assert os.path.exists(
        f"{root_dir}/testFiles/sftp_2/dest/{random_number}/test.taskhandler.txt"
    )


def test_sftp_basic_non_existent_source_directory(root_dir, setup_sftp_keys):
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None,
        "sftp-basic-non-existent-directory",
        sftp_task_non_existent_source_dir_definition,
    )

    # Run the transfer and expect a true status
    with pytest.raises(exceptions.FilesDoNotMeetConditionsError):
        transfer_obj.run()


def test_sftp_basic_no_permissions(root_dir, setup_sftp_keys):
    # Create a test file
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/sftp_1/src/test.taskhandler.txt": {
                    "content": "test1234"
                }
            }
        ]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "sftp-basic-no-permissions", sftp_task_definition_no_permissions
    )

    # Run the transfer and expect a true status
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()


def test_sftp_filewatch_no_error(setup_sftp_keys):
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "scp-no-file-no-error", sftp_file_watch_task_no_error_definition
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()


def test_sftp_basic_write_fin(root_dir, setup_sftp_keys):
    # Delete any fin files that exist
    for file in os.listdir(f"{root_dir}/testFiles/sftp_2/dest"):
        if file.endswith(".fin"):
            os.remove(f"{root_dir}/testFiles/sftp_2/dest/{file}")

    # Create a test file
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/sftp_1/src/test.taskhandler.fin.txt": {
                    "content": "test1234"
                }
            }
        ]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_with_fin_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/test.taskhandler.fin.txt")

    # Check the fin file exists
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/sftp_with_fin.fin")


def test_pca_move(root_dir, setup_sftp_keys):
    # Empty the PCA archive directory
    for file in os.listdir(f"{root_dir}/testFiles/sftp_1/archive"):
        os.remove(f"{root_dir}/testFiles/sftp_1/archive/{file}")

    # Create the test file
    fs.create_files(
        [{f"{root_dir}/testFiles/sftp_1/src/pca_move.txt": {"content": "test1234"}}]
    )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "scp-pca-move", sftp_pca_move_task_definition_1
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/pca_move.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{root_dir}/testFiles/sftp_1/src/pca_move.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{root_dir}/testFiles/sftp_1/archive/pca_move.txt")

    # Create the next test file
    fs.create_files(
        [{f"{root_dir}/testFiles/sftp_1/src/pca_move_2.txt": {"content": "test1234"}}]
    )
    transfer_obj = transfer.Transfer(
        None, "scp-pca-move-2", sftp_pca_move_task_definition_2
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()

    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/pca_move_2.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{root_dir}/testFiles/sftp_1/src/pca_move_2.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{root_dir}/testFiles/sftp_1/archive/pca_move_2.txt")

    fs.create_files(
        [{f"{root_dir}/testFiles/sftp_1/src/pca_move_3.txt": {"content": "test1234"}}]
    )
    transfer_obj = transfer.Transfer(
        None, "scp-pca-move-invalid", sftp_pca_invalid_move_task_definition
    )

    # Run the transfer and expect a failure status
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/pca_move_3.txt")
    # Check the source file should still exist
    assert os.path.exists(f"{root_dir}/testFiles/sftp_1/src/pca_move_3.txt")

    # Check the source file has not been archived
    assert not os.path.exists(f"{root_dir}/testFiles/sftp_1/archive/pca_move_bad.txt")


def test_pca_delete(root_dir, setup_sftp_keys):
    # Create the next test file
    fs.create_files(
        [{f"{root_dir}/testFiles/sftp_1/src/pca_delete.txt": {"content": "test1234"}}]
    )
    transfer_obj = transfer.Transfer(
        None, "scp-pca-delete", sftp_pca_delete_task_definition
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()

    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/pca_delete.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{root_dir}/testFiles/sftp_1/src/pca_delete.txt")

    # Check the source file has been deleted
    assert not os.path.exists(f"{root_dir}/testFiles/sftp_1/pca_delete.txt")


def test_destination_file_rename(root_dir, setup_sftp_keys):
    # Random number
    import random

    random_no = random.randint(1, 1000)

    # Create the test file
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/sftp_1/src/dest_rename_{random_no}_taskhandler.txt": {
                    "content": "test1234"
                }
            }
        ]
    )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "scp-dest-rename", sftp_destination_file_rename
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(
        f"{root_dir}/testFiles/sftp_2/dest/dest_rename_{random_no}_TaskhaNDLER.txt"
    )


def test_pca_rename(root_dir, setup_sftp_keys):
    # Empty the PCA archive directory
    for file in os.listdir(f"{root_dir}/testFiles/sftp_1/archive"):
        os.remove(f"{root_dir}/testFiles/sftp_1/archive/{file}")

    # Create the test file
    fs.create_files(
        [{f"{root_dir}/testFiles/sftp_1/src/pca_rename_1.txt": {"content": "test1234"}}]
    )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "scp-pca-rename", sftp_pca_rename_task_definition_1
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/pca_rename_1.txt")
    # Check the source file no longer exists
    assert not os.path.exists(f"{root_dir}/testFiles/sftp_1/src/pca_rename_1.txt")

    # Check the source file has been archived
    assert os.path.exists(f"{root_dir}/testFiles/sftp_1/archive/pca_renamed_1.txt")


def test_pca_rename_many(root_dir, setup_sftp_keys):
    # Create the test file
    # Empty the PCA archive directory
    for file in os.listdir(f"{root_dir}/testFiles/sftp_1/archive"):
        os.remove(f"{root_dir}/testFiles/sftp_1/archive/{file}")

    # for 1 to 10
    for i in range(1, 10):
        fs.create_files(
            [
                {
                    f"{root_dir}/testFiles/sftp_1/src/pca_rename_many_{i}.txt": {
                        "content": "test1234"
                    }
                }
            ]
        )
    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "scp-pca-rename-name", sftp_pca_rename_many_task_definition_1
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    for i in range(1, 10):
        assert os.path.exists(
            f"{root_dir}/testFiles/sftp_2/dest/pca_rename_many_{i}.txt"
        )
        # Check the source file no longer exists
        assert not os.path.exists(
            f"{root_dir}/testFiles/sftp_1/src/pca_rename_many_{i}.txt"
        )

        # Check the source file has been archived
        assert os.path.exists(
            f"{root_dir}/testFiles/sftp_1/archive/pca_renamed_many_{i}.txt"
        )


def test_sftp_proxy(root_dir, setup_sftp_keys):
    # Create a test file
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/sftp_1/src/test.taskhandler.proxy.txt": {
                    "content": "test1234"
                }
            }
        ]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_proxy_task_definition)
    local_staging_dir = transfer_obj.local_staging_dir

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(
        f"{root_dir}/testFiles/sftp_2/dest/test.taskhandler.proxy.txt"
    )

    # Ensure that local files are tidied up
    assert not os.path.exists(local_staging_dir)
