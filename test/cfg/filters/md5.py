"""Custom filter to return the MD5 hash of a string.

Example usage:

{{ "some string" | md5 }}
"""

import hashlib


def md5(value: str) -> str:
    """Returns the MD5 hash of a string.

    Args:
        value (str): The string to hash

    Returns:
        str: The MD5 hash of the string

    """
    return hashlib.md5(value.encode("utf-8")).hexdigest()
