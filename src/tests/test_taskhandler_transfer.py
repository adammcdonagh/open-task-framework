import os
import unittest

from opentaskpy.taskhandlers import transfer
from tests.file_helper import BASE_DIRECTORY, write_test_file


class TaskHandlerTransferTest(unittest.TestCase):

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

    @classmethod
    def setUpClass(cls):
        cls.tearDownClass()

    def test_remote_handler(self):
        # Validate that given a transfer with ssh protocol, that we get a remote handler of type SSH
        transfer_obj = transfer.Transfer("scp-basic", self.scp_task_definition)

        transfer_obj._set_remote_handlers()

        # Validate some things were set as expected
        self.assertEqual(
            transfer_obj.source_remote_handler.__class__.__name__, "SSHTransfer"
        )
        # dest_remote_handler should be an array
        self.assertTrue(isinstance(transfer_obj.dest_remote_handlers, list))
        self.assertEqual(len(transfer_obj.dest_remote_handlers), 1)
        #  of SSHTransfer objects
        self.assertEqual(
            transfer_obj.dest_remote_handlers[0].__class__.__name__, "SSHTransfer"
        )

    def test_scp_basic(self):

        # Create a test file
        write_test_file(
            f"{BASE_DIRECTORY}/ssh_1/src/test.taskhandler.txt", content="test1234"
        )

        # Create a transfer object
        transfer_obj = transfer.Transfer("scp-basic", self.scp_task_definition)

        # Run the transfer and expect a true status
        self.assertTrue(transfer_obj.run())
        # Check the destination file exists
        self.assertTrue(
            os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/test.taskhandler.txt")
        )

    @classmethod
    def tearDownClass(cls):

        to_remove = [
            f"{BASE_DIRECTORY}/ssh_1/src/test.taskhandler.txt",
            f"{BASE_DIRECTORY}/ssh_2/dest/test.taskhandler.txt",
        ]
        for file in to_remove:
            if os.path.exists(file):
                os.remove(file)
