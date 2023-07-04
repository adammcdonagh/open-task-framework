"""An example plugin that simply returns the word "hello"."""

import opentaskpy.otflogging

logger = opentaskpy.otflogging.init_logging(__name__)

PLUGIN_NAME = "test_plugin"


def run(**kwargs) -> str:  # type: ignore[no-untyped-def]
    """Returns hello.

    Returns:
        str: The word hello
    """
    # Return a random number
    return "hello"
