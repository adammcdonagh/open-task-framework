# pylint: skip-file
import pytest

from opentaskpy.config.schemas import validate_batch_json


@pytest.fixture(scope="function")
def valid_batch_definition():
    return {
        "type": "batch",
        "tasks": [{"order_id": 1, "task_id": "sleep-300"}],
    }


def test_batch(valid_batch_definition):
    json_data = valid_batch_definition

    assert validate_batch_json(json_data)


def test_batch_missing_tasks(valid_batch_definition):
    json_data = valid_batch_definition

    del json_data["tasks"]
    assert not validate_batch_json(json_data)


def test_batch_timeout(valid_batch_definition):
    json_data = valid_batch_definition

    json_data["tasks"][0]["timeout"] = 10
    assert validate_batch_json(json_data)

    json_data["tasks"][0]["timeout"] = 0
    assert not validate_batch_json(json_data)

    json_data["tasks"][0]["timeout"] = -1
    assert not validate_batch_json(json_data)


def test_batch_continue_on_fail(valid_batch_definition):
    json_data = valid_batch_definition

    json_data["tasks"][0]["continue_on_fail"] = True
    assert validate_batch_json(json_data)

    json_data["tasks"][0]["continue_on_fail"] = False
    assert validate_batch_json(json_data)


def test_batch_retry_on_rerun(valid_batch_definition):
    json_data = valid_batch_definition

    json_data["tasks"][0]["retry_on_rerun"] = True
    assert validate_batch_json(json_data)

    json_data["tasks"][0]["retry_on_rerun"] = False
    assert validate_batch_json(json_data)
