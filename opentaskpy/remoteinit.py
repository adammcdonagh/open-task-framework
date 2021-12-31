from paramiko import SSHClient, AutoAddPolicy
import logging
import os
import sys

logger = logging.getLogger("opentaskpy.remoteinit")

# Handles the validation of the remote hosts


def validate_remote_host(hostname, protocol):
    logger.log(11, "Remote setup")

    if protocol["name"] == "ssh":
        logger.info("Using SSH")
        # Check that we can establish a connection to the remote host, and if so, return that connection
        try:
            client = SSHClient()
            client.set_missing_host_key_policy(AutoAddPolicy())
            client.connect(hostname, username=protocol["credentials"]
                           ["username"], password=protocol["credentials"]["password"], timeout=5)
            stdin, stdout, stderr = client.exec_command("uname -a")
            with stdout as stdout_fh:
                logger.log(
                    11, f"Remote uname: {stdout_fh.read().decode('UTF-8')}")

            # Transfer over the transfer.py script
            local_script = f"{os.path.dirname(os.path.realpath(__file__))}/remotehandlers/scripts/transfer.py"

            sftp = client.open_sftp()
            sftp.put(local_script, '/tmp/transfer.py')
            sftp.close()
        except Exception as ex:
            logging.error(
                f"Exception while setting up remote SSH client: {ex}")
            return None

        return client
