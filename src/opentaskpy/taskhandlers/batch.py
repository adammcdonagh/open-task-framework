"""Batch task handler class."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait

import opentaskpy.otflogging
from opentaskpy.config.loader import ConfigLoader
from opentaskpy.exceptions import InvalidConfigError
from opentaskpy.taskhandlers.execution import Execution
from opentaskpy.taskhandlers.taskhandler import TaskHandler
from opentaskpy.taskhandlers.transfer import Transfer

DEFAULT_TASK_TIMEOUT = 300
DEFAULT_TASK_CONTINUE_ON_FAIL = False
DEFAULT_TASK_RETRY_ON_RERUN = False
DEFAULT_TASK_EXIT_CODE = 0
TASK_TYPE = "B"
BATCH_TASK_LOG_MARKER = "__OTF_BATCH_TASK_MARKER__"


class Batch(TaskHandler):
    """Batch task handler class."""

    overall_result = False

    def __init__(
        self,
        global_config: dict,
        task_id: str,
        batch_definition: dict,
        config_loader: ConfigLoader,
    ):
        """Initialise the batch task handler.

        Args:
            global_config (dict): The global configuration for the task.
            task_id (str): The ID of the task.
            batch_definition (dict): The definition of the batch task.
            config_loader (ConfigLoader): The config loader to use to load
            task definitions within the batch.
        """
        self.task_id = task_id
        self.batch_definition = batch_definition
        self.config_loader = config_loader
        self.tasks = {}
        self.task_order_tree = {}

        super().__init__(global_config)

        self.logger = opentaskpy.otflogging.init_logging(
            __name__, self.task_id, TASK_TYPE
        )

        # We need to get the latest log file (if there is one), to determine
        # where to start from (if we are resuming a batch)
        previous_log_file = opentaskpy.otflogging.get_latest_log_file(
            self.task_id, TASK_TYPE
        )

        self.logger.info(
            f"Found previous log file: {previous_log_file}"
            if previous_log_file
            else "No previous log file found"
        )

        previous_status = {}
        if previous_log_file:
            self.logger.info("Parsing previous log file for log marks")

            # Parse the previous log file to determine where we left off
            with open(previous_log_file, encoding="utf-8") as f:
                for line in f:
                    if BATCH_TASK_LOG_MARKER in line:
                        log_mark = line.split(f"{BATCH_TASK_LOG_MARKER}: ")[1].strip()
                        self.logger.info(f"Found log mark: {log_mark}")
                        # Mark the task with the appropriate status
                        # Determine which order id this is for
                        mark_metadata = log_mark.split("::")
                        order_id = int(mark_metadata[1])
                        task_status = mark_metadata[4]

                        previous_status[order_id] = task_status

        # Order the batch_definitions by order_id
        self.batch_definition["tasks"] = sorted(
            self.batch_definition["tasks"], key=lambda k: k["order_id"]  # type: ignore[no-any-return]
        )

        # Parse the batch definition and create the appropriate tasks to run
        # in the correct order, based on the dependencies specified
        for task in self.batch_definition["tasks"]:
            # Load the definition for the task
            task_definition = self.config_loader.load_task_definition(task["task_id"])
            order_id = task["order_id"]

            # Add it to the list of tasks
            self.tasks[order_id] = task_definition

            # Set the timeout for the task
            timeout = task.get("timeout", DEFAULT_TASK_TIMEOUT)

            # Same for continue on fail
            continue_on_fail = None
            if "continue_on_fail" in task:
                continue_on_fail = task["continue_on_fail"]
            else:
                continue_on_fail = DEFAULT_TASK_CONTINUE_ON_FAIL

            # Same for retry on rerun
            retry_on_rerun = None
            retry_on_rerun = task.get("retry_on_rerun", DEFAULT_TASK_RETRY_ON_RERUN)

            # Set the status of the task
            status = "NOT_STARTED"
            if order_id in previous_status:
                # Check whether it should be rerun if it worked last time
                if retry_on_rerun:
                    if previous_status[order_id] == "COMPLETED":
                        # Log something to make it clear that we are rerunning
                        self.logger.info(
                            f"Task {task_id} succeeded last time, but is marked to be"
                            " rerun"
                        )
                    status = "NOT_STARTED"
                elif previous_status[order_id] == "COMPLETED":
                    self.logger.info(
                        f"Task {task_id} succeeded last time, and is not marked to be"
                        " rerun, so marking as complete"
                    )
                    # Output the log mark
                    self._log_task_result(
                        "COMPLETED",
                        str(order_id),
                        task["task_id"],
                    )
                    status = "COMPLETED"

            # Create the task handlers for anything we intend on running
            task_handler = None
            if status == "NOT_STARTED":
                # Create the appropriate task handler based on the task type
                if task_definition["type"] == "execution":
                    task_handler = Execution(
                        global_config, task["task_id"], task_definition
                    )
                elif task_definition["type"] == "transfer":
                    task_handler = Transfer(
                        global_config, task["task_id"], task_definition
                    )
                elif task_definition["type"] == "batch":
                    task_handler = Batch(
                        global_config,
                        task["task_id"],
                        task_definition,
                        self.config_loader,
                    )
                else:
                    raise InvalidConfigError("Unknown task type")

            self.task_order_tree[order_id] = {
                "task_id": task["task_id"],
                "batch_task_spec": task,
                "task": task_definition,
                "task_handler": task_handler,
                "timeout": timeout,
                "continue_on_fail": continue_on_fail,
                "retry_on_rerun": retry_on_rerun,
                "status": status,
                "result": None,
            }

        # Debug to show the structure of the tree
        self.logger.debug(f"Task order tree: {self.task_order_tree}")

    def _set_remote_handlers(self) -> None:
        pass

    def return_result(
        self,
        status: int,
        message: str | None = None,
        exception: type[Exception] | None = None,
    ) -> bool:
        """Return the result of the task run.

        Args:
            status (int): The status code to return.
            message (str, optional): The message to return. Defaults to None.
            exception (Exception, optional): The exception to return. Defaults to None.

        Returns:
            bool: The result of the task run.
        """
        return super().return_result(status, message, exception)  # type: ignore[no-any-return]

    def run(self, kill_event: threading.Event | None = None) -> bool:
        """Run the batch.

        Args:
            kill_event (threading.Event, optional): An event to kill the batch. Defaults to None.

        Returns:
            bool: True if the batch completed successfully, False otherwise.
        """
        self.logger.info("Running batch")

        # This is where we could potentially be waiting for a while. So,
        # for each task handler, we should spawn a new thread to run
        # the command. Then we can wait for all threads to complete.

        ex = None
        while True:
            # Loop through every task in the tree
            for order_id, batch_task in self.task_order_tree.items():
                task = batch_task["task"]
                logged = False
                if "logged_status" in batch_task:
                    logged = batch_task["logged_status"]
                else:
                    batch_task["logged_status"] = False

                self.logger.log(
                    12, f"Checking task {order_id} ({batch_task['task_id']})"
                )

                # Check if there are dependencies for this task that have not yet completed, if so then we skip it
                if "dependencies" in batch_task["batch_task_spec"]:
                    all_dependencies_complete = True
                    for dependency in batch_task["batch_task_spec"]["dependencies"]:
                        if self.task_order_tree[dependency]["status"] != "COMPLETED":
                            self.logger.log(
                                12,
                                (
                                    "Skipping task"
                                    f" {order_id} ({batch_task['task_id']}) as"
                                    f" dependency {dependency} has not completed"
                                ),
                            )
                            all_dependencies_complete = False
                            continue
                        self.logger.info(
                            "All dependencies for task"
                            f" {order_id} ({batch_task['task_id']}) have completed"
                        )
                    if not all_dependencies_complete:
                        continue

                # Check if the task has already been triggered
                if batch_task["status"] == "NOT_STARTED":
                    # Create a new thread to run the task. Pass an event into the thread so we can handle timeouts
                    batch_task["executing_thread"] = None
                    e = threading.Event()
                    thread = threading.Thread(
                        target=self.task_runner,
                        args=(batch_task, e),
                        name=f"{batch_task['task_id']}_parent",
                    )
                    # Start the thread
                    thread.start()

                    self.logger.info(
                        f"Spawned thread for task {order_id} ({batch_task['task_id']})"
                    )
                    batch_task["status"] = "RUNNING"
                    batch_task["start_time"] = time.time()
                    batch_task["thread"] = thread
                    batch_task["kill_event"] = e

                    # Sleep 1 second to allow the thread to start
                    time.sleep(1)

                # Check if the task has completed
                if batch_task["status"] == "RUNNING":
                    # Check if the task has timed out
                    if (
                        time.time() - batch_task["start_time"] > batch_task["timeout"]
                        and batch_task["thread"].is_alive()
                    ):
                        self.logger.error(
                            f"Task {order_id} ({batch_task['task_id']}) has timed out"
                        )
                        logged = True
                        batch_task["status"] = "TIMED_OUT"
                        # Send event to the thread to kill it
                        self.logger.debug(
                            f"Sending kill event to task {order_id} ({batch_task['task_id']})"
                        )
                        batch_task["kill_event"].set()
                        # Wait for the thread to return
                        batch_task["thread"].join()
                        self.logger.debug(
                            f"Task {order_id} ({batch_task['task_id']}) has been killed"
                        )
                        batch_task["result"] = False

                    # Check whether the thread is actually still running.
                    # If it has died uncleanly, then we need to set the appropriate statuses for it
                    if (
                        not batch_task["thread"].is_alive()
                        and batch_task["status"] != "TIMED_OUT"
                    ):
                        self.logger.error(
                            f"Task {order_id} ({batch_task['task_id']}) has failed"
                        )
                        logged = True
                        batch_task["status"] = "FAILED"
                        batch_task["result"] = False

                if batch_task["status"] == "COMPLETED" and "thread" in batch_task:
                    batch_task["thread"].join()
                    if not logged:
                        self.logger.info(
                            f"Task {order_id} ({batch_task['task_id']}) has completed"
                        )
                        logged = True
                    else:
                        self.logger.log(
                            12,
                            f"Task {order_id} ({batch_task['task_id']}) has completed",
                        )

                # Add a generic message to show the task failed
                if batch_task["status"] == "FAILED":
                    if not logged:
                        self.logger.error(
                            f"Task {order_id} ({batch_task['task_id']}) has failed"
                        )
                        logged = True
                    else:
                        self.logger.log(
                            12, f"Task {order_id} ({batch_task['task_id']}) has failed"
                        )

                # Handle instances where we timed out or failed, and we should continue on fail
                if (
                    batch_task["status"] in ["TIMED_OUT", "FAILED"]
                    and batch_task["continue_on_fail"]
                ):
                    self.logger.info(
                        f"Task {order_id} ({batch_task['task_id']}) has failed, but"
                        " continuing on fail"
                    )
                    batch_task["status"] = "COMPLETED"
                    batch_task["result"] = False
                    logged = True

                batch_task["logged_status"] = logged

            # Check if there are any tasks that are still in RUNNING state, if not then we are done
            running_tasks = [
                task
                for task in self.task_order_tree.values()
                if task["status"] == "RUNNING"
            ]
            if len(running_tasks) == 0:
                break

            # Sleep 5 seconds before checking again
            time.sleep(5)

            # Check if we have been asked to kill the batch
            if kill_event and kill_event.is_set():
                self.logger.info("Kill event received, stopping threads")
                for _order_id, batch_task in self.task_order_tree.items():
                    if batch_task["status"] == "RUNNING":
                        batch_task["kill_event"].set()
                        # Give the thread 2 seconds to stop, otherwise we kill it
                        batch_task["thread"].join(2)
                        if batch_task["thread"].is_alive():
                            batch_task["thread"].cancel()

                        batch_task["status"] = "KILLED"

        # Check if any tasks have failed
        failed_tasks = [
            task
            for task__ in self.task_order_tree.values()
            if task__["status"] != "COMPLETED" or task__["result"] is False
        ]
        if len(failed_tasks) == 0:
            self.overall_result = True

        self.logger.info(f"Batch completed with result {self.overall_result}")

        if self.overall_result:
            return self.return_result(0, "All batch tasks completed successfully")

        return self.return_result(1, "Batch failed", ex)

    def task_runner(self, batch_task: dict, event: threading.Event) -> None:
        """Run the task in a separate thread.

        Args:
            batch_task (dict): The task to run
            event (threading.Event): The event to use to kill the thread
        """
        self.logger.info(f"Running task {batch_task['task_id']}")
        with ThreadPoolExecutor(
            max_workers=1, thread_name_prefix=batch_task["task_id"]
        ) as executor:
            while True:
                if batch_task["executing_thread"] is None:
                    self.logger.log(
                        12,
                        f"Spawning task handler for {batch_task['task_id']} with timeout of {batch_task['timeout']}",
                    )
                    # Spawn the task as it's own thread
                    batch_task["executing_thread"] = [
                        executor.submit(
                            self._execute, batch_task["task_handler"], event
                        )
                    ]
                else:
                    self.logger.log(
                        12, f"Checking task handler for {batch_task['task_id']}"
                    )
                    # Check to see if the thread is still alive
                    if (
                        not batch_task["executing_thread"][0].running()
                        and batch_task["status"] != "TIMED_OUT"
                    ):
                        # Get the returncode from the thread

                        batch_task["result"] = batch_task["executing_thread"][
                            0
                        ].result()

                        if batch_task["result"]:
                            batch_task["status"] = "COMPLETED"
                        else:
                            batch_task["status"] = "FAILED"
                        self._log_task_result(
                            batch_task["status"],
                            batch_task["batch_task_spec"]["order_id"],
                            batch_task["task_id"],
                        )
                        break

                    # Check if we have been asked to kill the thread
                    if event.is_set():
                        self.logger.log(
                            12, f"Killing task handler for {batch_task['task_id']}"
                        )
                        # Kill the thread and all it's child processes
                        batch_task["executing_thread"][0].cancel()
                        executor.shutdown(wait=False)
                        self._log_task_result(
                            "FAILED",
                            batch_task["batch_task_spec"]["order_id"],
                            batch_task["task_id"],
                        )

                        break

                    # Wait for the thread to complete
                    self.logger.log(
                        12, f"Waiting for task handler for {batch_task['task_id']}"
                    )
                    wait(batch_task["executing_thread"], timeout=2)

            batch_task["end_time"] = time.time()

    def _log_task_result(self, status: str, order_id: str, task_id: str) -> None:
        self.logger.info(
            f"{BATCH_TASK_LOG_MARKER}: ORDER_ID::{order_id}::TASK::{task_id}::{status}"
        )

    def _execute(
        self, task_handler: TaskHandler, event: threading.Event | None = None
    ) -> bool:  #
        result = False
        try:
            result = task_handler.run(kill_event=event)
        except Exception as ex:  # pylint: disable=broad-exception-caught
            task_handler.return_result(1, str(ex), ex)
            self.logger.error(f"[{task_handler.task_id}] Failed to run task")
            # Log the call stack
            self.logger.exception(ex)
            result = False

        self.logger.info(f"[{task_handler.task_id}] Returned {result}")
        return result
