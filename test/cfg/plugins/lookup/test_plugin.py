"""An example plugin that simply returns the word "hello"."""

import re

import opentaskpy.otflogging

logger = opentaskpy.otflogging.init_logging(__name__)

PLUGIN_NAME = "test_plugin"


def run(**kwargs) -> str:  # type: ignore[no-untyped-def]
    """Test."""
    dd = str(kwargs.get("dd"))
    yyyy = str(kwargs.get("yyyy"))
    globals_dict = kwargs.get("globals", {})
    global_dd = globals_dict.get("DD")
    global_yyyy = globals_dict.get("NESTED_VAR", {}).get("NESTED_VAR1")

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
