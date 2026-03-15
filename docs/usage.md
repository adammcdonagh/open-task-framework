# Using OTF

This guide walks through installing and running OTF for the first time, explains how the configuration directory is structured, and covers day-to-day usage patterns.

## Prerequisites

- Python 3.10+
- SSH key pair set up on all remote hosts you want to connect to (for SSH-based tasks)
- `gnupg` installed on the host if you intend to use encryption/decryption

## Installation

```shell
pip install opentaskpy
```

This installs two CLI commands:

- `task-run` — runs a single task (transfer, execution, or batch)
- `otf-batch-validator` — validates a batch configuration without running it

To also use addons (AWS S3, WinRM, SharePoint, Vault), install the relevant packages alongside:

```shell
pip install otf-addons-aws
pip install otf-addons-winrm
pip install otf-addons-o365
pip install otf-addons-vault
```

## Configuration Directory Layout

All configuration lives under a single directory (referred to as `configDir` or `cfg`). OTF expects the following structure:

```
cfg/
├── variables.json.j2          # Required: global variable definitions
├── filters/                   # Optional: custom Jinja2 filters
│   └── my_filter.py
├── plugins/                   # Optional: custom lookup plugins
│   └── my_lookup.py
├── transfers/
│   └── my-transfer.json
├── executions/
│   └── my-execution.json
└── batches/
    └── my-batch.json
```

Task definitions can live in any sub-directory structure you like. The `task-run` command identifies them by name (the filename without extension) relative to `configDir`.

### variables.json.j2

Every `configDir` must have a `variables.json.j2` file at its root, even if it is empty:

```json
{}
```

Variables are defined as key/value pairs and support Jinja2 templating, including self-referencing:

```json
{
  "YYYY": "{{ now().strftime('%Y') }}",
  "MM": "{{ now().strftime('%m') }}",
  "DD": "{{ now().strftime('%d') }}",
  "TODAY": "{{ YYYY }}{{ MM }}{{ DD }}",
  "HOST_A": "server1.example.com",
  "SSH_USERNAME": "transfer_user"
}
```

Variables defined here are available in all task definitions via Jinja2 template syntax, e.g. `{{ HOST_A }}`.

## Running a Task

```shell
task-run -t <task-name> -c /path/to/cfg
```

The task name is the filename of the task definition **without** the `.json` or `.json.j2` extension, and **without** the `configDir` and sub directory prefix. For example, for `cfg/transfers/my-transfer.json`:

```shell
task-run -t my-transfer -c /path/to/cfg
```

### Useful flags

| Flag         | Description                                                              |
| ------------ | ------------------------------------------------------------------------ |
| `--noop`     | Validate the config and print what would run, without executing anything |
| `-r RUNID`   | Group log files under a named sub-directory (useful in batch pipelines)  |
| `-v 1\|2\|3` | Increase log verbosity (1=VERBOSE1, 2=VERBOSE2, 3=DEBUG)                 |

### Validating a batch

```shell
otf-batch-validator -t batches/my-batch -c /path/to/cfg
```

## Logging

By default, logs are written to a `logs/` directory in the current working directory. Each task gets its own log file named `<task-name>_<YYYYMMDD>.log`.

| Environment Variable | Effect                                                   |
| -------------------- | -------------------------------------------------------- |
| `OTF_LOG_DIRECTORY`  | Change the base log directory                            |
| `OTF_NO_LOG`         | Disable file logging; write to stderr only               |
| `OTF_LOG_JSON`       | Write stderr output as JSON (useful for log aggregators) |

When running a batch, setting `-r` (or `OTF_RUN_ID`) causes all sub-task logs to be written under a single named sub-directory, making it easy to find all logs for one pipeline run.

## Environment Variables

The full list of supported environment variables:

| Variable                    | Description                                                                  |
| --------------------------- | ---------------------------------------------------------------------------- |
| `OTF_SSH_KEY`               | Default private SSH key path for all SSH connections                         |
| `OTF_LOG_DIRECTORY`         | Base directory for log files                                                 |
| `OTF_NO_LOG`                | Set to `1` to disable file logging                                           |
| `OTF_LOG_JSON`              | Set to `1` for JSON-formatted stderr logging                                 |
| `OTF_STAGING_DIR`           | Override the staging directory for file transfers (default: `/tmp`)          |
| `OTF_RUN_ID`                | Log aggregation identifier; equivalent to `-r` flag                          |
| `OTF_BATCH_RESUME_LOG_DATE` | Resume batch from a specific date's logs (`YYYYMMDD` format)                 |
| `OTF_VARIABLES_FILE`        | Override the default variables file path. Comma-separate multiple files      |
| `OTF_LAZY_LOAD_VARIABLES`   | Set to `1` to only resolve variables that are referenced by the current task |
| `OTF_NO_THREAD_SLEEP`       | Set to `1` to disable the 1-second sleep between batch task thread creation  |
| `OTF_PARAMIKO_ULTRA_DEBUG`  | Set to `1` to enable ultra-verbose Paramiko SSH debug output (SFTP only)     |

## Overriding Variables at Runtime

Global variables can be overridden by setting an environment variable with the same name:

```shell
export DD=01
task-run -t transfers/my-transfer -c /path/to/cfg
# Logs: "Overriding global variable (DD: 15) with environment variable (01)"
```

Nested variables use dot notation:

```shell
export SOME_VARIABLE.NESTED_VARIABLE=new_value
```

Task-specific attributes can be overridden using `OTF_OVERRIDE_<TASK_TYPE>_<ATTRIBUTE>`:

```shell
# Override the source hostname of a transfer
export OTF_OVERRIDE_TRANSFER_SOURCE_HOSTNAME=staging.example.com

# Override a nested destination attribute (array index 0)
export OTF_OVERRIDE_TRANSFER_DESTINATION_0_PROTOCOL_CREDENTIALS_USERNAME=myuser
```

If an attribute name itself contains underscores, use `!!` as the separator:

```shell
export OTF_OVERRIDE_EXECUTION_PROTOCOL!!SOME_ATTRIBUTE=value
```

## Using Jinja2 Templates for Task Definitions

Task definitions can be plain `.json` files or Jinja2 templates with a `.json.j2` extension. Templates have access to all variables defined in `variables.json.j2`, all built-in filters (`now`, `utc_now`, `delta_days`, etc.), any custom filters placed in `cfg/filters/`, and any lookup plugins defined in `cfg/plugins/lookup/`.

Example task using variables and a built-in filter:

```json
{
  "type": "transfer",
  "source": {
    "hostname": "{{ HOST_A }}",
    "directory": "/data/exports",
    "fileRegex": "report_{{ YYYY }}{{ MM }}{{ DD }}\\.csv",
    "protocol": {
      "name": "ssh",
      "credentials": { "username": "{{ SSH_USERNAME }}" }
    }
  },
  "destination": [
    {
      "hostname": "{{ HOST_B }}",
      "directory": "/data/imports",
      "protocol": {
        "name": "ssh",
        "credentials": { "username": "{{ SSH_USERNAME }}" }
      }
    }
  ]
}
```

## Running via Docker

```shell
docker build -t opentaskpy -f Dockerfile .
docker run --rm \
  --volume /opt/otf/cfg:/cfg \
  --volume /var/log/otf:/logs \
  --volume /home/$USER/.ssh/id_rsa:/id_rsa \
  -e OTF_SSH_KEY=/id_rsa \
  -e OTF_LOG_DIRECTORY=/logs \
  opentaskpy task-run -t transfers/my-transfer -c /cfg
```
