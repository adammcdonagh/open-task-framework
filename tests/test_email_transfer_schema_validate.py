from opentaskpy.config.schemas import validate_transfer_json

valid_protocol_definition = {"name": "email"}

valid_source_definition = {
    "hostname": "{{ HOST_A }}",
    "directory": "/tmp/testFiles/src",
    "fileRegex": ".*\\.txt",
    "protocol": {"name": "ssh", "credentials": {"username": "test"}},
}

valid_destination_definition = {
    "recipients": ["test@example.com"],
    "subject": "Here is your email",
    "protocol": valid_protocol_definition,
}


def test_email_basic():
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
        "destination": [valid_destination_definition],
    }

    assert validate_transfer_json(json_data)
