"""Schemas for the configuration files."""
from jsonschema import validate
from jsonschema.exceptions import ValidationError

# TODO: Validate the rest of the schema
transfer_schema = {
    "type": "object",
    "properties": {"type": {"type": "string"}, "source": {"type": "object"}, "destination": {"type": "array"}},
    "required": ["type", "source"],
}


def validate_json(json_data):
    try:
        validate(instance=json_data, schema=transfer_schema)
    except ValidationError as err:
        print(err.message)
        return False
    return True
