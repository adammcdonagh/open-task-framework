"""Abstract classes for remote handlers."""

from abc import ABC, abstractmethod


class RemoteHandler(ABC):
    """Parent class for remote handlers."""

    def __init__(self, spec: dict):
        """Initialise the handler.

        Args:
            spec (dict): The spec for the handler.
        """
        self.spec = spec


class RemoteTransferHandler(RemoteHandler):
    """Abstract class for remote transfer handlers."""

    def __init__(self, spec: dict, remote_spec: dict | None = None):
        """Initialise the handler.

        Args:
            spec (dict): The spec for the transfer.
            remote_spec (dict, optional): The remote spec for the transfer. Defaults to None.
        """
        self.remote_spec = remote_spec
        # Call super with the spec
        super().__init__(spec)

    @abstractmethod
    def supports_direct_transfer(self) -> bool:
        """Check if the remote handler supports direct transfers."""

    @abstractmethod
    def list_files(
        self, directory: str | None = None, file_pattern: str | None = None
    ) -> dict:
        """Generate a list of files to transfer."""

    @abstractmethod
    def transfer_files(
        self,
        files: list[str],
        remote_spec: dict,
        dest_remote_handler: dict | None = None,
    ) -> int:
        """Transfer files to the remote location.

        Args:
            files (list[str]): The files to transfer.
            remote_spec (dict): The remote spec for the transfer.
            dest_remote_handler (RemoteTransferHandler, optional): The remote handler for the destination. Defaults to None.

        Returns:
            int: The result of the transfer. 0 for success, 1 for failure.
        """

    @abstractmethod
    def push_files_from_worker(
        self, local_staging_directory: str, file_list: dict | None = None
    ) -> int:
        """Push files from the worker to the remote location.

        This is used when files have been either generated on the worker, or copied
        as a proxy transfer onto the worker.

        Args:
            local_staging_directory (str): The local staging directory.
            file_list (dict, optional): The list of files to transfer. Defaults to None.

        Returns:
            int: The result of the transfer. 0 for success, 1 for failure.
        """

    @abstractmethod
    def pull_files_to_worker(
        self, files: list[str], local_staging_directory: str
    ) -> int:
        """Pull files from the remote location to the worker.

        Args:
            files (list[str]): The files to pull.
            local_staging_directory (str): The local staging directory.

        Returns:
            int: The result of the transfer. 0 for success, 1 for failure.
        """

    @abstractmethod
    def pull_files(self, files: list[str]) -> int:
        """Pull files from the remote location to the destination system.

        Used when a direct push cannot be done, and the files need to be pulled instead.

        Args:
            files (list[str]): The files to pull.

        Returns:
            int: The result of the transfer. 0 for success, 1 for failure.
        """

    @abstractmethod
    def move_files_to_final_location(self, files: dict) -> int:
        """Move files to their final location.

        Once dropped on the destination system, the files may need to be moved to their
        final location.

        Args:
            files (dict): The files to move.

        Returns:
            int: The result of the transfer. 0 for success, 1 for failure.
        """

    @abstractmethod
    def handle_post_copy_action(self, files: list[str]) -> int:
        """Handle any post copy actions.

        Post Copy Actions (PCA) are actions that need to be performed after the files
        have been copied to the destination system and are in their final location. The
        PCA acts on the source files, and will typically delete them, move them, or
        rename them.

        Args:
            files (list[str]): The files to act on.

        Returns:
            int: The result of the transfer. 0 for success, 1 for failure.
        """

    def tidy(self) -> None:
        """Tidy up after the transfer, if necessary. Otherwise do nothing."""


class RemoteExecutionHandler(RemoteHandler):
    """Abstract class for remote execution handlers."""

    @abstractmethod
    def execute(self) -> bool:
        """Execute the command.

        Returns:
            bool: True if the command was successful, False otherwise.
        """
