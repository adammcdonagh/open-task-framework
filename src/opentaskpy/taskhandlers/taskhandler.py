from abc import ABC, abstractmethod
from importlib import import_module
from sys import modules

from opentaskpy import exceptions


class TaskHandler(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def return_result(self, status, mesaage, exception):
        ...

    @abstractmethod
    def _set_remote_handlers(self):
        ...

    @abstractmethod
    def run(self):
        ...

    def _get_handler_for_protocol(self, protocol_name, spec):
        # Remove the class name from the end of addon_protocol
        addon_package = ".".join(protocol_name.split(".")[:-1])

        if addon_package == "":
            raise exceptions.UnknownProtocolError(f"Unknown protocol {protocol_name}")

        # Import the plugin if its not already loaded
        if addon_package not in modules:
            # Check the module is loadable
            try:
                self.logger.log(12, f"Loading addon protocol: {addon_package}")
                import_module(addon_package)
            except ModuleNotFoundError:
                raise exceptions.UnknownProtocolError(
                    f"Unknown protocol {protocol_name}"
                )

        # Get the imported class relating to addon_protocol
        addon_class = getattr(modules[addon_package], protocol_name.split(".")[-1])

        # Create the remote handler from this class
        return addon_class(spec)
