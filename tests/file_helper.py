# pylint: skip-file
import logging
import os
import shutil
from re import match

import pytest

BASE_DIRECTORY = "test/testFiles"


def write_test_file(file_name, content=None, length=0, mode="w"):
    with open(file_name, mode) as f:
        if content is not None:
            f.write(content)
        else:
            f.write("a" * length)
    logging.info(f"Wrote file: {file_name}")


def list_test_files(directory, file_pattern, delimiter):
    files = [
        f"{directory}/{f}"
        for f in os.listdir(directory)
        if match(rf"{file_pattern}", f)
    ]
    return delimiter.join(files)


@pytest.fixture(scope="function")
def clear_logs() -> None:
    """Clear the logs directory."""
    if os.path.exists("logs"):
        # Delete the files inside the logs directory
        for file_name in os.listdir("logs"):
            file_path = os.path.join("logs", file_name)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except OSError:
                pass
