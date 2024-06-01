"""Utility functions for caching variables."""

from importlib import import_module

DEFAULT_CACHE_PLUGINS = ["file"]


def update_cache(cacheable_variable: dict, updated_value: str) -> None:
    """Update the cache with the new value.

    Args:
        cacheable_variable (dict): The cacheable variable to update.
        updated_value (str): The new value to update the cache with.

    Returns:
        None
    """
    # Now find and call the appropriate caching plugin
    handler_package = None
    if cacheable_variable["cachingPlugin"] in DEFAULT_CACHE_PLUGINS:
        handler_package = (
            f"opentaskpy.config.variablecaching.{cacheable_variable['cachingPlugin']}"
        )

    else:
        handler_package = (
            f"opentaskpy.variablecaching.{cacheable_variable['cachingPlugin']}"
        )

    # Call the run method of the handler_package, getting the actual function first
    handler_function = getattr(import_module(handler_package), "run")

    # Call the function
    kwargs = cacheable_variable["cacheArgs"]
    kwargs["value"] = updated_value
    handler_function(**kwargs)
