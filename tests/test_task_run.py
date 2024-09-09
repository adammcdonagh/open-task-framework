# pylint: skip-file
# ruff: noqa
import ctypes
import datetime
import json
import logging
import os
import random
import subprocess
import threading
import time

import pytest
from pytest_shell import fs

from opentaskpy import taskrun
from tests.fixtures.ssh_clients import *  # noqa: F403

# Create a variable with a random number
RANDOM = random.randint(10000, 99999)
FILE_PREFIX = "unittest_task_run"
MOVED_FILES_DIR = "archive"
DELIMITER = ","

"""
#################
Tests for the "binary" task runner
#################
"""

# Setup logger so we can see the stdout and err from the binary
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)


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


def test_lazy_load_performance(env_vars, tmpdir):
    # Dont run on GITHUB actions
    if os.getenv("GITHUB_ACTIONS"):
        return

    # Create a variables file with 5000 different dynamic variables using the random number addon

    # This point of this test is to prove that loading lots of variables that aren't used is slower
    # that loading just the variable that is used. This is very hard to do with a unit test, so there's
    # no assertion on the time. It's more to prove the concept.

    # Having lots of different tasks that lookup variables that are not used by that task adds unnecessary
    # overhead to the task run, and risks failures for no reason if the variable is not used by the task.

    file_content_json = {}
    for i in range(1, 5001):
        file_content_json[f"test{i}"] = "{{ lookup('random_number', min=1, max=100) }}"

    task_definition = {
        "type": "transfer",
        "source": {
            "directory": "/tmp",
            "fileRegex": ".*",
            "protocol": {"name": "local"},
        },
        "destination": [],
    }
    fs.create_files(
        [{f"{tmpdir}/test-task1.json.j2": {"content": json.dumps(task_definition)}}]
    )

    fs.create_files(
        [{f"{tmpdir}/variables.json.j2": {"content": json.dumps(file_content_json)}}]
    )

    # Create a batch task definition
    batch_task_definition = {
        "type": "batch",
        "tasks": [
            {"order_id": i, "task_id": "test-task1", "timeout": 60} for i in range(1, 5)
        ],
    }
    fs.create_files(
        [
            {
                f"{tmpdir}/batch-task.json.j2": {
                    "content": json.dumps(batch_task_definition)
                }
            }
        ]
    )

    # Get the current time in milliseconds
    current_time_ms = time.time_ns() / 1000000

    # Run the binary
    result = subprocess.run(
        [
            "python",
            "src/opentaskpy/cli/task_run.py",
            "-t",
            "batch-task",
            "-r",
            "test-lazy-performance-no-lazy",
            "-v",
            "3",
            "-c",
            tmpdir,
        ],
        capture_output=True,
    )

    # Check the return code
    assert result.returncode == 0

    # Get the time in milliseconds after the task run
    end_time_ms = time.time_ns() / 1000000

    # Calculate the time taken to run the task
    time_taken_ms = end_time_ms - current_time_ms

    # Set the OTF_LAZY_LOAD_VARIABLES environment variable
    os.environ["OTF_LAZY_LOAD_VARIABLES"] = "1"

    current_time_ms = time.time_ns() / 1000000

    # Run the binary again
    result = subprocess.run(
        [
            "python",
            "src/opentaskpy/cli/task_run.py",
            "-t",
            "batch-task",
            "-r",
            "test-lazy-performance-with-lazy",
            "-v",
            "3",
            "-c",
            tmpdir,
        ],
        capture_output=True,
    )

    # Check the return code
    assert result.returncode == 0

    # Get the time in milliseconds after the task run
    end_time_ms = time.time_ns() / 1000000

    # Calculate the time taken to run the task
    time_taken_ms_lazy = end_time_ms - current_time_ms

    # Check that the time taken to run the task is more than the time taken without lazy loading
    print(f"Time taken without lazy loading: {time_taken_ms} ms")
    print(f"Time taken with lazy loading: {time_taken_ms_lazy} ms")


def test_noop_binary(env_vars, setup_ssh_keys, root_dir):
    # Pass noop argument to the binary

    # Delete the destination file in case something else copied it
    if os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/noop_test.txt"):
        os.remove(f"{root_dir}/testFiles/ssh_2/dest/noop_test.txt")

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/noop_test.txt": {"content": "test1234"}}]
    )

    assert run_task_run("scp-basic", noop=True)["returncode"] == 0

    # Verify that the file has not been transferred
    assert not os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/noop_test.txt")

    # Override the variables config location and verify we get an error
    assert run_task_run("scp-basic", config="/tmp/non-existent")["returncode"] == 1

    # Verify a --noop runs for an execution too

    # Use the touch example
    touched_file = f"{root_dir}/testFiles/ssh_1/src/touchedFile.txt"
    # Delete if it already exists
    if os.path.exists(touched_file):
        os.remove(touched_file)

    assert run_task_run("touch", noop=True)["returncode"] == 0
    # Verify the file still doesn't exist
    assert not os.path.exists(touched_file)


