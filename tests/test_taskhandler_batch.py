import os
import random

from fixtures.ssh_clients import *  # noqa:F401
from pytest_shell import fs

import opentaskpy.logging
from opentaskpy.config.loader import ConfigLoader

# from opentaskpy.taskhandlers.batch import Batch
from opentaskpy.taskhandlers import batch, execution, transfer

os.environ["OTF_NO_LOG"] = "1"
os.environ["OTF_LOG_LEVEL"] = "DEBUG"


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


def test_basic_batch(setup_ssh_keys, env_vars, root_dir):
    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    # We need a config loader object, so that the batch class can load in the configs for
    # the sub tasks
    config_loader = ConfigLoader("test/cfg")
    batch_obj = batch.Batch(f"basic-{RANDOM}", basic_batch_definition, config_loader)

    # Check that the batch_obj contains an execution type task
    # batch_obj.tasks[0] should be an instance of a execution task handler class
    assert isinstance(
        batch_obj.task_order_tree[1]["task_handler"],
        execution.Execution,
    )

    # Run the batch and expect a true status
    assert batch_obj.run()

    # Check the execution task was run
    assert os.path.exists(f"{root_dir}/testFiles/ssh_1/src/touchedFile.txt")


def test_batch_parallel(setup_ssh_keys, env_vars, root_dir):
    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    # We need a config loader object, so that the batch class can load in the configs for
    # the sub tasks
    config_loader = ConfigLoader("test/cfg")
    batch_obj = batch.Batch(
        f"parallel-{RANDOM}", parallel_batch_definition, config_loader
    )

    # Check that the batch_obj contains an execution type task
    # batch_obj.tasks[0] should be an instance of a execution task handler class
    assert isinstance(batch_obj.task_order_tree[1]["task_handler"], execution.Execution)
    assert isinstance(batch_obj.task_order_tree[2]["task_handler"], transfer.Transfer)

    # Run the batch and expect a true status
    assert batch_obj.run()


def test_batch_dependencies(root_dir, setup_ssh_keys, env_vars):
    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    # We need a config loader object, so that the batch class can load in the configs for
    # the sub tasks
    config_loader = ConfigLoader("test/cfg")
    batch_obj = batch.Batch(
        f"dependencies-1-{RANDOM}", dependent_batch_definition, config_loader
    )

    # Check that the batch_obj contains an execution type task
    # batch_obj.tasks[0] should be an instance of a execution task handler class
    assert isinstance(batch_obj.task_order_tree[1]["task_handler"], execution.Execution)
    assert isinstance(batch_obj.task_order_tree[2]["task_handler"], transfer.Transfer)

    # Run the batch and expect a true status
    assert batch_obj.run()


def test_batch_invalid_task_id(root_dir, setup_ssh_keys, env_vars):
    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    # We need a config loader object, so that the batch class can load in the configs for
    # the sub tasks
    config_loader = ConfigLoader("test/cfg")
    # Expect a FileNotFoundError as the task_id is non-existent
    with pytest.raises(FileNotFoundError):
        batch.Batch(f"fail-{RANDOM}", fail_batch_definition, config_loader)


def test_batch_timeout(setup_ssh_keys, env_vars, root_dir):
    # Set a log file prefix for easy identification
    # Get a random number

    os.environ["OTF_LOG_RUN_PREFIX"] = f"testbatch_timeout_{RANDOM}"

    config_loader = ConfigLoader("test/cfg")
    batch_obj = batch.Batch("timeout", timeout_batch_definition, config_loader)
    assert not batch_obj.run()

    # Validate that a log has been created with the correct status
    # Use the logging module to get the right log file name
    log_file_name_batch = opentaskpy.logging._define_log_file_name("timeout", "B")
    log_file_name_task = opentaskpy.logging._define_log_file_name("sleep-300", "E")

    # Check that both exist, but renamed with _failed
    assert os.path.exists(log_file_name_batch.replace("_running", "_failed"))
    assert os.path.exists(log_file_name_task.replace("_running", "_failed"))


def test_batch_parallel_single_success(setup_ssh_keys, env_vars, root_dir):
    # Forcing a prefix makes it easy to identify log files, as well as
    # ensuring that any rerun logic doesn't get hit
    os.environ["OTF_LOG_RUN_PREFIX"] = f"testbatch_timeout_{RANDOM}"

    task_id = f"parallel-single-failure-{RANDOM}"

    config_loader = ConfigLoader("test/cfg")
    batch_obj = batch.Batch(
        task_id,
        parallel_batch_with_single_failure_definition,
        config_loader,
    )
    # Run and expect a false status
    assert not batch_obj.run()

    # Validate that a log has been created with the correct status
    # Use the logging module to get the right log file name
    log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
    log_file_name_touch_task = opentaskpy.logging._define_log_file_name("touch", "E")
    log_file_name_failed_task = opentaskpy.logging._define_log_file_name(
        "fail-command", "E"
    )

    # Check that all exist, with the right status
    assert os.path.exists(log_file_name_batch.replace("_running", "_failed"))
    assert os.path.exists(log_file_name_touch_task.replace("_running", ""))
    assert os.path.exists(log_file_name_failed_task.replace("_running", "_failed"))


