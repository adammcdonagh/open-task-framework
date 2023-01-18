import os
from re import match

BASE_DIRECTORY = "test/testFiles"


def write_test_file(file_name, content=None, length=0, mode="w"):
    with open(file_name, mode) as f:

        if content is not None:
            f.write(content)
        else:
            f.write("a" * length)
    print(f"Wrote file: {file_name}")


def list_test_files(directory, file_pattern, delimiter):
    files = [
        f"{directory}/{f}"
        for f in os.listdir(directory)
        if match(rf"{file_pattern}", f)
    ]
    return delimiter.join(files)
