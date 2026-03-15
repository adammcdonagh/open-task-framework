# Lookup Plugins

Lookup plugins allow you to resolve dynamic or secret values at the time a task runs, rather than hard-coding them into your variable files.

They are invoked using the `lookup()` function inside Jinja2 templates:

```jinja2
"{{ lookup('plugin_name', kwarg1='value1', kwarg2='value2') }}"
```

Lookups can appear anywhere in a task definition or in `variables.json.j2` where Jinja2 templates are supported.

---

## Built-in Plugins

### `file`

Reads the first line of a file and returns it as a string. Useful for reading secrets or tokens stored on the local filesystem.

**Arguments:**

| Argument | Required | Description                       |
| -------- | -------- | --------------------------------- |
| `path`   | Yes      | Absolute path to the file to read |

**Example:**

```jinja2
"{{ lookup('file', path='/run/secrets/api_token') }}"
```

The file should contain a single line with the value. Trailing whitespace is stripped.

---

### `http_json`

Performs an HTTP GET request against a URL that returns JSON, and extracts a value using a [JSONPath](https://github.com/json-path/JsonPath) expression. The endpoint must respond within 5 seconds or the lookup will fail silently (returning `None`).

Does not support authentication — intended for internal or public endpoints only.

**Arguments:**

| Argument   | Required | Description                                      |
| ---------- | -------- | ------------------------------------------------ |
| `url`      | Yes      | Full URL to the JSON endpoint                    |
| `jsonpath` | Yes      | JSONPath expression to extract the desired value |

**Example:**

```jinja2
"{{ lookup('http_json', url='http://config-service/api/values', jsonpath='$.database.host') }}"
```

---

### `random_number`

Returns a random integer between two provided values (inclusive). Primarily useful for testing and demonstrations.

**Arguments:**

| Argument | Required | Description             |
| -------- | -------- | ----------------------- |
| `min`    | Yes      | Minimum value (integer) |
| `max`    | Yes      | Maximum value (integer) |

**Example:**

```jinja2
"{{ lookup('random_number', min=1000, max=9999) }}"
```

---

## Official Addon Plugins

Additional lookup plugins are available via addon packages:

| Plugin    | Package                                                              | Description                               |
| --------- | -------------------------------------------------------------------- | ----------------------------------------- |
| `aws.ssm` | [otf-addons-aws](https://github.com/adammcdonagh/otf-addons-aws)     | Fetch values from AWS SSM Parameter Store |
| `vault`   | [otf-addons-vault](https://github.com/adammcdonagh/otf-addons-vault) | Fetch secrets from HashiCorp Vault        |

---

## Writing a Custom Lookup Plugin

A lookup plugin is a plain Python module with a `run(**kwargs)` function that returns a string.

### Minimal example

```python
# cfg/plugins/my_lookup.py

PLUGIN_NAME = "my_lookup"


def run(**kwargs) -> str:
    name = kwargs.get("name")
    if not name:
        raise ValueError("Missing required argument: 'name'")
    # Replace this with your actual logic
    return f"resolved-value-for-{name}"
```

Usage in a template:

```jinja2
"{{ lookup('my_lookup', name='some_param') }}"
```

### Plugin interface rules

- The module must expose a `run(**kwargs)` function.
- Return value must be a `str` (or `None` if the value could not be resolved).
- Raise `opentaskpy.exceptions.LookupPluginError` for missing required arguments.
- Use `opentaskpy.otflogging.init_logging(__name__)` for consistent log output.

### Full example with logging

```python
import opentaskpy.otflogging
from opentaskpy.exceptions import LookupPluginError

logger = opentaskpy.otflogging.init_logging(__name__)

PLUGIN_NAME = "my_lookup"


def run(**kwargs) -> str:
    if "name" not in kwargs:
        raise LookupPluginError(
            f"Missing kwarg: 'name' while trying to run lookup plugin '{PLUGIN_NAME}'"
        )

    result = _fetch_value(kwargs["name"])
    logger.log(12, f"Resolved '{kwargs['name']}' to '{result}'")
    return result


def _fetch_value(name: str) -> str:
    # Your custom resolution logic here
    return f"value-for-{name}"
```

---

## Deploying Custom Plugins

OTF looks for plugins in two places:

### 1. Config directory (no install required)

Drop the plugin file into the `plugins/` directory under your `configDir`:

```
cfg/
└── plugins/
    └── my_lookup.py
```

Reference it by filename (without `.py`):

```jinja2
"{{ lookup('my_lookup', name='param') }}"
```

### 2. Installed Python package

Install your plugin as a Python package under the `opentaskpy.plugins.lookup` namespace. For example, a module at `opentaskpy.plugins.lookup.mycompany.config` would be referenced as:

```jinja2
"{{ lookup('mycompany.config', name='param') }}"
```

This approach is preferred for plugins shared across multiple config directories or deployed as part of a Docker image.

---

## Cacheable Variables

Some lookups return values that can change during execution (e.g. OAuth access tokens). OTF supports writing updated values back to the source using cacheable variables.

See the [README — Advanced Variables](../README.md#advanced-variables) section for full details.
