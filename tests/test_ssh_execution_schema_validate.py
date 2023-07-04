# pylint: skip-file
import pytest

from opentaskpy.config.schemas import validate_execution_json


@pytest.fixture(scope="function")
def valid_protocol_definition():
    return {
        "name": "ssh",
        "credentials": {
            "username": "test",
        },
    }


@pytest.fixture(scope="function")
def valid_execution(valid_protocol_definition):
    return {
        "hosts": ["{{ HOST_A }}"],
        "directory": "/tmp",
        "command": "test -e test.txt",
        "protocol": valid_protocol_definition,
    }


def test_ssh_basic(valid_execution):
    json_data = {
        "type": "execution",
    }
    # Append properties from valid_execution onto json_data
    json_data.update(valid_execution)

    assert validate_execution_json(json_data)

    # Add another host
    json_data["hosts"].append("host2")

    assert validate_execution_json(json_data)

    # Remove protocol
    del json_data["protocol"]
    assert not validate_execution_json(json_data)

    # Remove all hosts
    del json_data["hosts"]
    assert not validate_execution_json(json_data)
