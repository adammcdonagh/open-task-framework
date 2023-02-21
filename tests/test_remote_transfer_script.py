import grp
import os
import re
import shutil
import time

import pytest
from pytest_shell import fs

from opentaskpy.remotehandlers.scripts import transfer as transfer

FILE_PREFIX = "unittest_testfile"
FILE_CONTENT = "test1234"
MOVED_FILES_DIR = "test_move_files"
DELIMITER = ","

list = None


@pytest.fixture(scope="function")
def setup(tmpdir):
    # Write 10 random files to /tmp
    for i in range(10):
        fs.create_files([{f"{tmpdir}/{FILE_PREFIX}_{i}": {"content": FILE_CONTENT}}])

    global list
    list = list_test_files(tmpdir, f"{FILE_PREFIX}_.*", delimiter=DELIMITER)

    # If directory doesn't exist, create it
    if not os.path.exists(f"{tmpdir}/{MOVED_FILES_DIR}"):
        os.mkdir(f"{tmpdir}/{MOVED_FILES_DIR}")


def test_list_files_no_details(setup, tmpdir):
    # Expect a list of 10 files
    list = transfer.list_files(f"{tmpdir}/{FILE_PREFIX}_.*", False)
    assert len(list) == 10

    # Check that the list of files returned is the same as the list of files we created
    for i in range(10):
        assert f"{tmpdir}/{FILE_PREFIX}_{i}" in (list)

    # Expect nothing to be returned
    list = transfer.list_files(f"{tmpdir}/{FILE_PREFIX}_qwhuidhqwduihqd", False)
    assert len(list) == 0

    # Try a more specific regex
    list = transfer.list_files(f"{tmpdir}/{FILE_PREFIX}_.*[0-9]", False)
    assert len(list) == 10

    # Try again but with character classes
    list = transfer.list_files(f"{tmpdir}/{FILE_PREFIX}_\\d+", False)
    assert len(list) == 10


def test_list_files_details(setup, tmpdir):
    # Expect a list of 10 files
    list = transfer.list_files(f"{tmpdir}/{FILE_PREFIX}_.*", True)
    assert len(list) == 10

    # Check that the list of files returned is the same as the list of files we created
    for i in range(10):
        assert f"{tmpdir}/{FILE_PREFIX}_{i}" in (list)
        # Get that value from the list
        file = list[f"{tmpdir}/{FILE_PREFIX}_{i}"]

        # Check that the file is a dict
        assert isinstance(file, dict)

        # Check that the dict has the keys we expect
        assert "size" in (file)
        assert "modified_time" in (file)

        # Check that the size is as expected
        assert file["size"] == len(FILE_CONTENT)

        # Check the modified time is within 1 second of now
        assert file["modified_time"] <= time.time()
        assert file["modified_time"] >= time.time() - 1


def test_move_files_basic(setup, tmpdir):
    transfer.move_files(
        list, ",", f"{tmpdir}/{MOVED_FILES_DIR}", False, None, None, None, None, None
    )

    # Check that the files were moved
    for i in range(10):
        assert not os.path.exists(f"{tmpdir}/{FILE_PREFIX}_{i}")

        assert os.path.exists(f"{tmpdir}/{MOVED_FILES_DIR}/{FILE_PREFIX}_{i}")


def test_move_files_create_dest_dir_1(setup, tmpdir):
    # Try moving to a directory that doesn't exist without asking to create one and expect an error
    with pytest.raises(FileNotFoundError):
        transfer.move_files(
            list,
            DELIMITER,
            f"{tmpdir}/{MOVED_FILES_DIR}/non_existent_directory",
            False,
            None,
            None,
            None,
            None,
            None,
        )

    # Now move to a directory that doesn't exist and ask to create it
    transfer.move_files(
        list,
        DELIMITER,
        f"{tmpdir}/{MOVED_FILES_DIR}/created_directory",
        True,
        None,
        None,
        None,
        None,
        None,
    )
    # Check that the files were moved
    for i in range(10):
        assert not os.path.exists(f"{tmpdir}/{FILE_PREFIX}_{i}")

        assert os.path.exists(
            f"{tmpdir}/{MOVED_FILES_DIR}/created_directory/{FILE_PREFIX}_{i}"
        )


