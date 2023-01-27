import time
from math import ceil, floor
from os import environ

import opentaskpy.logging
from opentaskpy import exceptions
from opentaskpy.remotehandlers.ssh import SSHTransfer
from opentaskpy.taskhandlers.taskhandler import TaskHandler

# Full transfers expect that the remote host has a base install of python3
# We transfer over the wrapper script to the remote host and trigger it, which is responsible
# for doing some of the more complex work, rather than triggering a tonne of shell commands

TASK_TYPE = "T"


class Transfer(TaskHandler):
    def __init__(self, task_id, transfer_definition):
        self.task_id = task_id
        self.transfer_definition = transfer_definition
        self.source_remote_handler = None
        self.dest_remote_handlers = None
        self.source_file_spec = None
        self.dest_file_specs = None
        self.overall_result = False

        self.logger = opentaskpy.logging.init_logging(
            "opentaskpy.taskhandlers.transfer", self.task_id, TASK_TYPE
        )

    def return_result(self, status, message=None, exception=None):
        if message:
            if status == 0:
                self.logger.info(message)
            else:
                self.logger.error(message)

        if status == 0:
            self.overall_result = True

        # Delete the remote connection objects
        if self.source_remote_handler:
            self.logger.log(12, "Closing source connection")
            self.source_remote_handler.tidy()
        if self.dest_remote_handlers:
            for remote_handler in self.dest_remote_handlers:
                self.logger.log(12, f"Closing dest connection for {remote_handler}")
                remote_handler.tidy()

        self.logger.info("Closing log file handler")
        opentaskpy.logging.close_log_file(self.logger, self.overall_result)

        # Throw an exception if we have one
        if exception:
            raise exception(message)

        return status == 0

    def _set_remote_handlers(self):
        # Based on the transfer definition, determine what to do first
        self.source_file_spec = self.transfer_definition["source"]

        # Create a list of destination file specs
        if (
            "destination" in self.transfer_definition
            and self.transfer_definition["destination"]
            and isinstance(self.transfer_definition["destination"], list)
        ):
            self.dest_file_specs = self.transfer_definition["destination"]

        # Based on the source protocol pick the appropriate remote handler
        if self.source_file_spec["protocol"]["name"] == "ssh":
            self.source_remote_handler = SSHTransfer(self.source_file_spec)

        # Based on the destination protocol pick the appropriate remote handler
        if self.dest_file_specs:
            self.dest_remote_handlers = []
            for dest_file_spec in self.dest_file_specs:

                # For each host, create a remote handler
                if dest_file_spec["protocol"]["name"] == "ssh":
                    self.dest_remote_handlers.append(SSHTransfer(dest_file_spec))
                else:
                    raise exceptions.UnknownProtocolError(
                        f"Unknown protocol {self.dest_file_specs['protocol']['name']}"
                    )

    def run(self, kill_event=None):
        self.logger.info("Running transfer")
        environ["OTF_TASK_ID"] = self.task_id

        self._set_remote_handlers()

        # If log watching, do that first
        if "logWatch" in self.source_file_spec:
            self.logger.info(
                f"Performing a log watch of {self.source_file_spec['logWatch']['directory']}/{self.source_file_spec['logWatch']['log']}"
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
                else:
                    remaining_seconds = ceil(
                        (start_time + timeout_seconds) - time.time()
                    )
                    if remaining_seconds == 0:
                        break

                    # If the sleep time is longer than the time remaining, sleep for that long instead
                    if remaining_seconds < sleep_seconds:
                        actual_sleep_seconds = remaining_seconds
                    else:
                        actual_sleep_seconds = sleep_seconds

                    self.logger.info(
                        f"No entry found in log. Sleeping for {sleep_seconds} secs. {remaining_seconds} seconds remain"
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
            remote_files = []

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

                if remote_files:
                    self.logger.info("Filewatch found remote file(s)")
                    break
                else:
                    remaining_seconds = ceil(
                        (start_time + timeout_seconds) - time.time()
                    )
                    if remaining_seconds == 0:
                        break

                    # If the sleep time is longer than the time remaining, sleep for that long instead
                    if remaining_seconds < sleep_seconds:
                        actual_sleep_seconds = remaining_seconds
                    else:
                        actual_sleep_seconds = sleep_seconds

                    self.logger.info(
                        f"No files found. Sleeping for {sleep_seconds} secs. {remaining_seconds} seconds remain"
                    )
                    time.sleep(actual_sleep_seconds)

            if (
                remote_files
                and "watchOnly" in self.source_file_spec["fileWatch"]
                and self.source_file_spec["fileWatch"]["watchOnly"]
            ):
                return self.return_result("0", "Just performing filewatch")
            elif not remote_files:
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
                            f"File is too small: Min size: [{min_size} B] Actual size: [{file_size} B]"
                        )
                        meets_condition = False

                    if max_size and file_size >= max_size:
                        self.logger.info(
                            f"File is too big: Max size: [{max_size} B] Actual size: [{file_size} B]"
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
                        f"Checking file age - Last modified time: {time.ctime(file_modified_time)}",
                    )

                    if min_age and file_age <= min_age:
                        self.logger.info(
                            f"File is too new: Min age: [{min_age} secs] Actual age: [{file_age} secs]"
                        )
                        meets_condition = False

                    if max_age and file_age >= max_age:
                        self.logger.info(
                            f"File is too old: Max age: [{max_age} secs] Actual age: [{file_age} secs]"
                        )
                        meets_condition = False

                if not meets_condition:
                    remote_files.pop(remote_file)

        if not remote_files:
            if "error" in self.source_file_spec and not self.source_file_spec["error"]:
                return self.return_result(
                    0,
                    "No remote files could be found to transfer. But not erroring due to config",
                    exception=exceptions.FilesDoNotMeetConditionsError,
                )
            else:
                return self.return_result(
                    1,
                    "No remote files could be found to transfer",
                    exception=exceptions.FilesDoNotMeetConditionsError,
                )
        else:
            self.logger.info("Found the following file(s) that match all requirements:")
            for file in remote_files:
                self.logger.info(f" * {file}")

            # If there's a destination file spec, then we need to transfer the files
            if self.dest_file_specs:

                # Handle the push transfers first
                i = 0
                for dest_file_spec in self.dest_file_specs:
                    if (
                        "transferType" not in dest_file_spec
                        or dest_file_spec["transferType"] == "push"
                    ):
                        transfer_result = self.source_remote_handler.transfer_files(
                            remote_files,
                            dest_file_spec,
                            dest_remote_handler=self.dest_remote_handlers[i],
                        )
                        if transfer_result != 0:
                            return self.return_result(
                                1,
                                "Remote transfer errored",
                                exception=exceptions.RemoteTransferError,
                            )

                        self.logger.info("Transfer completed successfully")

                    elif (
                        "transferType" in dest_file_spec
                        and dest_file_spec["transferType"] == "pull"
                    ):
                        transfer_result = self.dest_remote_handlers[i].pull_files(
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
                    i += 1
            else:
                self.logger.info("Performing filewatch only")

            if "postCopyAction" in self.source_file_spec:

                pca_result = self.source_remote_handler.handle_post_copy_action(
                    remote_files
                )
                if pca_result != 0:
                    return self.return_result(
                        1,
                        "Error performing post copy action",
                        exception=exceptions.RemoteTransferError,
                    )

            return self.return_result(0)

    # Destructor to handle when the transfer is finished. Make sure the log file
    # gets renamed as appropriate
    def __del__(self):
        self.logger.debug("Transfer object deleted")
        self.logger.info("Closing log file handler")
        opentaskpy.logging.close_log_file(self.logger, self.overall_result)
