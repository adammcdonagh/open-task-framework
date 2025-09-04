# pylint: skip-file
# ruff: noqa
import os

import pytest

from opentaskpy import exceptions
from opentaskpy.taskhandlers import execution
from tests.fixtures.ssh_clients import *  # noqa: F403

os.environ["OTF_NO_LOG"] = "1"
os.environ["OTF_LOG_LEVEL"] = "DEBUG"
os.environ["PYTHONPATH"] = "test/cfg/addons"

# Create a task definition
custom_task_definition = {
    "type": "execution",
    "protocol": {"name": "custom.test_addon.RandomNumberGenerator"},
}


def test_basic_execution():
    execution_obj = execution.Execution(None, "custom-task", custom_task_definition)
    execution_obj._set_remote_handlers()

    # Validate some things were set as expected
    assert (
        execution_obj.remote_handlers[0].__class__.__name__ == "RandomNumberGenerator"
    )

    # Run the execution and expect a true status
    assert execution_obj.run()
