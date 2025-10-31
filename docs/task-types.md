# OTF Task Types

This page documents the high-level task types supported by the Open Task Framework (OTF).

## Table of contents

- [Task types overview](#task-types-overview)
- [Transfers](#transfers)
- [Executions](#executions)
- [Batches](#batches)
- [Templates and variable resolution](#templates-and-variable-resolution)

## Task types overview

As mentioned in the [README.md](../README.md), OTF supports three main task types: Transfers, Executions and Batches. Task payloads are JSON-based (either plain `.json` or Jinja2 `.json.j2` templates). See `docs/architecture.md` for the full rendering/parsing pipeline.

## Transfers

Transfers move files from a single source to one or more destinations. Supported protocols include SFTP/SSH and local filesystem handlers. Key features:

- File polling and filewatch (wait for files to appear)
- Log watching for specific patterns
- Conditional selection by file size, age, and count
- Post-copy actions: archive, delete, or move source files

Transfers can operate in "direct" mode (remote-to-remote where supported) or via a local staging step if protocols differ.

## Executions

Execution tasks run commands on remote hosts (via SSH or local execution handlers). Execution handlers capture stdout, stderr, exit code and may include PID tokenization for advanced lifecycle management (useful for `kill`).

## Batches

Batches compose multiple tasks (executions, transfers, or nested batches). They support:

- Ordered execution using `order_id`
- Explicit `dependencies` for DAG-style control
- `timeout`, `continue_on_fail`, and `retry_on_rerun` per-task options
- Resumption via log markers so batches can be rerun from the last known state

Batches are documented in more detail in `docs/taskhandlers.md`.

## Templates and variable resolution

- All task/config payloads are JSON-based. Files are either plain `.json` or Jinja2 templates with `.json.j2`.
- The loader pipeline renders `.json.j2` templates using Jinja2 and available plugin helpers, then parses the rendered text as JSON and validates against `src/opentaskpy/config/schemas/`.
- When editing templates, ensure the rendered output is valid JSON and that required variables are present in the rendering context.

If you want this page removed instead of updated, tell me and I'll delete it.
