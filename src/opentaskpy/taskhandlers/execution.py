import logging
from os import environ
from opentaskpy.remotehandlers.ssh import SSHExecution
from opentaskpy.taskhandlers.taskhandler import TaskHandler

logger = logging.getLogger("opentaskpy.taskhandlers.execution")


class Execution(TaskHandler):
    def __init__(self, task_id, execution_definition):
        self.task_id = task_id
        self.execution_definition = execution_definition
        self.remote_handlers = None

    def return_result(self, status, message=None, exception=None):
        if message:
            if status == 0:
                logger.info(message)
            else:
                logger.error(message)

        # Delete the remote connection objects
        if self.remote_handlers:
            for remote_handler in self.remote_handlers:
                logger.log(12, f"Closing source connection for {remote_handler}")
                remote_handler.tidy()

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
                self.remote_handlers.append(SSHExecution(host, self.execution_definition))

    def run(self):
        logger.info("Running execution")
        environ["OTF_TASK_ID"] = self.task_id

        self._set_remote_handlers()
