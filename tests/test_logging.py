import os
import re
import time
from datetime import datetime

from fixtures.ssh_clients import *  # noqa:F401

import opentaskpy.logging


def test_define_log_file_name(env_vars, tmpdir):
    # Pass in different task types and validate that the log file name is correct
    timestamp = datetime.now().strftime("%Y%m%d-") + r"\d{6}\.\d{6}"
    log_path = "logs"
    expected_result_regex = rf"{log_path}/no_task_id/{timestamp}_B_running.log"

    assert re.search(
        expected_result_regex, opentaskpy.logging._define_log_file_name(None, "B")
    )

    # Pass in a task ID and validate that the log file name is correct
    expected_result_regex = f"{log_path}/123/{timestamp}_B_running.log"
    assert re.search(
        expected_result_regex, opentaskpy.logging._define_log_file_name("123", "B")
    )

    # Manually override the log directory and validate that the path changes
    os.environ["OTF_LOG_DIRECTORY"] = str(tmpdir)
    expected_result_regex = rf"{tmpdir}/no_task_id/{timestamp}_B_running.log"
    assert re.search(
        expected_result_regex, opentaskpy.logging._define_log_file_name(None, "B")
    )

    # unset the environment variable
    del os.environ["OTF_LOG_DIRECTORY"]

    # Set a run prefix and check that log file names correlate
    os.environ["OTF_LOG_RUN_PREFIX"] = "test"
    expected_result = rf"{log_path}/no_task_id/test_B_running.log"
    assert opentaskpy.logging._define_log_file_name(None, "B") == expected_result

    # unset the environment variable if it's set
    if "OTF_LOG_RUN_PREFIX" in os.environ:
        del os.environ["OTF_LOG_RUN_PREFIX"]

    # Call the function to get the current name prefix, then call it again and validate the prefix is the same
    log_filename = opentaskpy.logging._define_log_file_name(None, "B")
    # Sleep 1 second to make sure the filename would have changed
    import time

    time.sleep(1)
    assert log_filename == opentaskpy.logging._define_log_file_name(None, "B")

    # Set an OTF_RUN_ID and validate that the directory name gets set to that
    os.environ["OTF_RUN_ID"] = "some-run-id"
    expected_result_regex = (
        rf"{log_path}/some-run-id/{timestamp}_B_some-task-id_running.log"
    )
    assert re.search(
        expected_result_regex,
        opentaskpy.logging._define_log_file_name("some-task-id", "B"),
    )

    # unset the environment variable if it's set
    if "OTF_RUN_ID" in os.environ:
        del os.environ["OTF_RUN_ID"]

    # Pass no task type, and expect None in it's place
    expected_result_regex = rf"{log_path}/no_task_id/{timestamp}_None_running.log"
    assert re.search(
        expected_result_regex, opentaskpy.logging._define_log_file_name(None, None)
    )


def test_init_logging(env_vars):
    # Call init logging function and ensure that the returned logger includes a TaskFileHandler
    # pointing at the correct filename
    timestamp = datetime.now().strftime("%Y%m%d-") + r"\d{6}\.\d{6}"
    log_path = "logs"
    expected_result_regex = rf"{log_path}/some_task_id/{timestamp}_None_running.log"
    logger = opentaskpy.logging.init_logging("some.class.name1", task_id="some_task_id")

    found_handler = False
    for log_handler in logger.handlers:
        if log_handler.__class__.__name__ == "TaskFileHandler":
            assert re.search(expected_result_regex, log_handler.baseFilename)
            found_handler = True
            break

    assert found_handler

    # Create a logger with a valid task type
    logger = opentaskpy.logging.init_logging(
        "some.class.name2", task_id="some_task_id", task_type="B"
    )
    expected_result_regex = rf"{log_path}/some_task_id/{timestamp}_B_running.log"
    # Find a handler of type TaskFileHandler in the logger
    found_handler = False
    for log_handler in logger.handlers:
        if log_handler.__class__.__name__ == "TaskFileHandler":
            assert re.search(expected_result_regex, log_handler.baseFilename)
            found_handler = True
            break

    assert found_handler

    # Disable logging via env variable and ensure there's no handler defined
    os.environ["OTF_NO_LOG"] = "1"
    logger = opentaskpy.logging.init_logging(
        "some.class.name3", task_id="some_task_id", task_type="B"
    )
    assert len(logger.handlers) == 0


def test_get_latest_log_file(env_vars):
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
    assert opentaskpy.logging.get_latest_log_file(None, "B") is None

    # Rename the last created file to remove the _running suffix
    os.rename(last_created_file, last_created_file.replace("_running", ""))
    last_created_file = last_created_file.replace("_running", "")
    # Run the function again and validate that it still returns nothing
    assert opentaskpy.logging.get_latest_log_file(None, "B") is None

    # Rename this file to _failed
    os.rename(last_created_file, last_created_file.replace("_B", "_B_failed"))
    last_created_file = last_created_file.replace("_B", "_B_failed")
    # Run the function again and validate that it returns this file
    assert opentaskpy.logging.get_latest_log_file(None, "B") == last_created_file

    # Create a new file that has succeeded, make sure it still returns None, as the lastest
    # state is success
    log_file_name = opentaskpy.logging._define_log_file_name(None, "B")
    # Write to the file
    with open(log_file_name, "w") as f:
        f.write("test")
    # Rename the file to remove the _running suffix
    os.rename(log_file_name, log_file_name.replace("_running", ""))

    # Run the function again and validate that it returns nothing, as last state is success
    assert opentaskpy.logging.get_latest_log_file(None, "B") is None


def test_close_log_file(env_vars, tmpdir):
    os.environ["OTF_LOG_DIRECTORY"] = f"{tmpdir}/test/testLogs"

    # Create a logger and log something to it
    logger = opentaskpy.logging.init_logging(
        "some.class.name4", task_id="some_task_id", task_type="B"
    )
    logger.info("test")

    # Find a handler of type TaskFileHandler in the logger
    found_handler = None
    for log_handler in logger.handlers:
        print(log_handler)
        if log_handler.__class__.__name__ == "TaskFileHandler":
            found_handler = log_handler
            break

    assert found_handler is not None

    # Now the file should exist, we will close it with a success state and then check it's been renamed
    opentaskpy.logging.close_log_file(logger, True)

    # Check the file has been renamed
    assert os.path.exists(found_handler.baseFilename.replace("_running", ""))

    # Now create a new logger and log something to it
    logger = opentaskpy.logging.init_logging(
        "some.class.name5", task_id="some_task_id", task_type="B"
    )
    logger.info("test")

    # Do the same, but make it fail
    opentaskpy.logging.close_log_file(logger, False)
    # Check the file has been renamed
    assert os.path.exists(
        logger.handlers[0].baseFilename.replace("_running", "_failed")
    )
