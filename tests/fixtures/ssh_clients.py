# pylint: skip-file
# ruff: noqa
import contextlib
import os
import shutil
import subprocess

import pytest
from pytest_shell import fs


@pytest.fixture(scope="function")
def env_vars() -> None:
    # Ensure all custom env vars are
    if "OTF_LOG_DIRECTORY" in os.environ:
        del os.environ["OTF_LOG_DIRECTORY"]
    if "OTF_LOG_RUN_PREFIX" in os.environ:
        del os.environ["OTF_LOG_RUN_PREFIX"]
    if "OTF_RUN_ID" in os.environ:
        del os.environ["OTF_RUN_ID"]
    if "OTF_NO_LOG" in os.environ:
        del os.environ["OTF_NO_LOG"]

    # We're using the proper config file for this, so we need to make sure something exist in /tmp/variable_lookup.txt
    fs.create_files(
        [
            {"/tmp/variable_lookup.txt": {"content": "test1234"}},
            {"/tmp/public_key_1.txt": {"content": "test1234"}},
            {"/tmp/public_key_2.txt": {"content": "test1234"}},
            {"/tmp/public_key_1.txt": {"content": "test1234"}},
            {"/tmp/private_key_2.txt": {"content": "test1234"}},
        ]
    )


@pytest.fixture(scope="session")
def root_dir() -> str:
    # Get current working directory
    return os.path.join(os.getcwd(), "test")


@pytest.fixture(scope="session")
def top_level_root_dir() -> str:
    # Get current working directory
    return os.getcwd()


@pytest.fixture(scope="session")
def docker_compose_files(root_dir) -> list[str]:
    """Get the docker-compose.yml absolute path."""
    return [
        f"{root_dir}/docker-compose.yml",
    ]


@pytest.fixture(scope="session")
def ssh_1(docker_services) -> str:
    docker_services.start("ssh_1")
    port = docker_services.port_for("ssh_1", 22)
    address = f"{docker_services.docker_ip}:{port}"
    return address


@pytest.fixture(scope="session")
def ssh_2(docker_services) -> str:
    docker_services.start("ssh_2")
    port = docker_services.port_for("ssh_2", 22)
    address = f"{docker_services.docker_ip}:{port}"
    return address


@pytest.fixture(scope="session")
def sftp_1(docker_services) -> str:
    docker_services.start("sftp_1")
    port = docker_services.port_for("sftp_1", 22)
    address = f"{docker_services.docker_ip}:{port}"
    return address


@pytest.fixture(scope="session")
def sftp_2(docker_services) -> str:
    docker_services.start("sftp_2")
    port = docker_services.port_for("sftp_2", 22)
    address = f"{docker_services.docker_ip}:{port}"
    return address


@pytest.fixture(scope="session")
def test_directories(root_dir) -> None:
    # Get the root directory of the project

    hosts = ["1", "2"]
    protocols = ["ssh", "sftp"]
    # Create the directory structure
    structure = []
    for host in hosts:
        for protocol in protocols:
            structure.append(f"{root_dir}/testFiles/{protocol}_{host}")
            structure.append(f"{root_dir}/testFiles/{protocol}_{host}/ssh")
            structure.append(f"{root_dir}/testFiles/{protocol}_{host}/dest")
            structure.append(f"{root_dir}/testFiles/{protocol}_{host}/archive")

    fs.create_files(structure)


