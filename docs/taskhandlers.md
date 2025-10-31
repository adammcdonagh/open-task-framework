# Task Handlers — execution, transfer, batch

This document explains the responsibilities and usage patterns for the core task handlers under `src/opentaskpy/taskhandlers`.

Core handlers

- `taskhandler.py` — a lightweight facade that selects and invokes a concrete handler based on the incoming task's `type` field.
- `execution.py` — `ExecutionTaskHandler`: handles `execution` tasks. Responsibilities:
  - Validate the task manifest (schema)
  - Instantiate the configured `Execution` handler
  - Execute the command remotely or locally, stream output, collect results, and handle process termination if requested
- `transfer.py` — `TransferTaskHandler`: handles `transfer` tasks. Responsibilities:
  - Validate transfer payloads
  - Handle staging directories (worker staging)
  - Invoke transfer handler methods for listing, pulling, pushing, and final move to destination
  - Apply post-copy actions (move, delete) as configured
- `batch.py` — `BatchTaskHandler`: orchestrates multiple sub-tasks (either execution or transfer). Useful for multi-target deployments or multi-step workflows.

Design notes

- Each handler focuses on orchestration; concrete remote behavior lives in `remotehandlers` implementations.
- Handlers must return structured result objects for consistent test assertions. Typical result fields include: `success` (bool), `result` (dict), `errors` (list), and `logs` (list) or a flattened `stdout`/`stderr` pair.
- Handlers should be resilient to partial failures in batch operations and should provide granular results per sub-task.

Examples

Invoke an `execution` task programmatically (pseudo-code):

```py
from opentaskpy.taskhandlers.taskhandler import TaskHandler

manifest = {...}  # validated dict
handler = TaskHandler()
result = handler.handle(manifest)
print(result)
```

Testing handlers

- Unit tests should mock remote handlers where possible (use `dummy.py` handler).
- Integration tests can instantiate real handlers against local test services defined in `test/docker-compose.yml`.

Batch handling details (flow and options)

The `Batch` handler orchestrates multiple sub-tasks defined in a `batch` task manifest. Each batch task entry contains control fields that determine ordering, dependency, failure handling, timeout, and rerun behavior.

Key fields available for each sub-task in the batch manifest:

- `order_id` (int): sequence identifier used to order tasks and identify them in logs.
- `task_id` (string): the referenced task definition file to load and execute.
- `dependencies` (array of order_id): optional list of order_ids that must be in a completed state before this task is considered runnable.
- `timeout` (int): seconds to allow this sub-task to run before marking TIMED_OUT and attempting to kill it.
- `continue_on_fail` (bool): if true the batch will mark the sub-task as COMPLETED and continue even if the sub-task failed or timed out.
- `retry_on_rerun` (bool): if true and the batch is being rerun, tasks that previously completed will be scheduled to run again.

Batch orchestration behavior:

- Ordering: `batch.tasks` are sorted by `order_id`.
- Dependencies: a task will not be started until all dependencies' statuses are in `COMPLETED`.
- Execution model: each runnable task is started in a separate thread. The batch loop polls task statuses and enforces timeouts.
- Failure semantics:
  - If a task fails and `continue_on_fail` is false, the sub-task is marked FAILED and the batch will not proceed with tasks that depend on it. The overall batch will ultimately return a non-zero exit code.
  - If `continue_on_fail` is true, the sub-task is marked COMPLETED and the batch continues.
- Restart / resume semantics:
  - On startup the batch inspects the most recent batch log file to locate `__OTF_BATCH_TASK_MARKER__` marks to determine which tasks previously completed. Tasks marked as completed are skipped unless `retry_on_rerun` is true.

Killing and timeouts:

- A sub-task running longer than `timeout` will be marked `TIMED_OUT`. The batch will set the sub-task's `kill_event` and wait for the thread to stop; if it does not stop in time, the thread is canceled.
- A global kill_event passed to `Batch.run(kill_event)` will stop all running sub-tasks gracefully by setting each sub-task's `kill_event`.

Logging and resumption

- The batch writes ordered log markers using `__OTF_BATCH_TASK_MARKER__: ORDER_ID::<order_id>::TASK::<task_id>::<status>` so reruns can detect state and take appropriate action.

Best practices when authoring batch manifests

- Prefer explicit `dependencies` for complex DAGs rather than relying purely on ordering.
- Set reasonable `timeout` values for long-running jobs and ensure handlers support graceful shutdown when `kill_event` is set.
- Use `continue_on_fail` only when downstream tasks are tolerant of upstream failures.

Where to find related tests

- `tests/test_taskhandler_transfer_dummy.py`
- `tests/test_taskhandler_execution_local.py`
- `tests/test_taskhandler_batch.py`
