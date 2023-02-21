import pytest
from pytest_shell import fs

from opentaskpy.plugins.lookup.file import run


def test_file_plugin_missing_path():
    with pytest.raises(Exception) as ex:
        run()

    assert (
        ex.value.args[0]
        == "Missing kwarg: 'path' while trying to run lookup plugin 'file'"
    )


def test_file_plugin_file_not_found(tmpdir):
    with pytest.raises(FileNotFoundError) as ex:
        run(path=f"{tmpdir}/does_not_exist.txt")

    assert (
        ex.value.args[0]
        == f"File {tmpdir}/does_not_exist.txt does not exist while trying to run lookup plugin 'file'"
    )


def test_file_plugin(tmpdir):
    # Run test with a valid variable file, and ensure it's read and contains that value
    file_name = f"{tmpdir}/test.variable.txt"
    content = "test1234"
    fs.create_files([{file_name: {"content": "test1234"}}])
    result = run(path=file_name)
    assert result == content
