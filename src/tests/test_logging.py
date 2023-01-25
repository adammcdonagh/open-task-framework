import os
import shutil
import time
import unittest
from datetime import datetime

import opentaskpy.logging


class LoggingTest(unittest.TestCase):
    def setUp(self):
        self.tearDown()

    def test_define_log_file_name(self):
        # Pass in different task types and validate that the log file name is correct
        timestamp = datetime.now().strftime("%Y%m%d-") + r"\d{6}\.\d{6}"
        log_path = opentaskpy.logging.LOG_DIRECTORY
        expected_result_regex = rf"{log_path}/no_task_id/{timestamp}_B_running.log"

        self.assertRegex(
            opentaskpy.logging._define_log_file_name(None, "B"),
            expected_result_regex,
        )

        # Pass in a task ID and validate that the log file name is correct
        expected_result_regex = f"{log_path}/123/{timestamp}_B_running.log"
        self.assertRegex(
            opentaskpy.logging._define_log_file_name("123", "B"),
            expected_result_regex,
        )

        # Manually override the log directory and validate that the path changes
        os.environ["OTF_LOG_DIRECTORY"] = "/tmp"
        expected_result_regex = rf"/tmp/no_task_id/{timestamp}_B_running.log"
        self.assertRegex(
            opentaskpy.logging._define_log_file_name(None, "B"),
            expected_result_regex,
        )

        # unset the environment variable
        del os.environ["OTF_LOG_DIRECTORY"]

        # Set a run prefix and check that log file names correlate
        os.environ["OTF_LOG_RUN_PREFIX"] = "test"
        expected_result = rf"{log_path}/no_task_id/test_B_running.log"
        self.assertEqual(
            opentaskpy.logging._define_log_file_name(None, "B"),
            expected_result,
        )

        # unset the environment variable if it's set
        if "OTF_LOG_RUN_PREFIX" in os.environ:
            del os.environ["OTF_LOG_RUN_PREFIX"]

        # Call the function to get the current name prefix, then call it again and validate the prefix is the same
        log_filename = opentaskpy.logging._define_log_file_name(None, "B")
        # Sleep 1 second to make sure the filename would have changed
        import time

        time.sleep(1)
        self.assertEqual(
            log_filename,
            opentaskpy.logging._define_log_file_name(None, "B"),
        )

        # Set an OTF_RUN_ID and validate that the directory name gets set to that
        os.environ["OTF_RUN_ID"] = "some-run-id"
        expected_result = (
            rf"{log_path}/some-run-id/{timestamp}_B_some-task-id_running.log"
        )
        self.assertRegex(
            opentaskpy.logging._define_log_file_name("some-task-id", "B"),
            expected_result,
        )

        # unset the environment variable if it's set
        if "OTF_RUN_ID" in os.environ:
            del os.environ["OTF_RUN_ID"]

        # Pass no task type, and expect None in it's place
        expected_result = rf"{log_path}/no_task_id/{timestamp}_None_running.log"
        self.assertRegex(
            opentaskpy.logging._define_log_file_name(None, None),
            expected_result,
        )

    def test_init_logging(self):
        # Call init logging function and ensure that the returned logger includes a TaskFileHandler
        # pointing at the correct filename
        timestamp = datetime.now().strftime("%Y%m%d-") + r"\d{6}\.\d{6}"
        log_path = opentaskpy.logging.LOG_DIRECTORY
        expected_result_regex = rf"{log_path}/some_task_id/{timestamp}_None_running.log"
        logger = opentaskpy.logging.init_logging(
            "some.class.name1", task_id="some_task_id"
        )

        self.assertRegex(logger.handlers[0].baseFilename, expected_result_regex)
        # Validate the handler is of type TaskFileHandler
        self.assertEqual(logger.handlers[0].__class__.__name__, "TaskFileHandler")

        # Create a logger with a valid task type
        logger = opentaskpy.logging.init_logging(
            "some.class.name2", task_id="some_task_id", task_type="B"
        )
        expected_result_regex = rf"{log_path}/some_task_id/{timestamp}_B_running.log"
        self.assertRegex(logger.handlers[0].baseFilename, expected_result_regex)

        # Disable logging via env variable and ensure there's no handler defined
        os.environ["OTF_NO_LOG"] = "1"
        logger = opentaskpy.logging.init_logging(
            "some.class.name3", task_id="some_task_id", task_type="B"
        )
        self.assertEqual(len(logger.handlers), 0)

    def test_get_latest_log_file(self):
        # Setup some dummy log files
        log_path = "test/testLogs"
        os.environ["OTF_LOG_DIRECTORY"] = log_path

        last_created_file = None

        # loop 1 to 10
        for _ in range(1, 11):

            log_file_name = opentaskpy.logging._define_log_file_name(None, "B")
            # Ensure the directory exists, if not, create it
            if not os.path.exists(os.path.dirname(log_file_name)):
                os.makedirs(os.path.dirname(log_file_name))

            # Create the file
            with open(log_file_name, "w") as f:
                f.write("test")
            # Sleep 1 second to make sure the filename would have changed
            time.sleep(0.01)
            # Clear the prefix which will have been set in the environment
            del os.environ["OTF_LOG_RUN_PREFIX"]
            last_created_file = log_file_name

        # Run the function to see what it thinks the latest file is,
        # this should return none, because they are all in the _running state to being with
        self.assertEqual(opentaskpy.logging.get_latest_log_file(None, "B"), None)

        # Rename the last created file to remove the _running suffix
        os.rename(last_created_file, last_created_file.replace("_running", ""))
        last_created_file = last_created_file.replace("_running", "")
        # Run the function again and validate that it still returns nothing
        self.assertEqual(opentaskpy.logging.get_latest_log_file(None, "B"), None)

        # Rename this file to _failed
        os.rename(last_created_file, last_created_file.replace("_B", "_B_failed"))
        last_created_file = last_created_file.replace("_B", "_B_failed")
        # Run the function again and validate that it returns this file
        self.assertEqual(
            opentaskpy.logging.get_latest_log_file(None, "B"), last_created_file
        )

        # Create a new file that has succeeded, make sure it still returns None, as the lastest
        # state is success
        log_file_name = opentaskpy.logging._define_log_file_name(None, "B")
        # Write to the file
        with open(log_file_name, "w") as f:
            f.write("test")
        # Rename the file to remove the _running suffix
        os.rename(log_file_name, log_file_name.replace("_running", ""))

        # Run the function again and validate that it returns nothing, as last state is success
        self.assertEqual(opentaskpy.logging.get_latest_log_file(None, "B"), None)

    def test_close_log_file(self):
        log_path = "test/testLogs"
        os.environ["OTF_LOG_DIRECTORY"] = log_path

        # Create a logger and log something to it
        logger = opentaskpy.logging.init_logging(
            "some.class.name4", task_id="some_task_id", task_type="B"
        )
        logger.info("test")

        # Now the file should exist, we will close it with a success state and then check it's been renamed
        opentaskpy.logging.close_log_file(logger, True)
        # Check the file has been renamed
        self.assertTrue(
            os.path.exists(logger.handlers[0].baseFilename.replace("_running", ""))
        )

        # Now create a new logger and log something to it
        logger = opentaskpy.logging.init_logging(
            "some.class.name5", task_id="some_task_id", task_type="B"
        )
        logger.info("test")

        # Do the same, but make it fail
        opentaskpy.logging.close_log_file(logger, False)
        # Check the file has been renamed
        self.assertTrue(
            os.path.exists(
                logger.handlers[0].baseFilename.replace("_running", "_failed")
            )
        )

    def tearDown(self):
        # Remove the test log directory
        log_path = "test/testLogs"
        if os.path.exists(log_path):
            shutil.rmtree(log_path)
