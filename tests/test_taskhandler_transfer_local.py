# pylint: skip-file
# ruff: noqa
import hashlib
import os
import random
from copy import deepcopy

import gnupg
import pytest
from pytest_shell import fs

from opentaskpy import exceptions
from opentaskpy.taskhandlers import transfer
from tests.fixtures.pgp import *  # noqa: F403, F401
from tests.fixtures.ssh_clients import *  # noqa: F403, F401

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

# Count conditional tests
local_task_with_counts = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": "counts[0-9]\\.txt",
        "conditionals": {
            "count": {
                "minCount": 2,
                "maxCount": 2,
            },
        },
        "protocol": {"name": "local"},
    },
    "destination": [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ],
}

local_file_watch_task_with_counts = {
    "type": "transfer",
    "source": {
        "directory": f"{local_test_dir}/src",
        "fileRegex": "counts_watch[0-9]\\.txt",
        "fileWatch": {"timeout": 5},
        "conditionals": {
            "count": {
                "minCount": 2,
                "maxCount": 2,
            },
            "checkDuringFilewatch": True,
        },
        "protocol": {"name": "local"},
    },
    "destination": [
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


def test_local_decrypt_incoming_file(
    tmpdir, root_dir, setup_local_test_dir, private_key, public_key
):

    # Create a test file
    fs.create_files(
        [{f"{tmpdir}/src/test.decryption.txt": {"content": "test12345678"}}]
    )

    # Checksum the file
    with open(f"{tmpdir}/src/test.decryption.txt", "rb") as f:
        original_file_checksum = hashlib.md5(f.read()).hexdigest()

    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the public key
    gpg.import_keys(public_key)

    # Encrypt the file
    with open(f"{tmpdir}/src/test.decryption.txt", "rb") as f:
        status = gpg.encrypt_file(
            f,
            always_trust=True,
            recipients="test@example.com",
            output=f"{tmpdir}/test.decryption.txt.gpg",
        )

        # Check status returns a 0 exit code
        assert status.ok

    # Check the output file exists
    assert os.path.exists(f"{tmpdir}/test.decryption.txt.gpg")

    # Now we have an encrypted file (we can pretend we are collecting from elsewhere),
    # run a transfer to copy the file locally, and decrypt it
    local_task_definition_copy = deepcopy(local_task_definition)
    local_task_definition_copy["source"]["directory"] = f"{tmpdir}"
    local_task_definition_copy["source"]["fileRegex"] = "test.decryption.txt.gpg"
    local_task_definition_copy["source"]["encryption"] = {
        "decrypt": True,
        "private_key": private_key,
    }

    # Override the destination
    local_task_definition_copy["destination"] = [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ]

    # Run the transfer
    transfer_obj = transfer.Transfer(None, "local-decrypt", local_task_definition_copy)
    assert transfer_obj.run()

    # Check the decrypted source files have been deleted
    assert not os.path.exists(f"{tmpdir}/test.decryption.txt")

    # Check the output file exists
    assert os.path.exists(f"{local_test_dir}/dest/test.decryption.txt")
    # Check that the file's checksum matches that of the original unencrypted source file
    # Check the checksum of the new file
    with open(f"{local_test_dir}/dest/test.decryption.txt", "rb") as f:
        new_file_checksum = hashlib.md5(f.read()).hexdigest()
    assert new_file_checksum == original_file_checksum


def test_local_decrypt_incoming_file_custom_extensions(
    tmpdir, root_dir, setup_local_test_dir, private_key, public_key
):

    # Create a test file
    fs.create_files(
        [{f"{tmpdir}/src/test.decryption.txt": {"content": "test12345678"}}]
    )

    # Checksum the file
    with open(f"{tmpdir}/src/test.decryption.txt", "rb") as f:
        original_file_checksum = hashlib.md5(f.read()).hexdigest()

    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the public key
    gpg.import_keys(public_key)

    # Encrypt the file
    with open(f"{tmpdir}/src/test.decryption.txt", "rb") as f:
        status = gpg.encrypt_file(
            f,
            always_trust=True,
            recipients="test@example.com",
            output=f"{tmpdir}/test.decryption.txt.pgp",
        )

        # Check status returns a 0 exit code
        assert status.ok

    # Check the output file exists
    assert os.path.exists(f"{tmpdir}/test.decryption.txt.pgp")

    # Now we have an encrypted file (we can pretend we are collecting from elsewhere),
    # run a transfer to copy the file locally, and decrypt it
    local_task_definition_copy = deepcopy(local_task_definition)
    local_task_definition_copy["source"]["directory"] = f"{tmpdir}"
    local_task_definition_copy["source"]["fileRegex"] = "test.decryption.txt.pgp"
    local_task_definition_copy["source"]["encryption"] = {
        "decrypt": True,
        "private_key": private_key,
    }

    # Override the destination
    local_task_definition_copy["destination"] = [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ]

    # Run the transfer
    transfer_obj = transfer.Transfer(None, "local-decrypt", local_task_definition_copy)
    assert transfer_obj.run()

    # Check the decrypted source files have been deleted
    assert not os.path.exists(f"{tmpdir}/test.decryption.txt")

    # Check the output file exists
    assert os.path.exists(f"{local_test_dir}/dest/test.decryption.txt")
    # Check that the file's checksum matches that of the original unencrypted source file
    # Check the checksum of the new file
    with open(f"{local_test_dir}/dest/test.decryption.txt", "rb") as f:
        new_file_checksum = hashlib.md5(f.read()).hexdigest()
    assert new_file_checksum == original_file_checksum

    # Now do it again, but with a different extension that's not pgp or gpg
    # Rename the original encrypted file and use that as the input
    os.rename(f"{tmpdir}/test.decryption.txt.pgp", f"{tmpdir}/test.decryption.txt.enc")
    local_task_definition_copy["source"]["fileRegex"] = "test.decryption.txt.enc"

    # Run the transfer
    transfer_obj = transfer.Transfer(None, "local-decrypt", local_task_definition_copy)
    assert transfer_obj.run()

    # Check the decrypted source files have been deleted
    assert not os.path.exists(f"{tmpdir}/test.decryption.txt")

    # Check the output file exists with the .decrypted file extension
    assert os.path.exists(f"{local_test_dir}/dest/test.decryption.txt.enc.decrypted")


def test_local_encrypt_outgoing_file(
    tmpdir, root_dir, setup_local_test_dir, private_key, public_key
):

    # Create a test file
    fs.create_files(
        [{f"{tmpdir}/src/test.encryption.txt": {"content": "test12345678"}}]
    )

    # Checksum the file
    with open(f"{tmpdir}/src/test.encryption.txt", "rb") as f:
        original_file_checksum = hashlib.md5(f.read()).hexdigest()

    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the public key
    gpg.import_keys(private_key)

    # run a transfer to copy the file locally, and encrypt it
    local_task_definition_copy = deepcopy(local_task_definition)
    local_task_definition_copy["source"]["directory"] = f"{tmpdir}/src"
    local_task_definition_copy["source"]["fileRegex"] = "test.encryption.txt"

    # Override the destination
    local_task_definition_copy["destination"] = [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
            "encryption": {
                "encrypt": True,
                "public_key": public_key,
            },
        },
    ]

    # Run the transfer
    transfer_obj = transfer.Transfer(None, "local-encrypt", local_task_definition_copy)
    assert transfer_obj.run()

    # Check the output file exists
    assert os.path.exists(f"{local_test_dir}/dest/test.encryption.txt.gpg")

    # Now we need to decrypt this file to check that it matches the original content,
    # and can actually be decrypted again
    decryption_data = gpg.decrypt_file(
        open(f"{local_test_dir}/dest/test.encryption.txt.gpg", "rb"),
        output=f"{local_test_dir}/dest/test.encryption.txt",
    )

    assert decryption_data.ok
    assert decryption_data.returncode == 0

    # Check that the file's checksum matches that of the original unencrypted source file
    # Check the checksum of the new file
    with open(f"{local_test_dir}/dest/test.encryption.txt", "rb") as f:
        new_file_checksum = hashlib.md5(f.read()).hexdigest()
    assert new_file_checksum == original_file_checksum

    # Ensure that the source encrypted file has been deleted
    assert not os.path.exists(f"{local_test_dir}/src/test.encryption.txt.gpg")


def test_local_encrypt_outgoing_file_custom_extension(
    tmpdir, root_dir, setup_local_test_dir, private_key, public_key
):

    # Create a test file
    fs.create_files(
        [{f"{tmpdir}/src/test.encryption_custom_ext.txt": {"content": "test12345678"}}]
    )

    # Checksum the file
    with open(f"{tmpdir}/src/test.encryption_custom_ext.txt", "rb") as f:
        original_file_checksum = hashlib.md5(f.read()).hexdigest()

    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the public key
    gpg.import_keys(private_key)

    # run a transfer to copy the file locally, and encrypt it
    local_task_definition_copy = deepcopy(local_task_definition)
    local_task_definition_copy["source"]["directory"] = f"{tmpdir}/src"
    local_task_definition_copy["source"]["fileRegex"] = "test.encryption_custom_ext.txt"

    # Override the destination
    local_task_definition_copy["destination"] = [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
            "encryption": {
                "encrypt": True,
                "public_key": public_key,
                "output_extension": "pgp",
            },
        },
    ]

    # Run the transfer
    transfer_obj = transfer.Transfer(None, "local-encrypt", local_task_definition_copy)
    assert transfer_obj.run()

    # Check the output file exists
    assert os.path.exists(f"{local_test_dir}/dest/test.encryption_custom_ext.txt.pgp")

    # Now we need to decrypt this file to check that it matches the original content,
    # and can actually be decrypted again
    decryption_data = gpg.decrypt_file(
        open(f"{local_test_dir}/dest/test.encryption_custom_ext.txt.pgp", "rb"),
        output=f"{local_test_dir}/dest/test.encryption_custom_ext.txt",
    )

    assert decryption_data.ok
    assert decryption_data.returncode == 0

    # Check that the file's checksum matches that of the original unencrypted source file
    # Check the checksum of the new file
    with open(f"{local_test_dir}/dest/test.encryption_custom_ext.txt", "rb") as f:
        new_file_checksum = hashlib.md5(f.read()).hexdigest()
    assert new_file_checksum == original_file_checksum

    # Ensure that the source encrypted file has been deleted
    assert not os.path.exists(
        f"{local_test_dir}/src/test.encryption_custom_ext.txt.pgp"
    )


