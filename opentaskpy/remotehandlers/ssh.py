import logging
import json
import os
import sys
import re
from paramiko import SSHClient, AutoAddPolicy
logger = logging.getLogger("opentaskpy.remotehandlers.ssh")

SSH_OPTIONS = "-o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=5"


class SSH:
    def __init__(self, spec, remote_spec=None):
        self.spec = spec
        self.ssh_client = None
        self.sftp_connection = None
        self.remote_spec = remote_spec

        # We need to copy the required remote scripts to the source and destination (if applicable) hosts
        hostname = spec['hostname']
        logger.info(
            f"Validating source remote host: {hostname}")

        try:
            client = SSHClient()
            client.set_missing_host_key_policy(AutoAddPolicy())
            client.connect(hostname, username=self.spec["protocol"]["credentials"]["username"],
                           password=self.spec["protocol"]["credentials"]["password"], timeout=5)
            stdin, stdout, stderr = client.exec_command("uname -a")
            with stdout as stdout_fh:
                logger.log(
                    11, f"Remote uname: {stdout_fh.read().decode('UTF-8')}")

            # Transfer over the transfer.py script
            local_script = f"{os.path.dirname(os.path.realpath(__file__))}/scripts/transfer.py"

            sftp = client.open_sftp()
            sftp.put(local_script, '/tmp/transfer.py')

            self.ssh_client = client
            self.sftp_connection = sftp
        except Exception as ex:
            logger.error(
                f"Exception while setting up remote SSH client: {ex}")

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

            logging.debug(f"Closing SSH connection to {self.spec['hostname']}")
            self.ssh_client.close()

    def get_staging_directory(self):
        return self.remote_spec["stagingDirectory"] if "stagingDirectory" in self.remote_spec else f"~/otf/{os.environ['OTF_TASK_ID']}/"

    # Determine the list of files that match the source definition
    # List remote files based on the source file pattern

    def list_files(self):

        remote_files = dict()
        remote_file_list = self.sftp_connection.listdir(self.spec['directory'])
        for file in list(remote_file_list):
            if re.match(f"{self.spec['fileRegex']}", file):
                # Get the file attributes
                file_attr = self.sftp_connection.lstat(f"{self.spec['directory']}/{file}")
                logger.log(12, f"File attributes {file_attr}")
                remote_files[f"{self.spec['directory']}/{file}"] = {
                    "size": file_attr.st_size,
                    "modified_time": file_attr.st_mtime
                }
        # remote_command = f"python3 /tmp/transfer.py --listFiles '{self.spec['directory']}/{self.spec['fileRegex']}' --details"
        # logger.log(12, f"Running: {remote_command}")

        # remote_files = None
        # stdin, stdout, stderr = self.ssh_client.exec_command(remote_command)
        # with stdout as stdout_fh:
        #     str_stdout = stdout_fh.read().decode('UTF-8')
        #     logger.log(
        #         12, f"Remote command returned:\n{str_stdout}")
        #     remote_files = json.loads(str_stdout)

        return remote_files

    def transfer_files(self, files, dest_client):
        # Construct an SCP command to transfer the files to the destination server
        remote_user = self.remote_spec["protocol"]["credentials"]["transferUsername"] if "transferUsername" in self.remote_spec["protocol"]["credentials"] else self.remote_spec["protocol"]["credentials"]["username"]
        remote_host = self.remote_spec["hostname"]
        # Handle staging directory if there is one
        destination_directory = self.get_staging_directory()

        # Create/validate staging directory exists on destination
        remote_command = f'test -e {destination_directory} || mkdir -p {destination_directory}'
        logging.info(f"Validating staging dir via SSH: {remote_command}")
        stdin, stdout, stderr = dest_client.exec_command(remote_command)
        with stdout as stdout_fh:
            str_stdout = stdout_fh.read().decode('UTF-8')
            if str_stdout:
                logger.info(f"Remote stdout returned:\n{str_stdout}")

        with stderr as stderr_fh:
            str_stderr = stderr_fh.read().decode('UTF-8')
            if str_stderr:
                logger.error(f"Remote stderr returned:\n{str_stderr}")

        remote_rc = stdout.channel.recv_exit_status()
        logger.info(f"Got return code {remote_rc} from SSH command")

        remote_command = f'scp {SSH_OPTIONS} {"".join(files)} {remote_user}@{remote_host}:"{destination_directory}"'
        logging.info(f"Transferring files via SCP: {remote_command}")

        stdin, stdout, stderr = self.ssh_client.exec_command(remote_command)

        with stdout as stdout_fh:
            str_stdout = stdout_fh.read().decode('UTF-8')
            if str_stdout:
                logger.info(f"Remote stdout returned:\n{str_stdout}")

        with stderr as stderr_fh:
            str_stderr = stderr_fh.read().decode('UTF-8')
            if str_stderr:
                logger.error(f"Remote stderr returned:\n{str_stderr}")

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
        remote_command = f'test -e {destination_directory} || mkdir -p {destination_directory}'
        logging.info(f"Validating staging dir via SSH: {remote_command}")
        stdin, stdout, stderr = self.ssh_client.exec_command(remote_command)
        with stdout as stdout_fh:
            str_stdout = stdout_fh.read().decode('UTF-8')
            if str_stdout:
                logger.info(f"Remote stdout returned:\n{str_stdout}")

        with stderr as stderr_fh:
            str_stderr = stderr_fh.read().decode('UTF-8')
            if str_stderr:
                logger.error(f"Remote stderr returned:\n{str_stderr}")

        remote_rc = stdout.channel.recv_exit_status()
        logger.info(f"Got return code {remote_rc} from SSH command")

        files_str = ""
        for file in files:
            files_str += f"{source_user}@{source_host}:{file} "

        remote_command = f'scp {SSH_OPTIONS} {files_str.strip()} {destination_directory}'
        logging.info(f"Transferring files via SCP: {remote_command}")

        stdin, stdout, stderr = self.ssh_client.exec_command(remote_command)

        with stdout as stdout_fh:
            str_stdout = stdout_fh.read().decode('UTF-8')
            if str_stdout:
                logger.info(f"Remote stdout returned:\n{str_stdout}")

        with stderr as stderr_fh:
            str_stderr = stderr_fh.read().decode('UTF-8')
            if str_stderr:
                logger.error(f"Remote stderr returned:\n{str_stderr}")

        remote_rc = stdout.channel.recv_exit_status()
        logger.info(f"Got return code {remote_rc} from SCP command")

        return remote_rc

    def move_files_to_final_location(self, files):

        # Convert all the source file names into the filename with the destination directory as a prefix
        file_names_str = ""
        for file in list(files):
            file_names_str += f"{self.get_staging_directory()}{os.path.basename(file)} "
        file_names_str = file_names_str.strip()

        # Next step is to move the file to it's final resting place with the correct permissions and ownership
        # Build a commnd to pass to the remote transfer.py to do the work
        owner_args = f"--owner {self.spec['permissions']['owner']}" if "permissions" in self.spec and "owner" in self.spec[
            "permissions"] else ""
        group_args = f"--group {self.spec['permissions']['group']}" if "permissions" in self.spec and "group" in self.spec[
            "permissions"] else ""
        mode_args = f"--mode {self.spec['mode']}" if "mode" in self.spec else ""
        rename_args = f"--renameRegex '{self.spec['rename']['pattern']}' --renameSub '{self.spec['rename']['sub']}'" if "rename" in self.spec else ""
        remote_command = f"python3 /tmp/transfer.py --moveFiles '{file_names_str}' --destination {self.spec['directory']} {owner_args} {group_args} {mode_args} {rename_args}"
        logger.log(12, f"Running: {remote_command}")

        stdin, stdout, stderr = self.ssh_client.exec_command(remote_command)

        with stdout as stdout_fh:
            str_stdout = stdout_fh.read().decode('UTF-8')
            if str_stdout:
                logger.info(f"Remote stdout returned:\n{str_stdout}")

        with stderr as stderr_fh:
            str_stderr = stderr_fh.read().decode('UTF-8')
            if str_stderr:
                logger.error(f"Remote stderr returned:\n{str_stderr}")

        remote_rc = stdout.channel.recv_exit_status()
        logger.info(f"Got return code {remote_rc} from SSH move command")
        return remote_rc

    def handle_post_copy_action(self, files):
        remote_command = None
        if self.spec["postCopyAction"]["action"] == "delete":
            remote_command = f"python3 /tmp/transfer.py --deleteFiles '{' '.join(files)}'"
        if self.spec["postCopyAction"]["action"] == "move":
            remote_command = f"python3 /tmp/transfer.py --moveFiles '{' '.join(files)}' --destination {self.spec['postCopyAction']['destination']}"

        if remote_command:
            logger.log(12, f"Running: {remote_command}")

            stdin, stdout, stderr = self.ssh_client.exec_command(remote_command)

            with stdout as stdout_fh:
                str_stdout = stdout_fh.read().decode('UTF-8')
                if str_stdout:
                    logger.info(f"Remote stdout returned:\n{str_stdout}")

            with stderr as stderr_fh:
                str_stderr = stderr_fh.read().decode('UTF-8')
                if str_stderr:
                    logger.error(f"Remote stderr returned:\n{str_stderr}")

            remote_rc = stdout.channel.recv_exit_status()
            logger.info(f"Got return code {remote_rc} from SSH post copy action command")
            return remote_rc
