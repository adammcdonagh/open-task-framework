"""Schemas for the configuration files."""
import copy
import importlib
import sys
from importlib.resources import files
from pathlib import Path

from jsonschema import validate
from jsonschema.exceptions import ValidationError
from jsonschema.validators import RefResolver

import opentaskpy.logging

TRANSFER_SCHEMA = {
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
                    "required": ["name"],
                },
            },
            "required": ["protocol"],
        },
        "destination": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "protocol": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                },
                "required": ["protocol"],
            },
        },
    },
    "required": ["type", "source"],
}

# Determine the type of transfer, and apply the correct sub schema based on the protocol used

EXECUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "protocol": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    "required": ["type", "protocol"],
}

# Declare a constant that cannot be changed


BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "tasks": {"type": "array", "items": {"$ref": "batch.json"}},
    },
    "required": ["type", "tasks"],
}

logger = opentaskpy.logging.init_logging(__name__)


def validate_transfer_json(json_data):
    new_schema = None
    try:
        validate(instance=json_data, schema=TRANSFER_SCHEMA)

        # If this works, then determine the protocol and apply the correct sub schema
        # Source protocol
        source_protocol = json_data["source"]["protocol"]["name"]

        # Dynamically apply the correct sub schema based on the protocol
        # We need to locate the schema files from the base location of this package
        # Get the directory of this package

        schema_dir = files("opentaskpy.config").joinpath("schemas")
        # This gets us the right path for default protocol schemas. But we need to be able to load custom schemas too
        # based on the protocol name, we need to find the location of the package using the files() function

        # Load the schema file for XXX_source
        resolver = RefResolver(
            base_uri=f"{schema_dir.as_uri()}/",
            referrer=True,
        )

        # source_protocol is the class name within the plugin, we need to determine if it's a default protocol or a custom one
        # If it's a default protocol, then we can use the files() function to get the path to the schema file
        # If it's a custom protocol, then we need to look in the plugins directory for the schema file
        # Default protocols are the only ones that aren't prefixed with a package name, and we don't need to do anything more
        if "." in source_protocol:
            # Get the full package name from the class name (strip the class off the end)
            package_name = ".".join(source_protocol.split(".")[:-2])
            if package_name not in sys.modules:
                # Check the module is loadable
                importlib.import_module(package_name)
            # Get the path to the module
            module_path = files(package_name).joinpath("schemas")

            # Shorten the source_protocol to just the name of the class
            source_protocol = source_protocol.split(".")[-2]

            # Append new path to the resolver
            resolver.store[module_path.as_uri()] = module_path
        else:
            # Default protocol
            module_path = schema_dir

        # Schema reference name should be schemas/transfer/xxx_source
        source_schema_name = Path(
            f"{module_path}/transfer/{source_protocol}_source.json"
        ).as_uri()

        # Destination protocol can be different for each destination in the array. Loop through each destination and get the protocol name
        schema_refs = []
        if "destination" in json_data:
            for destination in json_data["destination"]:
                # Get the protocol name
                destination_protocol = destination["protocol"]["name"]
                # As above, we need to determine the path of the protocol schema file if it's not a default protocol
                module_path = None
                if "." in destination_protocol:
                    # Get the full package name from the class name (strip the class off the end)
                    package_name = ".".join(destination_protocol.split(".")[:-2])

                    if package_name not in sys.modules:
                        # Check the module is loadable
                        importlib.import_module(package_name)
                    # Get the path to the module
                    module_path = files(package_name).joinpath("schemas")

                    # Shorten the destination_protocol to just the name of the class
                    destination_protocol = destination_protocol.split(".")[-2]

                    # Append new path to the resolver
                    resolver.store[module_path.as_uri()] = module_path
                else:
                    # Default protocol
                    module_path = schema_dir

                schema_def = {
                    "$ref": Path(
                        f"{module_path}/transfer/{destination_protocol}_destination.json"
                    ).as_uri()
                }

                # If schema_refs does not already contain the schema_def, then append it
                if schema_def not in schema_refs:
                    schema_refs.append(schema_def)

        # Update the TRANSFER_SCHEMA with the correct sub schema reference
        new_schema = copy.deepcopy(TRANSFER_SCHEMA)
        new_schema["properties"]["source"] = {"$ref": source_schema_name}

        # Now update the new_schema so that ["properties"]["destination"]["items"]["$ref"] = the list of destination protocols schema references
        # Schema reference name should be schemas/transfer/xxx_destination

        if "destination" in json_data and len(json_data["destination"]) > 0:
            new_schema["properties"]["destination"] = {
                "type": "array",
                "minItems": 0,
                "items": {
                    "oneOf": schema_refs,
                },
            }

        # Validate the new schema
        validate(instance=json_data, schema=new_schema, resolver=resolver)

    except ValidationError as err:
        print(err.message)
        return False
    return True


def validate_execution_json(json_data):
    try:
        validate(instance=json_data, schema=EXECUTION_SCHEMA)

        # If this works, then determine the protocol and apply the correct sub schema
        protocol = json_data["protocol"]["name"]

        # Dynamically apply the correct sub schema based on the protocol
        # We need to locate the schema files from the base location of this package
        # Get the directory of this package
        schema_dir = files("opentaskpy.config").joinpath("schemas")

        # Load the schema file for xxx
        resolver = RefResolver(
            base_uri=f"{schema_dir.as_uri()}/",
            referrer=True,
        )

        if "." in protocol:
            # Get the full package name from the class name (strip the class off the end)
            package_name = ".".join(protocol.split(".")[:-2])

            if package_name not in sys.modules:
                # Check the module is loadable
                importlib.import_module(package_name)
            # Get the path to the module
            module_path = files(package_name).joinpath("schemas")

            # Shorten the protocol to just the name of the class
            protocol = protocol.split(".")[-2]

            # Append new path to the resolver
            resolver.store[module_path.as_uri()] = module_path
        else:
            # Default protocol
            module_path = schema_dir

        # Schema reference name should be schemas/execution/xxx
        schema_name = Path(
            f"{module_path}/execution/{protocol}/{protocol}.json"
        ).as_uri()

        # Update the schema with the correct sub schema reference
        new_schema = {}
        new_schema["$ref"] = schema_name

        # Validate the new schema
        validate(instance=json_data, schema=new_schema, resolver=resolver)

    except ValidationError as err:
        print(err.message)
        return False
    return True


def validate_batch_json(json_data):
    try:
        schema_dir = files("opentaskpy.config").joinpath("schemas")

        # Load the schema file for xxx
        resolver = RefResolver(
            base_uri=f"{schema_dir.as_uri()}/",
            referrer=True,
        )

        validate(instance=json_data, schema=BATCH_SCHEMA, resolver=resolver)
    except ValidationError as err:
        print(err.message)
        return False
    return True
