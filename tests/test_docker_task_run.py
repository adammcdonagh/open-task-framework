import random
import subprocess

import pytest
from fixtures.ssh_clients import *  # noqa:F401

IMAGE_PREFIX = "opentaskpy_unittest"
MOVED_FILES_DIR = "archive"
DELIMITER = ","

"""
#################
Tests for running task-run via a docker container
#################
"""


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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.stdout:
        images = result.stdout.decode("utf-8").split("\n")
        # Split the repository name from the rest of the line
        image_ids = [image.split(" ")[0] for image in images if image]
        for image_id in image_ids:
            # If this image name matches the prefix, remove it
            if image_id.startswith(IMAGE_PREFIX):
                print(f"Removing image: {image_id}")
                result = subprocess.run(
                    [
                        "docker",
                        "rmi",
                        image_id,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                print(result.stdout.decode("utf-8"))
                print(result.stderr.decode("utf-8"))
    else:
        print("No images to remove")


@pytest.fixture(scope="module")
def docker_build_dev_image(tidy_images, image_name_dev, root_dir):
    print("Building dev docker image")
    print(root_dir)

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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 0


@pytest.fixture(scope="module")
def docker_build_image(tidy_images, image_name, root_dir):
    print("Building docker image")
    print(root_dir)

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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 0


@pytest.fixture(scope="module")
def test_network_id():
    # Get the webdevops/ssh container thats running, and determine the network it's attached to
    result = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            "name=^ssh_1",
            "--format",
            "{{.Networks}}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 0
    return result.stdout.decode("utf-8").strip()


def test_docker_run(
    setup_ssh_keys,
    docker_build_dev_image,
    test_network_id,
    image_name_dev,
    root_dir,
    env_vars,
):
    # Run the container
    print("Running docker container")
    command_args = [
        "docker",
        "run",
        "--rm",
        "--network",
        test_network_id,
        "--volume",
        f"{root_dir}:/test",
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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print(result.stdout.decode("utf-8"))
    print(result.stderr.decode("utf-8"))
    assert result.returncode == 0


def test_standard_docker_image(
    setup_ssh_keys,
    docker_build_image,
    test_network_id,
    image_name,
    root_dir,
    env_vars,
):
    # Delete the output log directory
    log_dir = f"{root_dir}/testLogs/docker_log_test"
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)

    # This image pulls down whatever is on pypi, so we're not really testing the code here. Just that we can call a simple transfer.
    # We want to check that the logging works correctly when running in a docker container and mapping volumes
    # Run the container
    print("Running docker container")
    command_args = [
        "docker",
        "run",
        "--rm",
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
    print(" ".join(command_args))

    subprocess.run(
        command_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # We dont care whether this worked or not, we just want to check the logs
    # Check that the log file exists containing scp-basic in the name in log_dir
    log_files = os.listdir(log_dir)
    assert len(log_files) == 1
    assert "scp-basic" in log_files[0]