def test_local_encrypt_with_signing_outgoing_file(
    tmpdir, root_dir, setup_local_test_dir, private_key, public_key
):

    # Create a test file
    fs.create_files(
        [{f"{tmpdir}/src/test.encryptionSign.txt": {"content": "test12345678"}}]
    )

    # Checksum the file
    with open(f"{tmpdir}/src/test.encryptionSign.txt", "rb") as f:
        original_file_checksum = hashlib.md5(f.read()).hexdigest()

    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the private key
    import_result = gpg.import_keys(private_key)

    # run a transfer to copy the file locally, and encrypt it
    local_task_definition_copy = deepcopy(local_task_definition)
    local_task_definition_copy["source"]["directory"] = f"{tmpdir}/src"
    local_task_definition_copy["source"]["fileRegex"] = "test.encryptionSign.txt"

    # Override the destination
    local_task_definition_copy["destination"] = [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
            "encryption": {
                "encrypt": True,
                "sign": True,
                "private_key": private_key,
                "public_key": public_key,
            },
        },
    ]

    # Run the transfer
    transfer_obj = transfer.Transfer(
        None, "local-encrypt-and-sign", local_task_definition_copy
    )
    assert transfer_obj.run()

    # Check the output file exists
    assert os.path.exists(f"{local_test_dir}/dest/test.encryptionSign.txt.gpg")

    # Now we need to decrypt this file to check that it matches the original content,
    # and can actually be decrypted again
    decryption_data = gpg.decrypt_file(
        open(f"{local_test_dir}/dest/test.encryptionSign.txt.gpg", "rb"),
        output=f"{local_test_dir}/dest/test.encryptionSign.txt",
    )

    assert decryption_data.ok
    assert decryption_data.returncode == 0

    # Check that it was signed to start with
    assert decryption_data.sig_info is not None
    # Get the sig_info, loop through the signatures and check that they all have a status of "signature valid"
    for sig in decryption_data.sig_info:
        assert decryption_data.sig_info[sig]["status"] == "signature valid"

    # Check that the file's checksum matches that of the original unencrypted source file
    # Check the checksum of the new file
    with open(f"{local_test_dir}/dest/test.encryptionSign.txt", "rb") as f:
        new_file_checksum = hashlib.md5(f.read()).hexdigest()
    assert new_file_checksum == original_file_checksum

    # Ensure that the source encrypted file has been deleted
    assert not os.path.exists(f"{local_test_dir}/src/test.encryptionSign.txt.gpg")


