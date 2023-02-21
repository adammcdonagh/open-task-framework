import opentaskpy.logging
from opentaskpy.config.loader import ConfigLoader
from opentaskpy.config.schemas import validate_execution_json, validate_transfer_json
from opentaskpy.taskhandlers.batch import Batch
from opentaskpy.taskhandlers.execution import Execution
from opentaskpy.taskhandlers.transfer import Transfer

GLOBAL_VERBOSITY = 1


class TaskRun:
    def __init__(self, task_id, config_dir):
        self.logger = opentaskpy.logging.init_logging(__name__)
        self.task_id = task_id
        self.config_dir = config_dir
        self.active_task_definition = None
        self.config_loader = None

    def run(self):
        # Create a config loader object
        self.config_loader = ConfigLoader(self.config_dir)

        # Populate the task definition with the global variables
        active_task_definition = self.config_loader.load_task_definition(self.task_id)

        result = False

        # Now we've loaded the config, determine what to do with it
        if "type" not in active_task_definition:
            self.logger.error("Invalid task configuration. Cannot continue")
            return False
        elif active_task_definition["type"] == "transfer":
            # Hand off to the transfer module
            self.logger.log(12, "Transfer")
            # Validate the schema
            if not validate_transfer_json(active_task_definition):
                self.logger.error("JSON format does not match schema")
                return False

            transfer = Transfer(self.task_id, active_task_definition)

            result = transfer.run()

        elif active_task_definition["type"] == "execution":
            # Hand off to the execuiton module
            self.logger.log(12, "Execution")

            # Validate the schema
            if not validate_execution_json(active_task_definition):
                self.logger.error("JSON format does not match schema")
                return False

            execution = Execution(self.task_id, active_task_definition)

            result = execution.run()

        elif active_task_definition["type"] == "batch":
            # Hand off to the batch module
            self.logger.log(12, "Batch")
            batch = Batch(self.task_id, active_task_definition, self.config_loader)
            result = batch.run()

        else:
            self.logger.error("Unknown task type!")

        self.logger.info(f"Task completed with result: {result}")
        return result
