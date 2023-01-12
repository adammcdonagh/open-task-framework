import logging
import os
import sys
import re
from paramiko import SSHClient, AutoAddPolicy
from opentaskpy.remotehandlers.remotehandler import RemoteTransferHandler, RemoteExecutionHandler

logger = logging.getLogger(__name__)

SSH_OPTIONS = "-o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=5"


class SSHTransfer(RemoteTransferHandler):

    FILE_NAME_DELIMITER = "|||"

    def __init__(self, spec, remote_spec=None):
        self.spec = spec
        self.ssh_client = None
        self.sftp_connection = None
        self.remote_spec = remote_spec
        self.log_watch_start_row = 0

        # We need to copy the required remote scripts to the source and destination (if applicable) hosts
        hostname = spec["hostname"]
        logger.info(f"Validating source remote host: {hostname}")

        try:
            client = SSHClient()
            client.set_missing_host_key_policy(AutoAddPolicy())
            client.connect(
                hostname,
                username=self.spec["protocol"]["credentials"]["username"],
                timeout=5,
            )
            _, stdout, _ = client.exec_command("uname -a")
            with stdout as stdout_fh:
                logger.log(11, f"Remote uname: {stdout_fh.read().decode('UTF-8')}")

            # Transfer over the transfer.py script
            local_script = f"{os.path.dirname(os.path.realpath(__file__))}/scripts/transfer.py"

            sftp = client.open_sftp()
            sftp.put(local_script, "/tmp/transfer.py")

            self.ssh_client = client
            self.sftp_connection = sftp
        except Exception as ex:
            logger.error(f"Exception while setting up remote SSH client: {ex}")

        if not self.ssh_client or not self.sftp_connection:
            logger.error(f"Failed to set up SSH client to {hostname}")
            sys.exit(1)

    def tidy(self):
        # Remove remote scripts
        if self.ssh_client:
            file_list = self.sftp_connection.listdir("/tmp")
            if "transfer.py" in file_list:
                self.sftp_connection.remove("/tmp/transfer.py")
            self.sftp_connection.close()

            logger.debug(f"Closing SSH connection to {self.spec['hostname']}")
            self.ssh_client.close()

    def get_staging_directory(self):
        return (
            self.remote_spec["stagingDirectory"]
            if "stagingDirectory" in self.remote_spec
            else f"~/otf/{os.environ['OTF_TASK_ID']}/"
        )

    """
    Determine the list of files that match the source definition
    List remote files based on the source file pattern
    """

    def list_files(self, directory=None, file_pattern=None):

        if not directory:
            directory = self.spec["directory"]
        if not file_pattern:
            file_pattern = self.spec["fileRegex"]

        logger.log(12, f"Searching in {directory} for files with pattern {file_pattern}")
        remote_files = dict()
        remote_file_list = self.sftp_connection.listdir(directory)
        for file in list(remote_file_list):
            if re.match(file_pattern, file):
                # Get the file attributes
                file_attr = self.sftp_connection.lstat(f"{directory}/{file}")
                logger.log(12, f"File attributes {file_attr}")
                remote_files[f"{directory}/{file}"] = {"size": file_attr.st_size, "modified_time": file_attr.st_mtime}

        return remote_files

    def transfer_files(self, files, dest_remote_handler=None):
        # Construct an SCP command to transfer the files to the destination server
        remote_user = (
            self.remote_spec["protocol"]["credentials"]["transferUsername"]
            if "transferUsername" in self.remote_spec["protocol"]["credentials"]
            else self.remote_spec["protocol"]["credentials"]["username"]
        )
        remote_host = self.remote_spec["hostname"]
        # Handle staging directory if there is one
        destination_directory = self.get_staging_directory()

        # Create/validate staging directory exists on destination
        remote_command = f"test -e {destination_directory} || mkdir -p {destination_directory}"
        logger.info(f"Validating staging dir via SSH: {remote_command}")
        _, stdout, stderr = dest_remote_handler.ssh_client.exec_command(remote_command)
        with stdout as stdout_fh:
            str_stdout = stdout_fh.read().decode("UTF-8")
            if str_stdout:
                self.log_stdout(str_stdout)

        with stderr as stderr_fh:
            str_stderr = stderr_fh.read().decode("UTF-8")
            if str_stderr and len(str_stderr) > 0:
                logger.info(f"Remote stderr returned:\n{str_stderr}")

        remote_rc = stdout.channel.recv_exit_status()
        logger.info(f"Got return code {remote_rc} from SSH command")

        remote_command = f'scp {SSH_OPTIONS} {" ".join(files)} {remote_user}@{remote_host}:"{destination_directory}"'
        logger.info(f"Transferring files via SCP: {remote_command}")

        _, stdout, stderr = self.ssh_client.exec_command(remote_command)

        with stdout as stdout_fh:
            str_stdout = stdout_fh.read().decode("UTF-8")
            if str_stdout:
                self.log_stdout(str_stdout)

        with stderr as stderr_fh:
            str_stderr = stderr_fh.read().decode("UTF-8")
            if str_stderr and len(str_stderr) > 0:
                logger.info(f"Remote stderr returned:\n{str_stderr}")

        remote_rc = stdout.channel.recv_exit_status()
        logger.info(f"Got return code {remote_rc} from SCP command")

        return remote_rc

    def pull_files(self, files):
        # Construct an SCP command to transfer the files from the source server
        source_user = self.spec["protocol"]["credentials"]["transferUsername"]
        source_host = self.remote_spec["hostname"]

        # Handle staging directory if there is one
        destination_directory = self.get_staging_directory()

        # Create/validate staging directory exists
        remote_command = f"test -e {destination_directory} || mkdir -p {destination_directory}"
        logger.info(f"Validating staging dir via SSH: {remote_command}")
        _, stdout, stderr = self.ssh_client.exec_command(remote_command)
        with stdout as stdout_fh:
            str_stdout = stdout_fh.read().decode("UTF-8")
            if str_stdout:
                self.log_stdout(str_stdout)

        with stderr as stderr_fh:
            str_stderr = stderr_fh.read().decode("UTF-8")
            if str_stderr and len(str_stderr) > 0:
                logger.info(f"Remote stderr returned:\n{str_stderr}")

        remote_rc = stdout.channel.recv_exit_status()
        logger.info(f"Got return code {remote_rc} from SSH command")

        files_str = ""
        for file in files:
            files_str += f"{source_user}@{source_host}:{file} "

        remote_command = f"scp {SSH_OPTIONS} {files_str.strip()} {destination_directory}"
        logger.info(f"Transferring files via SCP: {remote_command}")

        stdin, stdout, stderr = self.ssh_client.exec_command(remote_command)

        with stdout as stdout_fh:
            str_stdout = stdout_fh.read().decode("UTF-8")
            if str_stdout:
                self.log_stdout(str_stdout)

        with stderr as stderr_fh:
            str_stderr = stderr_fh.read().decode("UTF-8")
            if str_stderr and len(str_stderr) > 0:
                logger.info(f"Remote stderr returned:\n{str_stderr}")

        remote_rc = stdout.channel.recv_exit_status()
        logger.info(f"Got return code {remote_rc} from SCP command")

        return remote_rc

    def move_files_to_final_location(self, files):

        # Convert all the source file names into the filename with the destination directory as a prefix
        file_names_str = ""
        files_with_directory = []
        for file in list(files):
            files_with_directory.append(f"{self.get_staging_directory()}{os.path.basename(file)}")
        file_names_str = self.FILE_NAME_DELIMITER.join(files_with_directory).strip()

        # Next step is to move the file to it's final resting place with the correct permissions and ownership
        # Build a commnd to pass to the remote transfer.py to do the work
        owner_args = (
            f"--owner {self.spec['permissions']['owner']}"
            if "permissions" in self.spec and "owner" in self.spec["permissions"]
            else ""
        )
        group_args = (
            f"--group {self.spec['permissions']['group']}"
            if "permissions" in self.spec and "group" in self.spec["permissions"]
            else ""
        )
        mode_args = f"--mode {self.spec['mode']}" if "mode" in self.spec else ""
        rename_args = (
            f"--renameRegex '{self.spec['rename']['pattern']}' --renameSub '{self.spec['rename']['sub']}'"
            if "rename" in self.spec
            else ""
        )
        remote_command = f"python3 /tmp/transfer.py --moveFiles '{file_names_str}' --destination {self.spec['directory']} {owner_args} {group_args} {mode_args} {rename_args}"
        logger.info(f"[{self.spec['hostname']}] - Running: {remote_command}")

        stdin, stdout, stderr = self.ssh_client.exec_command(remote_command)

        with stdout as stdout_fh:
            str_stdout = stdout_fh.read().decode("UTF-8")
            if str_stdout:
                self.log_stdout(str_stdout)

        with stderr as stderr_fh:
            str_stderr = stderr_fh.read().decode("UTF-8")
            if str_stderr and len(str_stderr) > 0:
                logger.info(f"Remote stderr returned:\n{str_stderr}")

        remote_rc = stdout.channel.recv_exit_status()
        logger.info(f"Got return code {remote_rc} from SSH move command")
        return remote_rc

    def handle_post_copy_action(self, files):
        remote_command = None
        if self.spec["postCopyAction"]["action"] == "delete":
            remote_command = f"python3 /tmp/transfer.py --deleteFiles '{self.FILE_NAME_DELIMITER.join(files)}'"
        if self.spec["postCopyAction"]["action"] == "move":
            remote_command = f"python3 /tmp/transfer.py --moveFiles '{self.FILE_NAME_DELIMITER.join(files)}' --destination {self.spec['postCopyAction']['destination']}"

        if remote_command:
            logger.info(f"[{self.spec['hostname']}] - Running: {remote_command}")
            _, stdout, stderr = self.ssh_client.exec_command(remote_command)

            with stdout as stdout_fh:
                str_stdout = stdout_fh.read().decode("UTF-8")
                if str_stdout:
                    self.log_stdout(str_stdout)

            with stderr as stderr_fh:
                str_stderr = stderr_fh.read().decode("UTF-8")
                if str_stderr and len(str_stderr) > 0:
                    logger.info(f"Remote stderr returned:\n{str_stderr}")

            remote_rc = stdout.channel.recv_exit_status()
            logger.info(f"Got return code {remote_rc} from SSH post copy action command")
            return remote_rc

    def init_logwatch(self):
        # There are 2 options for logwatches. One is to watch for new entries, the other is to scan the entire log.
        # Default if not specified is to watch for new entries

        # Determine the log details and check it exists first
        log_file = f"{self.spec['logWatch']['directory']}/{self.spec['logWatch']['log']}"

        # Stat the file
        try:
            _ = self.sftp_connection.lstat(f"{log_file}")
        except FileNotFoundError:
            logger.error(f"Log file {log_file} does not exist")
            return 1
        except PermissionError:
            logger.error(f"Log file {log_file} cannot be accessed")
            return 1

        # Open the existing file and determine the number of rows
        with self.sftp_connection.open(log_file) as log_fh:
            rows = 0
            for rows, _ in enumerate(log_fh):  # noqa #B007
                pass
            logger.log(12, f"Found {rows+1} lines in log")
            self.log_watch_start_row = rows + 1

        return 0

    def do_logwatch(self):
        # Determine if the config requires scanning the entire log, or just from the start_row determine in the init function
        start_row = self.log_watch_start_row if "tail" in self.spec["logWatch"] and self.spec["logWatch"]["tail"] else 0
        logger.log(12, f"Starting logwatch from row {start_row}")

        # Open the remote log file and parse each line for the pattern
        log_file = f"{self.spec['logWatch']['directory']}/{self.spec['logWatch']['log']}"

        with self.sftp_connection.open(log_file) as log_fh:
            for i, line in enumerate(log_fh):
                # We need to start after the previous line in the log
                if i >= start_row:
                    logger.log(11, f"Log line: {line.strip()}")
                    if re.search(self.spec["logWatch"]["contentRegex"], line.strip()):
                        logger.log(12, f"Found matching line in log: {line.strip()} on line: {i+1}")
                        return 0

        return 1

    def log_stdout(self, str_stdout):
        logger.info("Remote stdout returned:")
        logger.info("###########")
        for line in str_stdout.splitlines():
            print(f"REMOTE OUTPUT: {line}")
        logger.info("###########")


class SSHExecution(RemoteExecutionHandler):
    def __init__(self, spec):
        self.spec = spec
        self.ssh_client = None
        self.log_watch_start_row = 0

        hostname = spec["hostname"]
        logger.info(f"Validating source remote host: {hostname}")

        try:
            client = SSHClient()
            client.set_missing_host_key_policy(AutoAddPolicy())
            client.connect(
                hostname,
                username=self.spec["protocol"]["credentials"]["username"],
                timeout=5,
            )
            _, stdout, _ = client.exec_command("uname -a")
            with stdout as stdout_fh:
                logger.log(11, f"Remote uname: {stdout_fh.read().decode('UTF-8')}")

            # Transfer over the transfer.py script
            local_script = f"{os.path.dirname(os.path.realpath(__file__))}/scripts/transfer.py"

            sftp = client.open_sftp()
            sftp.put(local_script, "/tmp/transfer.py")

            self.ssh_client = client
            self.sftp_connection = sftp
        except Exception as ex:
            logger.error(f"Exception while setting up remote SSH client: {ex}")

        if not self.ssh_client or not self.sftp_connection:
            logger.error(f"Failed to set up SSH client to {hostname}")
            sys.exit(1)
