# pylint: skip-file
# ruff: noqa

import json
import os

import pytest

from opentaskpy.cli import batch_validator

valid_batch_defininition = {
    "type": "batch",
    "tasks": [
        {"task_id": "task1", "order_id": 1},
        {"task_id": "task2", "order_id": 2, "dependencies": [1]},
    ],
}

valid_task_definition = {
    "type": "execution",
    "command": "echo 'hello world'",
    "protocol": "local",
}

batch_def_no_order_id_1 = {
    "type": "batch",
    "tasks": [
        {"task_id": "task1", "order_id": 2},
        {"task_id": "task2", "order_id": 3, "dependencies": [2]},
    ],
}

batch_def_dependency_non_existent_task_id = {
    "type": "batch",
    "tasks": [
        {"task_id": "task1", "order_id": 1},
        {"task_id": "task2", "order_id": 2, "dependencies": [3]},
    ],
}

batch_def_non_existent_task_id = {
    "type": "batch",
    "tasks": [
        {"task_id": "task3", "order_id": 1},
        {"task_id": "task4", "order_id": 2, "dependencies": [1]},
    ],
}


# Since the batch validator uses OTF_NOOP, we need to clear it down after
# the tests in this module have completed
@pytest.fixture(scope="module", autouse=True)
def tests_setup_and_teardown():
    # Will be executed before the first test
    old_environ = dict(os.environ)

    yield

    # Will be executed after the last test
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture(scope="function")
def write_config_files(tmpdir):
    # Write the valid_task_definition into a temporary dir as both task1 and task2
    for i in range(1, 3):
        with open(f"{tmpdir}/task{i}.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(valid_task_definition))

    # Create a blank variables.json file in the temporary dir
    with open(f"{tmpdir}/variables.json", "w", encoding="utf-8") as f:
        f.write("{}")


def test_valid_batch_definition(tmpdir, write_config_files):

    # Write the valid_batch_definition into a temporary dir
    with open(f"{tmpdir}/test-task.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(valid_batch_defininition))

    # Run the main function and expect a True response
    assert batch_validator.main("test-task", 2, tmpdir)


def test_batch_definition_no_order_id_1(tmpdir, write_config_files):

    # Write the batch_def_no_order_id_1 into a temporary dir
    with open(f"{tmpdir}/test-task.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(batch_def_no_order_id_1))

    # Expect a False response as there's no task with order_id 1
    assert not batch_validator.main("test-task", 2, tmpdir)


def test_batch_definition_dependency_non_existent_task_id(tmpdir, write_config_files):

    # Write the batch_def_dependency_non_existent_task_id into a temporary dir
    with open(f"{tmpdir}/test-task.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(batch_def_dependency_non_existent_task_id))

    # Expect a False response as there's a dependency pointing at a non-existent task_id
    assert not batch_validator.main("test-task", 2, tmpdir)


def test_batch_definition_non_existent_task_id(tmpdir, write_config_files):

    # Write the batch_def_non_existent_task_id into a temporary dir
    with open(f"{tmpdir}/test-task.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(batch_def_non_existent_task_id))

    # Expect a FileNotFoundError exception as the task_id doesn't exist
    with pytest.raises(FileNotFoundError):
        batch_validator.main("test-task", 2, tmpdir)
