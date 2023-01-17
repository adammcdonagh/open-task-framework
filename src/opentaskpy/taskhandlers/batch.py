import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from os import environ

from opentaskpy.taskhandlers.execution import Execution
from opentaskpy.taskhandlers.taskhandler import TaskHandler
from opentaskpy.taskhandlers.transfer import Transfer

logger = logging.getLogger("opentaskpy.taskhandlers.batch")

DEFAULT_TASK_TIMEOUT = 300
DEFAULT_TASK_CONTINUE_ON_FAIL = False
DEFAULT_TASK_RETRY_ON_RERUN = False
DEFAULT_TASK_EXIT_CODE = 0


class Batch(TaskHandler):
    def __init__(self, task_id, batch_definition, config_loader):
        self.task_id = task_id
        self.batch_definition = batch_definition
        self.config_loader = config_loader
        self.tasks = dict()
        self.task_order_tree = dict()

        # Parse the batch definition and create the appropriate tasks to run
        # in the correct order, based on the dependencies specified
        for task in self.batch_definition["tasks"]:
            # Load the definition for the task
            task_definition = self.config_loader.load_task_definition(task["task_id"])
            order_id = task["order_id"]

            # Add it to the list of tasks
            self.tasks[order_id] = task_definition

            # Create the appropriate task handler based on the task type
            if task_definition["type"] == "execution":
                task_handler = Execution(task["task_id"], task_definition)
            elif task_definition["type"] == "transfer":
                task_handler = Transfer(task["task_id"], task_definition)
            elif task_definition["type"] == "batch":
                task_handler = Batch(task["task_id"], task_definition, self.config_loader)
            else:
                raise Exception("Unknown task type")

            # Set the timeout for the task
            timeout = None
            if "timeout" in task:
                timeout = task["timeout"]
            else:
                timeout = DEFAULT_TASK_TIMEOUT

            # Same for continue on fail
            continue_on_fail = None
            if "continue_on_fail" in task:
                continue_on_fail = task["continue_on_fail"]
            else:
                continue_on_fail = DEFAULT_TASK_CONTINUE_ON_FAIL

            # Same for retry on rerun
            retry_on_rerun = None
            if "retry_on_rerun" in task:
                retry_on_rerun = task["retry_on_rerun"]
            else:
                retry_on_rerun = DEFAULT_TASK_RETRY_ON_RERUN

            # If this task has no dependencies, then it can sit at the top level of the tree
            if "dependencies" not in task:
                self.task_order_tree[order_id] = {
                    "task_id": task["task_id"],
                    "task": task_definition,
                    "task_handler": task_handler,
                    "timeout": timeout,
                    "continue_on_fail": continue_on_fail,
                    "retry_on_rerun": retry_on_rerun,
                    "status": "NOT_STARTED",
                    "children": [],
                }

        # Debug to show the structure of the tree
        logger.debug(f"Task order tree: {self.task_order_tree}")

    def _set_remote_handlers(self):
        pass

    def return_result(self, status, message=None, exception=None):
        if message:
            if status == 0:
                logger.info(message)
            else:
                logger.error(message)

        # Throw an exception if we have one
        if exception:
            raise exception(message)

        return status == 0

    def run(self):
        logger.info("Running batch")
        environ["OTF_TASK_ID"] = self.task_id

        # This is where we could potentially be waiting for a while. So,
        # for each task handler, we should spawn a new thread to run
        # the command. Then we can wait for all threads to complete.

        overall_result = True

        while True:
            # Loop through every task in the tree
            for order_id, batch_task in self.task_order_tree.items():
                task = batch_task["task"]

                logger.log(12, f"Checking task {order_id} ({batch_task['task_id']})")

                # Check if there are dependencies for this task that have not yet completed, if so then we skip it
                if "dependencies" in task:
                    for dependency in task["dependencies"]:
                        if self.task_order_tree[dependency]["status"] != "COMPLETED":
                            logger.log(
                                12,
                                f"Skipping task {order_id} ({batch_task['task_id']}) as dependency {dependency} has not completed",
                            )
                            continue

                # Check if the task has already been triggered
                if batch_task["status"] == "NOT_STARTED":
                    # Create a new thread to run the task. Pass an event into the thread so we can handle timeouts
                    batch_task["executing_thread"] = None
                    e = threading.Event()
                    thread = threading.Thread(
                        target=self.task_runner, args=(batch_task, e), name=f"{batch_task['task_id']}_parent"
                    )
                    # Start the thread
                    thread.start()

                    logging.info(f"Spawned thread for task {order_id} ({batch_task['task_id']})")
                    batch_task["status"] = "RUNNING"
                    batch_task["start_time"] = time.time()
                    batch_task["thread"] = thread
                    batch_task["kill_event"] = e

                # Check if the task has completed
                if batch_task["status"] == "RUNNING":
                    # Check if the task has timed out
                    if (
                        time.time() - batch_task["start_time"] > batch_task["timeout"]
                        and batch_task["thread"].is_alive()
                    ):
                        logging.error(f"Task {order_id} ({batch_task['task_id']}) has timed out")
                        batch_task["status"] = "TIMED_OUT"
                        # Send event to the thread to kill it
                        batch_task["kill_event"].set()
                        batch_task["thread"].join()
                        batch_task["result"] = False

                if batch_task["status"] == "COMPLETED":
                    logging.info(f"Task {order_id} ({batch_task['task_id']}) has completed")

            # Check if there are any tasks that are still in RUNNING state, if not then we are done
            running_tasks = [task for task in self.task_order_tree.values() if task["status"] == "RUNNING"]
            if len(running_tasks) == 0:
                break

            # Sleep 5 seconds before checking again
            time.sleep(5)

        # Check if any tasks have failed
        failed_tasks = [task for task in self.task_order_tree.values() if task["status"] == "FAILED"]
        if len(failed_tasks) > 0:
            overall_result = False

        return overall_result

    def task_runner(self, batch_task, event):
        # Thread to trigger the task itself

        logger.info(f"Running task {batch_task['task_id']}")
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix=batch_task["task_id"]) as executor:

            while True:
                if batch_task["executing_thread"] is None:
                    logger.log(12, f"Spawning task handler for {batch_task['task_id']}")
                    # Spawn the task as it's own thread
                    batch_task["executing_thread"] = executor.submit(self._execute, batch_task["task_handler"])
                else:
                    logger.log(12, f"Checking task handler for {batch_task['task_id']}")
                    # Check to see if the thread is still alive
                    if not batch_task["executing_thread"].running():
                        # Get the returncode from the thread
                        batch_task["result"] = batch_task["executing_thread"].result(timeout=1)
                        if batch_task["result"]:
                            batch_task["status"] = "COMPLETED"
                        else:
                            batch_task["status"] = "FAILED"
                        break
                    else:
                        # Check if we have been asked to kill the thread
                        if event.is_set():
                            logger.log(12, f"Killing task handler for {batch_task['task_id']}")
                            # Kill the thread
                            batch_task["executing_thread"].cancel()
                            break
                        # Wait for the thread to complete
                        logger.log(12, f"Waiting for task handler for {batch_task['task_id']}")
                        wait(batch_task["executing_thread"], timeout=5)

            batch_task["end_time"] = time.time()

    def _execute(self, remote_handler):
        result = remote_handler.run()
        logger.info(f"[{remote_handler.task_id}] Returned {result}")
        return result
