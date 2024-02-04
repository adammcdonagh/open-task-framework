"""Basic HTTP JSON lookup plugin.

Does an HTTP GET request to the given URL and returns the value of an attribute JSON response.
This does not support any type of authentication, and just expects a simple
JSON response from which to extract a value using a provided JSONPath.

"""

import requests
from jsonpath_ng import parse

import opentaskpy.otflogging
from opentaskpy.exceptions import LookupPluginError

logger = opentaskpy.otflogging.init_logging(__name__)

PLUGIN_NAME = "http_json"


def run(**kwargs) -> str | None:  # type: ignore[no-untyped-def]
    """Pull a variable from a URL that returns JSON.

    The endpoint must respond within 5 seconds, or the request will fail.

    Args:
        **kwargs: Expect a kwarg named url and jsonpath. This should be the URL to the
        JSON endpoint, and the JSONPath to the attribute to return.

    Raises:
        LookupPluginError: Returned if the kwarg 'url' or 'jsonpath' is not provided
        FileNotFoundError: Returned if the file does not exist

    Returns:
        _type_: The value read from the file
    """
    # Expect a kwarg named url, and value
    expected_kwargs = ["url", "jsonpath"]
    for kwarg in expected_kwargs:
        if kwarg not in kwargs:
            raise LookupPluginError(
                f"Missing kwarg: '{kwarg}' while trying to run lookup plugin"
                f" '{PLUGIN_NAME}'"
            )

    result: str | None = None
    try:
        response = requests.get(kwargs["url"], timeout=5)
        response.raise_for_status()
        json = response.json()
        jsonpath_expr = parse(kwargs["jsonpath"])
        result = [match.value for match in jsonpath_expr.find(json)][0]

        logger.log(12, f"Read '{result}' from URL {kwargs['url']}")
    except Exception as ex_:  # pylint: disable=broad-except
        logger.error(f"Failed to read from URL {kwargs['url']}: {ex_}")

    return result
