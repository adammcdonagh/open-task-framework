# pylint: skip-file
import pytest

from opentaskpy.config.schemas import validate_transfer_json


@pytest.fixture(scope="function")
def valid_protocol_definition():
    return {"name": "email"}


@pytest.fixture(scope="function")
def valid_source_definition():
    return {
        "hostname": "{{ HOST_A }}",
        "directory": "/tmp/testFiles/src",
        "fileRegex": ".*\\.txt",
        "protocol": {"name": "ssh", "credentials": {"username": "test"}},
    }


@pytest.fixture(scope="function")
def valid_destination_definition(valid_protocol_definition):
    return {
        "recipients": ["test@example.com"],
        "subject": "Here is your email",
        "protocol": valid_protocol_definition,
    }


def test_email_basic(valid_source_definition, valid_destination_definition):
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [valid_destination_definition],
    }

    assert validate_transfer_json(json_data)
