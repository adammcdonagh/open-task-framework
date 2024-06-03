"""File caching plugin.

This is a basic caching plugin that when given a value, and path to a file, will update it with the new value
"""

import opentaskpy.otflogging
from opentaskpy.exceptions import CachingPluginError

logger = opentaskpy.otflogging.init_logging(__name__)

CACHE_NAME = "file"


def run(**kwargs):  # type: ignore[no-untyped-def]
    """Update a file with a new value.

    Args:
        **kwargs: Expect kwargs named file, and value. This should be the file to write
        to, and the value to put into the file

    Raises:
        CachingPluginError: Returned if the kwarg 'file' or 'value' is not provided
        FileNotFoundException: Returned if unable to write to the destination
    """
    # Expect a kwarg named file
    expected_kwargs = ["file", "value"]
    for kwarg in expected_kwargs:
        if kwarg not in kwargs:
            raise CachingPluginError(
                f"Missing kwarg: '{kwarg}' while trying to run caching plugin"
                f" '{CACHE_NAME}'"
            )

    # Write the value to the file
    try:
        with open(kwargs["file"], "w", encoding="utf-8") as file_:
            file_.write(kwargs["value"])
            logger.log(12, f"Wrote '{kwargs['value']}' to file {kwargs['file']}")
    except FileNotFoundError as e:
        logger.error(f"Unable to write to file {kwargs['file']}. Error: {e}")
        raise e
