- [Files in this docs folder](#files-in-this-docs-folder)
- [Task types overview](#task-types-overview)
- [Transfers](#transfers)
- [Executions](#executions)
- [Batches](#batches)
- [Templates and variable resolution](#templates-and-variable-resolution)

This folder contains documentation Open Task Framework (OTF). Use these docs to understand core concepts, the package layout, how plugins and handlers are structured, and concrete examples for using built-in handlers.

## Files in this docs folder

- `architecture.md` — high-level architecture and component responsibilities
- `remotehandlers.md` — built-in remote handlers, usage notes and examples
- `taskhandlers.md` — execution/transfer/batch task flow and responsibility mapping
- `plugins.md` — index of built-in plugins and how to author new ones
- `plugins/lookup.md` — details for the lookup plugin family

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