def test_scp_basic_binary(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/text.txt": {"content": "test1234"}}]
    )

    assert run_task_run("scp-basic")["returncode"] == 0


def test_scp_basic_no_error_on_exit_binary(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    assert run_task_run("scp-basic-no-error")["returncode"] == 0


def test_scp_basic_no_error_on_exit_binary_1(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    assert run_task_run("scp-basic-no-error-1")["returncode"] == 0


def test_execution_basic_binary(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    assert run_task_run("df")["returncode"] == 0


def test_execution_invalid_host(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    assert run_task_run("df-invalid-host")["returncode"] == 1


def test_batch_basic_binary(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    assert run_task_run("batch-basic")["returncode"] == 0


def test_transfer_local_binary(env_vars, root_dir):
    # Create a test_basic_local.txt file in /tmp/src
    fs.create_files([{"/tmp/src/test_basic_local.txt": {"content": "test1234"}}])
    # Ensure /tmp/dest exists
    if not os.path.exists("/tmp/dest"):
        os.makedirs("/tmp/dest")

    # Use the "binary" to trigger the job with command line arguments
    assert run_task_run("local-basic")["returncode"] == 0


def test_batch_execution_invalid_host(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    assert run_task_run("batch-basic-invalid-execution-host")["returncode"] == 1


def test_binary_invalid_config_file(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    assert run_task_run("scp-basic-non-existent")["returncode"] == 1
    # Check the output indicates that the task could not be found
    assert "Couldn't find task with name: scp-basic-non-existent" in (
        run_task_run("scp-basic-non-existent")["stderr"]
    )


def test_binary_invalid_config_directory(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    result = run_task_run("scp-basic", config="/tmp/non-existent")
    assert result["returncode"] == 1
    # Check the output indicates that no variables could be loaded
    assert "Couldn't find any variables" in (result["stderr"])


class thread_with_exception(threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self)
        self.name = name

    def run(self):

        import socket

        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to the address
        server_address = ("localhost", 1234)
        sock.bind(server_address)
        # Listen for incoming connections
        sock.listen(1)

    def get_id(self):

        # returns id of the respective thread
        if hasattr(self, "_thread_id"):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def raise_exception(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            thread_id, ctypes.py_object(SystemExit)
        )
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print("Exception raise failure")


def test_binary_sftp_timeout(env_vars, setup_ssh_keys, root_dir):

    # Start a new thread, listening in port 1234 that does nothing listen on the port and accept connections
    # This will cause the sftp connection to timeout
    t = thread_with_exception("Dummy socket")
    t.start()

    # Use the "binary" to trigger the job with command line arguments
    assert run_task_run("sftp-timeout")["returncode"] == 1

    # Kill the thread
    t.raise_exception()

    # Check the logs directory for the most recent log files in the sftp-timeout sub
    # directory, there should be 2, both with _failed.log at the end of the filename
    log_files = os.listdir("logs/sftp-timeout")

    # Find the most recent 2 log files
    log_files = sorted(
        log_files,
        key=lambda x: os.path.getmtime(f"logs/sftp-timeout/{x}"),
        reverse=True,
    )[:2]
    # Check that they both have the same starting timestamp up to the _
    assert log_files[0].split("_")[0] == log_files[1].split("_")[0]

    # Check they both end with _failed
    for file in log_files:
        assert "_failed.log" in file


"""
#################
Tests using the Python code directly
#################
"""


def test_unknown_task_name(env_vars, setup_ssh_keys, root_dir):
    task_runner = taskrun.TaskRun("non-existent", "test/cfg")

    # Verify an exception with appropriate text is thrown
    with pytest.raises(FileNotFoundError) as e:
        task_runner.run()
    assert e.value.args[0] == "Couldn't find task with name: non-existent"


def test_batch_basic(env_vars, setup_ssh_keys, root_dir):
    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    # Use the TaskRun class to trigger the job properly
    task_runner = taskrun.TaskRun("batch-basic", "test/cfg")
    assert task_runner.run()


def test_execution_basic(env_vars, setup_ssh_keys, root_dir):
    # Use the TaskRun class to trigger the job properly
    task_runner = taskrun.TaskRun("df", "test/cfg")
    assert task_runner.run()


def test_execution_fail(env_vars, setup_ssh_keys, root_dir):
    # Use the TaskRun class to trigger the job properly
    task_runner = taskrun.TaskRun("fail-command", "test/cfg")
    assert not task_runner.run()


def test_scp_basic(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    # Use the TaskRun class to trigger the job properly
    task_runner = taskrun.TaskRun("scp-basic", "test/cfg")
    assert task_runner.run()


def test_scp_basic_multiple_dests(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    # Use the TaskRun class to trigger the job properly
    task_runner = taskrun.TaskRun("scp-basic-multiple-dests", "test/cfg")
    assert task_runner.run()

    # Check the files were copied to all 3 destinations
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test.txt")
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test-2.txt")
    assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test-3.txt")


def test_scp_basic_10_files(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

    # Create 10 test files
    for i in range(10):
        fs.create_files(
            [{f"{root_dir}/testFiles/ssh_1/src/test{i}.txt": {"content": "test1234"}}]
        )

    # Use the TaskRun class to trigger the job properly
    task_runner = taskrun.TaskRun("scp-basic", "test/cfg")
    assert task_runner.run()

    # Check that the files were all transferred
    for i in range(10):
        assert os.path.exists(f"{root_dir}/testFiles/ssh_2/dest/test{i}.txt")


def test_scp_basic_pull(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    task_runner = taskrun.TaskRun("scp-basic-pull", "test/cfg")
    assert task_runner.run()


def test_scp_basic_pca_delete(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/test1.txt
    # File will be delteted after transfer

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test1.txt": {"content": "test1234"}}]
    )

    task_runner = taskrun.TaskRun("scp-basic-pca-delete", "test/cfg")
    assert task_runner.run()

    # Verify the file has disappeared
    assert not os.path.exists(f"{root_dir}/testFiles/ssh_1/src/test1.txt")


def test_scp_basic_pca_move(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/test2.txt
    # File will be moved after transfer

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test2.txt": {"content": "test1234"}}]
    )

    task_runner = taskrun.TaskRun("scp-basic-pca-move", "test/cfg")
    assert task_runner.run()

    # Verify the file has disappeared
    assert not os.path.exists(f"{root_dir}/testFiles/ssh_1/src/test2.txt")

    # Verify the file has been moved
    assert os.path.exists(f"{root_dir}/testFiles/ssh_1/archive/test2.txt")


def test_scp_source_file_conditions(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/log\..*\.log
    # File must be >10 bytes and less than 20
    # File must be older than 60 seconds and less than 600

    # Write a 11 byte long file

    write_test_file(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log", content="01234567890"
    )

    # This should fail, because the file is too new
    task_runner = taskrun.TaskRun("scp-source-file-conditions", "test/cfg")
    assert not task_runner.run()

    # Modify the file to be older than 1 minute and try again
    os.utime(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log",
        (time.time() - 61, time.time() - 61),
    )

    task_runner = taskrun.TaskRun("scp-source-file-conditions", "test/cfg")
    assert task_runner.run()

    # Modify the file to be older than 10 minutes and try again
    os.utime(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log",
        (time.time() - 601, time.time() - 601),
    )
    task_runner = taskrun.TaskRun("scp-source-file-conditions", "test/cfg")
    assert not task_runner.run()

    # Write a 9 byte long file - we need to change the age again
    write_test_file(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log", content="012345678"
    )

    os.utime(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log",
        (time.time() - 61, time.time() - 61),
    )

    task_runner = taskrun.TaskRun("scp-source-file-conditions", "test/cfg")
    assert not task_runner.run()

    # Write a 21 byte long file - we need to change the age again
    write_test_file(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log",
        content="012345678901234567890",
    )
    os.utime(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log",
        (time.time() - 61, time.time() - 61),
    )

    task_runner = taskrun.TaskRun("scp-source-file-conditions", "test/cfg")
    assert not task_runner.run()


def test_scp_file_watch(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/.*\.log
    # File should not exist to start with

    # Create the source file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/fileWatch.log": {"content": "01234567890"}}]
    )

    # Ensure the source file doesn't exist
    if os.path.exists(f"{root_dir}/testFiles/ssh_1/src/fileWatch.txt"):
        os.remove(f"{root_dir}/testFiles/ssh_1/src/fileWatch.txt")

    # Filewatch configured to wait 15 seconds before giving up. Expect it to fail
    task_runner = taskrun.TaskRun("scp-file-watch", "test/cfg")
    assert not task_runner.run()

    # This time, we run it again, but after 5 seconds, create the file
    # Create a thread that will run fs.create_fi:e{"s [{aft":r 5 second}}])
    t = threading.Timer(
        5,
        write_test_file,
        [f"{root_dir}/testFiles/ssh_1/src/fileWatch.txt"],
        {"content": "01234567890"},
    )
    t.start()
    logging.info("Started thread - Expect file in 5 seconds, starting task-run now...")

    task_runner = taskrun.TaskRun("scp-file-watch", "test/cfg")
    assert task_runner.run()

    # Delete the fileWatch.txt and log file
    os.remove(f"{root_dir}/testFiles/ssh_1/src/fileWatch.txt")
    os.remove(f"{root_dir}/testFiles/ssh_1/src/fileWatch.log")


def test_scp_log_watch(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/logYYYYWatch.log
    # File should not exist to start with
    # To succeed, the file should contain the text "someText"
    year = datetime.datetime.now().year
    # Ensure the log file is removed
    log_file = f"{root_dir}/testFiles/ssh_1/src/log{year}Watch.log"
    if os.path.exists(log_file):
        os.remove(log_file)

    # Logwatch will fail if the log file doesn't exist
    task_runner = taskrun.TaskRun("scp-log-watch", "test/cfg")
    assert not task_runner.run()

    # This time, we run it again with the file created and populated. It should fail because the file doesn't contain the expected text
    # Write the file
    fs.create_files([{log_file: {"content": "NOT_THE_RIGHT_PATTERN"}}])

    task_runner = taskrun.TaskRun("scp-log-watch", "test/cfg")
    assert not task_runner.run()

    # This time we run again, but populate the file after 5 seconds
    t = threading.Timer(
        5,
        write_test_file,
        [log_file],
        {"content": "someText\n"},
    )
    t.start()
    logging.info("Started thread - Expect file in 5 seconds, starting task-run now...")
    task_runner = taskrun.TaskRun("scp-log-watch", "test/cfg")
    assert task_runner.run()


def test_scp_log_watch_tail(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/logYYYYWatch.log
    # File should not exist to start with
    # To succeed, the file should contain the text "someText"
    year = datetime.datetime.now().year

    # Ensure the log file is removed
    if os.path.exists(f"{root_dir}/testFiles/ssh_1/src/log{year}Watch1.log"):
        os.remove(f"{root_dir}/testFiles/ssh_1/src/log{year}Watch1.log")

    # Write the matching pattern into the log, but before it runs.. This should
    # make the task fail because the pattern isn't written after the task starts
    fs.create_files(
        [
            {
                f"{root_dir}/testFiles/ssh_1/src/log{year}Watch1.log": {
                    "content": "someText\n"
                }
            }
        ]
    )
    task_runner = taskrun.TaskRun("scp-log-watch-tail", "test/cfg")
    assert not task_runner.run()

    # This time write the contents after 5 seconds
    t = threading.Timer(
        5,
        write_test_file,
        [f"{root_dir}/testFiles/ssh_1/src/log{year}Watch1.log"],
        {"content": "someText\n", "mode": "a"},
    )
    t.start()
    logging.info("Started thread - Expect file in 5 seconds, starting task-run now...")
    task_runner = taskrun.TaskRun("scp-log-watch-tail", "test/cfg")
    assert task_runner.run()


def run_task_run(task, verbose="2", config="test/cfg", noop=False):
    # We need to run the bin/task-run script to test this
    script = "python"
    args = [
        "src/opentaskpy/cli/task_run.py",
        "-t",
        task,
        "-v",
        verbose,
        "-c",
        config,
    ]

    if noop:
        args.append("--noop")

    # Run the script
    result = subprocess.run([script] + args, capture_output=True)
    # Write stdout and stderr to the console
    logging.info("\n########## STDOUT ##########")
    logging.info(result.stdout.decode("utf-8"))
    # Get the console colour for red

    logging.info("########## STDERR ##########")
    logging.info(f"{result.stderr.decode('utf-8')}")

    return {
        "returncode": result.returncode,
        "stdout": result.stdout.decode("utf-8"),
        "stderr": result.stderr.decode("utf-8"),
    }


def write_test_file(file_name, content=None, length=0, mode="w"):
    with open(file_name, mode) as f:
        if content is not None:
            f.write(content)
        else:
            f.write("a" * length)
    logging.info(f"Wrote file: {file_name}")
