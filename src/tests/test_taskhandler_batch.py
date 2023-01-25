import logging
import os
import random
import shutil
import unittest

import opentaskpy.logging
from opentaskpy.config.loader import ConfigLoader

# from opentaskpy.taskhandlers.batch import Batch
from opentaskpy.taskhandlers import batch, execution, transfer
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

    timeout_batch_definition = {
        "type": "batch",
        "tasks": [
            {
                "order_id": 1,
                "task_id": "sleep-300",
                "timeout": 3,
            }
        ],
    }

    parallel_batch_definition = {
        "type": "batch",
        "tasks": [
            {
                "order_id": 1,
                "task_id": "touch",
            },
            {
                "order_id": 2,
                "task_id": "scp-basic",
            },
        ],
    }

    parallel_batch_with_single_failure_definition = {
        "type": "batch",
        "tasks": [
            {
                "order_id": 1,
                "task_id": "touch",
            },
            {
                "order_id": 2,
                "task_id": "fail-command",
            },
        ],
    }

    parallel_batch_with_single_failure_with_retry_definition = {
        "type": "batch",
        "tasks": [
            {
                "order_id": 1,
                "task_id": "touch",
                "retry_on_rerun": True,
            },
            {
                "order_id": 2,
                "task_id": "fail-command",
            },
        ],
    }

    dependent_batch_definition = {
        "type": "batch",
        "tasks": [
            {
                "order_id": 1,
                "task_id": "touch",
            },
            {
                "order_id": 2,
                "task_id": "scp-basic",
                "dependencies": [
                    1,
                ],
            },
        ],
    }

    dependent_batch_continue_on_fail_definition = {
        "type": "batch",
        "tasks": [
            {
                "order_id": 1,
                "task_id": "fail-command",
                "continue_on_fail": True,
            },
            {
                "order_id": 2,
                "task_id": "scp-basic",
                "dependencies": [
                    1,
                ],
            },
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
    def setUpClass(cls):

        cls.tearDownClass()

        write_test_file("/tmp/variable_lookup.txt", content=f"{cls.RANDOM}")

    def test_basic_batch(self):

        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        # We need a config loader object, so that the batch class can load in the configs for
        # the sub tasks
        config_loader = ConfigLoader("test/cfg")
        batch_obj = batch.Batch("basic", self.basic_batch_definition, config_loader)

        # Check that the batch_obj contains an execution type task
        # batch_obj.tasks[0] should be an instance of a execution task handler class
        self.assertIsInstance(
            batch_obj.task_order_tree[1]["task_handler"], execution.Execution
        )

        # Run the batch and expect a true status
        self.assertTrue(batch_obj.run())

        # Check the execution task was run
        self.assertTrue(os.path.exists(f"{BASE_DIRECTORY}/ssh_1/src/touchedFile.txt"))

    def test_batch_parallel(self):
        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        # We need a config loader object, so that the batch class can load in the configs for
        # the sub tasks
        config_loader = ConfigLoader("test/cfg")
        batch_obj = batch.Batch(
            "parallel", self.parallel_batch_definition, config_loader
        )

        # Check that the batch_obj contains an execution type task
        # batch_obj.tasks[0] should be an instance of a execution task handler class
        self.assertIsInstance(
            batch_obj.task_order_tree[1]["task_handler"], execution.Execution
        )
        self.assertIsInstance(
            batch_obj.task_order_tree[2]["task_handler"], transfer.Transfer
        )

        # Run the batch and expect a true status
        self.assertTrue(batch_obj.run())

    def test_batch_dependencies(self):
        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        # We need a config loader object, so that the batch class can load in the configs for
        # the sub tasks
        config_loader = ConfigLoader("test/cfg")
        batch_obj = batch.Batch(
            "parallel", self.dependent_batch_definition, config_loader
        )

        # Check that the batch_obj contains an execution type task
        # batch_obj.tasks[0] should be an instance of a execution task handler class
        self.assertIsInstance(
            batch_obj.task_order_tree[1]["task_handler"], execution.Execution
        )
        self.assertIsInstance(
            batch_obj.task_order_tree[2]["task_handler"], transfer.Transfer
        )

        # Run the batch and expect a true status
        self.assertTrue(batch_obj.run())

    def test_batch_invalid_task_id(self):
        # Create a test file
        write_test_file(f"{BASE_DIRECTORY}/ssh_1/src/test.txt", content="test1234")

        # We need a config loader object, so that the batch class can load in the configs for
        # the sub tasks
        config_loader = ConfigLoader("test/cfg")
        # Expect a FileNotFoundError as the task_id is non-existent
        with self.assertRaises(FileNotFoundError):
            batch.Batch("fail", self.fail_batch_definition, config_loader)

    def test_batch_timeout(self):
        # Set a log file prefix for easy identification
        # Get a random number

        os.environ["OTF_LOG_RUN_PREFIX"] = f"testbatch_timeout_{self.RANDOM}"

        config_loader = ConfigLoader("test/cfg")
        batch_obj = batch.Batch("timeout", self.timeout_batch_definition, config_loader)
        self.assertFalse(batch_obj.run())

        # Validate that a log has been created with the correct status
        # Use the logging module to get the right log file name
        log_file_name_batch = opentaskpy.logging._define_log_file_name("timeout", "B")
        log_file_name_task = opentaskpy.logging._define_log_file_name("sleep-300", "E")

        # Check that both exist, but renamed with _failed
        self.assertTrue(
            os.path.exists(log_file_name_batch.replace("_running", "_failed"))
        )
        self.assertTrue(
            os.path.exists(log_file_name_task.replace("_running", "_failed"))
        )

    def test_batch_parallel_single_success(self):
        # Forcing a prefix makes it easy to identify log files, as well as
        # ensuring that any rerun logic doesn't get hit
        os.environ["OTF_LOG_RUN_PREFIX"] = f"testbatch_timeout_{self.RANDOM}"

        config_loader = ConfigLoader("test/cfg")
        batch_obj = batch.Batch(
            "parallel-single-failure",
            self.parallel_batch_with_single_failure_definition,
            config_loader,
        )
        # Run and expect a false status
        self.assertFalse(batch_obj.run())

        # Validate that a log has been created with the correct status
        # Use the logging module to get the right log file name
        log_file_name_batch = opentaskpy.logging._define_log_file_name(
            "parallel-single-failure", "B"
        )
        log_file_name_touch_task = opentaskpy.logging._define_log_file_name(
            "touch", "E"
        )
        log_file_name_failed_task = opentaskpy.logging._define_log_file_name(
            "fail-command", "E"
        )

        # Check that all exist, with the right status
        self.assertTrue(
            os.path.exists(log_file_name_batch.replace("_running", "_failed"))
        )
        self.assertTrue(
            os.path.exists(log_file_name_touch_task.replace("_running", ""))
        )
        self.assertTrue(
            os.path.exists(log_file_name_failed_task.replace("_running", "_failed"))
        )

    def test_batch_resume_after_failure(self):
        task_id = "parallel-single-failure-1"
        # Ensure there are no logs for this batch
        shutil.rmtree(
            f"{opentaskpy.logging.LOG_DIRECTORY}/{task_id}", ignore_errors=True
        )

        config_loader = ConfigLoader("test/cfg")
        batch_obj = batch.Batch(
            task_id,
            self.parallel_batch_with_single_failure_definition,
            config_loader,
        )
        # Run and expect a false status
        self.assertFalse(batch_obj.run())

        # Validate that a log has been created with the correct status
        # Use the logging module to get the right log file name
        log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
        log_file_name_touch_task = opentaskpy.logging._define_log_file_name(
            "touch", "E"
        )
        log_file_name_failed_task = opentaskpy.logging._define_log_file_name(
            "fail-command", "E"
        )

        # Check that all exist, with the right status
        self.assertTrue(
            os.path.exists(log_file_name_batch.replace("_running", "_failed"))
        )
        self.assertTrue(
            os.path.exists(log_file_name_touch_task.replace("_running", ""))
        )
        self.assertTrue(
            os.path.exists(log_file_name_failed_task.replace("_running", "_failed"))
        )

        # Reset the prefix so it doesn't get reused
        del os.environ["OTF_LOG_RUN_PREFIX"]

        # Run it again, but this time, expect it to only run the failed task
        batch_obj = batch.Batch(
            task_id,
            self.parallel_batch_with_single_failure_definition,
            config_loader,
        )

        # Check the task_order_tree to only have the failed task in a NOT_STARTED state
        self.assertEqual(batch_obj.task_order_tree[1]["status"], "COMPLETED")
        self.assertEqual(batch_obj.task_order_tree[2]["status"], "NOT_STARTED")

        # Run and expect a false status
        self.assertFalse(batch_obj.run())

        # Validate that the touch task has been skipped, so there's no log file
        log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
        log_file_name_touch_task = opentaskpy.logging._define_log_file_name(
            "touch", "E"
        )
        log_file_name_failed_task = opentaskpy.logging._define_log_file_name(
            "fail-command", "E"
        )

        # Check that all exist, with the right status
        self.assertTrue(
            os.path.exists(log_file_name_batch.replace("_running", "_failed"))
        )
        self.assertFalse(os.path.exists(log_file_name_touch_task))
        self.assertTrue(
            os.path.exists(log_file_name_failed_task.replace("_running", "_failed"))
        )

    def test_batch_resume_after_failure_retry_successful_tasks(self):
        task_id = "parallel-single-failure-2"
        # Ensure there are no logs for this batch
        shutil.rmtree(
            f"{opentaskpy.logging.LOG_DIRECTORY}/{task_id}", ignore_errors=True
        )

        config_loader = ConfigLoader("test/cfg")
        batch_obj = batch.Batch(
            task_id,
            self.parallel_batch_with_single_failure_with_retry_definition,
            config_loader,
        )
        # Run and expect a false status
        self.assertFalse(batch_obj.run())

        # Validate that a log has been created with the correct status
        # Use the logging module to get the right log file name
        log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
        log_file_name_touch_task = opentaskpy.logging._define_log_file_name(
            "touch", "E"
        )
        log_file_name_failed_task = opentaskpy.logging._define_log_file_name(
            "fail-command", "E"
        )

        # Check that all exist, with the right status
        self.assertTrue(
            os.path.exists(log_file_name_batch.replace("_running", "_failed"))
        )
        self.assertTrue(
            os.path.exists(log_file_name_touch_task.replace("_running", ""))
        )
        self.assertTrue(
            os.path.exists(log_file_name_failed_task.replace("_running", "_failed"))
        )

        # Reset the prefix so it doesn't get reused
        del os.environ["OTF_LOG_RUN_PREFIX"]

        # Run it again, but this time, expect it to only run the failed task
        batch_obj = batch.Batch(
            task_id,
            self.parallel_batch_with_single_failure_with_retry_definition,
            config_loader,
        )

        # Check the task_order_tree to check both tasks have a NOT_STARTED state
        self.assertEqual(batch_obj.task_order_tree[1]["status"], "NOT_STARTED")
        self.assertEqual(batch_obj.task_order_tree[2]["status"], "NOT_STARTED")

        # Run and expect a false status
        self.assertFalse(batch_obj.run())

        # Validate that the touch task has been skipped, so there's no log file
        log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
        log_file_name_touch_task = opentaskpy.logging._define_log_file_name(
            "touch", "E"
        )
        log_file_name_failed_task = opentaskpy.logging._define_log_file_name(
            "fail-command", "E"
        )

        # Check that all exist, with the right status
        self.assertTrue(
            os.path.exists(log_file_name_batch.replace("_running", "_failed"))
        )
        self.assertTrue(
            os.path.exists(log_file_name_touch_task.replace("_running", ""))
        )
        self.assertTrue(
            os.path.exists(log_file_name_failed_task.replace("_running", "_failed"))
        )

    def test_batch_continue_on_failure(self):
        task_id = "dependency-continue-on-fail-1"
        # Ensure there are no logs for this batch
        shutil.rmtree(
            f"{opentaskpy.logging.LOG_DIRECTORY}/{task_id}", ignore_errors=True
        )

        config_loader = ConfigLoader("test/cfg")
        batch_obj = batch.Batch(
            task_id,
            self.dependent_batch_continue_on_fail_definition,
            config_loader,
        )
        # Run and expect a false status
        self.assertFalse(batch_obj.run())

        # Validate that a log has been created with the correct status
        # Use the logging module to get the right log file name
        log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
        log_file_name_fail_task = opentaskpy.logging._define_log_file_name(
            "fail-command", "E"
        )
        log_file_name_scp_task = opentaskpy.logging._define_log_file_name(
            "scp-basic", "T"
        )

        # Check that all exist, with the right status
        self.assertTrue(
            os.path.exists(log_file_name_batch.replace("_running", "_failed"))
            # The failed task that we continue on, should still have a failed log
        )
        self.assertTrue(
            os.path.exists(log_file_name_fail_task.replace("_running", "_failed"))
        )
        # The successful task should have a successful
        self.assertTrue(os.path.exists(log_file_name_scp_task.replace("_running", "")))

    @classmethod
    def tearDownClass(cls):

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
