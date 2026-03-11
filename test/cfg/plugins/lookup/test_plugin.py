"""An example plugin that simply returns the word "hello"."""

import re

import opentaskpy.otflogging

logger = opentaskpy.otflogging.init_logging(__name__)

PLUGIN_NAME = "test_plugin"


def run(**kwargs) -> str:  # type: ignore[no-untyped-def]
    """Test."""
    dd = kwargs.get("dd")
    yyyy = kwargs.get("yyyy")
    globals_dict = kwargs.get("globals", {})
    global_dd = globals_dict.get("DD")
    global_yyyy = globals_dict.get("NESTED_VAR", {}).get("NESTED_VAR1")

    if not isinstance(dd, str):
        raise TypeError("dd should be a string")

    if not isinstance(yyyy, str):
        raise TypeError("yyyy should be a string")

    if not isinstance(global_dd, str):
        raise TypeError("globals DD should be a string")

    if not isinstance(global_yyyy, str):
        raise TypeError("globals NESTED_VAR.NESTED_VAR1 should be a string")

    # dd and YYY should be ints not strings, they should have been resolved. If not then we should error
    # Do a regex match to check that the variables are ints
    if (
        not re.match(r"^\d+$", dd)
        or not re.match(r"^\d+$", yyyy)
        or not re.match(r"^\d+$", global_dd)
        or not re.match(r"^\d+$", global_yyyy)
    ):
        raise Exception(  # pylint: disable=broad-exception-raised
            "dd, yyyy and globals values should be resolved integers"
        )

    # dd and yyyy should be ints, so we can do some maths on them so they're not just strings when returned
    # to prove that they're resolved
    dd_int = int(dd)
    yyyy_int = int(yyyy)

    result = f"hello {dd_int + 1 } {yyyy_int + 1}"

    return result