def test_local_encrypt_with_signing_missing_key_outgoing_file(
    tmpdir,
    root_dir,
    setup_local_test_dir,
    private_key,
    public_key_2,
    private_key_2,
    public_key,
):

    # Create a test file
    fs.create_files(
        [{f"{tmpdir}/src/test.encryptionSign2.txt": {"content": "test12345678"}}]
    )

    # Checksum the file
    with open(f"{tmpdir}/src/test.encryptionSign2.txt", "rb") as f:
        original_file_checksum = hashlib.md5(f.read()).hexdigest()

    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the second private key
    import_result = gpg.import_keys(private_key_2)

    # run a transfer to copy the file locally, and encrypt it
    local_task_definition_copy = deepcopy(local_task_definition)
    local_task_definition_copy["source"]["directory"] = f"{tmpdir}/src"
    local_task_definition_copy["source"]["fileRegex"] = "test.encryptionSign2.txt"

    # Override the destination
    local_task_definition_copy["destination"] = [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
            "encryption": {
                "encrypt": True,
                "sign": True,
                "private_key": private_key,
                "public_key": public_key_2,
            },
        },
    ]

    # Run the transfer
    transfer_obj = transfer.Transfer(
        None, "local-encrypt-and-sign", local_task_definition_copy
    )
    assert transfer_obj.run()

    # Check the output file exists
    assert os.path.exists(f"{local_test_dir}/dest/test.encryptionSign2.txt.gpg")

    # Now we need to decrypt this file to check that it matches the original content,
    # and can actually be decrypted again
    decryption_data = gpg.decrypt_file(
        open(f"{local_test_dir}/dest/test.encryptionSign2.txt.gpg", "rb"),
        output=f"{local_test_dir}/dest/test.encryptionSign2.txt",
    )

    # Check that there was a problem and the stratus is signature error
    problems = decryption_data.problems
    # There should be an object in the array with a status of signature error
    assert any("signature error" in problem["status"] for problem in problems)

    assert (
        decryption_data.ok
    )  # Decrypt was ok, but the return code will be non-zero due to sig error
    assert decryption_data.returncode != 0


