"""Task handler for running transfers."""
import random
import shutil
import threading
import time
from importlib import import_module
from math import ceil, floor
from os import environ, getpid, makedirs, path
from sys import modules
from typing import NamedTuple

import opentaskpy.otflogging
from opentaskpy import exceptions
from opentaskpy.remotehandlers.remotehandler import RemoteTransferHandler
from opentaskpy.taskhandlers.taskhandler import TaskHandler

# Full transfers expect that the remote host has a base install of python3
# We transfer over the wrapper script to the remote host and trigger it, which is responsible
# for doing some of the more complex work, rather than triggering a tonne of shell commands


class DefaultProtocolCharacteristics(NamedTuple):
    """Class defining the configuration for default protocols."""

    module: str
    class_: str


TASK_TYPE = "T"
DEFAULT_PROTOCOL_MAP = {
    "ssh": DefaultProtocolCharacteristics(
        "opentaskpy.remotehandlers.ssh", "SSHTransfer"
    ),
    "sftp": DefaultProtocolCharacteristics(
        "opentaskpy.remotehandlers.sftp", "SFTPTransfer"
    ),
    "email": DefaultProtocolCharacteristics(
        "opentaskpy.remotehandlers.email", "EmailTransfer"
    ),
    "local": DefaultProtocolCharacteristics(
        "opentaskpy.remotehandlers.local", "LocalTransfer"
    ),
}
DEFAULT_STAGING_DIR_BASE = "/tmp"  # nosec B108