def test_move_files_create_dest_dir_2(setup, tmpdir):
    # Move the files in there again, now that the directory exists, this should still work
    transfer.move_files(
        list,
        DELIMITER,
        f"{tmpdir}/created_directory",
        True,
        None,
        None,
        None,
        None,
        None,
    )
    # Check that the files were moved
    for i in range(10):
        assert not os.path.exists(f"{tmpdir}/{FILE_PREFIX}_{i}")
        assert os.path.exists(f"{tmpdir}/created_directory/{FILE_PREFIX}_{i}")

    # Remove the created directory
    shutil.rmtree(f"{tmpdir}/created_directory")


def test_move_files_rename(setup, tmpdir):
    transfer.move_files(
        list,
        DELIMITER,
        f"{tmpdir}/{MOVED_FILES_DIR}",
        False,
        None,
        None,
        None,
        f"({FILE_PREFIX})_(.*)",
        r"\1_renamed_\2",
    )

    # Check that the files were moved
    for i in range(10):
        assert not os.path.exists(f"{tmpdir}/{FILE_PREFIX}_{i}")
        assert os.path.exists(f"{tmpdir}/{MOVED_FILES_DIR}/{FILE_PREFIX}_renamed_{i}")


def test_move_files_set_owner(setup, tmpdir):
    # Determine if the current user is root or not
    is_root = os.getuid() == 0

    # Try setting the owner. This should fail because you cannot change the owner of a file unless you are root
    if not is_root:
        with pytest.raises(PermissionError):
            transfer.move_files(
                list,
                DELIMITER,
                f"{tmpdir}/{MOVED_FILES_DIR}",
                False,
                "root",
                None,
                None,
                None,
                None,
            )

        # Check that the files were not moved
        for i in range(10):
            assert os.path.exists(f"{tmpdir}/{FILE_PREFIX}_{i}")

            assert not os.path.exists(f"{tmpdir}/{MOVED_FILES_DIR}/{FILE_PREFIX}_{i}")

    # Now try setting the owner to the current user - Doesn't really make sense, but should work without throwing an exception
    transfer.move_files(
        list,
        DELIMITER,
        f"{tmpdir}/{MOVED_FILES_DIR}",
        False,
        os.environ.get("USER"),
        None,
        None,
        None,
        None,
    )

    # Check the files moved
    for i in range(10):
        assert not os.path.exists(f"{tmpdir}/{FILE_PREFIX}_{i}")

        assert os.path.exists(f"{tmpdir}/{MOVED_FILES_DIR}/{FILE_PREFIX}_{i}")


def test_move_files_set_group(setup, tmpdir):
    is_root = os.getuid() == 0

    # Try setting the group. This should fail because you cannot change the group of a file if you're not a member of it
    if not is_root:
        with pytest.raises(PermissionError):
            transfer.move_files(
                list,
                DELIMITER,
                f"{tmpdir}/{MOVED_FILES_DIR}",
                False,
                None,
                "root",
                None,
                None,
                None,
            )

        # Check that the files were not moved
        for i in range(10):
            assert os.path.exists(f"{tmpdir}/{FILE_PREFIX}_{i}")
            assert not os.path.exists(f"{tmpdir}/{MOVED_FILES_DIR}/{FILE_PREFIX}_{i}")

        # Now try setting the group to one of the secondary groups of the current user
        groups = os.getgrouplist(os.environ.get("USER"), os.getgid())

        # Convert group ID to name
        groups = [grp.getgrgid(group).gr_name for group in groups]

        transfer.move_files(
            list,
            DELIMITER,
            f"{tmpdir}/{MOVED_FILES_DIR}",
            False,
            None,
            groups[0],
            None,
            None,
            None,
        )

        # Check the files moved
        for i in range(10):
            assert not os.path.exists(f"{tmpdir}/{FILE_PREFIX}_{i}")
            assert os.path.exists(f"{tmpdir}/{MOVED_FILES_DIR}/{FILE_PREFIX}_{i}")

        # Check the group was set correctly
        for i in range(10):
            file_group = os.stat(f"{tmpdir}/{MOVED_FILES_DIR}/{FILE_PREFIX}_{i}").st_gid
            # Convert group ID to name
            file_group = grp.getgrgid(file_group).gr_name

            assert groups[0] == file_group


def test_delete_files(setup, tmpdir):
    transfer.delete_files(list, DELIMITER)

    # Check that the files were moved
    for i in range(10):
        assert not os.path.exists(f"{tmpdir}/{FILE_PREFIX}_{i}")


def list_test_files(directory, file_pattern, delimiter):
    files = [
        f"{directory}/{f}"
        for f in os.listdir(directory)
        if re.match(rf"{file_pattern}", f)
    ]
    return delimiter.join(files)
