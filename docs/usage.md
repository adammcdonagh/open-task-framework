# Usage examples and common commands

This page collects common commands for running tests, creating development environments, and debugging failing tests.

Environment setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
```

## Table of contents

- [Environment setup](#environment-setup)
- [Running tests](#running-tests)
- [Running tasks (CLI)](#running-tasks-cli)
- [Inspecting logs and artifacts](#inspecting-logs-and-artifacts)
- [Adding a handler checklist](#adding-a-handler-checklist)
- [CI recommendations](#ci-recommendations)

## Environment setup

Run a single unit test

```bash
pytest tests/test_file_helper.py::test_read_file -q
```

Run all unit tests

```bash
pytest tests/ -q
```

Run integration fixtures and tests

```bash
cd test
./createTestDirectories.sh && ./createTestFiles.sh
docker-compose up -d
./setupSSHKeys.sh
cd ..
pytest tests/ -q
```

Running a real task (CLI)

The package ships a CLI wrapper at `src/opentaskpy/cli/task_run.py` which exposes an executable entry point (installed as `task-run` in some packaging setups). You can also call the module directly with Python.

Example — run a transfer task by taskId (config files live in `cfg/` by default):

## Running tasks (CLI)

# run via installed CLI (if installed)

task-run --taskId transfer-myfiles -c ./cfg -v 1

# or run via the module (useful during development)

python -m opentaskpy.cli.task_run --taskId transfer-myfiles --configDir ./cfg

````

Example — run an execution task in noop mode (validate only):

```bash
python -m opentaskpy.cli.task_run --taskId run-example --configDir ./cfg --noop
````

Environment variables that impact runtime

How TaskRun selects and triggers tasks

Examples — batch runs

```bash
# Run a batch task
python -m opentaskpy.cli.task_run --taskId batch-basic --configDir ./cfg
```

Notes on reruns and resume

Inspecting logs and artifacts

Adding a new handler plugin (example checklist)

1. Implement the handler in `src/opentaskpy/remotehandlers/` or a new addon repo (follow naming convention `*Transfer` / `*Execution`).
2. Add or update schema(s) in `src/opentaskpy/config/schemas/` for new protocol options.
3. Add unit tests in `tests/` and, if needed, integration tests that use `test/docker-compose.yml`.
4. Run `pytest -q` and ensure new code is covered by tests.

CI recommendations

If you'd like, I can also add a small developer onboarding checklist or a short UML ASCII diagram to `architecture.md`.