@pytest.fixture(scope="session")
def setup_ssh_keys(docker_services, root_dir, test_directories, ssh_1, ssh_2) -> None:
    # Run command locally
    # if ssh key doesn't exist yet
    ssh_private_key_file = f"{root_dir}/testFiles/id_rsa"
    # Load the ssh key and validate it
    from paramiko import RSAKey

    key = None
    with contextlib.suppress(Exception):
        key = RSAKey.from_private_key_file(ssh_private_key_file)

    if not os.path.isfile(ssh_private_key_file) or not key:
        # If it exists, delete it first
        if os.path.isfile(ssh_private_key_file):
            os.remove(ssh_private_key_file)
        # Generate the key
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-N", "", "-f", ssh_private_key_file]
        ).returncode

    # Copy the file into the ssh directory for each host
    for i in ["1", "2"]:
        shutil.copy(ssh_private_key_file, f"{root_dir}/testFiles/ssh_{i}/ssh/id_rsa")
        shutil.copy(
            f"{root_dir}/testFiles/id_rsa.pub",
            f"{root_dir}/testFiles/ssh_{i}/ssh/authorized_keys",
        )

    # Copy the file into the ssh directory on this host
    # Current user's home directory
    home_dir = os.path.expanduser("~")
    # Make the .ssh directory if it doesn't exist
    if not os.path.isdir(f"{home_dir}/.ssh"):
        os.mkdir(f"{home_dir}/.ssh")

    shutil.copy(ssh_private_key_file, f"{home_dir}/.ssh/id_rsa")

    # Run the docker exec command to create the user
    # Get the current uid for the running process
    uid = str(os.getuid())
    # commands to run
    commands = [
        ("usermod", "-G", "operator", "-a", "application", "-u", uid),
        ("mkdir", "-p", "/home/application/.ssh"),
        ("cp", "/tmp/testFiles/ssh/id_rsa", "/home/application/.ssh"),
        (
            "cp",
            "/tmp/testFiles/ssh/authorized_keys",
            "/home/application/.ssh/authorized_keys",
        ),
        ("chown", "-R", "application", "/home/application/.ssh"),
        ("chmod", "-R", "700", "/home/application/.ssh"),
        ("chown", "-R", "application", "/tmp/testFiles"),
    ]
    for host in ["ssh_1", "ssh_2"]:
        for command in commands:
            docker_services.execute(host, *command)


@pytest.fixture(scope="session")
def ssh_key_file(setup_ssh_keys):
    home_dir = os.path.expanduser("~")

    key = None
    with open(f"{home_dir}/.ssh/id_rsa") as file:
        key = file.read()

    return key


@pytest.fixture(scope="session")
def setup_sftp_keys(
    docker_services, root_dir, test_directories, sftp_1, sftp_2
) -> None:
    # Run command locally
    # if ssh key doesn't exist yet
    ssh_private_key_file = f"{root_dir}/testFiles/id_rsa"
    # Load the ssh key and validate it
    from paramiko import RSAKey

    key = None
    with contextlib.suppress(Exception):
        key = RSAKey.from_private_key_file(ssh_private_key_file)

    if not os.path.isfile(ssh_private_key_file) or not key:
        # If it exists, delete it first
        if os.path.isfile(ssh_private_key_file):
            os.remove(ssh_private_key_file)
        # Generate the key
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-N", "", "-f", ssh_private_key_file]
        ).returncode

    # Copy the file into the ssh directory for each host
    for i in ["1", "2"]:
        shutil.copy(ssh_private_key_file, f"{root_dir}/testFiles/sftp_{i}/ssh/id_rsa")
        shutil.copy(
            f"{root_dir}/testFiles/id_rsa.pub",
            f"{root_dir}/testFiles/sftp_{i}/ssh/authorized_keys",
        )

    # Copy the file into the ssh directory on this host
    # Current user's home directory
    home_dir = os.path.expanduser("~")
    # Make the .ssh directory if it doesn't exist
    if not os.path.isdir(f"{home_dir}/.ssh"):
        os.mkdir(f"{home_dir}/.ssh")

    shutil.copy(ssh_private_key_file, f"{home_dir}/.ssh/id_rsa")

    # Run the docker exec command to create the user
    # Get the current uid for the running process
    uid = str(os.getuid())
    # commands to run
    commands = [
        ("usermod", "-G", "operator", "-a", "application", "-u", uid),
        ("mkdir", "-p", "/home/application/.ssh"),
        ("cp", "/home/application/testFiles/ssh/id_rsa", "/home/application/.ssh"),
        (
            "cp",
            "/home/application/testFiles/ssh/authorized_keys",
            "/home/application/.ssh/authorized_keys",
        ),
        ("chown", "-R", "application", "/home/application/.ssh"),
        ("chmod", "-R", "700", "/home/application/.ssh"),
        ("mkdir", "-p", "/sftp/application"),
    ]
    for host in ["sftp_1", "sftp_2"]:
        for command in commands:
            docker_services.execute(host, *command)


@pytest.fixture(scope="session")
def sftp_key_file(setup_sftp_keys):
    home_dir = os.path.expanduser("~")

    key = None
    with open(f"{home_dir}/.ssh/id_rsa") as file:
        key = file.read()

    return key
