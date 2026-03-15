# Developing Addons

Addons extend OTF with support for new remote systems — e.g. cloud storage buckets, Windows machines, SaaS file APIs. An addon is a Python package that implements one or both of:

- **`RemoteTransferHandler`** — source and/or destination for file transfers
- **`RemoteExecutionHandler`** — remote command execution

Real examples to reference alongside this guide:

- [`otf-addons-winrm`](https://github.com/adammcdonagh/otf-addons-winrm) — WinRM transfer + execution
- [`otf-addons-aws`](https://github.com/adammcdonagh/otf-addons-aws) — S3 transfer, Lambda execution
- [`otf-addons-o365`](https://github.com/adammcdonagh/otf-addons-o365) — SharePoint Online transfer

---

## Package Layout

Addons must follow the `opentaskpy.addons.<name>` namespace. A minimal layout:

```
otf-addons-myservice/
├── src/
│   └── opentaskpy/
│       └── addons/
│           └── myservice/
│               ├── __init__.py
│               └── remotehandlers/
│                   ├── __init__.py
│                   ├── myservice.py          # Handler class(es)
│                   └── schemas/
│                       ├── transfer/
│                       │   ├── myservice_source.json
│                       │   ├── myservice_source/
│                       │   │   └── protocol.json
│                       │   ├── myservice_destination.json
│                       │   └── myservice_destination/
│                       │       └── protocol.json
│                       └── execution/
│                           └── myservice/
│                               ├── myservice.json
│                               └── protocol.json
├── tests/
├── pyproject.toml
└── README.md
```

The schema directory name is derived from the last two parts of the Python module path (i.e., `myservice` in `opentaskpy.addons.myservice.remotehandlers.myservice`). Only include the schemas for the handler types you are implementing.

---

## Referencing Your Addon in Task Definitions

Use the fully-qualified class name as the `protocol.name`:

```json
{
  "type": "transfer",
  "source": {
    "protocol": {
      "name": "opentaskpy.addons.myservice.remotehandlers.myservice.MyServiceTransfer"
    }
  }
}
```

OTF uses the protocol name to:

1. Import the class dynamically and instantiate it.
2. Locate the JSON schema for validation (see [Schema Discovery](#schema-discovery)).

---

## Implementing a Transfer Handler

Subclass `RemoteTransferHandler` from `opentaskpy.remotehandlers.remotehandler`.

```python
import opentaskpy.otflogging
from opentaskpy.remotehandlers.remotehandler import RemoteTransferHandler


class MyServiceTransfer(RemoteTransferHandler):

    TASK_TYPE = "T"

    def __init__(self, spec: dict):
        self.logger = opentaskpy.otflogging.init_logging(
            __name__, spec["task_id"], self.TASK_TYPE
        )
        super().__init__(spec)
        # Initialise your client here using self.spec
```

### Required methods

All methods listed here are abstract and **must** be implemented. Return `0` for success and `1` (or raise) for failure in all methods that return `int`.

---

#### `supports_direct_transfer() -> bool`

Return `True` if your handler can transfer a file directly from one remote to another (i.e. remote-to-remote without staging on the OTF worker). Return `False` if files must be proxied through the worker.

```python
def supports_direct_transfer(self) -> bool:
    return False  # Most addons return False
```

---

#### `list_files(directory, file_pattern) -> dict`

Return a dict of files in the given directory whose names match `file_pattern` (a regex string). The dict maps each matched filename (relative, no directory prefix) to a metadata dict containing at minimum `size` (bytes) and `age` (seconds since last modification):

```python
def list_files(
    self, directory: str | None = None, file_pattern: str | None = None
) -> dict:
    directory = directory or self.spec["directory"]
    file_pattern = file_pattern or self.spec["fileRegex"]

    result = {}
    for item in self._list_remote(directory):
        if re.match(file_pattern, item.name):
            result[item.name] = {
                "size": item.size_bytes,
                "age": (datetime.now() - item.last_modified).total_seconds(),
            }
    return result
```

---

#### `transfer_files(files, remote_spec, dest_remote_handler) -> int`

Called when `supports_direct_transfer()` returns `True`. Implements a direct remote-to-remote transfer without staging. If your handler does not support this, raise `NotImplementedError` or return `1`.

```python
def transfer_files(
    self,
    files: list[str],
    remote_spec: dict,
    dest_remote_handler=None,
) -> int:
    raise NotImplementedError
```

---

#### `pull_files_to_worker(files, local_staging_directory) -> int`

Download `files` from the remote source to `local_staging_directory` on the OTF worker. Called when the source must be staged locally before being pushed to the destination.

```python
def pull_files_to_worker(
    self, files: list[str], local_staging_directory: str
) -> int:
    for filename in files:
        remote_path = f"{self.spec['directory']}/{filename}"
        local_path = os.path.join(local_staging_directory, filename)
        self._download(remote_path, local_path)
    return 0
```

---

#### `push_files_from_worker(local_staging_directory, file_list) -> int`

Upload files from `local_staging_directory` on the OTF worker to the remote destination. `file_list` may be `None`; in that case, upload everything found in the staging directory.

```python
def push_files_from_worker(
    self, local_staging_directory: str, file_list: dict | None = None
) -> int:
    files = file_list or {
        f: {} for f in os.listdir(local_staging_directory)
    }
    for filename in files:
        local_path = os.path.join(local_staging_directory, filename)
        remote_path = f"{self.spec['directory']}/{filename}"
        self._upload(local_path, remote_path)
    return 0
```

---

#### `pull_files(files) -> int`

Used for pull-mode transfers where the destination connects back to the source. If your handler does not support this (most don't), return `1`.

```python
def pull_files(self, files: list[str]) -> int:
    raise NotImplementedError
```

---

#### `move_files_to_final_location(files) -> int`

After files have been pushed to the destination, move them from any staging/temporary path to their final location. If your handler writes files directly to their final destination, this can be a no-op returning `0`.

```python
def move_files_to_final_location(self, files: dict) -> int:
    return 0  # Already in the right place
```

---

#### `handle_post_copy_action(files) -> int`

Called after a successful transfer. Implement `move`, `delete`, and `rename` actions on the **source** file(s) based on `self.spec.get("postCopyAction")`.

```python
def handle_post_copy_action(self, files: list[str]) -> int:
    pca = self.spec.get("postCopyAction")
    if not pca:
        return 0

    action = pca["action"]
    for filename in files:
        src = f"{self.spec['directory']}/{filename}"
        if action == "delete":
            self._delete(src)
        elif action == "move":
            dest = f"{pca['destination']}/{filename}"
            self._move(src, dest)
        elif action == "rename":
            new_name = re.sub(pca["pattern"], pca["sub"], filename)
            dest = f"{pca['destination']}/{new_name}"
            self._move(src, dest)
    return 0
```

---

### Optional methods

| Method                         | Default | When to override                            |
| ------------------------------ | ------- | ------------------------------------------- |
| `tidy()`                       | no-op   | Close connections, delete temp files        |
| `handle_cacheable_variables()` | no-op   | Variable caching (e.g. OAuth token refresh) |

---

## Implementing an Execution Handler

Subclass `RemoteExecutionHandler`. Only one method is required.

```python
import opentaskpy.otflogging
from opentaskpy.remotehandlers.remotehandler import RemoteExecutionHandler


class MyServiceExecution(RemoteExecutionHandler):

    TASK_TYPE = "E"

    def __init__(self, spec: dict):
        self.logger = opentaskpy.otflogging.init_logging(
            __name__, spec["task_id"], self.TASK_TYPE
        )
        super().__init__(spec)

    def execute(self) -> bool:
        """Run self.spec['command'] on the remote host.

        Returns:
            bool: True if the command exited successfully, False otherwise.
        """
        command = self.spec["command"]
        hostname = self.spec["hostname"]
        # ... run the command ...
        return exit_code == 0

    def tidy(self) -> None:
        """Close any open connections."""
```

The `execute()` method should:

- Run the command defined in `self.spec["command"]` against the host(s) in `self.spec`
- Log stdout/stderr via `self.logger`
- Return `True` on success, `False` on non-zero exit or connection failure

---

## Schema Discovery

OTF locates schema files from the addon package automatically based on the protocol name. Given:

```
opentaskpy.addons.myservice.remotehandlers.myservice.MyServiceTransfer
```

The **package** is derived as everything before the last two components:

```
opentaskpy.addons.myservice.remotehandlers
```

The framework then looks for schema files relative to that package's `schemas/` directory:

| Purpose                     | Expected path                                 |
| --------------------------- | --------------------------------------------- |
| Transfer source schema      | `schemas/transfer/myservice_source.json`      |
| Transfer destination schema | `schemas/transfer/myservice_destination.json` |
| Execution schema            | `schemas/execution/myservice/myservice.json`  |

Sub-schemas (e.g. `protocol.json`, `conditionals.json`) are referenced via relative `$ref` paths inside the top-level schema.

### Example source schema

```json
{
  "$id": "http://localhost/transfer/myservice_source.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "hostname": { "type": "string" },
    "directory": { "type": "string" },
    "fileRegex": { "type": "string" },
    "error": { "type": "boolean" },
    "postCopyAction": { "$ref": "myservice_source/postCopyAction.json" },
    "protocol": { "$ref": "myservice_source/protocol.json" }
  },
  "additionalProperties": false,
  "required": ["hostname", "directory", "fileRegex", "protocol"]
}
```

### Example protocol sub-schema

```json
{
  "$id": "http://localhost/transfer/myservice_source/protocol.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "enum": [
        "opentaskpy.addons.myservice.remotehandlers.myservice.MyServiceTransfer"
      ]
    },
    "credentials": {
      "type": "object",
      "properties": {
        "api_key": { "type": "string" }
      },
      "required": ["api_key"],
      "additionalProperties": false
    }
  },
  "required": ["name", "credentials"],
  "additionalProperties": false
}
```

---

## Logging

Always initialise a logger via OTF's logging module so that output goes to the correct per-task log file:

```python
self.logger = opentaskpy.otflogging.init_logging(
    __name__,           # module name
    spec["task_id"],    # task ID for log file naming
    self.TASK_TYPE,     # "T" for Transfer, "E" for Execution
)
```

Use `self.logger.info()`, `.debug()`, `.error()` etc. throughout. If you use any third-party libraries that have their own loggers, redirect them too:

```python
opentaskpy.otflogging.set_log_file("boto3")
opentaskpy.otflogging.set_log_file("botocore")
```

---

## Packaging

### pyproject.toml essentials

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "otf-addons-myservice"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "opentaskpy >= 25.0.0",
    "my-client-library >= 1.0.0",
]

[tool.setuptools]
include-package-data = true   # Required to include JSON schema files

[tool.setuptools.packages.find]
where = ["src"]
```

> **Important:** `include-package-data = true` is required so that JSON schema files inside your package are included in the built distribution. Without it, schema validation will fail at runtime.

### Versioning

Official OTF addons use [CalVer](https://calver.org/) in `YY.WW.PATCH` format (e.g. `25.37.0`). You are free to use any versioning scheme for your own addons.

---

## Testing

### Unit test structure

```
tests/
├── test_schema_validate.py    # Schema validation tests (no real connection needed)
└── test_taskhandler.py        # Integration tests (requires a real or mocked service)
```

### Schema validation tests

Test that valid configs pass and invalid configs are rejected:

```python
from opentaskpy.config.schemas import validate_transfer_json

def test_valid_source_schema():
    assert validate_transfer_json({
        "type": "transfer",
        "source": {
            "hostname": "myhost",
            "directory": "/path",
            "fileRegex": ".*\\.txt",
            "protocol": {
                "name": "opentaskpy.addons.myservice.remotehandlers.myservice.MyServiceTransfer",
                "credentials": { "api_key": "abc123" }
            }
        }
    })

def test_missing_required_field():
    assert not validate_transfer_json({
        "type": "transfer",
        "source": {
            "hostname": "myhost",
            # directory missing — should fail
            "protocol": {
                "name": "opentaskpy.addons.myservice.remotehandlers.myservice.MyServiceTransfer",
                "credentials": { "api_key": "abc123" }
            }
        }
    })
```

---

## Checklist

Before publishing your addon:

- [ ] Handler class inherits from `RemoteTransferHandler` or `RemoteExecutionHandler`
- [ ] All abstract methods implemented (or raise `NotImplementedError` with a clear message)
- [ ] Logger initialised with `opentaskpy.otflogging.init_logging(__name__, task_id, TASK_TYPE)`
- [ ] JSON schemas present for source, destination, and/or execution
- [ ] `$id` fields in schemas use `http://localhost/transfer/...` convention
- [ ] `include-package-data = true` in `pyproject.toml`
- [ ] Schema validation tests pass
- [ ] `tidy()` method cleans up open connections and temporary files
- [ ] Third-party library loggers redirected via `set_log_file()`
