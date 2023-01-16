import logging
from concurrent.futures import ThreadPoolExecutor, wait
from os import environ

from opentaskpy.taskhandlers.execution import Execution
from opentaskpy.taskhandlers.taskhandler import TaskHandler
from opentaskpy.taskhandlers.transfer import Transfer

logger = logging.getLogger("opentaskpy.taskhandlers.batch")


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

            # If this task has no dependencies, then it can sit at the top level of the tree
            if "dependencies" not in task:
                self.task_order_tree[order_id] = {"task": task_definition, "task_handler": task_handler, "children": []}

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
        ex = None

        # Loop through all tasks in the tree that do not have a child, and trigger them
        for order_id, task in self.task_order_tree.items():
            if len(task["children"]) == 0:
                logger.info(f"Triggering task {order_id}")
                result = task["task_handler"].run()

                if not result:
                    overall_result = False

        return overall_result

        # with ThreadPoolExecutor(len(self.remote_handlers)) as executor:

        #     futures = [
        #         executor.submit(self._execute, self.execution_definition, remote_handler)
        #         for remote_handler in self.remote_handlers
        #     ]

        #     wait(futures)

        #     # Check the results
        #     for future in futures:
        #         try:
        #             result = future.result()
        #             if not result:
        #                 overall_result = False
        #         except Exception as e:
        #             overall_result = False
        #             ex = e
        #             logger.error("Thread returned exception")

        # if overall_result:
        #     return self.return_result(0, "All executions completed successfully")
        # else:
        #     return self.return_result(1, "Execution(s) failed", ex)

    def _execute(self, spec, remote_handler):
        result = remote_handler.execute(spec["command"])
        logger.info(f"[{remote_handler.remote_host}] Execution returned {result}")
        return result
