# OTF Task Types

OTF has three task types. Each is a JSON (or Jinja2-templated JSON) file placed anywhere under your `configDir`.

- [OTF Task Types](#otf-task-types)
  - [Transfers](#transfers)
    - [Source types](#source-types)
      - [SSH / SFTP source fields](#ssh--sftp-source-fields)
      - [Local source fields](#local-source-fields)
    - [Destination types](#destination-types)
      - [SSH / SFTP destination fields](#ssh--sftp-destination-fields)
      - [Local destination fields](#local-destination-fields)
      - [Email destination fields](#email-destination-fields)
    - [Sub-object reference](#sub-object-reference)
      - [SSH protocol](#ssh-protocol)
      - [Email protocol](#email-protocol)
      - [fileWatch](#filewatch)
      - [logWatch](#logwatch)
      - [conditionals](#conditionals)
      - [postCopyAction](#postcopyaction)
      - [rename](#rename)
      - [permissions](#permissions)
      - [flags](#flags)
      - [encryption](#encryption)
    - [Transfer example](#transfer-example)
  - [Executions](#executions)
    - [SSH execution](#ssh-execution)
    - [Local execution](#local-execution)
  - [Batches](#batches)
    - [Batch task entry fields](#batch-task-entry-fields)
    - [Parallel execution](#parallel-execution)
    - [Resuming a failed batch](#resuming-a-failed-batch)
    - [Validating a batch](#validating-a-batch)

---

## Transfers

A transfer moves files from a single **source** to one or more **destinations**.

```json
{
  "type": "transfer",
  "source": { ... },
  "destination": [ { ... } ],
  "cacheableVariables": [ ... ]
}
```

### Source types

The protocol specified inside `source.protocol.name` determines which source schema is used:

| Protocol name         | Handler | Description                                         |
| --------------------- | ------- | --------------------------------------------------- |
| `ssh`                 | SSH/SCP | File transfer from a remote Linux/Unix host via SSH |
| `sftp`                | SFTP    | File transfer from a remote host via SFTP           |
| `local`               | Local   | Files already present on the OTF worker machine     |
| `opentaskpy.addons.*` | Addon   | AWS S3, SharePoint, WinRM, etc.                     |

---

#### SSH / SFTP source fields

| Field            | Type    | Required | Description                                                                                       |
| ---------------- | ------- | -------- | ------------------------------------------------------------------------------------------------- |
| `hostname`       | string  | Yes      | Remote hostname or IP                                                                             |
| `directory`      | string  | Yes      | Remote directory containing source files                                                          |
| `fileRegex`      | string  | Yes      | Regular expression to match filenames                                                             |
| `protocol`       | object  | Yes      | Protocol definition (see [SSH protocol](#ssh-protocol))                                           |
| `fileWatch`      | object  | No       | Poll for a file to appear before transferring (see [fileWatch](#filewatch))                       |
| `logWatch`       | object  | No       | Tail a log file and wait for a matching line (see [logWatch](#logwatch))                          |
| `conditionals`   | object  | No       | Filter files by size, age, or count (see [conditionals](#conditionals))                           |
| `postCopyAction` | object  | No       | Action to take on the source file after a successful copy (see [postCopyAction](#postcopyaction)) |
| `encryption`     | object  | No       | Decrypt or verify a signature on the source file (see [encryption](#encryption))                  |
| `error`          | boolean | No       | If `true`, the task fails if no files match. Default: `false`                                     |

---

#### Local source fields

| Field            | Type    | Required | Description                                                                          |
| ---------------- | ------- | -------- | ------------------------------------------------------------------------------------ |
| `directory`      | string  | Yes      | Local directory containing source files                                              |
| `fileRegex`      | string  | Yes      | Regular expression to match filenames                                                |
| `protocol`       | object  | Yes      | `{ "name": "local" }`                                                                |
| `fileWatch`      | object  | No       | Poll for a file to appear (see [fileWatch](#filewatch))                              |
| `conditionals`   | object  | No       | Filter files by size, age, or count (see [conditionals](#conditionals))              |
| `postCopyAction` | object  | No       | Action to take on the source file after copy (see [postCopyAction](#postcopyaction)) |
| `encryption`     | object  | No       | Decrypt or verify a GPG signature (see [encryption](#encryption))                    |
| `error`          | boolean | No       | If `true`, the task fails if no files match                                          |

---

### Destination types

Multiple destinations can be specified. Each is processed in sequence.

| Protocol name         | Handler | Description                                  |
| --------------------- | ------- | -------------------------------------------- |
| `ssh`                 | SSH/SCP | Copy to a remote Linux/Unix host via SSH     |
| `sftp`                | SFTP    | Copy to a remote host via SFTP               |
| `local`               | Local   | Write to a local directory on the OTF worker |
| `email`               | SMTP    | Send files as email attachments              |
| `opentaskpy.addons.*` | Addon   | AWS S3, SharePoint, WinRM, etc.              |

---

#### SSH / SFTP destination fields

| Field                        | Type    | Required | Description                                                                 |
| ---------------------------- | ------- | -------- | --------------------------------------------------------------------------- |
| `hostname`                   | string  | Yes      | Remote hostname or IP                                                       |
| `directory`                  | string  | Yes      | Destination directory on the remote host                                    |
| `protocol`                   | object  | Yes      | Protocol definition (see [SSH protocol](#ssh-protocol))                     |
| `transferType`               | string  | No       | `push` (default), `pull`, or `proxy`                                        |
| `createDirectoryIfNotExists` | boolean | No       | Create the destination directory if it doesn't exist. Default: `false`      |
| `rename`                     | object  | No       | Rename the file at the destination (see [rename](#rename))                  |
| `permissions`                | object  | No       | Set ownership/mode after transfer (see [permissions](#permissions))         |
| `mode`                       | string  | No       | Octal file mode string, e.g. `"0644"`                                       |
| `flags`                      | object  | No       | Additional flags (see [flags](#flags))                                      |
| `encryption`                 | object  | No       | Encrypt or sign the file at the destination (see [encryption](#encryption)) |

---

#### Local destination fields

| Field                        | Type    | Required | Description                                                                 |
| ---------------------------- | ------- | -------- | --------------------------------------------------------------------------- |
| `directory`                  | string  | Yes      | Local destination directory                                                 |
| `protocol`                   | object  | Yes      | `{ "name": "local" }`                                                       |
| `transferType`               | string  | No       | `push` (default), `pull`, or `proxy`                                        |
| `createDirectoryIfNotExists` | boolean | No       | Create the destination directory if it doesn't exist. Default: `false`      |
| `rename`                     | object  | No       | Rename the file at the destination (see [rename](#rename))                  |
| `permissions`                | object  | No       | Set ownership/mode after transfer (see [permissions](#permissions))         |
| `mode`                       | string  | No       | Octal file mode string                                                      |
| `flags`                      | object  | No       | Additional flags (see [flags](#flags))                                      |
| `encryption`                 | object  | No       | Encrypt or sign the file at the destination (see [encryption](#encryption)) |

---

#### Email destination fields

Sends each transferred file as an email attachment via SMTP.

| Field                            | Type             | Required | Description                                                               |
| -------------------------------- | ---------------- | -------- | ------------------------------------------------------------------------- |
| `recipients`                     | array of strings | Yes      | List of recipient email addresses                                         |
| `subject`                        | string           | Yes      | Email subject line                                                        |
| `protocol`                       | object           | Yes      | Protocol definition (see [email protocol](#email-protocol))               |
| `message`                        | string           | No       | Email body text                                                           |
| `messageContentType`             | string           | No       | `text/html` (default) or `text/plain`                                     |
| `messageContentFilename`         | string           | No       | If set, the body is read from this local file instead of `message`        |
| `rename`                         | object           | No       | Rename the attachment (see [rename](#rename))                             |
| `deleteContentFileAfterTransfer` | boolean          | No       | Delete the `messageContentFilename` file after sending. Default: `true`   |
| `encryption`                     | object           | No       | GPG encrypt the attachment before sending (see [encryption](#encryption)) |

---

### Sub-object reference

#### SSH protocol

Used in `source.protocol` and `destination.protocol` for SSH and SFTP handlers.

```json
{
  "name": "ssh",
  "credentials": {
    "username": "transfer_user",
    "keyFile": "/path/to/private_key",
    "transferUsername": "other_user"
  },
  "port": 22,
  "hostKeyValidation": false,
  "knownHostsFile": "/etc/ssh/known_hosts"
}
```

| Field                          | Type    | Required | Description                                                                              |
| ------------------------------ | ------- | -------- | ---------------------------------------------------------------------------------------- |
| `name`                         | string  | Yes      | `"ssh"` or `"sftp"`                                                                      |
| `credentials.username`         | string  | Yes      | SSH username for connecting                                                              |
| `credentials.keyFile`          | string  | No       | Path to a private key file; overrides `OTF_SSH_KEY`                                      |
| `credentials.transferUsername` | string  | No       | Username for `pull` transfers (the destination connects back to the source as this user) |
| `port`                         | integer | No       | SSH port. Default: `22`                                                                  |
| `hostKeyValidation`            | boolean | No       | Whether to validate the remote host key. Default: `true`                                 |
| `knownHostsFile`               | string  | No       | Path to a known_hosts file                                                               |

---

#### Email protocol

```json
{
  "name": "email",
  "smtp_server": "smtp.example.com",
  "smtp_port": 587,
  "use_tls": true,
  "sender": "otf@example.com",
  "credentials": {
    "username": "otf@example.com",
    "password": "secret"
  }
}
```

| Field                  | Type    | Required | Description                                            |
| ---------------------- | ------- | -------- | ------------------------------------------------------ |
| `name`                 | string  | Yes      | Must be `"email"`                                      |
| `smtp_server`          | string  | Yes      | SMTP server hostname                                   |
| `sender`               | string  | Yes      | Sender email address                                   |
| `smtp_port`            | number  | No       | SMTP port (1–65535)                                    |
| `use_tls`              | boolean | No       | Whether to use TLS                                     |
| `credentials.username` | string  | No\*     | SMTP username (\*required if `credentials` is present) |
| `credentials.password` | string  | No\*     | SMTP password (\*required if `credentials` is present) |

---

#### fileWatch

Polls for a file matching `fileRegex` in `directory` before starting the transfer. The task fails if the file does not appear within `timeout` seconds.

```json
{
  "timeout": 300,
  "directory": "/tmp/trigger",
  "fileRegex": "ready\\.flag",
  "watchOnly": false
}
```

| Field       | Type    | Required | Description                                                       |
| ----------- | ------- | -------- | ----------------------------------------------------------------- |
| `timeout`   | integer | No       | Seconds to wait before giving up                                  |
| `directory` | string  | No       | Directory to watch (defaults to source `directory`)               |
| `fileRegex` | string  | No       | Regex to match the trigger file (defaults to source `fileRegex`)  |
| `watchOnly` | boolean | No       | If `true`, only watch — do not actually transfer the matched file |

---

#### logWatch

Tails a log file and waits for a line matching `contentRegex` to appear. If `tail` is `true`, only lines written after OTF starts watching are considered.

```json
{
  "timeout": 120,
  "directory": "/var/log/app",
  "log": "app.log",
  "contentRegex": "Job complete: [0-9]+",
  "tail": true
}
```

| Field          | Type    | Required | Description                                                   |
| -------------- | ------- | -------- | ------------------------------------------------------------- |
| `log`          | string  | Yes      | Log filename                                                  |
| `directory`    | string  | Yes      | Directory containing the log file                             |
| `contentRegex` | string  | Yes      | Regular expression to match against log lines                 |
| `timeout`      | integer | No       | Seconds to wait before giving up                              |
| `tail`         | boolean | No       | If `true`, only consider lines appended after watching starts |

---

#### conditionals

Filters the matched files, keeping only those that satisfy all specified conditions.

```json
{
  "size": { "gt": 100, "lt": 10485760 },
  "age": { "gt": 60, "lt": 3600 },
  "count": { "minCount": 1, "maxCount": 10 },
  "checkDuringFilewatch": true
}
```

| Field                  | Type    | Required | Description                                                 |
| ---------------------- | ------- | -------- | ----------------------------------------------------------- |
| `size.gt`              | integer | No       | File size must be greater than this many bytes              |
| `size.lt`              | integer | No       | File size must be less than this many bytes                 |
| `age.gt`               | integer | No       | File modification time must be older than this many seconds |
| `age.lt`               | integer | No       | File modification time must be newer than this many seconds |
| `count.minCount`       | integer | No       | At least this many files must match                         |
| `count.maxCount`       | integer | No       | No more than this many files must match                     |
| `checkDuringFilewatch` | boolean | No       | Apply conditionals while waiting in a fileWatch loop        |

---

#### postCopyAction

Action to perform on the **source** file after a successful transfer.

```json
{ "action": "move", "destination": "/archive/processed" }
```

```json
{ "action": "delete" }
```

```json
{
  "action": "rename",
  "destination": "/archive",
  "pattern": "^(.*)\\.csv$",
  "sub": "\\1_done.csv"
}
```

| Field         | Type   | Required                  | Description                                     |
| ------------- | ------ | ------------------------- | ----------------------------------------------- |
| `action`      | string | Yes                       | `move`, `rename`, or `delete`                   |
| `destination` | string | Yes (for `move`/`rename`) | Target directory                                |
| `pattern`     | string | Yes (for `rename`)        | Regex pattern to match against the filename     |
| `sub`         | string | Yes (for `rename`)        | Replacement string using regex group references |

---

#### rename

Rename the file at the **destination**.

```json
{
  "pattern": "^report_(.*)\\.csv$",
  "sub": "PROCESSED_\\1.csv"
}
```

| Field     | Type   | Required | Description                                                              |
| --------- | ------ | -------- | ------------------------------------------------------------------------ |
| `pattern` | string | Yes      | Regex pattern to match against the original filename                     |
| `sub`     | string | Yes      | Replacement string; supports regex group references (`\\1`, `\\2`, etc.) |

---

#### permissions

Set file ownership and/or mode on the destination file after transfer. Only supported for SSH/SFTP/local destinations.

```json
{
  "owner": "appuser",
  "group": "appgroup",
  "mode": "0644"
}
```

| Field   | Type   | Required | Description                       |
| ------- | ------ | -------- | --------------------------------- |
| `owner` | string | No       | Username to set as file owner     |
| `group` | string | No       | Group name to set on the file     |
| `mode`  | string | No       | Octal mode string (e.g. `"0644"`) |

---

#### flags

```json
{ "fullPath": "/exact/destination/path/file.txt" }
```

| Field      | Type   | Required | Description                                                          |
| ---------- | ------ | -------- | -------------------------------------------------------------------- |
| `fullPath` | string | Yes      | Write the file to this exact path, ignoring `directory` and `rename` |

---

#### encryption

Apply GPG encryption, decryption, or signing. Requires `gnupg` installed on the OTF worker.

```json
{
  "encrypt": true,
  "public_key": "{{ lookup('file', path='/keys/recipient.pub.asc') }}",
  "output_extension": "gpg"
}
```

```json
{
  "decrypt": true,
  "private_key": "{{ lookup('file', path='/keys/my.priv.asc') }}"
}
```

```json
{
  "sign": true,
  "private_key": "{{ lookup('file', path='/keys/my.priv.asc') }}"
}
```

| Field              | Type    | Required                   | Description                                             |
| ------------------ | ------- | -------------------------- | ------------------------------------------------------- |
| `encrypt`          | boolean | No                         | Encrypt the file using `public_key`                     |
| `decrypt`          | boolean | No                         | Decrypt the file using `private_key`                    |
| `sign`             | boolean | No                         | Sign the file using `private_key`                       |
| `private_key`      | string  | Yes (for `sign`/`decrypt`) | ASCII-armored PGP private key                           |
| `public_key`       | string  | No                         | ASCII-armored PGP public key (required for `encrypt`)   |
| `output_extension` | string  | No                         | Extension appended to the output file. Default: `"gpg"` |

---

### Transfer example

```json
{
  "type": "transfer",
  "source": {
    "hostname": "{{ HOST_A }}",
    "directory": "/data/exports",
    "fileRegex": "report_{{ TODAY }}\\.csv",
    "conditionals": {
      "size": { "gt": 0 },
      "age": { "lt": 3600 }
    },
    "postCopyAction": { "action": "move", "destination": "/data/archive" },
    "protocol": {
      "name": "ssh",
      "credentials": { "username": "{{ SSH_USER }}" }
    }
  },
  "destination": [
    {
      "hostname": "{{ HOST_B }}",
      "directory": "/data/imports",
      "createDirectoryIfNotExists": true,
      "permissions": { "group": "dataops" },
      "protocol": {
        "name": "ssh",
        "credentials": { "username": "{{ SSH_USER }}" }
      }
    }
  ]
}
```

---

## Executions

An execution runs a shell command on one or more remote or local hosts.

### SSH execution

```json
{
  "type": "execution",
  "hosts": ["{{ HOST_A }}", "{{ HOST_B }}"],
  "directory": "/opt/scripts",
  "command": "bash run_job.sh",
  "protocol": {
    "name": "ssh",
    "credentials": { "username": "{{ SSH_USER }}" }
  }
}
```

| Field       | Type             | Required | Description                                             |
| ----------- | ---------------- | -------- | ------------------------------------------------------- |
| `type`      | string           | Yes      | Must be `"execution"`                                   |
| `hosts`     | array of strings | Yes      | List of hostnames or IPs to run the command on          |
| `directory` | string           | Yes      | Working directory the command is run from               |
| `command`   | string           | Yes      | Shell command to execute                                |
| `protocol`  | object           | Yes      | Protocol definition (see [SSH protocol](#ssh-protocol)) |

When multiple `hosts` are specified, one thread per host is spawned and they run in parallel. If any host fails, the overall task is marked as failed once all threads have completed.

Executions have no built-in timeout. To add a timeout, wrap the execution in a [batch](#batches) and set `timeout` on the batch task entry.

---

### Local execution

Runs a command on the OTF worker machine itself. Useful for scripts that do not require SSH connectivity.

```json
{
  "type": "execution",
  "directory": "/opt/scripts",
  "command": "python3 process_data.py",
  "protocol": {
    "name": "local"
  }
}
```

| Field       | Type   | Required | Description                       |
| ----------- | ------ | -------- | --------------------------------- |
| `type`      | string | Yes      | Must be `"execution"`             |
| `directory` | string | Yes      | Working directory for the command |
| `command`   | string | Yes      | Shell command to execute          |
| `protocol`  | object | Yes      | `{ "name": "local" }`             |

Note: local executions do not have a `hosts` field.

---

## Batches

A batch chains multiple transfers, executions, and other batches together with optional dependencies, timeouts, and failure handling.

```json
{
  "type": "batch",
  "tasks": [
    {
      "order_id": 1,
      "task_id": "executions/prepare-data"
    },
    {
      "order_id": 2,
      "task_id": "transfers/upload-report",
      "dependencies": [1],
      "timeout": 600,
      "continue_on_fail": false,
      "retry_on_rerun": false
    },
    {
      "order_id": 3,
      "task_id": "executions/notify",
      "dependencies": [2],
      "continue_on_fail": true
    }
  ]
}
```

### Batch task entry fields

| Field              | Type              | Required | Description                                                                                        |
| ------------------ | ----------------- | -------- | -------------------------------------------------------------------------------------------------- |
| `order_id`         | integer           | Yes      | Unique identifier for this step within the batch (start at 1, increment by 1)                      |
| `task_id`          | string            | Yes      | Name of the task to run (filename without extension, relative to `configDir`)                      |
| `dependencies`     | array of integers | No       | List of `order_id` values that must complete successfully before this task starts                  |
| `timeout`          | integer           | No       | Seconds before this task is killed and marked as failed. Default: `300`                            |
| `continue_on_fail` | boolean           | No       | If `true`, subsequent dependent tasks still run even when this one fails. Default: `false`         |
| `retry_on_rerun`   | boolean           | No       | If `true`, this task re-runs even if it succeeded in a previous failed batch run. Default: `false` |

### Parallel execution

Tasks with no dependencies, or whose dependencies are already satisfied, run in parallel. Use `dependencies` to enforce ordering.

### Resuming a failed batch

When a batch fails and is re-run with the same `task-run` arguments on the **same calendar day**, OTF automatically skips tasks that already succeeded and re-runs only the failed steps.

To resume from a different day's log files:

```shell
export OTF_BATCH_RESUME_LOG_DATE=20260310
task-run -t batches/my-batch -c /path/to/cfg
```

Note that any date specific variables (e.g. `YYYY`, `MM`, `DD`) will need to be overridden too, in order to correcctly simulate the previous date.

### Validating a batch

```shell
otf-batch-validator -t batches/my-batch -c /path/to/cfg
```

This checks that all referenced `task_id` files exist, all `order_id` values are unique, and all `dependencies` reference valid `order_id` values.
