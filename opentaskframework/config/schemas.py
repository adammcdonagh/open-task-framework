import json
import jsonschema

from jsonschema import validate

# TODO: Validate the rest of the schema
transfer_schema = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "source": {"type": "object"},
        "destination": {"type": "object"}
    },
    "required": ["type", "source"]
}


def validate_json(json_data):
    try:
        validate(instance=json_data, schema=transfer_schema)
    except jsonschema.exceptions.ValidationError as err:
        print(err.message)
        return False
    return True