def test_transfer_decryption_failure_local(
    tmpdir, root_dir, setup_local_test_dir, private_key_2, public_key
):

    # Create a file and encrypt it with public key
    fs.create_files(
        [{f"{tmpdir}/src/test.decryption.txt": {"content": "test12345678"}}]
    )
    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the public key
    gpg.import_keys(public_key)

    # Encrypt the file
    with open(f"{tmpdir}/src/test.decryption.txt", "rb") as f:
        status = gpg.encrypt_file(
            f,
            always_trust=True,
            recipients="test@example.com",
            output=f"{tmpdir}/test.decryption.txt.gpg",
        )

        # Check status returns a 0 exit code
        assert status.ok

    # Check the output file exists
    assert os.path.exists(f"{tmpdir}/test.decryption.txt.gpg")

    # Now we have an encrypted file (we can pretend we are collecting from elsewhere),
    # run a transfer to copy the file locally, and decrypt it
    local_task_definition_copy = deepcopy(local_task_definition)
    local_task_definition_copy["source"]["directory"] = f"{tmpdir}"
    local_task_definition_copy["source"]["fileRegex"] = "test.decryption.txt.gpg"
    local_task_definition_copy["source"]["encryption"] = {
        "decrypt": True,
        "private_key": private_key_2,
    }

    # Override the destination
    local_task_definition_copy["destination"] = [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
        },
    ]

    # Run the transfer
    transfer_obj = transfer.Transfer(None, "local-decrypt", local_task_definition_copy)
    # This should fail to decrypt because the private key is incorrect
    with pytest.raises(exceptions.DecryptionError):
        transfer_obj.run()


def test_transfer_encryption_local_invalid_key(root_dir, setup_local_test_dir):
    # Create a test file
    fs.create_files(
        [{f"{local_test_dir}/src/test.encryption.txt": {"content": "test12345678"}}]
    )

    local_task_definition_copy = deepcopy(local_task_definition)
    local_task_definition_copy["source"]["directory"] = f"{local_test_dir}/src"
    local_task_definition_copy["source"]["fileRegex"] = "test.encryption.txt"

    # Override the destination
    local_task_definition_copy["destination"] = [
        {
            "directory": f"{local_test_dir}/dest",
            "protocol": {"name": "local"},
            "encryption": {
                "encrypt": True,
                "public_key": "invalid_public_key",
            },
        },
    ]

    # Create a transfer object
    transfer_obj = transfer.Transfer(None, "local-encrypt", local_task_definition_copy)

    # Run the transfer and expect an exception due to failed encryption
    with pytest.raises(exceptions.EncryptionError):
        transfer_obj.run()


