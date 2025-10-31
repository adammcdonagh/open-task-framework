# Task Handlers — execution, transfer, batch

This document explains the responsibilities and usage patterns for the core task handlers under `src/opentaskpy/taskhandlers`.

Core handlers

- `taskhandler.py` — a lightweight facade that selects and invokes a concrete handler based on the incoming task's `type` field.
- `execution.py` — `ExecutionTaskHandler`: handles `execution` tasks. Responsibilities include:

  - Validate the task manifest (schema)
  - Instantiate the configured `Execution` handler
  - Execute the command remotely or locally, stream output, collect results, and handle process termination if requested

- `transfer.py` — `TransferTaskHandler`: handles `transfer` tasks. Responsibilities include:
  - Validate transfer payloads
  - Handle staging directories (worker staging)
  - Invoke transfer handler methods for listing, pulling, pushing, and final move to destination
  - Apply post-copy actions (move, delete) as configured
- `batch.py` — `BatchTaskHandler`: orchestrates multiple sub-tasks (either execution, transfer or batch). Useful for multi-step workflows.

## Design notes

- Each handler focuses on orchestration; concrete remote behavior lives in `remotehandlers` implementations.
- Handlers should be resilient to partial failures in batch operations and should provide granular results per sub-task.

## Batch handling details (flow and options)

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
- Dependencies: a task will not be started until all dependencies' statuses are `COMPLETED`.
- Execution model: each runnable task is started in a separate thread. The batch loop polls task statuses and enforces timeouts.
- Failure semantics:
  - If a task fails and `continue_on_fail` is false (the default), the sub-task is marked FAILED and the batch will not proceed with tasks that depend on it. The overall batch will ultimately return a non-zero exit code.
  - If `continue_on_fail` is true, the sub-task is marked COMPLETED and the batch continues. The overall batch will still return a non-zero exit code.
- Restart / resume semantics:
  - On startup the batch inspects the most recent batch log file to locate `__OTF_BATCH_TASK_MARKER__` marks to determine which tasks previously completed. Tasks marked as completed are skipped unless `retry_on_rerun` is true.

### Killing and timeouts:

- A sub-task running longer than `timeout` will be marked `TIMED_OUT`. The batch will set the sub-task's `kill_event` and wait for the thread to stop; if it does not stop in time, the thread is cancelled.
- A global kill_event passed to `Batch.run(kill_event)` will stop all running sub-tasks gracefully by setting each sub-task's `kill_event`.

### Logging and resumption

- The batch writes ordered log markers using `__OTF_BATCH_TASK_MARKER__: ORDER_ID::<order_id>::TASK::<task_id>::<status>` so reruns can detect state and take appropriate action. Note this only applies to gracefully failed runs, if a batch is killed via a kill command for example, it will not be able to rename it's log file with the `_failed` suffix, meaning the run will not be taken into account for resumption. If there are previously failed log files, the batch will use those instead, or if not then start from scratch.

### Best practices when authoring batch definitions

- Prefer explicit `dependencies` for complex tasks rather than relying purely on ordering.
- Set reasonable `timeout` values for long-running jobs and ensure handlers support graceful shutdown when `kill_event` is set. Ensure a timeout is longer than any file watch timeouts defined within transfers, otherwise these will be killed before the filewatching has finished.
- Use `continue_on_fail` only when downstream tasks are tolerant of upstream failures.
