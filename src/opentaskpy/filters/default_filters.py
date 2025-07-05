"""Default filters provided by opentaskpy."""

import base64
import datetime


def now_localtime() -> datetime.datetime:
    """Alias of now."""
    return now()


def now() -> datetime.datetime:
    """Return the current time in the local timezone."""
    return datetime.datetime.now().astimezone()


def utc_now() -> datetime.datetime:
    """Alias of now_utc."""
    return now_utc()


def now_utc() -> datetime.datetime:
    """Return the current time in UTC."""
    return datetime.datetime.now(tz=datetime.UTC)


def delta_days(value: datetime.datetime, days: int) -> datetime.datetime:
    """Returns a new datetime object + or - the number of delta days.

    Args:
        value (datetime.datetime): Starting datetime object
        days (int): Days to increment or decrement the value

    Returns:
        datetime.datetime: New datetime object with the delta applied
    """
    return value + datetime.timedelta(days)


def delta_hours(value: datetime.datetime, hours: int) -> datetime.datetime:
    """Returns a new datetime object + or - the number of delta hours.

    Args:
        value (datetime.datetime): Starting datetime object
        hours (int): Hours to increment or decrement the value

    Returns:
        datetime.datetime: New datetime object with the delta applied
    """
    return value + datetime.timedelta(hours=hours)


def base64_encode(value: str) -> str:
    """Returns the base64 encoded value of a string.

    Args:
        value (str): The string to encode

    Returns:
        str: The base64 encoded string
    """
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def base64_decode(value: str) -> str:
    """Returns the base64 decoded value of a string.

    Args:
        value (str): The string to decode

    Returns:
        str: The base64 decoded string
    """
    return base64.b64decode(value).decode("utf-8")
