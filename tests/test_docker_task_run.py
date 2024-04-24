# pylint: skip-file
# ruff: noqa
import logging
import os
import random
import shutil
import subprocess

import pytest
from pytest_shell import fs

from tests.fixtures.ssh_clients import *  # noqa: F403

IMAGE_PREFIX = "opentaskpy_unittest"
MOVED_FILES_DIR = "archive"
DELIMITER = ","

"""
#################
Tests for running task-run via a docker container
#################
"""

# Get the current user and group id
user_id = os.getuid()
group_id = os.getgid()


@pytest.fixture(scope="module")
def image_name_dev():
    return f"{IMAGE_PREFIX}_dev_{random.randint(100000, 999999)}"


@pytest.fixture(scope="module")
def image_name():
    return f"{IMAGE_PREFIX}_{random.randint(100000, 999999)}"


@pytest.fixture(scope="module")
def tidy_images(root_dir):
    # Remove all images with the prefix
    result = subprocess.run(
        [
            "docker",
            "images",
            f"{IMAGE_PREFIX}_*",
        ],
        capture_output=True,
    )
    if result.stdout:
        images = result.stdout.decode("utf-8").split("\n")
        # Split the repository name from the rest of the line
        image_ids = [image.split(" ")[0] for image in images if image]
        for image_id in image_ids:
            # If this image name matches the prefix, remove it
            if image_id.startswith(IMAGE_PREFIX):
                logging.info(f"Removing image: {image_id}")
                result = subprocess.run(
                    [
                        "docker",
                        "rmi",
                        image_id,
                    ],
                    capture_output=True,
                )
                logging.info(result.stdout.decode("utf-8"))
                logging.info(result.stderr.decode("utf-8"))
    else:
        logging.info("No images to remove")


@pytest.fixture(scope="module")
def docker_build_dev_image(tidy_images, image_name_dev, root_dir):
    logging.info("Building dev docker image")
    logging.info(root_dir)

    # Trigger docker build
    command_args = [
        "docker",
        "build",
        "-t",
        image_name_dev,
        "-f",
        "Dockerfile.dev",
        f"{root_dir}/..",
    ]
    result = subprocess.run(
        command_args,
        capture_output=True,
    )
    assert result.returncode == 0


@pytest.fixture(scope="module")
def docker_build_image(tidy_images, image_name, root_dir):
    logging.info("Building docker image")
    logging.info(root_dir)

    # Trigger docker build
    command_args = [
        "docker",
        "build",
        "-t",
        image_name,
        "-f",
        "Dockerfile",
        f"{root_dir}/..",
    ]
    result = subprocess.run(
        command_args,
        capture_output=True,
    )
    assert result.returncode == 0


@pytest.fixture(scope="module")
def test_network_id():
    # Get the webdevops/ssh container that's running, and determine the network it's attached to
    result = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            "name=^ssh_1",
            "--format",
            "{{.Networks}}",
        ],
        capture_output=True,
    )
    assert result.returncode == 0

    # We need to extract the network name
    network = result.stdout.decode("utf-8").strip()

    # Get the network ID
    result = subprocess.run(
        [
            "docker",
            "network",
            "inspect",
            network,
            "--format",
            "{{.Id}}",
        ],
        capture_output=True,
    )
    assert result.returncode == 0
    return result.stdout.decode("utf-8").strip()


@pytest.fixture(scope="module")
def log_dir(root_dir):
    return f"{root_dir}/testLogs"


@pytest.fixture(scope="function")
def clear_logs(log_dir):
    # Delete the output log directory
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)

    # Create an empty directory for the logs
    os.makedirs(log_dir, exist_ok=True)
    # Check the directory exists
    assert os.path.exists(log_dir)


@pytest.fixture(scope="function")
def create_test_file(root_dir):
    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/text.txt": {"content": "test1234"}}]
    )


def test_docker_run(
    setup_ssh_keys,
    docker_build_dev_image,
    test_network_id,
    image_name_dev,
    root_dir,
    env_vars,
    clear_logs,
    create_test_file,
):
    # Create the testLogs directory
    log_dir = f"{root_dir}/testLogs"
    os.makedirs(log_dir, exist_ok=True)

    # Run the container
    logging.info("Running docker container")
    command_args = [
        "docker",
        "run",
        "--rm",
        "--user",
        f"{user_id}:{group_id}",
        "--network",
        test_network_id,
        "--volume",
        f"{root_dir}:/test",
        "--volume",
        f"{log_dir}:/logs",
        "--volume",
        "/tmp/variable_lookup.txt:/tmp/variable_lookup.txt",
        "-e",
        "OTF_SSH_KEY=/test/testFiles/id_rsa",
        image_name_dev,
        "task-run",
        "-t",
        "scp-basic",
        "-v",
        "2",
        "-c",
        "/test/cfg",
    ]

    result = subprocess.run(
        command_args,
        capture_output=True,
    )
    logging.info(result.stdout.decode("utf-8"))
    logging.info(result.stderr.decode("utf-8"))

    assert result.returncode == 0


def test_standard_docker_image(
    setup_ssh_keys,
    docker_build_image,
    test_network_id,
    image_name,
    root_dir,
    log_dir,
    env_vars,
    clear_logs,
    create_test_file,
):
    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/text.txt": {"content": "test1234"}}]
    )

    # This image pulls down whatever is on pypi, so we're not really testing the code here. Just that we can call a simple transfer.
    # We want to check that the logging works correctly when running in a docker container and mapping volumes
    # Run the container
    logging.info("Running docker container")
    command_args = [
        "docker",
        "run",
        "--rm",
        "--user",
        f"{user_id}:{group_id}",
        "--network",
        test_network_id,
        "--volume",
        f"{root_dir}:/test",
        "--volume",
        "/tmp/variable_lookup.txt:/tmp/variable_lookup.txt",
        "--volume",
        f"{root_dir}/testLogs:/logs",
        "--env",
        "OTF_RUN_ID=docker_log_test",
        image_name,
        "task-run",
        "-t",
        "scp-basic",
        "-v",
        "2",
        "-c",
        "/test/cfg",
    ]
    logging.info(" ".join(command_args))

    subprocess.run(
        command_args,
        capture_output=True,
    )
    # We dont care whether this worked or not, we just want to check the logs
    # Check that the log file exists containing scp-basic in the name in log_dir
    log_files = os.listdir(f"{log_dir}/docker_log_test")
    assert len(log_files) == 1
    assert "scp-basic" in log_files[0]
