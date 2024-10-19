# pylint: skip-file
# ruff: noqa

import pytest

from opentaskpy.remotehandlers.ssh import SSHTransfer


def test_cacheable_variable_dotted_notation():

    spec = {"task_id": "1234", "x": {"y": "value"}, "protocol": {"name": "ssh"}}
    rh = SSHTransfer(spec)

    assert rh.obtain_variable_from_spec("x.y", spec) == "value"


def test_cacheable_variable_dotted_notation_array():

    spec = {
        "task_id": "1234",
        "hostname": "172.16.0.11",
        "directory": "/tmp/testFiles/src",
        "fileRegex": ".*taskhandler.proxy\\.txt",
        "invalidParam": [1, 2, 3, 4, 5],
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    }
    rh = SSHTransfer(spec)

    assert rh.obtain_variable_from_spec("invalidParam[2]", spec) == "3"
