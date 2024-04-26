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

    sftp_task_definition_copy = deepcopy(sftp_task_definition)
    # Create a transfer object
    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition_copy)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/test.taskhandler.txt")

    # Generate a random number
    random_number = random.randint(1, 1000000)
    # Test transferring to a subdir that doesn't exist, and creating it
    sftp_task_definition_copy["destination"][0][
        "directory"
    ] = f"/home/application/testFiles/dest/{random_number}"

    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition_copy)

    # Run the transfer and expect a false status, as we've not asked the directory to be created
    # Expect a RemoteTransferError
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()

    assert not os.path.exists(
        f"{root_dir}/testFiles/sftp_2/dest/{random_number}/test.taskhandler.txt"
    )

    # Now run again, but ask for the dir to be created

    sftp_task_definition_copy["destination"][0]["createDirectoryIfNotExists"] = True

    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition_copy)

    # Run the transfer and expect a true status
    assert transfer_obj.run()

    # Check the destination file exists
    assert os.path.exists(
        f"{root_dir}/testFiles/sftp_2/dest/{random_number}/test.taskhandler.txt"
    )

    # Now run again, but set supportsPosixRename to false in the protocol definition
    sftp_task_definition_copy["destination"][0]["protocol"][
        "supportsPosixRename"
    ] = False

    # Delete the destination file
    os.remove(f"{root_dir}/testFiles/sftp_2/dest/{random_number}/test.taskhandler.txt")

    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition_copy)

    # Run the transfer and expect a true status
    assert transfer_obj.run()

    # Check the destination file exists
    assert os.path.exists(
        f"{root_dir}/testFiles/sftp_2/dest/{random_number}/test.taskhandler.txt"
    )

    # Finally run again, but set supportsStatAfterUpload to false in the protocol definition
    sftp_task_definition_copy["destination"][0]["protocol"][
        "supportsStatAfterUpload"
    ] = False

    # Delete the destination file
    os.remove(f"{root_dir}/testFiles/sftp_2/dest/{random_number}/test.taskhandler.txt")

    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition_copy)

    # Run the transfer and expect a true status
    assert transfer_obj.run()

    # Check the destination file exists
    assert os.path.exists(
        f"{root_dir}/testFiles/sftp_2/dest/{random_number}/test.taskhandler.txt"
    )

    # Change the destination directory to / and validate that it works
    sftp_task_definition_copy["destination"][0]["directory"] = "/"

    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition_copy)

    # Run the transfer and expect a false status, because it cannot write to / on the remote
    # Expect a RemoteTransferError
    with pytest.raises(exceptions.RemoteTransferError):
        transfer_obj.run()


def test_sftp_basic_key_from_protocol_definition(root_dir, sftp_key_file):
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
    sftp_task_definition["source"]["protocol"]["credentials"]["key"] = sftp_key_file

    transfer_obj = transfer.Transfer(None, "sftp-basic", sftp_task_definition)

    # Run the transfer and expect a true status
    assert transfer_obj.run()
    # Check the destination file exists
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/test.taskhandler.txt")


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


def test_sftp_decrypt_incoming_file(
    tmpdir, root_dir, setup_sftp_keys, private_key, public_key
):

    # Create a test file
    source_file = f"{root_dir}/testFiles/sftp_1/src/test.decryption.txt"
    fs.create_files([{f"{source_file}": {"content": "test12345678"}}])

    # Checksum the file
    with open(f"{source_file}", "rb") as f:
        original_file_checksum = hashlib.md5(f.read()).hexdigest()

    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the public key
    gpg.import_keys(public_key)

    # Encrypt the file
    with open(f"{source_file}", "rb") as f:
        status = gpg.encrypt_file(
            f,
            always_trust=True,
            recipients="test@example.com",
            output=f"{source_file}.gpg",
        )

        # Check status returns a 0 exit code
        assert status.ok

    # Check the output file exists
    assert os.path.exists(f"{source_file}.gpg")

    # Now we have an encrypted file (we can pretend we are collecting from elsewhere),
    # run a transfer to copy the file locally, and decrypt it
    sftp_task_definition_copy = deepcopy(sftp_task_definition)
    sftp_task_definition_copy["source"]["fileRegex"] = "test.decryption.txt.gpg"
    sftp_task_definition_copy["source"]["encryption"] = {
        "decrypt": True,
        "private_key": private_key,
    }

    # Override the destination
    sftp_task_definition_copy["destination"] = [
        {
            "directory": f"{tmpdir}/dest",
            "createDirectoryIfNotExists": True,
            "protocol": {"name": "local"},
        },
    ]

    # Run the transfer
    transfer_obj = transfer.Transfer(None, "local-decrypt", sftp_task_definition_copy)
    assert transfer_obj.run()

    # Check the output file exists
    assert os.path.exists(f"{tmpdir}/dest/test.decryption.txt")
    # Check that the file's checksum matches that of the original unencrypted source file
    # Check the checksum of the new file
    with open(f"{tmpdir}/dest/test.decryption.txt", "rb") as f:
        new_file_checksum = hashlib.md5(f.read()).hexdigest()
    assert new_file_checksum == original_file_checksum

    # Make sure only 1 file exists under the destination
    assert len(os.listdir(f"{tmpdir}/dest")) == 1


