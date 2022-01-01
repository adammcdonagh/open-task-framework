import logging
import sys
import time
from os import environ
from opentaskpy.remotehandlers.ssh import SSH

logger = logging.getLogger("opentaskpy.taskhandlers.transfer")

# Full transfers expect that the remote host has a base install of python3
# We transfer over the wrapper script to the remote host and trigger it, which is responsible
# for doing the majority of the hard work


class Transfer:

    def __init__(self, task_id, transfer_definition):
        self.task_id = task_id
        self.transfer_definition = transfer_definition
        self.source_remote_handler = None
        self.dest_remote_handler = None

    def return_result(self, status, message=None):
        if message:
            logger.error(message)

        # Delete the remote connection objects
        if self.source_remote_handler:
            logger.log(12, "Closing source connection")
            self.source_remote_handler.tidy()
        if self.dest_remote_handler:
            logger.log(12, "Closing dest connection")
            self.dest_remote_handler.tidy()
        return status

    def run(self):
        logger.info("Running transfer")
        environ['OTF_TASK_ID'] = self.task_id

        # Based on the transfer definition, determine what to do first
        source_file_spec = self.transfer_definition["source"]
        dest_file_spec = self.transfer_definition["destination"]
        # Based on the source protocol pick the appropriate remote handler
        if source_file_spec["protocol"]["name"] == "ssh":
            self.source_remote_handler = SSH(source_file_spec, remote_spec=dest_file_spec)

        # If log watching, do that first
        if "logWatch" in source_file_spec:
            logger.info("Performing a log watch")
            logging.error("NOT IMPLEMENTED")
            # TODO: Implement this
            self.source_remote_handler.do_logwatch()

        # If filewatching, do that next
        if "fileWatch" in source_file_spec:
            logger.info("Performing a file watch")
            # TODO: Implement this
            logging.error("NOT IMPLEMENTED")

            if not self.source_remote_handler.do_filewatch():
                self.return_result(1, "No files matched filewatch")

            if "watchOnly" in source_file_spec["fileWatch"]:
                logger.info("Only performing file watch")
                return 0

        # Determine what needs to be transferred

        remote_files = self.source_remote_handler.list_files()

        # Loop through the returned files to see if they match the file age and size spec (if defined)
        if "conditionals" in source_file_spec and remote_files:
            for remote_file in list(remote_files):
                logger.info(f"Checking {remote_file}")

                # Check to see if there's a size condition
                meets_condition = True

                if "size" in source_file_spec["conditionals"]:
                    logger.log(12, "Checking file size")
                    min_size = source_file_spec["conditionals"]["size"]["gt"] if "gt" in source_file_spec["conditionals"]["size"] else None
                    max_size = source_file_spec["conditionals"]["size"]["lt"] if "lt" in source_file_spec["conditionals"]["size"] else None

                    file_size = remote_files[remote_file]["size"]

                    if min_size and file_size <= min_size:
                        logger.info(
                            f"File is too small: Min size: [{min_size} B] Actual size: [{file_size} B]")
                        meets_condition = False

                    if max_size and file_size >= max_size:
                        logger.info(
                            f"File is too big: Max size: [{max_size} B] Actual size: [{file_size} B]")
                        meets_condition = False

                if "age" in source_file_spec["conditionals"]:
                    min_age = None if not "gt" in source_file_spec["conditionals"]["age"] else source_file_spec["conditionals"]["age"]["gt"]
                    max_age = None if not "lt" in source_file_spec["conditionals"]["age"] else source_file_spec["conditionals"]["age"]["lt"]

                    file_modified_time = remote_files[remote_file]["modified_time"]
                    file_age = time.time() - file_modified_time

                    logger.log(
                        12, f"Checking file age - Last modified time: {time.ctime(file_modified_time)}")

                    if min_age and file_age <= min_age:
                        logger.info(
                            f"File is too new: Min age: [{min_age} secs] Actual age: [{file_age} secs]")
                        meets_condition = False

                    if max_age and file_age >= max_age:
                        logger.info(
                            f"File is too old: Max age: [{max_age} secs] Actual age: [{file_age} secs]")
                        meets_condition = False

                if not meets_condition:
                    remote_files.pop(remote_file)

        if not remote_files:
            if "error" in source_file_spec and not source_file_spec["error"]:
                self.return_result(0, "No remote files could be found to transfer. But not erroring due to config")
            else:
                self.return_result(1, "No remote files could be found to transfer")
        else:
            logging.info(
                "Found the following file(s) that match all requirements:")
            for file in remote_files:
                logging.info(f" * {file}")
            # This is where the transfer actually needs to happen

            if dest_file_spec["protocol"]["name"] == "ssh":
                self.dest_remote_handler = SSH(dest_file_spec, remote_spec=source_file_spec)

            # Handle the push or pull transfer types
            if "transferType" not in dest_file_spec or dest_file_spec["transferType"] == "push":

                transfer_result = self.source_remote_handler.transfer_files(remote_files, dest_client)
                if transfer_result != 0:
                    self.return_result(1, "Remote transfer errored")

                logging.info("Transfer completed successfully")

            else:
                transfer_result = self.dest_remote_handler.pull_files(remote_files)
                if transfer_result != 0:
                    self.return_result(1, "Remote PULL transfer errored")

                logging.info("Transfer completed successfully")

            # Handle any ownership and permissions changes
            if dest_file_spec["protocol"]["name"] == "ssh":
                move_result = self.dest_remote_handler.move_files_to_final_location(remote_files)
                if move_result != 0:
                    self.return_result(1, "Error moving file into final location")

            if "postCopyAction" in source_file_spec:

                pca_result = self.source_remote_handler.handle_post_copy_action(remote_files)
                if pca_result != 0:
                    self.return_result(1, "Error performing post copy action")

            self.return_result(0)