def test_batch_resume_after_failure(setup_ssh_keys, env_vars, root_dir):
    task_id = f"parallel-single-failure-1-{RANDOM}"
    # Ensure there are no logs for this batch
    shutil.rmtree(f"{opentaskpy.logging.LOG_DIRECTORY}/{task_id}", ignore_errors=True)

    config_loader = ConfigLoader("test/cfg")
    batch_obj = batch.Batch(
        task_id,
        parallel_batch_with_single_failure_definition,
        config_loader,
    )
    # Run and expect a false status
    assert not batch_obj.run()

    # Validate that a log has been created with the correct status
    # Use the logging module to get the right log file name
    log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
    log_file_name_touch_task = opentaskpy.logging._define_log_file_name("touch", "E")
    log_file_name_failed_task = opentaskpy.logging._define_log_file_name(
        "fail-command", "E"
    )

    # Check that all exist, with the right status
    assert os.path.exists(log_file_name_batch.replace("_running", "_failed"))
    assert os.path.exists(log_file_name_touch_task.replace("_running", ""))
    assert os.path.exists(log_file_name_failed_task.replace("_running", "_failed"))

    # Reset the prefix so it doesn't get reused
    del os.environ["OTF_LOG_RUN_PREFIX"]

    # Run it again, but this time, expect it to only run the failed task
    batch_obj = batch.Batch(
        task_id,
        parallel_batch_with_single_failure_definition,
        config_loader,
    )

    # Check the task_order_tree to only have the failed task in a NOT_STARTED state
    assert batch_obj.task_order_tree[1]["status"] == "COMPLETED"
    assert batch_obj.task_order_tree[2]["status"] == "NOT_STARTED"

    # Run and expect a false status
    assert not batch_obj.run()

    # Validate that the touch task has been skipped, so there's no log file
    log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
    log_file_name_touch_task = opentaskpy.logging._define_log_file_name("touch", "E")
    log_file_name_failed_task = opentaskpy.logging._define_log_file_name(
        "fail-command", "E"
    )

    # Check that all exist, with the right status
    assert os.path.exists(log_file_name_batch.replace("_running", "_failed"))
    assert not os.path.exists(log_file_name_touch_task)
    assert os.path.exists(log_file_name_failed_task.replace("_running", "_failed"))


def test_batch_resume_after_failure_retry_successful_tasks(
    setup_ssh_keys, env_vars, root_dir
):
    task_id = f"parallel-single-failure-2-{RANDOM}"
    # Ensure there are no logs for this batch
    shutil.rmtree(f"{opentaskpy.logging.LOG_DIRECTORY}/{task_id}", ignore_errors=True)

    config_loader = ConfigLoader("test/cfg")
    batch_obj = batch.Batch(
        task_id,
        parallel_batch_with_single_failure_with_retry_definition,
        config_loader,
    )
    # Run and expect a false status
    assert not batch_obj.run()

    # Validate that a log has been created with the correct status
    # Use the logging module to get the right log file name
    log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
    log_file_name_touch_task = opentaskpy.logging._define_log_file_name("touch", "E")
    log_file_name_failed_task = opentaskpy.logging._define_log_file_name(
        "fail-command", "E"
    )

    # Check that all exist, with the right status
    assert os.path.exists(log_file_name_batch.replace("_running", "_failed"))
    assert os.path.exists(log_file_name_touch_task.replace("_running", ""))
    assert os.path.exists(log_file_name_failed_task.replace("_running", "_failed"))

    # Reset the prefix so it doesn't get reused
    del os.environ["OTF_LOG_RUN_PREFIX"]

    # Run it again, but this time, expect it to only run the failed task
    batch_obj = batch.Batch(
        task_id,
        parallel_batch_with_single_failure_with_retry_definition,
        config_loader,
    )

    # Check the task_order_tree to check both tasks have a NOT_STARTED state
    assert batch_obj.task_order_tree[1]["status"], "NOT_STARTED"
    assert batch_obj.task_order_tree[2]["status"], "NOT_STARTED"

    # Run and expect a false status
    assert not batch_obj.run()

    # Validate that the touch task has been skipped, so there's no log file
    log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
    log_file_name_touch_task = opentaskpy.logging._define_log_file_name("touch", "E")
    log_file_name_failed_task = opentaskpy.logging._define_log_file_name(
        "fail-command", "E"
    )

    # Check that all exist, with the right status
    assert os.path.exists(log_file_name_batch.replace("_running", "_failed"))
    assert os.path.exists(log_file_name_touch_task.replace("_running", ""))
    assert os.path.exists(log_file_name_failed_task.replace("_running", "_failed"))


def test_batch_continue_on_failure(setup_ssh_keys, env_vars, root_dir):
    task_id = f"dependency-continue-on-fail-1-{RANDOM}"
    # Ensure there are no logs for this batch
    shutil.rmtree(f"{opentaskpy.logging.LOG_DIRECTORY}/{task_id}", ignore_errors=True)

    config_loader = ConfigLoader("test/cfg")
    batch_obj = batch.Batch(
        task_id,
        dependent_batch_continue_on_fail_definition,
        config_loader,
    )
    # Run and expect a false status
    assert not batch_obj.run()

    # Validate that a log has been created with the correct status
    # Use the logging module to get the right log file name
    log_file_name_batch = opentaskpy.logging._define_log_file_name(task_id, "B")
    log_file_name_fail_task = opentaskpy.logging._define_log_file_name(
        "fail-command", "E"
    )
    log_file_name_scp_task = opentaskpy.logging._define_log_file_name("scp-basic", "T")

    # Check that all exist, with the right status
    assert os.path.exists(log_file_name_batch.replace("_running", "_failed"))

    # The failed task that we continue on, should still have a failed log
    assert os.path.exists(log_file_name_fail_task.replace("_running", "_failed"))

    # The successful task should have a successful
    assert os.path.exists(log_file_name_scp_task.replace("_running", ""))
