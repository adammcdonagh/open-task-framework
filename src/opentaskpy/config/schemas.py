"""Schemas for the configuration files."""
import os
from pathlib import Path

from jsonschema import validate
from jsonschema.exceptions import ValidationError
from jsonschema.validators import RefResolver

transfer_schema = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "source": {
            "type": "object",
            "properties": {
                "protocol": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            },
        },
        "destination": {"type": "array"},
    },
    "required": ["type", "source"],
}

# Determine the type of transfer, and apply the correct sub schema based on the protocol used

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

        # If this works, then determine the protocol and apply the correct sub schema
        # Source protocol
        source_protocol = json_data["source"]["protocol"]["name"]

        # Dynamically apply the correct sub schema based on the protocol
        # We need to locate the schema files from the base location of this package
        schema_dir = f"{os.path.dirname(os.path.realpath(__file__))}/schemas"
        path = Path(schema_dir)

        # Load the schema file for XXX_source
        resolver = RefResolver(
            base_uri=f"{path.as_uri()}/",
            referrer=True,
        )
        # Schema reference name should be schemas/transfer/xxx_source
        source_schema_name = Path(
            f"{schema_dir}/transfer/{source_protocol}_source.json"
        ).as_uri()
        destination_schema_name = Path(
            f"{schema_dir}/transfer/{source_protocol}_destination.json"
        ).as_uri()
        # Update the transfer_schema with the correct sub schema reference
        new_schema = transfer_schema.copy()
        new_schema["properties"]["source"] = {"$ref": source_schema_name}

        # Set the destination schema too
        new_schema["properties"]["destination"] = {
            "type": "array",
            "items": {"$ref": destination_schema_name},
        }

        # Validate the new schema
        validate(instance=json_data, schema=new_schema, resolver=resolver)

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