def test_sftp_encrypt_outgoing_file(
    tmpdir, root_dir, setup_sftp_keys, private_key, public_key
):

    source_file = f"{root_dir}/testFiles/sftp_1/src/test.encryption.txt"

    # Create a test file
    fs.create_files([{f"{source_file}": {"content": "test12345678"}}])

    # Checksum the file
    with open(f"{source_file}", "rb") as f:
        original_file_checksum = hashlib.md5(f.read()).hexdigest()

    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the public key
    gpg.import_keys(private_key)

    # run a transfer to copy the file locally, and encrypt it
    sftp_task_definition_copy = deepcopy(sftp_task_definition)
    sftp_task_definition_copy["source"][
        "directory"
    ] = f"/home/application/testFiles/src"
    sftp_task_definition_copy["source"]["fileRegex"] = "test.encryption.txt"

    # Override the destination
    sftp_task_definition_copy["destination"] = [
        {
            "directory": f"{tmpdir}",
            "protocol": {"name": "local"},
            "encryption": {
                "encrypt": True,
                "public_key": public_key,
            },
        },
    ]

    # Run the transfer
    transfer_obj = transfer.Transfer(None, "sftp-encrypt", sftp_task_definition_copy)
    assert transfer_obj.run()

    # Check the output file exists
    assert os.path.exists(f"{tmpdir}/test.encryption.txt.gpg")

    # Now we need to decrypt this file to check that it matches the original content,
    # and can actually be decrypted again
    decryption_data = gpg.decrypt_file(
        open(f"{tmpdir}/test.encryption.txt.gpg", "rb"),
        output=f"{tmpdir}/test.encryption.txt",
    )

    assert decryption_data.ok
    assert decryption_data.returncode == 0

    # Check that the file's checksum matches that of the original unencrypted source file
    # Check the checksum of the new file
    with open(f"{tmpdir}/test.encryption.txt", "rb") as f:
        new_file_checksum = hashlib.md5(f.read()).hexdigest()
    assert new_file_checksum == original_file_checksum


def test_sftp_to_sftp_decrypt(
    root_dir, setup_sftp_keys, tmpdir, private_key, public_key
):
    # This is the same as the above test, but instead of the destination being local
    # we will transfer to sftp_2 instead

    # Create a test file
    source_file = f"{root_dir}/testFiles/sftp_1/src/test.decryption.e2e.txt"
    dest_file = f"{root_dir}/testFiles/sftp_2/dest/test.decryption.e2e.txt"
    fs.create_files([{f"{source_file}": {"content": "test12345678"}}])

    # Checksum the file
    with open(f"{source_file}", "rb") as f:
        original_file_checksum = hashlib.md5(f.read()).hexdigest()

    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the public key
    gpg.import_keys(public_key)

    # Encrypt the file
    with open(f"{source_file}", "rb") as f:
        status = gpg.encrypt_file(
            f,
            always_trust=True,
            recipients="test@example.com",
            output=f"{source_file}.gpg",
        )

        # Check status returns a 0 exit code
        assert status.ok

    # Check the output file exists
    assert os.path.exists(f"{source_file}.gpg")

    # Now we have an encrypted file
    # run a transfer to copy the file to the other sftp, and decrypt it
    sftp_task_definition_copy = deepcopy(sftp_task_definition)
    sftp_task_definition_copy["source"]["fileRegex"] = "test.decryption.e2e.txt.gpg"
    sftp_task_definition_copy["source"]["encryption"] = {
        "decrypt": True,
        "private_key": private_key,
    }

    # Run the transfer
    transfer_obj = transfer.Transfer(None, "sftp-decrypt", sftp_task_definition_copy)
    assert transfer_obj.run()

    # Check the output file exists
    assert os.path.exists(dest_file)
    # Check that the file's checksum matches that of the original unencrypted source file
    # Check the checksum of the new file
    with open(dest_file, "rb") as f:
        new_file_checksum = hashlib.md5(f.read()).hexdigest()
    assert new_file_checksum == original_file_checksum


def test_sftp_to_sftp_encrypt_outgoing_file(
    tmpdir, root_dir, setup_sftp_keys, private_key, public_key
):

    source_file = f"{root_dir}/testFiles/sftp_1/src/test.encryption.e2e.txt"

    # Create a test file
    fs.create_files([{f"{source_file}": {"content": "test12345678"}}])

    # Checksum the file
    with open(f"{source_file}", "rb") as f:
        original_file_checksum = hashlib.md5(f.read()).hexdigest()

    # Create a gpg object
    gpg = gnupg.GPG(gnupghome=f"{tmpdir}")

    # Import the public key
    gpg.import_keys(private_key)

    # run a transfer to copy the file locally, and encrypt it
    sftp_task_definition_copy = deepcopy(sftp_task_definition)
    sftp_task_definition_copy["source"][
        "directory"
    ] = f"/home/application/testFiles/src"
    sftp_task_definition_copy["source"]["fileRegex"] = "test.encryption.e2e.txt"

    # Override the destination
    sftp_task_definition_copy["destination"][0]["encryption"] = {
        "encrypt": True,
        "public_key": public_key,
    }

    # Run the transfer
    transfer_obj = transfer.Transfer(None, "sftp-encrypt", sftp_task_definition_copy)
    assert transfer_obj.run()

    # Now we need to decrypt this file to check that it matches the original content,
    # and can actually be decrypted again
    decryption_data = gpg.decrypt_file(
        open(f"{root_dir}/testFiles/sftp_2/dest/test.encryption.e2e.txt.gpg", "rb"),
        output=f"{root_dir}/testFiles/sftp_2/dest/test.encryption.e2e.txt",
    )

    assert decryption_data.ok
    assert decryption_data.returncode == 0

    # Check that the file's checksum matches that of the original unencrypted source file
    # Check the checksum of the new file
    with open(f"{root_dir}/testFiles/sftp_2/dest/test.encryption.e2e.txt", "rb") as f:
        new_file_checksum = hashlib.md5(f.read()).hexdigest()
    assert new_file_checksum == original_file_checksum


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
