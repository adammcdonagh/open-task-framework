"""
Basic HTTP JSON lookup plugin

Does an HTTP GET request to the given URL and returns the value of an attribuet JSON response.
This does not support any type of authentication, and just expects a simple
JSON response from which to extract a value.

"""
import logging
import requests

logger = logging.getLogger(__name__)

plugin_name = "http_json"


def run(**kwargs):

    # Expect a kwarg named url, and value
    expected_kwargs = ["url", "value"]
    for kwarg in expected_kwargs:
        if kwarg not in kwargs:
            raise Exception(f"Missing kwarg: '{kwarg}' while trying to run lookup plugin '{plugin_name}'")

    result = None
    try:
        response = requests.get(kwargs["url"])
        response.raise_for_status()
        result = response.json()[kwargs["value"]]
        logger.log(12, f"Read '{result}' from URL {kwargs['url']}")
    except Exception as e:
        logger.error(f"Failed to read from URL {kwargs['url']}: {e}")

    return result
