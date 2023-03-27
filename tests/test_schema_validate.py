from opentaskpy.config.schemas import validate_transfer_json

valid_protocol_definition = {
    "name": "ssh",
    "credentials": {
        "username": "test",
    },
}

valid_protocol_definition_2 = {"name": "email"}

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

valid_destination_definition_2 = {
    "recipients": ["test@example.com"],
    "subject": "Here is your email",
    "protocol": valid_protocol_definition_2,
}


def test_dest_with_different_protocols():
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
