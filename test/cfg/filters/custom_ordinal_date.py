"""Custom filter to return the weekday ordinal.

Returns a string in the format YYNNN, where YY is the last two digits of the year,
and NNN is the ordinal count of the specified weekdays up to and including the given date.

Example usage:

{{ custom_weekday_ordinal([0, 2, 4]) }}
"""

from datetime import datetime, timedelta


def custom_weekday_ordinal(weekdays: list[int], dt: datetime | None = None) -> str:
    """Custom weekday ordinal filter.

    Returns a string in the format YYNNN, where YY is the last two digits of the year,
    and NNN is the ordinal count of the specified weekdays up to and including the given date.

    Args:
        weekdays (list[int]): List of integers (0=Monday ... 6=Sunday)
        dt (datetime.datetime, optional): Datetime object. Defaults to now.

    Returns:
        str: The formatted date string

    Example usage:
        {{ some_date | custom_weekday_ordinal([1, 5]) }}
        {{ custom_weekday_ordinal([0, 2, 4]) }}
    """
    if dt is None:
        dt = datetime.now()
    if weekdays is None:
        raise ValueError("weekdays must be specified")

    year = dt.year % 100
    start = datetime(dt.year, 1, 1)
    count = 0
    current = start
    while current <= dt:
        if current.weekday() in weekdays:
            count += 1
        current += timedelta(days=1)
    return f"{year:02d}{count:03d}"
