import logging
import os
import unittest

from opentaskpy import exceptions
from opentaskpy.taskhandlers import execution
from tests.file_helper import BASE_DIRECTORY, write_test_file

logging_level = 12

logging.addLevelName(11, "VERBOSE2")
logging.addLevelName(12, "VERBOSE1")

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging_level,
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger()
logger.setLevel(logging_level)


class TaskHandlerExecutionTest(unittest.TestCase):
    # Create a task definition
    touch_task_definition = {
        "type": "execution",
        "hosts": ["172.16.0.11", "172.16.0.12"],
        "username": "application",
        "directory": "/tmp",
        "command": "touch /tmp/testFiles/dest/execution.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    }

    fail_task_definition = {
        "type": "execution",
        "hosts": ["172.16.0.11", "172.16.0.12"],
        "username": "application",
        "directory": "/tmp",
        "command": "test -e /tmp/testFiles/src/execution.test.fail.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    }

    fail_host_task_definition = {
        "type": "execution",
        "hosts": ["172.16.0.11", "172.16.255.12"],
        "username": "application",
        "directory": "/tmp",
        "command": "touch /tmp/testFiles/dest/execution.invalidhost.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    }

    fail_invalid_protocol_task_definition = {
        "type": "execution",
        "hosts": ["172.16.0.11", "172.16.255.12"],
        "username": "application",
        "directory": "/tmp",
        "command": "touch /tmp/testFiles/dest/execution.invalidhost.txt",
        "protocol": {"name": "rubbish"},
    }

    @classmethod
    def setUpClass(cls):
        cls.tearDownClass()

    def test_invalid_protocol(self):
        execution_obj = execution.Execution(
            "invalid-protocol", self.fail_invalid_protocol_task_definition
        )
        # Expect a UnknownProtocolError exception
        with self.assertRaises(exceptions.UnknownProtocolError):
            execution_obj._set_remote_handlers()

    def test_basic_execution(self):
        execution_obj = execution.Execution("df-basic", self.touch_task_definition)
        execution_obj._set_remote_handlers()

        # Validate some things were set as expected
        self.assertEqual(
            execution_obj.remote_handlers[0].__class__.__name__, "SSHExecution"
        )
        self.assertEqual(
            execution_obj.remote_handlers[1].__class__.__name__, "SSHExecution"
        )

        # Run the execution and expect a true status
        self.assertTrue(execution_obj.run())

        # Check the destination file exists on both hosts
        self.assertTrue(os.path.exists(f"{BASE_DIRECTORY}/ssh_1/dest/execution.txt"))
        self.assertTrue(os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/execution.txt"))

    def test_basic_execution_cmd_failure(self):
        # Write a test file to the source directory
        write_test_file(
            f"{BASE_DIRECTORY}/ssh_1/src/execution.test.fail.txt", content="test1234"
        )

        execution_obj = execution.Execution("task-fail", self.fail_task_definition)
        execution_obj._set_remote_handlers()

        # Validate some things were set as expected
        self.assertEqual(
            execution_obj.remote_handlers[0].__class__.__name__, "SSHExecution"
        )
        self.assertEqual(
            execution_obj.remote_handlers[1].__class__.__name__, "SSHExecution"
        )

        # Run the execution and expect a failure
        self.assertFalse(execution_obj.run())

    def test_basic_execution_invalid_host(self):
        execution_obj = execution.Execution("task-fail", self.fail_host_task_definition)
        execution_obj._set_remote_handlers()

        # Validate some things were set as expected
        self.assertEqual(
            execution_obj.remote_handlers[0].__class__.__name__, "SSHExecution"
        )
        self.assertEqual(
            execution_obj.remote_handlers[1].__class__.__name__, "SSHExecution"
        )

        self.assertFalse(execution_obj.run())

        # But the remote file should still have been created on the valid host
        self.assertTrue(
            os.path.exists(f"{BASE_DIRECTORY}/ssh_1/dest/execution.invalidhost.txt")
        )
        self.assertFalse(
            os.path.exists(f"{BASE_DIRECTORY}/ssh_2/dest/execution.invalidhost.txt")
        )

    @classmethod
    def tearDownClass(cls):
        to_remove = [
            f"{BASE_DIRECTORY}/ssh_1/dest/execution.txt",
            f"{BASE_DIRECTORY}/ssh_2/dest/execution.txt",
            f"{BASE_DIRECTORY}/ssh_1/src/execution.test.fail.txt",
            f"{BASE_DIRECTORY}/ssh_1/dest/execution.invalidhost.txt",
        ]
        for file in to_remove:
            if os.path.exists(file):
                pass
                os.remove(file)
