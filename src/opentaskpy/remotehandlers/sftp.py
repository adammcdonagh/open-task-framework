"""SFTP Remote Handlers.

This module contains the SFTP remote handlers for transfers.
"""

import glob
import os
import re
import stat
import time
from io import StringIO
from shlex import quote

from paramiko import AutoAddPolicy, Channel, RSAKey, SFTPClient, SSHClient
from tenacity import retry, stop_after_attempt, wait_exponential

import opentaskpy.otflogging
from opentaskpy.remotehandlers.remotehandler import RemoteTransferHandler

SSH_OPTIONS: str = "-o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=5"
REMOTE_SCRIPT_BASE_DIR: str = "/tmp"  # nosec B108


class SFTPTransfer(RemoteTransferHandler):
    """SFTP Transfer Handler."""

    TASK_TYPE = "T"

    FILE_NAME_DELIMITER = "|||"

    sftp_client: SFTPClient | None = None
    log_watch_start_row = 0

    def __init__(self, spec: dict):
        """Initialise the SFTPTransfer handler.

        Args:
            spec (dict): The spec for the transfer. This is either the source, or the
            destination spec.
        """
        self.logger = opentaskpy.otflogging.init_logging(
            __name__, spec["task_id"], self.TASK_TYPE
        )

        # Handle default values
        if "createDirectoryIfNotExists" not in spec:
            spec["createDirectoryIfNotExists"] = False

        super().__init__(spec)

    def supports_direct_transfer(self) -> bool:
        """Return False, as all transfers require transfers via the worker."""
        return False

    def connect(self, hostname: str) -> None:
        """Connect to the remote host.

        Args:
            hostname (str): The hostname to connect to.
            sftp_client (SFTPClient, optional): An existing SFTPClient to use. Defaults to None.
        """
        if self.sftp_client and isinstance(self.sftp_client, SFTPClient):
            channel = self.sftp_client.get_channel()
            if channel is not None and isinstance(channel, Channel) and channel.active:
                return

        client_kwargs = {
            "hostname": hostname,
            "port": (self.spec["protocol"].get("port", 22)),
            "username": self.spec["protocol"]["credentials"]["username"],
            "timeout": 3,
            "allow_agent": False,
        }

        # If a custom key is set via env vars, then set that
        if (
            os.environ.get("OTF_SSH_KEY")
            and os.path.exists(str(os.environ.get("OTF_SSH_KEY")))
        ) and "keyFile" not in self.spec["protocol"]["credentials"]:
            self.logger.info("Loading custom private SSH key from OTF_SSH_KEY env var")
            key = RSAKey.from_private_key_file(str(os.environ.get("OTF_SSH_KEY")))
            client_kwargs["pkey"] = key

        # If a specific key file has been defined, then use that
        elif "keyFile" in self.spec["protocol"]["credentials"]:
            self.logger.info("Using key file from task spec")
            client_kwargs["key_filename"] = self.spec["protocol"]["credentials"][
                "keyFile"
            ]

        # If a private key has been defined as a string, then use that instead
        elif "key" in self.spec["protocol"]["credentials"]:
            self.logger.info("Using private key from task spec")
            key = RSAKey.from_private_key(
                StringIO(self.spec["protocol"]["credentials"]["key"])
            )
            client_kwargs["pkey"] = key

        # If a password has been defined, then use that
        elif "password" in self.spec["protocol"]["credentials"]:
            client_kwargs["password"] = self.spec["protocol"]["credentials"]["password"]

        self.connect_with_retry(client_kwargs)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def connect_with_retry(self, client_kwargs: dict) -> SSHClient:
        """Connect to the remote host with retry.

        Args:
            client_kwargs (dict): The kwargs to use for the SSH client.

        Returns:
            SSHClient: The SSH client.
        """
        try:
            ssh_client = SSHClient()
            ssh_client.set_log_channel(
                f"{__name__}.{ self.spec['task_id']}.paramiko.transport"
            )
            ssh_client.set_missing_host_key_policy(AutoAddPolicy())
            self.logger.info(f"Connecting to {client_kwargs['hostname']}")
            ssh_client.connect(**client_kwargs)
            self.sftp_client = ssh_client.open_sftp()

        except Exception as ex:
            self.logger.error(f"Unable to connect to {client_kwargs['hostname']}: {ex}")
            raise ex

        return ssh_client

    def tidy(self) -> None:
        """Tidy up the SFTP connection.

        Shut down the SFTP connection and remove the remote transfer script from the
        remote host.
        """
        # Close connection
        if self.sftp_client:
            self.logger.info(f"[{self.spec['hostname']}] Closing SFTP connection")
            self.sftp_client.get_channel().close()  # type: ignore[union-attr]

            # Wait until the channel is closed
            time.sleep(0.25)
            for _ in range(2):
                if not self.sftp_client.get_channel().closed:  # type: ignore[union-attr]
                    time.sleep(0.5)
                else:
                    break

            self.sftp_client.close()

    def list_files(
        self, directory: str | None = None, file_pattern: str | None = None
    ) -> dict:
        """Return list of files that match the source definition.

        Args:
            directory (str, optional): The directory to search in. Defaults to None.
            file_pattern (str, optional): The file pattern to search for. Defaults to
            None.

        Returns:
            dict: A dict of files that match the source definition.
        """
        self.connect(self.spec["hostname"])
        if not directory:
            directory = str(self.spec["directory"])
        if not file_pattern:
            file_pattern = str(self.spec["fileRegex"])

        self.logger.info(
            f"Searching for files in {directory} with pattern {file_pattern}"
        )

        self.logger.log(
            12,
            (
                f"[{self.spec['hostname']}] Searching in {directory} for files with"
                f" pattern {file_pattern}"
            ),
        )
        remote_files: dict = {}
        # Check the remote directory exists
        try:
            self.sftp_client.stat(directory)  # type: ignore[union-attr]
        except FileNotFoundError:
            self.logger.error(
                f"[{self.spec['hostname']}] Directory {directory} does not exist"
            )
            return remote_files

        remote_file_list = self.sftp_client.listdir(directory)  # type: ignore[union-attr]
        for file in list(remote_file_list):
            if re.match(file_pattern, file):
                # Get the file attributes
                file_attr = self.sftp_client.lstat(f"{directory}/{file}")  # type: ignore[union-attr]
                self.logger.log(12, f"File attributes {file_attr}")
                remote_files[f"{directory}/{file}"] = {
                    "size": file_attr.st_size,
                    "modified_time": file_attr.st_mtime,
                }

        return remote_files

    def pull_files_to_worker(
        self, files: list[str], local_staging_directory: str
    ) -> int:
        """Pull files to the worker.

        This function is used when we need to download source files from the source
        server onto the worker. These are then later pushed to the destination server

        Args:
            files (list): A list of files to download.
            local_staging_directory (str): The local staging directory to download the
            files to.

        Returns:
            int: 0 if successful, 1 if not.
        """
        result = 0
        # Connect to the source
        self.connect(self.spec["hostname"])

        # Create the staging directory locally
        if not os.path.exists(local_staging_directory):
            os.makedirs(local_staging_directory)

        # Download the files via SFTP
        for file in files:
            self.logger.info(
                f"[LOCALHOST] Downloading file {file} to {local_staging_directory}"
            )
            file_name = os.path.basename(file)
            try:
                self.sftp_client.get(file, f"{local_staging_directory}/{file_name}")  # type: ignore[union-attr]
            except Exception as ex:  # pylint: disable=broad-exception-caught
                self.logger.error(
                    f"[LOCALHOST] Unable to download file locally via SFTP: {ex}"
                )
                result = 1

        return result

    def push_files_from_worker(
        self, local_staging_directory: str, file_list: dict | None = None
    ) -> int:
        """Push files from the worker to the destination server.

        This function is used when the source files have been downloaded locally and
        need to be uploaded to the destination server. This would be expected to be
        called against the remote handler for the destination server.

        Args:
            local_staging_directory (str): The local staging directory to upload the
            files from.
            file_list (dict, optional): A list of files to upload. Defaults to None.

        Returns:
            int: 0 if successful, 1 if not.
        """
        # Connect to the destination server
        self.connect(self.spec["hostname"])
        # Check that the SFTP client is connected and active
        if not isinstance(self.sftp_client, SFTPClient):
            self.logger.error(f"[{self.spec['hostname']}] Cannot connect via SFTP")
            return 1

        # For SFTP, there is no staging directory, the files just go straight to where
        # they should do.

        destination_directory = quote(self.spec["directory"])

        # Sanitize the destination directory
        destination_directory = quote(destination_directory)

        self.logger.info(f"[{self.spec['hostname']}] Validating destination dir")
        # Use the SFTP client to check if the destination directory exists on the server
        remote_dir_exists = False
        try:
            self.sftp_client.stat(destination_directory)
            remote_dir_exists = True
        except OSError:
            self.logger.info(
                f"[{self.spec['hostname']}] Destination dir does not exist:"
                f" {destination_directory}"
            )

        if not remote_dir_exists and not self.spec["createDirectoryIfNotExists"]:
            self.logger.error(
                f"[{self.spec['hostname']}] Destination dir does not exist:"
                f" {destination_directory}"
            )
            return 1

        if not remote_dir_exists and self.spec["createDirectoryIfNotExists"]:
            self.logger.info(
                f"[{self.spec['hostname']}] Creating destination directory:"
                f" {destination_directory}"
            )
            self.sftp_client.mkdir(destination_directory)

        # Transfer the files
        result = 0

        if file_list:
            files = list(file_list.keys())
        else:
            # Get list of files in local_staging_directory
            files = glob.glob(f"{local_staging_directory}/*")
        for file in files:
            self.logger.info(f"[LOCALHOST] Transferring file via SFTP: {file}")
            file_name = os.path.basename(file)

            # Handle any rename that might be specified in the spec
            if "rename" in self.spec:
                rename_regex = self.spec["rename"]["pattern"]
                rename_sub = self.spec["rename"]["sub"]

                file_name = re.sub(rename_regex, rename_sub, file_name)
                self.logger.info(
                    f"[{self.spec['hostname']}] Renaming file to {file_name}"
                )

            mode = self.spec.get("mode", None)

            stat_after_upload = True
            if not self.spec["protocol"].get("supportsStatAfterUpload", True):
                stat_after_upload = False

            # If destination directory is the root, then set it to an empty string
            # so paths don't start with //
            if destination_directory == "/":
                destination_directory = ""

            try:

                # Check the protocol to see if supportsPosixRename is set
                if self.spec["protocol"].get("supportsPosixRename", True):

                    # While writing, the file should not have it's final name. Replace the
                    # file extension with .partial, and then rename it once the file has
                    # been transferred
                    file_name_partial = re.sub(r"\.[^.]+$", ".partial", file_name)

                    self.sftp_client.put(
                        file,
                        f"{destination_directory}/{file_name_partial}",
                        confirm=stat_after_upload,
                    )

                    # Rename the file to its final name
                    self.sftp_client.posix_rename(
                        f"{destination_directory}/{file_name_partial}",
                        f"{destination_directory}/{file_name}",
                    )
                else:
                    # Upload the file without using a temporary name
                    self.sftp_client.put(
                        file,
                        f"{destination_directory}/{file_name}",
                        confirm=stat_after_upload,
                    )

                if mode:
                    self.sftp_client.chmod(
                        f"{destination_directory}/{file_name}", int(mode, base=8)
                    )
            except Exception as ex:  # pylint: disable=broad-exception-caught
                self.logger.error(
                    f"[{self.spec['hostname']}] Unable to transfer file via SFTP: {ex}"
                )
                result = 1

        return result

    def transfer_files(self, files: list[str]) -> None:
        """Not implemented for this handler."""
        raise NotImplementedError

    def pull_files(self, files: list[str]) -> None:
        """Not implemented for this handler."""
        raise NotImplementedError

    def move_files_to_final_location(self, files: list[str]) -> None:
        """Not implemented for this handler."""
        raise NotImplementedError

    def handle_post_copy_action(self, files: list[str]) -> int:
        """Handle the post copy action specified in the config.

        Args:
            files (list[str]): A list of files that need to be handled.

        Returns:
            int: 0 if successful, 1 if not.
        """
        self.connect(self.spec["hostname"])

        # Check that the SFTP client is connected and active
        if not isinstance(self.sftp_client, SFTPClient):
            self.logger.error(f"[{self.spec['hostname']}] Cannot connect via SFTP")
            return 1

        if self.spec["postCopyAction"]["action"] == "delete":
            # Loop through each file and use the sftp client to delete the files

            for file in files:
                try:
                    self.logger.info(f"Deleting file {file}")
                    self.sftp_client.remove(file)
                except OSError:
                    self.logger.error(
                        f"[{self.spec['hostname']}] Could not delete file {file} on"
                        " source host"
                    )
                    return 1

        if (
            self.spec["postCopyAction"]["action"] == "move"
            or self.spec["postCopyAction"]["action"] == "rename"
        ):
            # Use the SFTP client, and check that the destination directory exists
            move_dir = os.path.dirname(self.spec["postCopyAction"]["destination"])

            try:
                stat_result = self.sftp_client.stat(move_dir)
                # If it exists, then we need to ensure its a directory and not just a file
                if not stat.S_ISDIR(stat_result.st_mode):  # type: ignore[arg-type]
                    self.logger.error(
                        f"[{self.spec['hostname']}] Destination directory {move_dir} is"
                        " not a directory on source host"
                    )
                    return 1
            except OSError:
                self.logger.error(
                    f"[{self.spec['hostname']}] Destination directory {move_dir} does"
                    " not exist on source host"
                )
                return 1

                # Loop through the files and move them

            for file in files:
                try:
                    # If this is a move, then just move the file
                    if self.spec["postCopyAction"]["action"] == "move":
                        self.logger.info(
                            f"[{self.spec['hostname']}] Moving {file} to"
                            f" {self.spec['postCopyAction']['destination']}"
                        )
                        # Get the actual file name
                        file_name = os.path.basename(file)
                        self.sftp_client.posix_rename(
                            file,
                            f"{self.spec['postCopyAction']['destination']}/{file_name}",
                        )
                    # If this is a rename, then we need to rename the file
                    if self.spec["postCopyAction"]["action"] == "rename":
                        # Determine the new file name
                        new_file_dir = os.path.dirname(
                            self.spec["postCopyAction"]["destination"]
                        )
                        current_file_name = os.path.basename(file)

                        rename_regex = self.spec["postCopyAction"]["pattern"]
                        rename_sub = self.spec["postCopyAction"]["sub"]

                        new_file_name = re.sub(
                            rename_regex, rename_sub, current_file_name
                        )

                        self.logger.info(
                            f"[{self.spec['hostname']}] Renaming {file} to"
                            f" {new_file_dir}/{new_file_name}"
                        )
                        self.sftp_client.posix_rename(
                            file, f"{new_file_dir}/{new_file_name}"
                        )
                except OSError as e:
                    self.logger.error(f"[{self.spec['hostname']}] Error: {e}")
                    self.logger.error(
                        f"[{self.spec['hostname']}] Error moving or renaming file"
                        f" {file}"
                    )
                    return 1

        return 0

    def create_flag_files(self) -> int:
        """Create the flag files on the remote host.

        Returns:
            int: 0 if successful, 1 if not.
        """
        self.connect(self.spec["hostname"])

        # Check that the SFTP client is connected and active
        if not isinstance(self.sftp_client, SFTPClient):
            self.logger.error(f"[{self.spec['hostname']}] Cannot connect via SFTP")
            return 1

        filename = self.spec["flags"]["fullPath"]

        try:
            # Use the SFTP client to create an empty file at this path
            self.sftp_client.file(filename, "w").close()

            # Set permissions on the file to whatever was specified in the spec,
            # otherwise we leave them as is
            # We cannot change ownership without using sudo, so we don't bother
            if "permissions" in self.spec:
                self.sftp_client.chmod(filename, int(self.spec["permissions"], base=8))

        except OSError as e:
            self.logger.error(f"[{self.spec['hostname']}] Error: {e}")
            self.logger.error(
                f"[{self.spec['hostname']}] Error creating flag file: {filename}"
            )
            return 1

        return 0
