from opentaskpy.config.schemas import validate_transfer_json

valid_protocol_definition = {
    "name": "ssh",
    "credentials": {
        "username": "test",
    },
}

valid_source_definition = {
    "hostname": "{{ HOST_A }}",
    "directory": "/tmp/testFiles/src",
    "fileRegex": ".*\\.txt",
    "protocol": valid_protocol_definition,
}

valid_destination_definition = {
    "hostname": "somehost",
    "directory": "/tmp/testFiles/dest",
    "protocol": valid_protocol_definition,
}


def test_ssh_basic():
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


def test_ssh_rename():
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [valid_destination_definition],
    }

    # Add rename config
    json_data["destination"][0]["rename"] = {"pattern": "test", "sub": "blah"}
    assert validate_transfer_json(json_data)


def test_ssh_permissions():
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


def test_ssh_transfer_type():
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
