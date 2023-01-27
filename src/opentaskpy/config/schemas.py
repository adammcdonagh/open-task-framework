"""Schemas for the configuration files."""
from jsonschema import validate
from jsonschema.exceptions import ValidationError

# TODO: Validate the rest of the schema
transfer_schema = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "source": {"type": "object"},
        "destination": {"type": "array"},
    },
    "required": ["type", "source"],
}

execution_schema = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "hosts": {"type": "array"},
        "directory": {"type": "string"},
        "command": {"type": "string"},
        "protocol": {"type": "object"},
    },
    "required": ["type", "hosts", "directory", "command", "protocol"],
}

batch_schema = {
    "type": "object",
    "properties": {"type": {"type": "string"}, "tasks": {"type": "array"}},
    "required": ["type", "tasks"],
}


def validate_transfer_json(json_data):
    try:
        validate(instance=json_data, schema=transfer_schema)
    except ValidationError as err:
        print(err.message)
        return False
    return True


def validate_execution_json(json_data):
    try:
        validate(instance=json_data, schema=execution_schema)
    except ValidationError as err:
        print(err.message)
        return False
    return True


def validate_batch_json(json_data):
    try:
        validate(instance=json_data, schema=batch_schema)
    except ValidationError as err:
        print(err.message)
        return False
    return True
