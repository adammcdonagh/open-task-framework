# AGENTS.md — Open Task Framework (OTF)

This file is written for autonomous agents and maintainers who will modify, test, and extend the Open Task Framework codebase; it provides focused, actionable context so automated systems can make safe, verifiable changes.

## Table of contents

- [AGENTS.md — Open Task Framework (OTF)](#agentsmd--open-task-framework-otf)
  - [Table of contents](#table-of-contents)
  - [Quick scan](#quick-scan)
  - [High-level summary](#high-level-summary)
  - [Architecture and main components](#architecture-and-main-components)
  - [Contracts and data shapes — precise](#contracts-and-data-shapes--precise)
  - [Variable resolution \& templates](#variable-resolution--templates)
  - [Developer and agent workflow — run / test / iterate](#developer-and-agent-workflow--run--test--iterate)
  - [Concrete examples (copy-and-paste)](#concrete-examples-copy-and-paste)
  - [Tests, debugging, and logs](#tests-debugging-and-logs)
  - [CI and release pointers](#ci-and-release-pointers)
  - [Best practices for automated agents (rules)](#best-practices-for-automated-agents-rules)
  - [Where to look for related code](#where-to-look-for-related-code)
  - [Change summary and contact](#change-summary-and-contact)

## Quick scan

- Entry point(s): `src/opentaskpy/taskrun.py`, `src/opentaskpy/taskhandlers/taskhandler.py`
- Schemas: `src/opentaskpy/config/schemas/` (validation source of truth)
- Remote handlers: `src/opentaskpy/remotehandlers/` (SSH/SFTP/local/email/dummy)
- Plugins: `src/opentaskpy/plugins/` (lookup family)
- Run unit tests: `pytest tests/ -q`

## High-level summary

Open Task Framework is a modular Python framework that validates and runs tasks defined as JSON documents. Tasks describe either an execution (run a command) or a transfer (move files). The framework uses pluggable remote handlers (execution and transfer) to support protocols like SSH, SFTP, WinRM, and cloud storage services.

Key responsibilities:

- Validate task payloads against JSON schemas.
- Orchestrate execution and transfer flows via `taskhandler` components.
- Provide well-encapsulated protocol handlers: concrete classes implement a consistent handler interface so the taskhandler layer can be protocol-agnostic.
- Provide test fixtures (unit and integration) to verify both logic and environment interactions.

## Architecture and main components

1. Core package: `src/opentaskpy`

   - `taskhandler` — central orchestration logic: accepts a validated task, decides whether to call execution or transfer workflow, orchestrates staging and cleanup, and returns standardized results.
   - `remotehandlers` — contains abstract base classes and concrete implementations. Expect classes following the naming convention: `*Transfer` and `*Execution`.
   - `config/schemas` — JSON schemas that the code uses to validate task payloads. Schemas are authoritative; runtime assumes inputs match them.
   - `otflogging` — logging helpers used across the project for consistent log formatting and task-scoped contexts.

2. Tests and fixtures:

   - `tests/` — pytest test suite with unit tests (fast) and integration tests (may require docker-compose fixtures).
   - `test/` — helper scripts and docker-compose configurations used to stand up test services (sshd, mock services). Look for `createTestFiles.sh`, `createTestDirectories.sh`, and `setupSSHKeys.sh`.

3. Addons: repository-level addons live in sibling repos. Each addon should follow the same shape: `remotehandlers` implementations, config schemas, tests, and an optional `AGENTS.md` describing the addon details (example: winrm addon).

## Contracts and data shapes — precise

Task manifest (canonical fields):

- `id` (string): unique task identifier
- `type` (string): one of `transfer`, `execution`, `batch`
- `source` / `destination` (objects): for transfers, each contains `hostname`, `directory`, `fileRegex`, and `protocol`
- `hostname`, `directory`, `command` (for execution tasks)
- `protocol` (object): minimally `{ "name": "<python-class-path>", "credentials": {...}, ... }`

Protocol object details:

- `name` (string): importable Python class path implementing a Transfer or Execution handler
- `credentials` (object): fields are protocol-specific (e.g., `username`/`password`, `cert_pem`, `transport`)
- `server_cert_validation` / `port` / `transport` are optional common fields used by multiple handlers

Handler interface expectations (implementations MUST):

- Transfer handlers expose: `list_files(spec)`, `pull_file(spec, dest)`, `push_file(spec, src)`, `move_file(spec)`, `delete_file(spec)`, plus bulk helpers like `pull_files_to_worker()` and `push_files_from_worker()`
- Execution handlers expose: `execute(spec)` returning a controlled stream or result object, plus `kill(pid)` to request termination. Results must include `exit_code`, `stdout`, `stderr`. If a PID token is emitted by the remote, include `pid` in results.

Error model:

- Handlers should raise specific exceptions for common error classes (validation error, auth error, networkIO error). Taskhandler should catch and translate to standardized result objects for callers and tests.

If you change these shapes, update the JSON schemas in `src/opentaskpy/config/schemas/` and add/update tests in `tests/`.

## Variable resolution & templates

- File types: configuration and task payloads are JSON-based only. Files are either plain `.json` or Jinja2 templates with a `.json.j2` extension. YAML is not used for task/config payloads.
- Pipeline: when a task/template file is loaded the system performs this pipeline:
  1. Read the `.json` or `.json.j2` file.

2. If it is a Jinja2 template (`.json.j2`), render it with the available context (variables, plugin helpers, and environment values).
3. Parse the rendered output as JSON.
4. Validate the parsed JSON against the appropriate schema in `src/opentaskpy/config/schemas/`.

- Template context and helpers: lookup plugins (see `src/opentaskpy/plugins/lookup`) and other small helpers/filters are available to templates to compute values at render time. Templates must render to valid JSON — agents should always validate rendered output before runtime.

- Guidance for agents:
  - When editing templates, ensure the rendered output is syntactically valid JSON (use a local render step in tests).
  - Do not introduce template constructs that rely on secrets stored in-repo; use environment variables or test fixtures for secret injection.
  - If new helpers/plugins are required by templates, add them under `src/opentaskpy/plugins/` and include unit tests that exercise rendering.

## Developer and agent workflow — run / test / iterate

Local dev quickstart (recommended):

1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
```

2. Run a focused unit test

```bash
pytest tests/test_file_helper.py::test_some_helper -q
```

3. Run full unit test suite

```bash
pytest tests/ -q
```

Integration tests (requires docker):

```bash
cd test
./createTestDirectories.sh && ./createTestFiles.sh
docker-compose up -d
./setupSSHKeys.sh
cd ..
pytest tests/ -q
```

CI notes:

- The project uses `pyproject.toml` for packaging and `pytest.ini` for test config. CI should install dependencies with `pip install -e .[test]` and run `pytest -q`.
- Integration tests that depend on docker-compose should be gated behind a separate job that runs `cd test && docker-compose up -d` first.

## Concrete examples (copy-and-paste)

Example task manifest — execution

```json
{
  "id": "task-123",
  "type": "execution",
  "hostname": "127.0.0.1",
  "directory": "/tmp",
  "command": "echo hello",
  "protocol": {
    "name": "ssh",
    "credentials": { "username": "test", "keyFile": "path/to/key" }
  }
}
```

Example transfer protocol snippet (schema-driven)

```json
{
  "name": "sftp",
  "credentials": { "username": "user", "keyFile": "path/to/key" }
}
```

## Tests, debugging, and logs

- Test fixtures live in `tests/fixtures` or are defined in `tests/conftest.py`. Reuse existing fixtures whenever possible.
- Integration test logs and artifacts created by `test/` helper scripts are placed under `test/testLogs/` for easy inspection.
- Logging format: use `otflogging` helpers to include `task_id` and `hostname` in logs. New code should add context to loggers so tests can assert on log markers if needed.

Common debugging steps:

- Reproduce failing test locally with `-k <test_name>` and `-s` to see stdout/stderr streaming.
- Inspect `test/testLogs/` for integration failures.
- For networking/auth issues, replicate the protocol flow manually in a small script that uses the same handler class to connect and run a simple command.

## CI and release pointers

- Ensure `pyproject.toml` and `MANIFEST.in` contain any new package data files you add.
- Bump versions according to semantic versioning and update `CHANGELOG.md` when releasing.
- Unit tests should be quick; heavy integration tests should run in separate CI jobs that provision docker services.

## Best practices for automated agents (rules)

1. Run the unit tests that exercise your changed files before creating a PR. If you cannot reproduce remote integration locally, add/modify only unit tests or mock the remote layer.
2. Never add secrets to the repo. Use environment variables or test fixtures that generate ephemeral keys.
3. If changing a JSON schema, update the schema file and add at least one positive and one negative test case.
4. Limit scope of edits in a single PR: small, focused changes are easier to review and test.

## Where to look for related code

- `src/opentaskpy/taskhandlers/taskhandler.py` and `src/opentaskpy/taskhandlers/`
- `src/opentaskpy/remotehandlers/` (SSH, SFTP, WinRM addons live in separate repos but follow the same interface)
- `src/opentaskpy/config/schemas/` — JSON schemas (canonical)
- `tests/`, `tests/conftest.py` and `test/` helper scripts

## Change summary and contact

This file was created to give automated agents a reliable starting point for code navigation, safe edits, and test execution. If you're an external maintainer, open issues or PRs in this repository; include failing test output and the `-k` test used to reproduce locally.
