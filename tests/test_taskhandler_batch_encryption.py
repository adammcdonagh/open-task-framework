# pylint: skip-file
# ruff: noqa
import os

from pytest_shell import fs

import opentaskpy.otflogging
from opentaskpy.config.loader import ConfigLoader
from opentaskpy.taskhandlers import batch, execution, transfer
from tests.file_helper import *  # noqa: F403
from tests.fixtures.pgp import *  # noqa: F403, F401
from tests.fixtures.ssh_clients import *  # noqa: F403

os.environ["OTF_NO_LOG"] = "1"
os.environ["OTF_LOG_LEVEL"] = "DEBUG"

parallel_encryption_batch = {
    "type": "batch",
    "tasks": [
        {"order_id": 1, "task_id": "encrypt-file-1-sftp"},
        {"order_id": 2, "task_id": "encrypt-file-2-sftp"},
    ],
}

parallel_decryption_batch = {
    "type": "batch",
    "tasks": [
        {"order_id": 1, "task_id": "decrypt-file-1-sftp"},
        {"order_id": 2, "task_id": "decrypt-file-2-sftp"},
    ],
}


def test_batch_parallel_encryption(
    root_dir, env_vars, clear_logs, store_pgp_keys, setup_sftp_keys
):
    # Assert one of the keys randomly
    assert os.path.exists("/tmp/public_key_1.txt")

    config_loader = ConfigLoader("test/cfg")

    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/sftp_1/src/file-encrypt1.txt": {
                    "content": "hellothere!"
                }
            },
            {
                f"{root_dir}/testFiles/sftp_1/src/file-encrypt2.txt": {
                    "content": "hellothere!"
                }
            },
        ]
    )
    assert os.path.exists(f"{root_dir}/testFiles/sftp_1/src/file-encrypt1.txt")
    assert os.path.exists(f"{root_dir}/testFiles/sftp_1/src/file-encrypt2.txt")

    batch_obj = batch.Batch(
        None,
        f"parallel-encryption-batch",
        parallel_encryption_batch,
        config_loader,
    )

    # Run the batch and expect a true status
    assert batch_obj.run()

    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/file-encrypt1.txt.gpg")
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/file-encrypt2.txt.gpg")


def test_batch_parallel_decryption(
    root_dir, env_vars, clear_logs, store_pgp_keys, setup_sftp_keys
):
    # Assert one of the keys randomly
    assert os.path.exists("/tmp/private_key_1.txt")

    config_loader = ConfigLoader("test/cfg")

    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/file-encrypt1.txt.gpg")
    assert os.path.exists(f"{root_dir}/testFiles/sftp_2/dest/file-encrypt2.txt.gpg")

    batch_obj = batch.Batch(
        None,
        f"parallel-decryption-batch",
        parallel_decryption_batch,
        config_loader,
    )

    # Run the batch and expect a true status
    assert batch_obj.run()

    # Assert files have been decrypted and transferred back to sftp1
    assert os.path.exists(
        f"{root_dir}/testFiles/sftp_1/dest/file-encrypt1-decrypted.txt"
    )
    assert os.path.exists(
        f"{root_dir}/testFiles/sftp_1/dest/file-encrypt2-decrypted.txt"
    )
