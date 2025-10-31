# Remote Handlers — built-in implementations

This document describes the built-in remote handlers found in `src/opentaskpy/remotehandlers` and how to use them.

## Table of contents

- [Available handlers](#available-handlers)
- [Referencing handlers](#referencing-handlers)
- [Notes and caveats](#notes-and-caveats)
- [Extending or adding a handler](#extending-or-adding-a-handler)
- [Where to find tests](#where-to-find-tests)

## Available handlers

- `ssh.py` — SSHExecution and SSHTransfer helpers (depends on local SSH client or paramiko-like behavior). Used for remote command execution and staging file transfers.
- `sftp.py` — SFTPTransfer: file transfer over SFTP
- `local.py` — LocalTransfer/Execution: runs commands and moves files on the local filesystem (useful for testing and local workflows)
- `email.py` — Email transfer helper for sending files via email
- `dummy.py` — No-op handlers used for testing and examples
- `scripts/` — utilities used by handlers to run or wrap platform scripts

## Referencing handlers

A handler is referenced by its importable class path in the `protocol.name` field, for example:

```json
"protocol": {
  "name": "opentaskpy.remotehandlers.sftp.SFTPTransfer",
  "credentials": { "username": "user", "password": "pw" }
}
```

### Example: execution task using SSH handler

```json
{
  "id": "exec-1",
  "type": "execution",
  "hostname": "127.0.0.1",
  "directory": "/tmp",
  "command": "ls -la",
  "protocol": {
    "name": "opentaskpy.remotehandlers.ssh.SSHExecution",
    "credentials": { "username": "test", "password": "pw" }
  }
}
```

## Notes and caveats

- Handlers vary in their required `protocol.credentials`. Consult individual handler docstrings and tests for exact fields.
- For networked handlers, ensure integration test services are available in `test/docker-compose.yml`.
- `local` handler is safe to use in CI for unit tests; it avoids external network dependencies.

## Extending or adding a handler

1. Implement a concrete class in `src/opentaskpy/remotehandlers/` that subclasses the appropriate abstract base (see `remotehandler.py`).
2. Add schema entries if your handler expects new protocol fields.
3. Write unit tests and, if appropriate, a small integration test using `test/docker-compose.yml` fixtures.

## Where to find tests

- See `tests/test_plugin_file.py`, `tests/test_remotehandler.py`, and other tests that exercise handlers for examples of usage and expected return values.
