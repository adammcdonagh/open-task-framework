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


def test_ssh_basic(valid_source_definition, valid_destination_definition):
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [],
    }
    # We dont actually need to give any destinations
    assert validate_transfer_json(json_data)

    # Add a valid destination
    json_data["destination"].append(valid_destination_definition)

    assert validate_transfer_json(json_data)

    # Remove protocol
    del json_data["destination"][0]["protocol"]
    assert not validate_transfer_json(json_data)


def test_ssh_rename(valid_source_definition, valid_destination_definition):
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [valid_destination_definition],
    }

    # Add rename config
    json_data["destination"][0]["rename"] = {"pattern": "test", "sub": "blah"}
    assert validate_transfer_json(json_data)


def test_ssh_permissions(valid_source_definition, valid_destination_definition):
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [valid_destination_definition],
    }

    # Add permission
    json_data["destination"][0]["permissions"] = {
        "owner": "test",
        "group": "blah",
        "mode": "0777",
    }
    assert validate_transfer_json(json_data)

    json_data["destination"][0]["permissions"] = {
        "mode": "0777",
    }

    assert validate_transfer_json(json_data)

    json_data["destination"][0]["permissions"] = {
        "invalid": "test",
    }
    assert not validate_transfer_json(json_data)


def test_ssh_flags(valid_source_definition, valid_protocol_definition):
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [
            {
                "hostname": "{{ HOST_A }}",
                "directory": "/tmp/testFiles/src",
                "flags": {},
                "protocol": valid_protocol_definition,
            }
        ],
    }
    assert not validate_transfer_json(json_data)

    # Add full path for flags
    json_data["destination"][0]["flags"]["fullPath"] = "/tmp/testFiles/src/flag.file"
    assert validate_transfer_json(json_data)


def test_ssh_transfer_type(valid_source_definition, valid_destination_definition):
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [valid_destination_definition],
    }

    # Add transfer type
    for type in ["push", "pull", "proxy"]:
        json_data["destination"][0]["transferType"] = type
        assert validate_transfer_json(json_data)

    json_data["destination"][0]["transferType"] = "blah"
    assert not validate_transfer_json(json_data)
