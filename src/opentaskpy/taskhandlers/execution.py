from concurrent.futures import ThreadPoolExecutor, wait
from os import environ

import opentaskpy.logging
from opentaskpy.remotehandlers.ssh import SSHExecution
from opentaskpy.taskhandlers.taskhandler import TaskHandler

TASK_TYPE = "E"


class Execution(TaskHandler):
    def __init__(self, task_id, execution_definition):
        self.task_id = task_id
        self.execution_definition = execution_definition
        self.remote_handlers = None
        self.overall_result = False

        self.logger = opentaskpy.logging.init_logging(
            "opentaskpy.taskhandlers.execution", self.task_id, TASK_TYPE
        )

    def return_result(self, status, message=None, exception=None):
        if message:
            if status == 0:
                self.logger.info(message)
            else:
                self.logger.error(message)

        if status == 0:
            self.overall_result = True

        # Delete the remote connection objects
        if self.remote_handlers:
            for remote_handler in self.remote_handlers:

                self.logger.log(
                    12,
                    f"[{remote_handler.remote_host}] Closing source connection for {remote_handler}",
                )
                remote_handler.tidy()

        # Close the file handler
        self.logger.info("Closing log file handler")
        opentaskpy.logging.close_log_file(self.logger, self.overall_result)

        # Throw an exception if we have one
        if exception:
            raise exception(message)

        return status == 0

    def _set_remote_handlers(self):
        # Based on the transfer definition, determine what to do first
        # Based on the source protocol pick the appropriate remote handler
        if self.execution_definition["protocol"]["name"] == "ssh":
            # For each host, create a remote handler
            self.remote_handlers = []
            for host in self.execution_definition["hosts"]:
                self.remote_handlers.append(
                    SSHExecution(host, self.execution_definition)
                )

    def run(self, kill_event=None):
        self.logger.info("Running execution")
        environ["OTF_TASK_ID"] = self.task_id

        self._set_remote_handlers()

        # This is where we could potentially be waiting for a while. So,
        # for each remote handler, we should spawn a new thread to run
        # the command. Then we can wait for all threads to complete.

        ex = None

        with ThreadPoolExecutor(len(self.remote_handlers)) as executor:

            futures = [
                executor.submit(
                    self._execute, self.execution_definition, remote_handler
                )
                for remote_handler in self.remote_handlers
            ]

            while True:
                try:
                    # Sleep 5 seconds for each loop
                    wait(futures, timeout=5)
                    self.logger.info("Waiting for threads to complete...")

                except TimeoutError:
                    pass

                if kill_event and kill_event.is_set():
                    self.logger.info("Kill event received, stopping threads")

                    # Before we terminate everything locally, we need to make sure that the processes
                    # on the remote hosts are terminated as well
                    for remote_handler in self.remote_handlers:
                        self.logger.info(
                            f"Killing remote processes on {remote_handler.remote_host}"
                        )
                        remote_handler.kill()

                    executor.shutdown(wait=False)
                    return self.return_result(
                        1, "Execution(s) failed - Kill signal received"
                    )

                # Break once all threads are done
                if all(future.done() for future in futures):
                    break

            # Check the results
            failures = False
            for future in futures:
                try:
                    result = future.result()
                    if not result:
                        failures = True
                except Exception as e:
                    self.overall_result = False
                    ex = e
                    self.logger.error("Thread returned exception")

            if not failures:
                self.overall_result = True

        if self.overall_result:
            return self.return_result(0, "All executions completed successfully")
        else:
            return self.return_result(1, "Execution(s) failed", ex)

    def _execute(self, spec, remote_handler):
        result = remote_handler.execute(spec["command"])
        self.logger.info(f"[{remote_handler.remote_host}] Execution returned {result}")
        return result

    # Destructor to handle when the execution is finished. Make sure the log file
    # gets renamed as appropriate
    def __del__(self):
        self.logger.debug("Execution object deleted")
        # Close the file handler
        self.logger.info("Closing log file handler")
        opentaskpy.logging.close_log_file(self.logger, self.overall_result)
