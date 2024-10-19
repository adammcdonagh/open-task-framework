"""Utility functions for SSH."""

from logging import Logger

from paramiko import AutoAddPolicy, SSHClient


def setup_host_key_validation(client: SSHClient, spec: dict, logger: Logger) -> None:
    """Set up host key validation for an SSH client.

    Args:
        client (SSHClient): The SSH client to set up.
        spec (dict): The spec for the SSH connection.
        logger (logging.Logger): The logger to use.
    """
    logger.info("Loading system host keys")
    client.load_system_host_keys()

    if (
        "hostKeyValidation" in spec["protocol"]
        and spec["protocol"]["hostKeyValidation"]
    ):
        if "knownHostsFile" in spec["protocol"]:
            host_key = spec["protocol"]["knownHostsFile"]
            logger.info(f"Loading host keys from {host_key}")
            client.load_host_keys(host_key)
    else:
        client.set_missing_host_key_policy(AutoAddPolicy())