def test_transfer_decryption_local_invalid_key(root_dir, setup_local_test_dir):
    # Create a test file
    fs.create_files(
        [{f"{local_test_dir}/src/test.encryption.txt": {"content": "test12345678"}}]
    )

    local_task_definition_copy = deepcopy(local_task_definition)
    local_task_definition_copy["source"]["directory"] = f"{local_test_dir}/src"
    local_task_definition_copy["source"]["fileRegex"] = "test.encryption.txt"
    local_task_definition_copy["source"]["encryption"] = {
        "decrypt": True,
        "private_key": "invalid_private_key",
    }

    # Create a transfer object
    transfer_obj = transfer.Transfer(None, "local-decrypt", local_task_definition_copy)

    # Run the transfer and expect an exception due to failed encryption
    with pytest.raises(exceptions.EncryptionError):
        transfer_obj.run()


def test_local_counts():
    # Create a test file
    fs.create_files(
        [
            {f"{local_test_dir}/src/counts1.txt": {"content": "test1234"}},
            {f"{local_test_dir}/src/counts2.txt": {"content": "test1234"}},
        ]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer(None, "local-counts", local_task_with_counts)

    # Run the transfer and expect a true status
    assert transfer_obj.run()


def test_local_counts_error():
    # Create a test file
    fs.create_files(
        [
            {f"{local_test_dir}/src/counts_error1.txt": {"content": "test1234"}},
        ]
    )
    local_task_with_counts_error = deepcopy(local_task_with_counts)
    local_task_with_counts_error["source"]["fileRegex"] = "counts_error[0-9]\\.txt"

    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None,
        "local-filewatch-counts-error-min",
        local_task_with_counts_error,
    )
    # Test 1 file < minCount of 2 errors
    # Run the transfer and expect a FilesDoNotMeetConditionsError exception
    with pytest.raises(exceptions.FilesDoNotMeetConditionsError):
        transfer_obj.run()

    fs.create_files(
        [
            {f"{local_test_dir}/src/counts_error2.txt": {"content": "test1234"}},
            {f"{local_test_dir}/src/counts_error3.txt": {"content": "test1234"}},
        ]
    )

    transfer_obj = transfer.Transfer(
        None,
        "local-filewatch-counts-error-max",
        local_task_with_counts_error,
    )
    #  Test 3 files > maxCount of 2 errors
    # Run the transfer and expect a FilesDoNotMeetConditionsError exception
    with pytest.raises(exceptions.FilesDoNotMeetConditionsError):
        transfer_obj.run()


def test_local_filewatch_counts():
    # Create a test file
    fs.create_files(
        [
            {f"{local_test_dir}/src/counts_watch1.txt": {"content": "test1234"}},
            {f"{local_test_dir}/src/counts_watch2.txt": {"content": "test1234"}},
        ]
    )

    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None, "local-filewatch-counts", local_file_watch_task_with_counts
    )

    # Run the transfer and expect a true status
    assert transfer_obj.run()


def test_local_filewatch_counts_error():
    # Create a test file
    fs.create_files(
        [
            {f"{local_test_dir}/src/counts_watch_error1.txt": {"content": "test1234"}},
        ]
    )
    local_file_watch_task_with_counts_error = deepcopy(
        local_file_watch_task_with_counts
    )
    local_file_watch_task_with_counts_error["source"][
        "fileRegex"
    ] = "counts_watch_error[0-9]\\.txt"

    # Create a transfer object
    transfer_obj = transfer.Transfer(
        None,
        "local-filewatch-counts-error-min",
        local_file_watch_task_with_counts_error,
    )
    # Test 1 file < minCount of 2 errors
    # Run the transfer and expect a RemoteFileNotFoundError exception
    with pytest.raises(exceptions.RemoteFileNotFoundError):
        transfer_obj.run()

    fs.create_files(
        [
            {f"{local_test_dir}/src/counts_watch_error2.txt": {"content": "test1234"}},
            {f"{local_test_dir}/src/counts_watch_error3.txt": {"content": "test1234"}},
        ]
    )

    transfer_obj = transfer.Transfer(
        None,
        "local-filewatch-counts-error-max",
        local_file_watch_task_with_counts_error,
    )
    #  Test 3 files > maxCount of 2 errors
    # Run the transfer and expect a RemoteFileNotFoundError exception
    with pytest.raises(exceptions.RemoteFileNotFoundError):
        transfer_obj.run()
