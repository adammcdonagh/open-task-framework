# pylint: skip-file
from tests.file_helper import list_test_files, write_test_file


def test_write_test_file_with_content(tmpdir):
    file_name = f"{tmpdir}/test.txt"
    content = "test1234"
    write_test_file(file_name, content)
    with open(file_name) as f:
        assert f.read() == content


def test_write_test_file_with_length(tmpdir):
    file_name = f"{tmpdir}/test.txt"
    length = 100
    write_test_file(file_name, length=length)
    with open(file_name) as f:
        assert len(f.read()) == length


def test_list_test_files(tmpdir):
    file_name = f"{tmpdir}/test.txt"
    content = "test1234"
    write_test_file(file_name, content)
    list = list_test_files(tmpdir, "test.txt", ",")
    assert list == file_name

    # Do the same but with a regex
    list = list_test_files(tmpdir, "test.*", ",")
    assert list == file_name
