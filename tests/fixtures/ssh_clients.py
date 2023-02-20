import os
import shutil
import subprocess

import pytest
from pytest_shell import fs


@pytest.fixture(scope="function")
def env_vars():
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
    fs.create_files([{"/tmp/variable_lookup.txt": {"content": "test1234"}}])


@pytest.fixture(scope="session")
def root_dir():
    # Get current working directory
    return os.path.join(os.getcwd(), "test")


@pytest.fixture(scope="session")
def docker_compose_files(root_dir):
    """Get the docker-compose.yml absolute path."""
    return [
        f"{root_dir}/docker-compose.yml",
    ]


@pytest.fixture(scope="session")
def ssh_1(docker_services):
    docker_services.start("ssh_1")
    port = docker_services.port_for("ssh_1", 22)
    address = f"{docker_services.docker_ip}:{port}"
    return address


@pytest.fixture(scope="session")
def ssh_2(docker_services):
    docker_services.start("ssh_2")
    port = docker_services.port_for("ssh_2", 22)
    address = f"{docker_services.docker_ip}:{port}"
    return address


@pytest.fixture(scope="session")
def test_directories(root_dir):
    # Get the root directory of the project

    structure = [
        f"{root_dir}/testFiles/ssh_1/ssh",
        f"{root_dir}/testFiles/ssh_1/src",
        f"{root_dir}/testFiles/ssh_1/dest",
        f"{root_dir}/testFiles/ssh_1/archive",
        f"{root_dir}/testFiles/ssh_2/ssh",
        f"{root_dir}/testFiles/ssh_2/src",
        f"{root_dir}/testFiles/ssh_2/dest",
        f"{root_dir}/testFiles/ssh_2/archive",
    ]
    fs.create_files(structure)


@pytest.fixture(scope="session")
def setup_ssh_keys(docker_services, root_dir, test_directories, ssh_1, ssh_2):
    # Run command locally
    # if ssh key dosent exist yet
    ssh_private_key_file = f"{root_dir}/testFiles/id_rsa"
    if not os.path.isfile(ssh_private_key_file):
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-N", "", "-f", ssh_private_key_file]
        ).returncode

        # Copy the file into the ssh directory for each host
        for i in ["1", "2"]:
            shutil.copy(
                ssh_private_key_file, f"{root_dir}/testFiles/ssh_{i}/ssh/id_rsa"
            )
            shutil.copy(
                f"{root_dir}/testFiles/id_rsa.pub",
                f"{root_dir}/testFiles/ssh_{i}/ssh/authorized_keys",
            )

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