class Transfer(TaskHandler):  # pylint: disable=too-many-instance-attributes
    """Task handler for running transfers."""

    source_remote_handler: RemoteTransferHandler
    dest_remote_handlers: RemoteTransferHandler = None
    source_file_spec: dict
    dest_file_specs: list[dict] | None = None
    overall_result: bool = False

    def __init__(self, global_config: dict, task_id: str, transfer_definition: dict):
        """Create a new transfer task handler.

        Args:
            global_config (dict): Global configuration dictionary
            task_id (str): Task ID
            transfer_definition (dict): Transfer definition
        """
        self.task_id = task_id
        self.transfer_definition = transfer_definition

        # Set up the local staging directory
        # Allow for a custom staging directory to be set via environment variable
        staging_dir_name = f"OTF_STAGING_{getpid()}.{random.randint(0, 1000000)}"
        if "OTF_STAGING_DIR" in environ:
            self.local_staging_dir = f"{environ['OTF_STAGING_DIR']}/{staging_dir_name}"
        else:
            self.local_staging_dir = f"/{DEFAULT_STAGING_DIR_BASE}/{staging_dir_name}"

        self.logger = opentaskpy.otflogging.init_logging(
            "opentaskpy.taskhandlers.transfer", self.task_id, TASK_TYPE
        )

        super().__init__(global_config)

    def return_result(
        self,
        status: int,
        message: str | None = None,
        exception: Exception | None = None,
    ) -> bool:
        """Return the result of the task run.

        Args:
            status (int): The status code to return.
            message (str, optional): The message to return. Defaults to None.
            exception (Exception, optional): The exception to return. Defaults to None.

        Returns:
            bool: The result of the task run.
        """
        # Delete the remote connection objects
        if self.source_remote_handler:
            self.logger.log(12, "Closing source connection")
            self.source_remote_handler.tidy()
        if self.dest_remote_handlers:
            for remote_handler in self.dest_remote_handlers:
                self.logger.log(12, f"Closing dest connection for {remote_handler}")
                remote_handler.tidy()

        # Remove local staging directory if it exists
        if path.exists(self.local_staging_dir):
            self.logger.log(
                12, f"Removing local staging directory {self.local_staging_dir}"
            )
            shutil.rmtree(self.local_staging_dir)

        # Call super to do the rest
        return super().return_result(status, message, exception)  # type: ignore[no-any-return]

    def _get_default_class(self, protocol_name: str) -> type:
        class_name = DEFAULT_PROTOCOL_MAP[protocol_name].class_
        module_name = DEFAULT_PROTOCOL_MAP[protocol_name].module

        # Load module
        if module_name not in modules:
            import_module(module_name)

        return getattr(modules[module_name], class_name)  # type: ignore[no-any-return]

    def _set_remote_handlers(self) -> None:
        # Based on the transfer definition, determine what to do first
        self.source_file_spec = self.transfer_definition["source"]
        source_protocol = self.source_file_spec["protocol"]["name"]

        # Create a list of destination file specs
        if (
            "destination" in self.transfer_definition
            and self.transfer_definition["destination"]
            and isinstance(self.transfer_definition["destination"], list)
        ):
            self.dest_file_specs = self.transfer_definition["destination"]

        # Based on the source protocol pick the appropriate remote handler
        if source_protocol in DEFAULT_PROTOCOL_MAP:
            handler_class = self._get_default_class(source_protocol)
            self.source_remote_handler = handler_class(self.source_file_spec)

        # If not SSH, then it's a non-standard protocol, we need to see if it's loadable
        # load it, and then create the remote handler
        else:
            self.source_remote_handler = super()._get_handler_for_protocol(
                source_protocol, self.source_file_spec
            )

        super()._set_handler_vars(source_protocol, self.source_remote_handler)

        # Based on the destination protocol pick the appropriate remote handler
        if self.dest_file_specs:
            self.dest_remote_handlers = []
            for dest_file_spec in self.dest_file_specs:
                remote_protocol = dest_file_spec["protocol"]["name"]

                # For each host, create a remote handler
                remote_handler = None
                if remote_protocol in DEFAULT_PROTOCOL_MAP:
                    handler_class = self._get_default_class(remote_protocol)
                    remote_handler = handler_class(dest_file_spec)

                else:
                    remote_handler = super()._get_handler_for_protocol(
                        remote_protocol, dest_file_spec
                    )

                self.dest_remote_handlers.append(remote_handler)
                super()._set_handler_vars(remote_protocol, remote_handler)

    def run(self, kill_event: threading.Event | None = None) -> bool:  # noqa: C901
        """Run the transfer task.

        Args:
            kill_event (threading.Event, optional): Event to kill the task. Defaults to None.

        Returns:
            bool: The result of the task run.
        """
        self.logger.info("Running transfer")
        environ["OTF_TASK_ID"] = self.task_id

        self._set_remote_handlers()

        # If log watching, do that first
        if "logWatch" in self.source_file_spec:
            self.logger.info(
                "Performing a log watch of"
                f" {self.source_file_spec['logWatch']['directory']}/{self.source_file_spec['logWatch']['log']}"
            )

            if self.source_remote_handler.init_logwatch() != 0:
                return self.return_result(
                    1, "Logwatch init failed", exception=exceptions.LogWatchInitError
                )

            timeout_seconds = (
                60
                if "timeout" not in self.source_file_spec["logWatch"]
                else self.source_file_spec["logWatch"]["timeout"]
            )
            sleep_seconds = (
                10
                if "sleepTime" not in self.source_file_spec["logWatch"]
                else self.source_file_spec["logWatch"]["sleepTime"]
            )

            # Now we start the loop to monitor the log file
            start_time = time.time()
            found_log_entry = False
            while floor(time.time() - start_time) <= timeout_seconds:
                if self.source_remote_handler.do_logwatch() == 0:
                    found_log_entry = True
                    break

                remaining_seconds = ceil((start_time + timeout_seconds) - time.time())
                if remaining_seconds == 0:
                    break

                # If the sleep time is longer than the time remaining, sleep for that long instead
                if remaining_seconds < sleep_seconds:
                    actual_sleep_seconds = remaining_seconds
                else:
                    actual_sleep_seconds = sleep_seconds

                self.logger.info(
                    f"No entry found in log. Sleeping for {sleep_seconds} secs."
                    f" {remaining_seconds} seconds remain"
                )
                time.sleep(actual_sleep_seconds)

            if found_log_entry:
                self.logger.info("Found pattern in log file")
            else:
                return self.return_result(
                    1,
                    f"No log entry found after {timeout_seconds} seconds",
                    exception=exceptions.LogWatchTimeoutError,
                )

        # If filewatching, do that next
        if "fileWatch" in self.source_file_spec:
            # Setup a loop for the filewatch
            timeout_seconds = (
                60
                if "timeout" not in self.source_file_spec["fileWatch"]
                else self.source_file_spec["fileWatch"]["timeout"]
            )
            sleep_seconds = (
                10
                if "sleepTime" not in self.source_file_spec["fileWatch"]
                else self.source_file_spec["fileWatch"]["sleepTime"]
            )

            start_time = time.time()
            remote_files: dict = {}

            # Determine if we're doing a plain filewatch, or looking for a different file to what we are transferring
            watch_directory = (
                self.source_file_spec["fileWatch"]["directory"]
                if "directory" in self.source_file_spec["fileWatch"]
                else self.source_file_spec["directory"]
            )
            watch_file_pattern = (
                self.source_file_spec["fileWatch"]["fileRegex"]
                if "fileRegex" in self.source_file_spec["fileWatch"]
                else self.source_file_spec["fileRegex"]
            )

            self.logger.info(
                f"Performing a file watch on {watch_directory}/{watch_file_pattern}"
            )

            while (
                not remote_files and floor(time.time() - start_time) <= timeout_seconds
            ):
                remote_files = self.source_remote_handler.list_files(
                    directory=watch_directory, file_pattern=watch_file_pattern
                )
                # TODO: #5 Change all references to remote_files to expect a generator # pylint: disable=fixme
                if remote_files:
                    self.logger.info("Filewatch found remote file(s)")
                    break

                remaining_seconds = ceil((start_time + timeout_seconds) - time.time())
                if remaining_seconds == 0:
                    break

                # If the sleep time is longer than the time remaining, sleep for that long instead
                if remaining_seconds < sleep_seconds:
                    actual_sleep_seconds = remaining_seconds
                else:
                    actual_sleep_seconds = sleep_seconds

                self.logger.info(
                    f"No files found. Sleeping for {sleep_seconds} secs."
                    f" {remaining_seconds} seconds remain"
                )
                time.sleep(actual_sleep_seconds)

            if (
                remote_files
                and "watchOnly" in self.source_file_spec["fileWatch"]
                and self.source_file_spec["fileWatch"]["watchOnly"]
            ):
                return self.return_result(0, "Just performing filewatch")
            if not remote_files:
                # Only error if error is not set to false
                if (
                    "error" in self.source_file_spec
                    and not self.source_file_spec["error"]
                ):
                    self.logger.info(
                        "No files found after timeout, but error is set to false"
                    )
                    return self.return_result(0, "No files found")

                return self.return_result(
                    1,
                    f"No files found after {timeout_seconds} seconds",
                    exception=exceptions.RemoteFileNotFoundError,
                )

        # Determine what needs to be transferred
        remote_files = self.source_remote_handler.list_files()

        # Loop through the returned files to see if they match the file age and size spec (if defined)
        if "conditionals" in self.source_file_spec and remote_files:
            for remote_file in list(remote_files):
                self.logger.info(f"Checking {remote_file}")

                # Check to see if there's a size condition
                meets_condition = True

                if "size" in self.source_file_spec["conditionals"]:
                    self.logger.log(12, "Checking file size")
                    min_size = (
                        self.source_file_spec["conditionals"]["size"]["gt"]
                        if "gt" in self.source_file_spec["conditionals"]["size"]
                        else None
                    )
                    max_size = (
                        self.source_file_spec["conditionals"]["size"]["lt"]
                        if "lt" in self.source_file_spec["conditionals"]["size"]
                        else None
                    )

                    file_size = remote_files[remote_file]["size"]

                    if min_size and file_size <= min_size:
                        self.logger.info(
                            f"File is too small: Min size: [{min_size} B] Actual size:"
                            f" [{file_size} B]"
                        )
                        meets_condition = False

                    if max_size and file_size >= max_size:
                        self.logger.info(
                            f"File is too big: Max size: [{max_size} B] Actual size:"
                            f" [{file_size} B]"
                        )
                        meets_condition = False

                if "age" in self.source_file_spec["conditionals"]:
                    min_age = (
                        None
                        if "gt" not in self.source_file_spec["conditionals"]["age"]
                        else self.source_file_spec["conditionals"]["age"]["gt"]
                    )
                    max_age = (
                        None
                        if "lt" not in self.source_file_spec["conditionals"]["age"]
                        else self.source_file_spec["conditionals"]["age"]["lt"]
                    )

                    file_modified_time = remote_files[remote_file]["modified_time"]
                    file_age = time.time() - file_modified_time

                    self.logger.log(
                        12,
                        (
                            "Checking file age - Last modified time:"
                            f" {time.ctime(file_modified_time)} - Age in secs:"
                            f" {file_age} secs"
                        ),
                    )

                    if min_age and file_age <= min_age:
                        self.logger.info(
                            f"File is too new: Min age: [{min_age} secs] Actual age:"
                            f" [{file_age} secs]"
                        )
                        meets_condition = False

                    if max_age and file_age >= max_age:
                        self.logger.info(
                            f"File is too old: Max age: [{max_age} secs] Actual age:"
                            f" [{file_age} secs]"
                        )
                        meets_condition = False

                if not meets_condition:
                    remote_files.pop(remote_file)

        if not remote_files:
            if "error" in self.source_file_spec and not self.source_file_spec["error"]:
                return self.return_result(
                    0,
                    (
                        "No remote files could be found to transfer. But not erroring"
                        " due to config"
                    ),
                )

            return self.return_result(
                1,
                "No remote files could be found to transfer",
                exception=exceptions.FilesDoNotMeetConditionsError,
            )

        self.logger.info("Found the following file(s) that match all requirements:")
        for file in remote_files:
            self.logger.info(f" * {file}")

        # If there's a destination file spec, then we need to transfer the files
        if self.dest_file_specs:
            # Loop through all dest_file specs and see if there are any transfers where the source and dest protocols are different
            # If there are, then we need to do a pull transfer first, then a push transfer
            any_different_protocols = False
            i = 0
            for dest_file_spec in self.dest_file_specs:
                different_protocols = False
                if (
                    (
                        "transferType" not in dest_file_spec
                        or dest_file_spec["transferType"] == "push"
                    )
                    # And the destination and source remote handler classes are not the same
                    and (
                        self.source_remote_handler.__class__
                        != self.dest_remote_handlers[i].__class__
                    )
                ):
                    different_protocols = True
                    any_different_protocols = True
                    i += 1

                # If there are differences, download the file locally first
                # so it's ready to upload to multiple destinations at once
                if (
                    different_protocols
                    or (
                        "transferType" in dest_file_spec
                        and dest_file_spec["transferType"] == "proxy"
                    )
                    or not self.source_remote_handler.supports_direct_transfer()
                ):
                    # Create local staging dir
                    makedirs(self.local_staging_dir, exist_ok=True)
                    transfer_result = self.source_remote_handler.pull_files_to_worker(
                        remote_files, self.local_staging_dir
                    )
                    if transfer_result != 0:
                        return self.return_result(
                            1,
                            "Pull to worker from remote source errored",
                            exception=exceptions.RemoteTransferError,
                        )

            i = 0
            for dest_file_spec in self.dest_file_specs:
                # Handle the push transfers first
                associated_dest_remote_handler = self.dest_remote_handlers[i]
                # If this is a default push transfer, and both source and dest protocols are the same
                if (
                    (
                        "transferType" not in dest_file_spec
                        or dest_file_spec["transferType"] == "push"
                        # And the destination and source remote handler classes are the same
                    )
                    and not any_different_protocols
                    and self.source_remote_handler.supports_direct_transfer()
                ):
                    transfer_result = self.source_remote_handler.transfer_files(
                        remote_files,
                        dest_file_spec,
                        dest_remote_handler=associated_dest_remote_handler,
                    )
                    if transfer_result != 0:
                        return self.return_result(
                            1,
                            "Remote transfer errored",
                            exception=exceptions.RemoteTransferError,
                        )

                    self.logger.info("Transfer completed successfully")
                # If this is a default push transfer, and source and dest protocols are different
                elif (
                    (
                        "transferType" in dest_file_spec
                        and (
                            dest_file_spec["transferType"] == "push"
                            or dest_file_spec["transferType"] == "proxy"
                        )
                    )
                    or different_protocols
                    or not self.source_remote_handler.supports_direct_transfer()
                ):
                    self.logger.debug(
                        "Transfer protocols are different, or proxy transfer is"
                        " requested"
                    )

                    transfer_result = (
                        associated_dest_remote_handler.push_files_from_worker(
                            self.local_staging_dir
                        )
                    )

                    if transfer_result != 0:
                        return self.return_result(
                            1,
                            "Push of files to destination errored",
                            exception=exceptions.RemoteTransferError,
                        )

                elif (
                    "transferType" in dest_file_spec
                    and dest_file_spec["transferType"] == "pull"
                ):
                    transfer_result = associated_dest_remote_handler.pull_files(
                        remote_files, self.source_file_spec
                    )
                    if transfer_result != 0:
                        return self.return_result(
                            1,
                            "Remote PULL transfer errored",
                            exception=exceptions.RemoteTransferError,
                        )

                    self.logger.info("Transfer completed successfully")

                # Handle any ownership and permissions changes
                if dest_file_spec["protocol"]["name"] == "ssh":
                    move_result = self.dest_remote_handlers[
                        i
                    ].move_files_to_final_location(remote_files)
                    if move_result != 0:
                        return self.return_result(
                            1,
                            "Error moving file into final location",
                            exception=exceptions.RemoteTransferError,
                        )

                # Create any flag files that might need creating
                if "flags" in dest_file_spec:
                    flag_result = self.dest_remote_handlers[i].create_flag_files()
                    if flag_result != 0:
                        return self.return_result(
                            1,
                            "Error creating flag files",
                            exception=exceptions.RemoteTransferError,
                        )

                i += 1

            if different_protocols:
                self.logger.debug("Removing local staging directory")
                shutil.rmtree(self.local_staging_dir)
        else:
            self.logger.info("Performing filewatch only")

        if "postCopyAction" in self.source_file_spec:
            try:
                self.logger.info("Performing post copy action")
                pca_result = self.source_remote_handler.handle_post_copy_action(
                    remote_files
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                pca_result = 1
                return self.return_result(
                    1,
                    "Error performing post copy action",
                    exception=e,
                )
            if pca_result != 0:
                return self.return_result(
                    1,
                    "Error performing post copy action",
                    exception=exceptions.RemoteTransferError,
                )

        return self.return_result(0)
