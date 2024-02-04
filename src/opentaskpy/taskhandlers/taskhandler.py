"""Abstract task handler class."""

from abc import ABC, abstractmethod
from importlib import import_module
from logging import Logger
from sys import modules

import opentaskpy.otflogging
from opentaskpy.exceptions import UnknownProtocolError
from opentaskpy.remotehandlers.remotehandler import RemoteHandler


class TaskHandler(ABC):
    """Abstract task handler class."""

    logger: Logger
    overall_result: bool
    handled_exception: bool = False

    def __init__(self, global_config: dict):
        """Initialize the class."""
        self.global_config = global_config

    def return_result(
        self, status: int, message: str, exception: type[Exception] | None = None
    ) -> bool:
        """Return the result of the task run.

        Args:
            status (int): The return code of the task run. 0 is success, anything else is failure.
            message (str): Message to return.
            exception (Exception, optional): Exception to return. Defaults to None.

        Returns:
            bool: True if the task was successful, False otherwise.
        """
        if message:
            if status == 0:
                self.logger.info(message)
            else:
                self.logger.error(message)

        if status == 0:
            self.overall_result = True

        opentaskpy.otflogging.close_log_file(self.logger, self.overall_result)

        # Throw an exception if we have one
        if exception and not self.handled_exception:
            self.handled_exception = True
            if callable(exception):
                raise exception(message)

            raise Exception(message)  # pylint: disable=broad-exception-raised

        return status == 0

    @abstractmethod
    def _set_remote_handlers(self) -> None: ...

    @abstractmethod
    def run(self) -> bool:
        """Run the task handler.

        Returns:
            bool: True if the task was successful, False otherwise.
        """

    def _set_handler_vars(
        self, source_protocol: str, remote_handler: RemoteHandler
    ) -> None:
        # If remote handler has a set handler vars method, call it and pass in any variables it might want
        if hasattr(remote_handler, "set_handler_vars"):
            self.logger.log(12, f"Setting handler vars for {source_protocol}")

            # Read the protocol specific variables from the global config
            if (
                self.global_config
                and "global_protocol_vars" in self.global_config
                and next(
                    (
                        item
                        for item in self.global_config["global_protocol_vars"]
                        if item["name"] == source_protocol
                    ),
                )
            ):
                protocol_vars = next(
                    (
                        item
                        for item in self.global_config["global_protocol_vars"]
                        if item["name"] == source_protocol
                    ),
                ).copy()
                # Remove "name" from the dict
                del protocol_vars["name"]

                remote_handler.set_handler_vars(protocol_vars)

    def _get_handler_for_protocol(
        self, protocol_name: str, spec: dict
    ) -> RemoteHandler:
        """Get the handler for a protocol.

        Looks for the protocol package to import. An addon must be accessible in the
        PYTHONPATH to be found and loaded.

        Args:
            protocol_name (str): The name of the protocol.
            spec (dict): The spec for the protocol.

        Raises:
            UnknownProtocolError: Raised if the protocol is unknown.

        Returns:
            RemoteHandler: The remote handler for the protocol.
        """
        # Remove the class name from the end of addon_protocol
        addon_package = ".".join(protocol_name.split(".")[:-1])

        if addon_package == "":
            raise UnknownProtocolError(f"Unknown protocol {protocol_name}")

        # Import the plugin if its not already loaded
        if addon_package not in modules:
            # Check the module is loadable
            try:
                self.logger.log(12, f"Loading addon protocol: {addon_package}")
                import_module(addon_package)
            except ModuleNotFoundError as exc:
                raise UnknownProtocolError(f"Unknown protocol {protocol_name}") from exc

        # Get the imported class relating to addon_protocol
        addon_class = getattr(modules[addon_package], protocol_name.split(".")[-1])

        # Create the remote handler from this class
        return addon_class(spec)
