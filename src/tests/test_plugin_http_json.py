import unittest

from opentaskpy.plugins.lookup.http_json import run


class HttpJsonPluginTest(unittest.TestCase):
    def test_http_json_plugin_missing_all(self):
        with self.assertRaises(Exception) as ex:
            run()

        self.assertIn("Missing kwarg:", str(ex.exception))

    def test_http_json_plugin_missing_url(self):
        with self.assertRaises(Exception) as ex:
            run(jsonpath="test")

        self.assertEqual(str(ex.exception), "Missing kwarg: 'url' while trying to run lookup plugin 'http_json'")

    def test_http_json_plugin_missing_jsonpath(self):
        with self.assertRaises(Exception) as ex:
            run(url="http://test.com")

        self.assertEqual(str(ex.exception), "Missing kwarg: 'jsonpath' while trying to run lookup plugin 'http_json'")

    def test_http_json_plugin(self):
        # Run test with a valid URL and JSONPath
        result = run(url="https://jsonplaceholder.typicode.com/todos/1", jsonpath="$.userId")
        self.assertEqual(result, 1)

    def test_http_json_plugin_complex(self):
        # A more complex JSONPath
        result = run(url="https://jsonplaceholder.typicode.com/todos", jsonpath="$[0].title")
        self.assertEqual(result, "delectus aut autem")
