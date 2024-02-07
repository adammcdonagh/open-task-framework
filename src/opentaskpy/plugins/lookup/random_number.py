"""An example plugin that simply returns a random number between the 2 provided values."""

import random

import opentaskpy.otflogging
from opentaskpy.exceptions import LookupPluginError

logger = opentaskpy.otflogging.init_logging(__name__)

PLUGIN_NAME = "random_number"


def run(**kwargs) -> str:  # type: ignore[no-untyped-def]
    """Returns a random number between the 2 provided values.

    Args:
        **kwargs: Expect a kwarg named min and max

    Raises:
        LookupPluginError: Returned if the kwarg 'min' or 'max' is not provided
        FileNotFoundError: Returned if the file does not exist

    Returns:
        _type_: The value read from the file
    """
    # Expect a kwarg named min, and max
    expected_kwargs = ["min", "max"]
    for kwarg in expected_kwargs:
        if kwarg not in kwargs:
            raise LookupPluginError(
                f"Missing kwarg: '{kwarg}' while trying to run lookup plugin"
                f" '{PLUGIN_NAME}'"
            )

    # Return a random number between the 2 provided values
    return str(random.randint(kwargs["min"], kwargs["max"]))
