# pylint: skip-file
# ruff: noqa
import os

import pytest

dummy_task_definition = {
    "task_id": 1234,
    "type": "transfer",
    "source": {
        "accessToken": "0",
        "protocol": {"name": "opentaskpy.remotehandlers.dummy"},
    },
    "cacheableVariables": [
        {
            "variableName": "source.accessToken",
            "cachingPlugin": "file",
            "cacheArgs": {
                "file": "/tmp/cacheable_variable.txt",
            },
        }
    ],
}


def test_dummy_transfer_cacheable_invalid_variable_name():
    from opentaskpy.remotehandlers.dummy import DummyTransfer

    dummy_task_definition["cacheableVariables"][0][
        "variableName"
    ] = "print('something_bad')"

    with pytest.raises(ValueError) as e:
        DummyTransfer(dummy_task_definition)
        # Check the message
    assert (
        "Variable name print('something_bad') is not a valid variable name."
        in e.value.args[0]
    )


def test_dummy_transfer(tmpdir):
    #  The key thing to test is that the access token
    #  is written to the cache file
    from opentaskpy.remotehandlers.dummy import DummyTransfer

    dummy_task_definition["cacheableVariables"][0]["cacheArgs"][
        "file"
    ] = f"{tmpdir}/cacheable_variable.txt"

    dummy_transfer = DummyTransfer(dummy_task_definition)

    # Check the cache file exists on the filesystem
    assert os.path.exists(f"{tmpdir}/cacheable_variable.txt")

    # Check the cache file has a random number in it now that's not the original

    with open(f"{tmpdir}/cacheable_variable.txt", "r") as f:
        contents = f.read()
        assert contents != "0"
        assert contents.isdigit()
