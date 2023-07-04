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


def test_ssh_protocol():
    json_data = {
        "type": "transfer",
        "source": {
            "hostname": "{{ HOST_A }}",
            "directory": "/tmp/testFiles/src",
            "fileRegex": ".*\\.txt",
            "protocol": {"name": "ssh"},
        },
    }

    assert not validate_transfer_json(json_data)

    # Set protocol creds
    json_data["source"]["protocol"]["credentials"] = {}
    assert not validate_transfer_json(json_data)

    json_data["source"]["protocol"]["credentials"] = {"username": "test"}
    assert validate_transfer_json(json_data)

    # Password is not supported
    json_data["source"]["protocol"]["credentials"] = {
        "username": "test",
        "password": "test",
    }
    assert not validate_transfer_json(json_data)


def test_ssh_basic(valid_protocol_definition):
    json_data = {
        "type": "transfer",
        "source": {
            "hostname": "{{ HOST_A }}",
            "directory": "/tmp/testFiles/src",
            "fileRegex": ".*\\.txt",
            "protocol": valid_protocol_definition,
        },
    }
    assert validate_transfer_json(json_data)

    # test error
    json_data["source"]["error"] = "blah"
    assert not validate_transfer_json(json_data)

    json_data["source"]["error"] = True
    assert validate_transfer_json(json_data)

    json_data["source"]["error"] = False
    assert validate_transfer_json(json_data)


def test_ssh_conditions(valid_protocol_definition):
    json_data = {
        "type": "transfer",
        "source": {
            "hostname": "{{ HOST_A }}",
            "directory": "/tmp/testFiles/src",
            "fileRegex": ".*\\.txt",
            "conditionals": {},
            "protocol": valid_protocol_definition,
        },
    }
    assert validate_transfer_json(json_data)

    # Add conditions
    for condition in ["size", "age"]:
        json_data["source"]["conditionals"][condition] = {"gt": 10}
        assert validate_transfer_json(json_data)

        json_data["source"]["conditionals"][condition] = {"lt": 10}
        assert validate_transfer_json(json_data)

        json_data["source"]["conditionals"][condition] = {"lt": 10, "gt": 5}
        assert validate_transfer_json(json_data)

    # Add an invalid condition
    json_data["source"]["conditionals"]["invalid"] = {"invalid": 10}
    assert not validate_transfer_json(json_data)


def test_ssh_filewatch(valid_protocol_definition):
    json_data = {
        "type": "transfer",
        "source": {
            "hostname": "{{ HOST_A }}",
            "directory": "/tmp/testFiles/src",
            "fileRegex": ".*\\.txt",
            "fileWatch": {},
            "protocol": valid_protocol_definition,
        },
    }
    assert validate_transfer_json(json_data)

    # Add fileWatch config
    json_data["source"]["fileWatch"] = {"timeout": 10}
    assert validate_transfer_json(json_data)

    # Add a file and directory
    json_data["source"]["fileWatch"]["fileRegex"] = ".*"
    json_data["source"]["fileWatch"]["directory"] = "/tmp"
    assert validate_transfer_json(json_data)

    # Add watchOnly, and remove the fileRegex and directory
    json_data["source"]["fileWatch"]["watchOnly"] = True
    del json_data["source"]["fileRegex"]
    del json_data["source"]["directory"]
    assert not validate_transfer_json(json_data)

    # Add an invalid property
    json_data["source"]["fileWatch"]["invalid"] = "invalid"
    assert not validate_transfer_json(json_data)


def test_ssh_logwatch(valid_protocol_definition):
    json_data = {
        "type": "transfer",
        "source": {
            "hostname": "{{ HOST_A }}",
            "directory": "/tmp/testFiles/src",
            "fileRegex": ".*\\.txt",
            "logWatch": {},
            "protocol": valid_protocol_definition,
        },
    }
    assert not validate_transfer_json(json_data)

    json_data = {
        "type": "transfer",
        "source": {
            "hostname": "{{ HOST_A }}",
            "directory": "/tmp/testFiles/src",
            "fileRegex": ".*\\.txt",
            "logWatch": {
                "log": "test.log",
                "directory": "/tmp",
                "contentRegex": ".*",
            },
            "protocol": valid_protocol_definition,
        },
    }
    assert validate_transfer_json(json_data)

    # Add tail
    json_data["source"]["logWatch"]["tail"] = True
    assert validate_transfer_json(json_data)

    # Add an invalid property
    json_data["source"]["logWatch"]["invalid"] = "invalid"
    assert not validate_transfer_json(json_data)


def test_ssh_pca(valid_protocol_definition):
    json_data = {
        "type": "transfer",
        "source": {
            "hostname": "{{ HOST_A }}",
            "directory": "/tmp/testFiles/src",
            "fileRegex": ".*\\.txt",
            "postCopyAction": {},
            "protocol": valid_protocol_definition,
        },
    }
    assert not validate_transfer_json(json_data)

    # PCA delete
    json_data["source"]["postCopyAction"]["action"] = "delete"
    assert validate_transfer_json(json_data)

    # PCA move
    json_data["source"]["postCopyAction"]["action"] = "move"
    assert not validate_transfer_json(json_data)

    json_data["source"]["postCopyAction"]["destination"] = "/tmp/testFiles/dest"
    assert validate_transfer_json(json_data)

    # PCA copy
    json_data["source"]["postCopyAction"]["action"] = "rename"
    assert not validate_transfer_json(json_data)

    json_data["source"]["postCopyAction"]["sub"] = "test"
    json_data["source"]["postCopyAction"]["pattern"] = "test"
    assert validate_transfer_json(json_data)
