"""
File lookup plugin.

Reads the first line of a file and returns it as a string.

"""
import os

import opentaskpy.logging

logger = opentaskpy.logging.init_logging(__name__)

plugin_name = "file"


def run(**kwargs):
    # Expect a kwarg named file
    if "path" not in kwargs:
        raise Exception(
            f"Missing kwarg: 'path' while trying to run lookup plugin '{plugin_name}'"
        )

    # Check if the file exists
    if not os.path.isfile(kwargs["path"]):
        raise FileNotFoundError(
            f"File {kwargs['path']} does not exist while trying to run lookup plugin '{plugin_name}'"
        )

    # Read the file
    result = None
    with open(kwargs["path"], "r") as f:
        result = f.readline().strip()
        logger.log(12, f"Read '{result}' from file {kwargs['path']}")
        pass

    return result
