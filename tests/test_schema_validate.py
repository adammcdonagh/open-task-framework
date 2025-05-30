# pylint: skip-file
import pytest

from opentaskpy.config.schemas import validate_transfer_json


@pytest.fixture(scope="function")
def valid_protocol_definition():
    return {
        "name": "ssh",
        "credentials": {
            "username": "test",
        },
    }


@pytest.fixture(scope="function")
def valid_protocol_definition_2():
    return {
        "name": "email",
        "smtp_server": "smtp.gmail.com",
        "sender": "Test Sender <test@example.com>",
    }


@pytest.fixture(scope="function")
def valid_source_definition(valid_protocol_definition):
    return {
        "hostname": "{{ HOST_A }}",
        "directory": "/tmp/testFiles/src",
        "fileRegex": ".*\\.txt",
        "protocol": valid_protocol_definition,
    }


@pytest.fixture(scope="function")
def valid_destination_definition(valid_protocol_definition):
    return {
        "hostname": "somehost",
        "directory": "/tmp/testFiles/dest",
        "protocol": valid_protocol_definition,
    }


@pytest.fixture(scope="function")
def valid_destination_definition_2(valid_protocol_definition_2):
    return {
        "recipients": ["test@example.com"],
        "subject": "Here is your email",
        "protocol": valid_protocol_definition_2,
    }


def test_source_protocols(valid_source_definition):
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [],
    }

    # Remove protocol
    del json_data["source"]["protocol"]
    assert not validate_transfer_json(json_data)


def test_local_source_protocol(valid_source_definition):
    valid_source_definition["protocol"] = {"name": "local"}
    del valid_source_definition["hostname"]
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [],
    }
    assert validate_transfer_json(json_data)


def test_dest_with_different_protocols(
    valid_source_definition,
    valid_destination_definition,
    valid_destination_definition_2,
):
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [],
    }

    # Add a valid destination
    json_data["destination"].append(valid_destination_definition)
    # Add a second valid destination
    json_data["destination"].append(valid_destination_definition_2)

    assert validate_transfer_json(json_data)


def test_encryption_with_public_key(valid_source_definition):

    valid_source_definition["encryption"] = {"public_key": "blah", "encrypt": True}

    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [],
    }

    assert validate_transfer_json(json_data)

    # Set sign to true and dont add a private key, expect a failure
    valid_source_definition["encryption"]["sign"] = True
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [],
    }

    assert not validate_transfer_json(json_data)

    # Add a private key
    valid_source_definition["encryption"]["private_key"] = "blah"
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [],
    }

    assert validate_transfer_json(json_data)
