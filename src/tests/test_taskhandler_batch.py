import logging
import os
import random
import unittest

# import opentaskpy
from opentaskpy.config.loader import ConfigLoader

# from opentaskpy.taskhandlers.batch import Batch
from opentaskpy.taskhandlers import batch, execution
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


class TaskHandlerBatchTest(unittest.TestCase):

    # Create a task definition
    basic_batch_definition = {
        "type": "batch",
        "tasks": [
            {
                "order_id": 1,
                "task_id": "touch",
            }
        ],
    }
    touch_task_definition = {
        "type": "execution",
        "hosts": ["172.16.0.11", "172.16.0.12"],
        "username": "application",
        "directory": "/tmp",
        "command": "touch /tmp/testFiles/dest/execution.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    }

    fail_batch_definition = {
        "type": "batch",
        "tasks": [
            {
                "order_id": 1,
                "task_id": "non-existent",
            }
        ],
    }

    # Create a variable with a random number
    RANDOM = random.randint(10000, 99999)

    @classmethod
    def setUpClass(self):

        self.tearDownClass()

        write_test_file("/tmp/variable_lookup.txt", content=f"{self.RANDOM}")

    def test_basic_batch(self):

        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        # We need a config loader object, so that the batch class can load in the configs for
        # the sub tasks
        config_loader = ConfigLoader("test/cfg")
        batch_obj = batch.Batch("basic", self.basic_batch_definition, config_loader)

        # Check that the batch_obj contains an execution type task
        # batch_obj.tasks[0] should be an instance of a execution task handler class
        self.assertIsInstance(batch_obj.task_order_tree[1]["task_handler"], execution.Execution)

        # Run the batch and expect a true status
        self.assertTrue(batch_obj.run())

        # Check the execution task was run
        self.assertTrue(os.path.exists(f"{BASE_DIRECTORY}/ssh_1/src/touchedFile.txt"))

    @classmethod
    def tearDownClass(self):

        to_remove = [
            f"{BASE_DIRECTORY}/ssh_1/dest/execution.txt",
            f"{BASE_DIRECTORY}/ssh_2/dest/execution.txt",
            f"{BASE_DIRECTORY}/ssh_1/src/execution.test.fail.txt",
            f"{BASE_DIRECTORY}/ssh_1/dest/execution.invalidhost.txt",
            "/tmp/variable_lookup.txt",
        ]
        for file in to_remove:
            if os.path.exists(file):
                pass
                os.remove(file)
