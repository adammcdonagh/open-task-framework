"""Abstract classes for remote handlers."""
from abc import ABC, abstractmethod


class RemoteTransferHandler(ABC):
    """Abstract class for remote transfer handlers."""

    def __init__(self, spec: dict, remote_spec: dict | None = None):
        """Initialise the handler.

        Args:
            spec (dict): The spec for the transfer.
            remote_spec (dict, optional): The remote spec for the transfer. Defaults to None.
        """
        self.spec = spec
        self.remote_spec = remote_spec

    @abstractmethod
    def list_files(self, directory=None, file_pattern=None) -> dict:
        """Generate a list of files to transfer."""
        ...

    @abstractmethod
    def transfer_files(self, files: dict, remote_spec: dict, dest_remote_handler=None):
        ...

    @abstractmethod
    def push_files_from_worker(self, local_staging_directory):
        ...

    @abstractmethod
    def pull_files_to_worker(self, files, local_staging_directory):
        ...

    @abstractmethod
    def pull_files(self, files):
        ...

    @abstractmethod
    def move_files_to_final_location(self, files: list):
        ...

    @abstractmethod
    def handle_post_copy_action(self, files):
        ...

    @abstractmethod
    def tidy(self):
        ...


class RemoteExecutionHandler(ABC):
    def __init__(self, spec):
        self.spec = spec

    @abstractmethod
    def execute(self, command):
        ...
