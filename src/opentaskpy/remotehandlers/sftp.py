"""SSH Remote Handlers.

This module contains the SSH remote handlers for transfers and executions.
"""
import os
import re

from paramiko import AutoAddPolicy, Channel, RSAKey, SFTPClient, SSHClient

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
            __name__, os.environ.get("OTF_TASK_ID"), self.TASK_TYPE
        )

        # Allow override of REMOTE_SCRIPT_BASE_DIR
        if os.environ.get("OTF_REMOTE_SCRIPT_BASE_DIR"):
            global REMOTE_SCRIPT_BASE_DIR  # pylint: disable=global-statement
            REMOTE_SCRIPT_BASE_DIR = str(os.environ.get("OTF_REMOTE_SCRIPT_BASE_DIR"))

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
            "port": (
                self.spec["protocol"]["port"] if "port" in self.spec["protocol"] else 22
            ),
            "username": self.spec["protocol"]["credentials"]["username"],
            "timeout": 5,
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

        # If a password has been defined, then use that
        elif "password" in self.spec["protocol"]["credentials"]:
            client_kwargs["password"] = self.spec["protocol"]["credentials"]["password"]

        try:
            ssh_client = SSHClient()
            ssh_client.set_log_channel(
                f"{__name__}.{os.environ.get('OTF_TASK_ID')}.paramiko.transport"
            )
            ssh_client.set_missing_host_key_policy(AutoAddPolicy())
            ssh_client.connect(**client_kwargs)
            self.sftp_client = ssh_client.open_sftp()

        except Exception as ex:
            self.logger.error(f"Unable to connect to {hostname}: {ex}")
            raise ex

    def tidy(self) -> None:
        """Tidy up the SFTP connection.

        Shut down the SFTP connection and remove the remote transfer script from the
        remote host.
        """
        # Close connection
        if self.sftp_client:
            self.logger.debug(
                f"[{self.spec['hostname']}] Closing SFTP connection to"
                f" {self.spec['hostname']}"
            )
            self.sftp_client.close()

    # Create abstract methods handle_post_copy_action, list_files, move_files_to_final_location, pull_files, pull_files_to_worker, push_files_from_worker, transfer_files
    def handle_post_copy_action(self, files: list[str]) -> int:
        """Implement this later."""
        raise NotImplementedError

    def move_files_to_final_location(self, files: list[str]) -> None:
        """Implement this later."""
        raise NotImplementedError

    def pull_files_to_worker(self, files: list[str]) -> None:
        """Implement this later."""
        raise NotImplementedError

    def push_files_from_worker(self, local_staging_directory: str) -> int:
        """Implement this later."""
        raise NotImplementedError

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

        self.logger.log(
            12,
            (
                f"[{self.spec['hostname']}] Searching in {directory} for files with"
                f" pattern {file_pattern}"
            ),
        )
        remote_files = {}
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

    # def pull_files_to_worker(
    #     self, files: list[str], local_staging_directory: str
    # ) -> int:
    #     """Pull files to the worker.

    #     This function is used when we need to download source files from the source
    #     server onto the worker. These are then later pushed to the destination server

    #     Args:
    #         files (list): A list of files to download.
    #         local_staging_directory (str): The local staging directory to download the
    #         files to.

    #     Returns:
    #         int: 0 if successful, 1 if not.
    #     """
    #     result = 0
    #     # Connect to the source
    #     self.connect(self.spec["hostname"])

    #     # Create the staging directory locally
    #     if not os.path.exists(local_staging_directory):
    #         os.makedirs(local_staging_directory)

    #     # Download the files via SFTP
    #     for file in files:
    #         self.logger.info(
    #             f"[LOCALHOST] Downloading file {file} to {local_staging_directory}"
    #         )
    #         file_name = os.path.basename(file)
    #         try:
    #             self.sftp_client.get(file, f"{local_staging_directory}/{file_name}")  # type: ignore[union-attr]
    #         except Exception as ex:  # pylint: disable=broad-exception-caught
    #             self.logger.error(
    #                 f"[LOCALHOST] Unable to download file locally via SFTP: {ex}"
    #             )
    #             result = 1

    #     return result

    # def push_files_from_worker(self, local_staging_directory: str) -> int:
    #     """Push files from the worker to the destination server.

    #     This function is used when the source files have been downloaded locally and
    #     need to be uploaded to the destination server. This would be expected to be
    #     called against the remote handler for the destination server.

    #     Args:
    #         local_staging_directory (str): The local staging directory to upload the
    #         files from.

    #     Returns:
    #         int: 0 if successful, 1 if not.
    #     """
    #     # Connect to the destination server
    #     self.connect(self.spec["hostname"])
    #     # Check that the SFTP client is connected and active
    #     if not isinstance(self.sftp_client, SFTPClient):
    #         self.logger.error(f"[{self.spec['hostname']}] Cannot connect via SFTP")
    #         return 1

    #     # Handle the staging directory
    #     destination_directory = self.get_staging_directory(self.spec)

    #     # Sanitize the destination directory
    #     destination_directory = quote(destination_directory)

    #     # Create/validate staging directory exists on destination
    #     remote_command = (
    #         f"test -e {destination_directory} || mkdir -p {destination_directory}"
    #     )

    #     self.logger.info(
    #         f"[{self.spec['hostname']}] Validating staging dir via SSH:"
    #         f" {remote_command}"
    #     )

    #     _, stdout, stderr = self.ssh_client.exec_command(remote_command)  # type: ignore[union-attr] # nosec B601 # We've sanitised as much as possible above
    #     with stdout as stdout_fh:
    #         if str_stdout := stdout_fh.read().decode("UTF-8"):
    #             log_stdout(str_stdout, self.spec["hostname"], self.logger)

    #     with stderr as stderr_fh:
    #         str_stderr = stderr_fh.read().decode("UTF-8")
    #         if str_stderr and len(str_stderr) > 0:
    #             self.logger.info(
    #                 f"[{self.spec['hostname']}] Remote stderr returned:\n{str_stderr}"
    #             )

    #     remote_rc = stdout.channel.recv_exit_status()
    #     self.logger.info(
    #         f"[{self.spec['hostname']}] Got return code {remote_rc} from SSH command"
    #     )

    #     # Transfer the files, just use SFTP
    #     result = 0
    #     # Get list of files in local_staging_directory
    #     files = glob.glob(f"{local_staging_directory}/*")
    #     for file in files:
    #         self.logger.info(f"[LOCALHOST] Transferring file via SFTP: {file}")
    #         file_name = os.path.basename(file)
    #         try:
    #             self.sftp_client.put(file, f"{destination_directory}{file_name}")
    #         except Exception as ex:  # pylint: disable=broad-exception-caught
    #             self.logger.error(f"[LOCALHOST] Unable to transfer file via SFTP: {ex}")
    #             result = 1

    #     return result

    def transfer_files(self, files: list[str]) -> None:
        """Not implemented for this handler."""
        raise NotImplementedError

    def pull_files(self, files: list[str]) -> None:
        """Not implemented for this handler."""
        raise NotImplementedError

    # def move_files_to_final_location(self, files: dict) -> int:
    #     """Move files from the staging directory to their final location.

    #     Args:
    #         files (dict): A dictionary of files to move.

    #     Returns:
    #         int: 0 if successful, if not, the return code from the remotely executed
    #         transfer.py
    #     """
    #     self.connect(self.spec["hostname"])

    #     # Convert all the source file names into the filename with the destination directory as a prefix
    #     file_names_str = ""
    #     files_with_directory = []
    #     for file in list(files):
    #         files_with_directory.append(
    #             quote(
    #                 f"{self.get_staging_directory(self.spec)}{os.path.basename(file)}"
    #             )
    #         )
    #     file_names_str = self.FILE_NAME_DELIMITER.join(files_with_directory).strip()

    #     # Next step is to move the file to it's final resting place with the correct permissions and ownership
    #     # Build a command to pass to the remote transfer.py to do the work
    #     owner_args = (
    #         f"--owner {quote(self.spec['permissions']['owner'])}"
    #         if "permissions" in self.spec and "owner" in self.spec["permissions"]
    #         else ""
    #     )
    #     group_args = (
    #         f"--group {quote(self.spec['permissions']['group'])}"
    #         if "permissions" in self.spec and "group" in self.spec["permissions"]
    #         else ""
    #     )
    #     mode_args = f"--mode {quote(self.spec['mode'])}" if "mode" in self.spec else ""
    #     rename_args = (
    #         f"--renameRegex {quote(self.spec['rename']['pattern'])} --renameSub"
    #         f" {quote(self.spec['rename']['sub'])}"
    #         if "rename" in self.spec
    #         else ""
    #     )

    #     directory = quote(self.spec["directory"])

    #     remote_command = (
    #         f"python3 {REMOTE_SCRIPT_BASE_DIR}/transfer.py --moveFiles"
    #         f" '{file_names_str}' --destination"
    #         f" {directory} {owner_args} {group_args} {mode_args} {rename_args}"
    #     )
    #     self.logger.info(f"[{self.spec['hostname']}] Running: {remote_command}")

    #     stdin, stdout, stderr = self.ssh_client.exec_command(remote_command)  # type: ignore[union-attr] # nosec B601

    #     with stdout as stdout_fh:
    #         str_stdout = stdout_fh.read().decode("UTF-8")
    #         if str_stdout:
    #             log_stdout(str_stdout, self.spec["hostname"], self.logger)

    #     with stderr as stderr_fh:
    #         str_stderr = stderr_fh.read().decode("UTF-8")
    #         if str_stderr and len(str_stderr) > 0:
    #             self.logger.info(
    #                 f"[{self.spec['hostname']}] Remote stderr returned:\n{str_stderr}"
    #             )

    #     remote_rc: int = stdout.channel.recv_exit_status()
    #     self.logger.info(
    #         f"[{self.spec['hostname']}] Got return code {remote_rc} from SSH move"
    #         " command"
    #     )
    #     return remote_rc

    # def handle_post_copy_action(self, files: list[str]) -> int:
    #     """Handle the post copy action specified in the config.

    #     Args:
    #         files (list[str]): A list of files that need to be handled.

    #     Returns:
    #         int: 0 if successful, 1 if not.
    #     """
    #     self.connect(self.spec["hostname"])
    #     sftp_client = self.ssh_client.open_sftp()  # type: ignore[union-attr]

    #     if self.spec["postCopyAction"]["action"] == "delete":
    #         # Loop through each file and use the sftp client to delete the files

    #         for file in files:
    #             try:
    #                 sftp_client.remove(file)
    #             except OSError:
    #                 self.logger.error(
    #                     f"[{self.spec['hostname']}] Could not delete file {file} on"
    #                     " source host"
    #                 )
    #                 return 1

    #     if (
    #         self.spec["postCopyAction"]["action"] == "move"
    #         or self.spec["postCopyAction"]["action"] == "rename"
    #     ):
    #         # Use the SFTP client, and check that the destination directory exists
    #         move_dir = os.path.dirname(self.spec["postCopyAction"]["destination"])

    #         try:
    #             stat_result = sftp_client.stat(move_dir)
    #             # If it exists, then we need to ensure its a directory and not just a file
    #             if not stat.S_ISDIR(stat_result.st_mode):  # type: ignore[arg-type]
    #                 self.logger.error(
    #                     f"[{self.spec['hostname']}] Destination directory {move_dir} is"
    #                     " not a directory on source host"
    #                 )
    #                 return 1
    #         except OSError:
    #             self.logger.error(
    #                 f"[{self.spec['hostname']}] Destination directory {move_dir} does"
    #                 " not exist on source host"
    #             )
    #             return 1

    #             # Loop through the files and move them

    #         for file in files:
    #             try:
    #                 # If this is a move, then just move the file
    #                 if self.spec["postCopyAction"]["action"] == "move":
    #                     self.logger.info(
    #                         f"[{self.spec['hostname']}] Moving {file} to"
    #                         f" {self.spec['postCopyAction']['destination']}"
    #                     )
    #                     # Get the actual file name
    #                     file_name = os.path.basename(file)
    #                     sftp_client.posix_rename(
    #                         file,
    #                         f"{self.spec['postCopyAction']['destination']}/{file_name}",
    #                     )
    #                 # If this is a rename, then we need to rename the file
    #                 if self.spec["postCopyAction"]["action"] == "rename":
    #                     # Determine the new file name
    #                     new_file_dir = os.path.dirname(
    #                         self.spec["postCopyAction"]["destination"]
    #                     )
    #                     current_file_name = os.path.basename(file)

    #                     rename_regex = self.spec["postCopyAction"]["pattern"]
    #                     rename_sub = self.spec["postCopyAction"]["sub"]

    #                     new_file_name = re.sub(
    #                         rename_regex, rename_sub, current_file_name
    #                     )

    #                     self.logger.info(
    #                         f"[{self.spec['hostname']}] Renaming {file} to"
    #                         f" {new_file_dir}/{new_file_name}"
    #                     )
    #                     sftp_client.posix_rename(
    #                         file, f"{new_file_dir}/{new_file_name}"
    #                     )
    #             except OSError as e:
    #                 self.logger.error(f"[{self.spec['hostname']}] Error: {e}")
    #                 self.logger.error(
    #                     f"[{self.spec['hostname']}] Error moving or renaming file"
    #                     f" {file}"
    #                 )
    #                 return 1

    #     return 0

    # def init_logwatch(self) -> int:
    #     """Initialise the logwatch process.

    #     Returns:
    #         int: 0 if successful, 1 if not.
    #     """
    #     self.connect(self.spec["hostname"])
    #     if not isinstance(self.sftp_client, SFTPClient):
    #         self.logger.error(f"[{self.spec['hostname']}] Cannot connect via SFTP")
    #         return 1

    #     # There are 2 options for logwatches. One is to watch for new entries, the other is to scan the entire log.
    #     # Default if not specified is to watch for new entries

    #     # Determine the log details and check it exists first
    #     log_file = (
    #         f"{self.spec['logWatch']['directory']}/{self.spec['logWatch']['log']}"
    #     )

    #     # Stat the file
    #     try:
    #         _ = self.sftp_client.lstat(f"{log_file}")
    #     except FileNotFoundError:
    #         self.logger.error(
    #             f"[{self.spec['hostname']}] Log file {log_file} does not exist"
    #         )
    #         return 1
    #     except PermissionError:
    #         self.logger.error(
    #             f"[{self.spec['hostname']}] Log file {log_file} cannot be accessed"
    #         )
    #         return 1

    #     # Open the existing file and determine the number of rows
    #     with self.sftp_client.open(log_file) as log_fh:
    #         rows = 0
    #         for _, _ in enumerate(log_fh):
    #             pass
    #         self.logger.log(
    #             12, f"[{self.spec['hostname']}] Found {rows+1} lines in log"
    #         )
    #         self.log_watch_start_row = rows + 1

    #     return 0

    # def do_logwatch(self) -> int:
    #     """Perform the logwatch process.

    #     Returns:
    #         int: 0 if successful, 1 if not.
    #     """
    #     self.connect(self.spec["hostname"])
    #     if not isinstance(self.sftp_client, SFTPClient):
    #         self.logger.error(f"[{self.spec['hostname']}] Cannot connect via SFTP")
    #         return 1

    #     # Determine if the config requires scanning the entire log, or just from the start_row determine in the init function
    #     start_row = (
    #         self.log_watch_start_row
    #         if "tail" in self.spec["logWatch"] and self.spec["logWatch"]["tail"]
    #         else 0
    #     )
    #     self.logger.log(
    #         12, f"[{self.spec['hostname']}] Starting logwatch from row {start_row}"
    #     )

    #     # Open the remote log file and parse each line for the pattern
    #     log_file = (
    #         f"{self.spec['logWatch']['directory']}/{self.spec['logWatch']['log']}"
    #     )

    #     with self.sftp_client.open(log_file) as log_fh:
    #         for i, line in enumerate(log_fh):
    #             # We need to start after the previous line in the log
    #             if i >= start_row:
    #                 self.logger.log(
    #                     11, f"[{self.spec['hostname']}] Log line: {line.strip()}"
    #                 )
    #                 if re.search(self.spec["logWatch"]["contentRegex"], line.strip()):
    #                     self.logger.log(
    #                         12,
    #                         (
    #                             f"[{self.spec['hostname']}] Found matching line in log:"
    #                             f" {line.strip()} on line: {i+1}"
    #                         ),
    #                     )
    #                     return 0

    #     return 1

    # def create_flag_files(self) -> int:
    #     """Create the flag files on the remote host.

    #     Returns:
    #         int: 0 if successful, 1 if not.
    #     """
    #     self.connect(self.spec["hostname"])

    #     if not isinstance(self.ssh_client, SSHClient):
    #         self.logger.error(f"[{self.spec['hostname']}] Cannot connect via SSH")
    #         return 1

    #     # Manually open SFTP client
    #     sftp_client = self.ssh_client.open_sftp()
    #     filename = self.spec["flags"]["fullPath"]

    #     try:
    #         # Use the SFTP client to create an empty file at this path
    #         sftp_client.file(filename, "w").close()

    #         # Set permissions on the file to whatever was specified in the spec,
    #         # otherwise we leave them as is
    #         # We cannot change ownership without using sudo, so we don't bother
    #         if "permissions" in self.spec:
    #             sftp_client.chmod(filename, self.spec["permissions"])

    #     except OSError as e:
    #         self.logger.error(f"[{self.spec['hostname']}] Error: {e}")
    #         self.logger.error(
    #             f"[{self.spec['hostname']}] Error creating flag file: {filename}"
    #         )
    #         return 1

    #     return 0
