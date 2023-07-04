"""Main class."""
import opentaskpy.otflogging
from opentaskpy.config.loader import ConfigLoader
from opentaskpy.config.schemas import validate_execution_json, validate_transfer_json
from opentaskpy.taskhandlers.batch import Batch
from opentaskpy.taskhandlers.execution import Execution
from opentaskpy.taskhandlers.transfer import Transfer

GLOBAL_VERBOSITY = 1


class TaskRun:  # pylint: disable=too-few-public-methods
    """Do the actual work.

    Class responsible for doing all the work. The TaskRun class
    parses config, loads variables and triggers the work
    """

    def __init__(self, task_id: str, config_dir: str) -> None:
        """Create the TaskRun object.

        Initialises the logging.

        Args:
            task_id (str): ID of the task being triggered
            config_dir (str): Path to the config directory
        """
        self.logger = opentaskpy.otflogging.init_logging(__name__)
        self.task_id = task_id
        self.config_dir = config_dir
        self.active_task_definition = None
        # Create a config loader object
        self.config_loader = ConfigLoader(self.config_dir)

    def run(self) -> bool:
        """Run the task.

        Load all variables, validate the task definitions, and
        trigger the run of the task itself.

        Returns:
            bool: The result of running the task, True is good, False is bad
        """
        global_variables = self.config_loader.get_global_variables()

        # Populate the task definition with the global variables
        active_task_definition = self.config_loader.load_task_definition(self.task_id)

        # Handle any overrides from the command line

        result = False

        # Now we've loaded the config, determine what to do with it
        if "type" not in active_task_definition:
            self.logger.error("Invalid task configuration. Cannot continue")
            return False

        if active_task_definition["type"] == "transfer":
            # Hand off to the transfer module
            self.logger.log(12, "Transfer")
            # Validate the schema
            if not validate_transfer_json(active_task_definition):
                self.logger.error("JSON format does not match schema")
                return False

            transfer = Transfer(global_variables, self.task_id, active_task_definition)

            result = transfer.run()

        elif active_task_definition["type"] == "execution":
            # Hand off to the execuiton module
            self.logger.log(12, "Execution")

            # Validate the schema
            if not validate_execution_json(active_task_definition):
                self.logger.error("JSON format does not match schema")
                return False

            execution = Execution(
                global_variables, self.task_id, active_task_definition
            )

            result = execution.run()

        elif active_task_definition["type"] == "batch":
            # Hand off to the batch module
            self.logger.log(12, "Batch")
            batch = Batch(
                global_variables,
                self.task_id,
                active_task_definition,
                self.config_loader,
            )
            result = batch.run()

        else:
            self.logger.error("Unknown task type!")

        self.logger.info(f"Task completed with result: {result}")
        return result
