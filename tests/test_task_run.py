import datetime
import os
import random
import subprocess
import threading
import time

from fixtures.ssh_clients import *  # noqa:F401
from pytest_shell import fs

from opentaskpy import exceptions, task_run

# Create a variable with a random number
RANDOM = random.randint(10000, 99999)
FILE_PREFIX = "unittest_task_run"
MOVED_FILES_DIR = "archive"
DELIMITER = ","

list = None


"""
#################
Tests for the "binary" task runner
#################
"""


def test_scp_basic_binary(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/text.txt": {"content": "test1234"}}]
    )

    assert run_task_run("scp-basic")["returncode"] == 0


def test_execution_basic_binary(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    assert run_task_run("df")["returncode"] == 0


def test_batch_basic_binary(env_vars, setup_ssh_keys, root_dir):
    # Use the "binary" to trigger the job with command line arguments

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    assert run_task_run("batch-basic")["returncode"] == 0


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


"""
#################
Tests using the Python code directly
#################
"""


def test_unknown_task_name(env_vars, setup_ssh_keys, root_dir):
    task_runner = task_run.TaskRun("non-existent", "test/cfg")

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
    task_runner = task_run.TaskRun("batch-basic", "test/cfg")
    assert task_runner.run()


def test_execution_basic(env_vars, setup_ssh_keys, root_dir):
    # Use the TaskRun class to trigger the job properly
    task_runner = task_run.TaskRun("df", "test/cfg")
    assert task_runner.run()


def test_execution_fail(env_vars, setup_ssh_keys, root_dir):
    # Use the TaskRun class to trigger the job properly
    task_runner = task_run.TaskRun("fail-command", "test/cfg")
    assert not task_runner.run()


def test_scp_basic(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    # Use the TaskRun class to trigger the job properly
    task_runner = task_run.TaskRun("scp-basic", "test/cfg")
    assert task_runner.run()


def test_scp_basic_multiple_dests(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/.*\.txt

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test.txt": {"content": "test1234"}}]
    )

    # Use the TaskRun class to trigger the job properly
    task_runner = task_run.TaskRun("scp-basic-multiple-dests", "test/cfg")
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
    task_runner = task_run.TaskRun("scp-basic", "test/cfg")
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

    task_runner = task_run.TaskRun("scp-basic-pull", "test/cfg")
    assert task_runner.run()


def test_scp_basic_pca_delete(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/test1.txt
    # File will be delteted after transfer

    # Create a test file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/test1.txt": {"content": "test1234"}}]
    )

    task_runner = task_run.TaskRun("scp-basic-pca-delete", "test/cfg")
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

    task_runner = task_run.TaskRun("scp-basic-pca-move", "test/cfg")
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
    task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
    with pytest.raises(exceptions.FilesDoNotMeetConditionsError) as cm:
        task_runner.run()
    assert "No remote files could be found to transfer" in (cm.value.args[0])

    # Modify the file to be older than 1 minute and try again
    os.utime(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log",
        (time.time() - 61, time.time() - 61),
    )

    task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
    assert task_runner.run()

    # Modify the file to be older than 10 minutes and try again
    os.utime(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log",
        (time.time() - 601, time.time() - 601),
    )
    task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
    with pytest.raises(exceptions.FilesDoNotMeetConditionsError) as cm:
        task_runner.run()
    assert "No remote files could be found to transfer" in (cm.value.args[0])

    # Write a 9 byte long file - we need to change the age again
    write_test_file(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log", content="012345678"
    )

    os.utime(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log",
        (time.time() - 61, time.time() - 61),
    )

    task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
    with pytest.raises(exceptions.FilesDoNotMeetConditionsError) as cm:
        task_runner.run()
    assert "No remote files could be found to transfer" in (cm.value.args[0])

    # Write a 21 byte long file - we need to change the age again
    write_test_file(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log",
        content="012345678901234567890",
    )
    os.utime(
        f"{root_dir}/testFiles/ssh_1/src/log.unittset.log",
        (time.time() - 61, time.time() - 61),
    )

    task_runner = task_run.TaskRun("scp-source-file-conditions", "test/cfg")
    with pytest.raises(exceptions.FilesDoNotMeetConditionsError) as cm:
        task_runner.run()
    assert "No remote files could be found to transfer" in (cm.value.args[0])


def test_scp_file_watch(env_vars, setup_ssh_keys, root_dir):
    # Required files for this test:
    # ssh_1 : test/testFiles/ssh_1/src/.*\.log
    # File should not exist to start with

    # Create the source file
    fs.create_files(
        [{f"{root_dir}/testFiles/ssh_1/src/fileWatch.log": {"content": "01234567890"}}]
    )

    # Filewatch configured to wait 15 seconds before giving up. Expect it to fail
    task_runner = task_run.TaskRun("scp-file-watch", "test/cfg")
    with pytest.raises(exceptions.RemoteFileNotFoundError) as cm:
        task_runner.run()
    assert "No files found after " in (cm.value.args[0])

    # This time, we run it again, but after 5 seconds, create the file
    # Create a thread that will run fs.create_fi:e{"s [{aft":r 5 second}}])
    t = threading.Timer(
        5,
        write_test_file,
        [f"{root_dir}/testFiles/ssh_1/src/fileWatch.txt"],
        {"content": "01234567890"},
    )
    t.start()
    print("Started thread - Expect file in 5 seconds, starting task-run now...")

    task_runner = task_run.TaskRun("scp-file-watch", "test/cfg")
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

    # Logwatch will fail if the log file dosent exist
    task_runner = task_run.TaskRun("scp-log-watch", "test/cfg")
    with pytest.raises(exceptions.LogWatchInitError) as cm:
        task_runner.run()
    assert "Logwatch init failed" in (cm.value.args[0])

    # This time, we run it again with the file created and populated. It should fail because the file dosent contain the expected text
    # Write the file
    fs.create_files([{log_file: {"content": "NOT_THE_RIGHT_PATTERN"}}])

    task_runner = task_run.TaskRun("scp-log-watch", "test/cfg")
    with pytest.raises(exceptions.LogWatchTimeoutError) as cm:
        task_runner.run()
    assert "No log entry found after " in (cm.value.args[0])

    # This time we run again, but populate the file after 5 seconds
    t = threading.Timer(
        5,
        write_test_file,
        [log_file],
        {"content": "someText\n"},
    )
    t.start()
    print("Started thread - Expect file in 5 seconds, starting task-run now...")
    task_runner = task_run.TaskRun("scp-log-watch", "test/cfg")
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
    task_runner = task_run.TaskRun("scp-log-watch-tail", "test/cfg")
    with pytest.raises(exceptions.LogWatchTimeoutError) as cm:
        task_runner.run()
    assert "No log entry found after " in (cm.value.args[0])

    # This time write the contents after 5 seconds
    t = threading.Timer(
        5,
        write_test_file,
        [f"{root_dir}/testFiles/ssh_1/src/log{year}Watch1.log"],
        {"content": "someText\n", "mode": "a"},
    )
    t.start()
    print("Started thread - Expect file in 5 seconds, starting task-run now...")
    task_runner = task_run.TaskRun("scp-log-watch-tail", "test/cfg")
    assert task_runner.run()


def run_task_run(task, verbose="2", config="test/cfg"):
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

    # Run the script
    result = subprocess.run(
        [script] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # Write stdout and stderr to the console
    print("\n########## STDOUT ##########")
    print(result.stdout.decode("utf-8"))
    # Get the console colour for red

    print("########## STDERR ##########")
    print(f"{result.stderr.decode('utf-8')}")

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
    print(f"Wrote file: {file_name}")
