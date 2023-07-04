"""Logging module."""
import logging
import os
import re
from datetime import datetime

OTF_LOG_FORMAT = "%(asctime)s — %(name)s [%(threadName)s] — %(levelname)s — %(message)s"
LOG_DIRECTORY = (
    "logs"
    if os.environ.get("OTF_LOG_DIRECTORY") is None
    else os.environ.get("OTF_LOG_DIRECTORY")
)


def _define_log_file_name(task_id: str | None, task_type: str | None) -> str:
    global LOG_DIRECTORY  # pylint: disable=global-statement
    LOG_DIRECTORY = (
        "logs"
        if os.environ.get("OTF_LOG_DIRECTORY") is None
        else os.environ.get("OTF_LOG_DIRECTORY")
    )

    # Set a custom handler to write to a specific file
    # Get the appropriate timestamp for the log file
    prefix = datetime.now().strftime("%Y%m%d-%H%M%S.%f")
    if os.environ.get("OTF_LOG_RUN_PREFIX") is not None:
        prefix = f"{os.environ.get('OTF_LOG_RUN_PREFIX')}"
    else:
        os.environ["OTF_LOG_RUN_PREFIX"] = prefix

    if task_type:
        task_type = f"_{task_type}"
    else:
        task_type = ""

    directory = f"{LOG_DIRECTORY}"
    if os.environ.get("OTF_RUN_ID") is not None:
        directory = f"{directory}/{os.environ.get('OTF_RUN_ID')}"
        filename = f"{prefix}{task_type}_{task_id}_running.log"
    else:
        if task_id is None:
            task_id = "no_task_id"
        directory = f"{directory}/{task_id}"
        filename = f"{prefix}{task_type}_running.log"

    return f"{directory}/{filename}"


def init_logging(
    name: str, task_id: str | None = None, task_type: str | None = None
) -> logging.Logger:
    """Setup a logger with the custom format and output filename.

    Args:
        name (str): The name of the logger, usually the class name, but can also
        reference the thread, or batch task
        task_id (str | None, optional): The Task ID. Defaults to None.
        task_type (str | None, optional): The Task Type, either T for transfer, E for execution or B for batch. Defaults to None.

    Returns:
        logging.Logger: The logger object used for logging output.
    """
    # Check if there's a root logger already
    if not logging.getLogger().hasHandlers():
        # Set the root logger
        logging.basicConfig(
            format=OTF_LOG_FORMAT,
            level=logging.INFO,
            handlers=[
                logging.StreamHandler(),
            ],
        )

    # Set the log format
    formatter = logging.Formatter(OTF_LOG_FORMAT)

    # Create a unique logger object for this task
    if not task_id:
        otf_logger = logging.getLogger(f"{name}")
    else:
        otf_logger = logging.getLogger(f"{name}.{task_id}")

    # Set verbosity
    otf_logger.setLevel(logging.getLogger().getEffectiveLevel())
    # Ensure the logger is at least at INFO level
    if otf_logger.getEffectiveLevel() > logging.INFO:
        otf_logger.setLevel(logging.INFO)

    # If the log level is set in the environment, then use that
    if os.environ.get("OTF_LOG_LEVEL") is not None:
        otf_logger.setLevel(os.environ["OTF_LOG_LEVEL"])

    # If OTF_NO_LOG is set, then don't create the handler
    if os.environ.get("OTF_NO_LOG") is not None or not task_id:
        return otf_logger

    log_file_name = _define_log_file_name(task_id, task_type)

    tfh = TaskFileHandler(log_file_name)
    # Check there are no handlers of this class already with the same baseFilename
    if not any(
        isinstance(handler, TaskFileHandler)
        and handler.baseFilename == tfh.baseFilename
        for handler in otf_logger.handlers
    ):
        otf_logger.addHandler(tfh)
        tfh.setFormatter(formatter)

    otf_logger.info("Logging initialised")

    return otf_logger


def get_latest_log_file(task_id: str, task_type: str) -> str | None:
    """Get the latest log file for this task.

    Args:
        task_id (str): The Task ID
        task_type (str): The task type

    Returns:
        str | None: Either the latest log file name, or None if there are no previous
        logs
    """
    log_file_name = _define_log_file_name(task_id, task_type)
    # Obviously the date/time in the filename needs to be replaced with the latest
    # log file
    # Replace the prefix with a regex wildcard
    log_file_name = log_file_name.replace(os.environ["OTF_LOG_RUN_PREFIX"], ".*")
    # Also, we don't want to limit to running jobs, only failed or successful ones
    log_file_name = log_file_name.replace("_running", "(_failed)*")

    if not os.path.exists(os.path.dirname(log_file_name)):
        return None

    # List the contents of the directory
    log_files = os.listdir(os.path.dirname(log_file_name))
    # Filter the list to only include files that match the log_file_name, and contain a valid date/time prefix
    log_files = [
        f
        for f in log_files
        if re.match(os.path.basename(log_file_name), f)
        and re.match(r"\d{8}-\d{6}\.\d{6}", f.split("_")[0])
    ]

    # Sort the list by the date/time in the filename
    log_files.sort(key=lambda x: datetime.strptime(x.split("_")[0], "%Y%m%d-%H%M%S.%f"))
    # Get the latest log file
    if log_files:
        log_file_name = f"{os.path.dirname(log_file_name)}/{log_files[-1]}"
        logger.info(f"Latest log file: {log_file_name}")
        # If the last log was a failure, return that, otherwise we just start from scratch, so return nothing
        if "_failed" in log_file_name:
            return log_file_name

        logger.info("No failed log file found. Starting from scratch.")

    return None


def _mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def close_log_file(logger__: logging.Logger, result: bool = False) -> None:
    """Closes the log file handle.

    Closes the log file, and renames the log file using the handler, based on the result
    argument

    Args:
        logger__ (_type_): The logger that needs to be closed.
        result (bool, optional): The return status of the task that was run. Defaults to False.
    """
    # Close the log file
    for handler in logger__.handlers:
        # If its a task file handler, and the log file still exists
        if isinstance(handler, TaskFileHandler) and os.path.exists(
            handler.baseFilename
        ):
            handler.close(result)


logger = init_logging(__name__)


# mypy: ignore-errors
class TaskFileHandler(logging.FileHandler):
    """Custom file handler to ensure logs get correct naming.

    This class handles the closing of log files. It will rename based on the argument
    passed into the close method.
    """

    def __init__(self, filename, mode="a", encoding=None, delay=True):
        """Create the log directory.

        Overrides the default __init_ to ensure that the path containing the log exists
        before attempting to write to it.

        """
        _mkdir(os.path.dirname(filename))
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)

    # Override the close method
    def close(self, result: bool = False):
        """Close the file handle for the log file.

        Args:
            result (bool, optional): Uodate the filename of the log file to match the
            result status. If set to False, then the _running suffix in the filename
            will be replaced with _failed, otherwise "". Defaults to False.
        """
        logging.FileHandler.close(self)
        # If result is True, then rename the file and remove _running from the name
        if result:
            os.rename(self.baseFilename, self.baseFilename.replace("_running", ""))
        elif result is not None and not result:
            # Replace _running with _failed
            os.rename(
                self.baseFilename, self.baseFilename.replace("_running", "_failed")
            )
