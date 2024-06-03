# pylint: skip-file
import pytest

from opentaskpy.config.schemas import validate_transfer_json


@pytest.fixture(scope="function")
def valid_source_definition():
    return {
        "accessToken": "1234",
        "protocol": {"name": "dummy"},
    }


def test_dummy_basic(valid_source_definition):
    json_data = {"type": "transfer", "source": valid_source_definition}

    assert validate_transfer_json(json_data)


# Test dummy again but with cachableVariables defined too
def test_dummy_with_cachable_variables(valid_source_definition):
    json_data = {
        "type": "transfer",
        "source": valid_source_definition,
    }

    json_data["source"]["cacheableVariables"] = [
        {
            "variableName": "accessToken",
            "cachingPlugin": "file",
            "cacheArgs": {
                "file": "/tmp/cacheable_variable.txt",
            },
        }
    ]

    assert validate_transfer_json(json_data)

    # Remove the cacheArgs and validate the validation fails
    del json_data["source"]["cacheableVariables"][0]["cacheArgs"]
    assert not validate_transfer_json(json_data)
