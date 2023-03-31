"""
An example plugin that simply returns a random number between the 2 provided values

"""
import random

import opentaskpy.logging

logger = opentaskpy.logging.init_logging(__name__)

plugin_name = "random"


def run(**kwargs):
    # Expect a kwarg named min, and max
    expected_kwargs = ["min", "max"]
    for kwarg in expected_kwargs:
        if kwarg not in kwargs:
            raise Exception(
                f"Missing kwarg: '{kwarg}' while trying to run lookup plugin '{plugin_name}'"
            )

    # Return a random number between the 2 provided values
    return random.randint(kwargs["min"], kwargs["max"])
