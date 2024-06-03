# pylint: skip-file
# ruff: noqa

import pytest

from opentaskpy.config.variablecaching import file
from opentaskpy.exceptions import CachingPluginError


def test_cacheable_variable_file(tmpdir):

    spec = {"task_id": "1234", "x": {"y": "value"}}

    kwargs = {"file": f"{tmpdir}/cacheable_variable.txt", "value": "newvalue"}

    file.run(**kwargs)

    # Check the new file has content of "newvalue"
    with open(f"{tmpdir}/cacheable_variable.txt", "r") as f:
        assert f.read() == "newvalue"


def test_cacheable_variable_file_invalid(tmpdir):

    spec = {"task_id": "1234", "x": {"y": "value"}}

    kwargs = {"file": f"/NONEXISTENT/NONEXISTENT", "value": "newvalue"}

    # Should throw a FileNotFoundError
    with pytest.raises(FileNotFoundError):
        file.run(**kwargs)


def test_cachable_variable_file_invalid_args():
    with pytest.raises(CachingPluginError):
        file.run()

    with pytest.raises(CachingPluginError):
        file.run(file="/tmp/file.txt")

    with pytest.raises(CachingPluginError):
        file.run(value="newvalue")
