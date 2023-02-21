import pytest

from opentaskpy.plugins.lookup.http_json import run


def test_http_json_plugin_missing_all():
    with pytest.raises(Exception) as ex:
        run()

    assert "Missing kwarg:" in (ex.value.args[0])


def test_http_json_plugin_missing_url():
    with pytest.raises(Exception) as ex:
        run(jsonpath="test")

    assert (
        ex.value.args[0]
        == "Missing kwarg: 'url' while trying to run lookup plugin 'http_json'"
    )


def test_http_json_plugin_missing_jsonpath():
    with pytest.raises(Exception) as ex:
        run(url="http://test.com")

    assert (
        ex.value.args[0]
        == "Missing kwarg: 'jsonpath' while trying to run lookup plugin 'http_json'"
    )


def test_http_json_plugin():
    # Run test with a valid URL and JSONPath
    result = run(
        url="https://jsonplaceholder.typicode.com/todos/1", jsonpath="$.userId"
    )
    assert result == 1


def test_http_json_plugin_complex():
    # A more complex JSONPath
    result = run(
        url="https://jsonplaceholder.typicode.com/todos", jsonpath="$[0].title"
    )
    assert result == "delectus aut autem"
