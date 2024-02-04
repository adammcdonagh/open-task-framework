"""File lookup plugin.

Reads the first line of a file and returns it as a string.

"""

import os

import opentaskpy.otflogging
from opentaskpy.exceptions import LookupPluginError

logger = opentaskpy.otflogging.init_logging(__name__)

PLUGIN_NAME = "file"


def run(**kwargs) -> str:  # type: ignore[no-untyped-def]
    """Pull a variable from a named file.

    Args:
        **kwargs: Expect a kwarg named path. This should be the path to the file to read
        The file contents should be a single line, and will be returned as a string.

    Raises:
        LookupPluginError: Returned if the kwarg 'path' is not provided
        FileNotFoundError: Returned if the file does not exist

    Returns:
        _type_: The value read from the file
    """
    # Expect a kwarg named file
    if "path" not in kwargs:
        raise LookupPluginError(
            f"Missing kwarg: 'path' while trying to run lookup plugin '{PLUGIN_NAME}'"
        )

    # Check if the file exists
    if not os.path.isfile(kwargs["path"]):
        raise FileNotFoundError(
            f"File {kwargs['path']} does not exist while trying to run lookup plugin"
            f" '{PLUGIN_NAME}'"
        )

    # Read the file
    result = None
    with open(kwargs["path"], encoding="utf-8") as file_:
        result = file_.readline().strip()
        logger.log(12, f"Read '{result}' from file {kwargs['path']}")

    return result
