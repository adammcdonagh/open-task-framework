"""Logging module."""

import json
import logging
import os
import re
from datetime import datetime

OTF_LOG_FORMAT = (
    "%(asctime)s — %(levelname)s - %(name)s - %(filename)s:%(lineno)s [%(threadName)s]"
    " — %(message)s"
)
LOG_DIRECTORY = (
    "logs"
    if os.environ.get("OTF_LOG_DIRECTORY") is None
    else os.environ.get("OTF_LOG_DIRECTORY")
)


class JSONFormatter(logging.Formatter):
    """JSON formatter.

    This will take a log message and output it as JSON rather than plain text

    Args:
        logging (logging.Formatter): The logging formatter to use
    """

    # Add an init that takes task_id
    def __init__(self, task_id: str | None):
        """Initialise the formatter.

        Args:
            task_id (str | None): The Task ID. Defaults to None.
        """
        super().__init__()
        self.task_id = task_id

    def format(self, record):
        """Format the log message as JSON."""
        task_id = self.task_id
        run_id = os.environ.get("OTF_RUN_ID")
        message = record.msg
        json_log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "function": record.funcName,
            "file": f"{record.pathname}:{record.lineno}",
            "thread": record.threadName,
            "logger": record.name,
            "message": message,
            "task_id": task_id,
            "run_id": run_id,
        }
        record.msg = json.dumps(json_log_record)
        return super().format(record)


def _define_log_file_name(task_id: str | None, task_type: str | None) -> str:
    global LOG_DIRECTORY  # pylint: disable=global-statement
    LOG_DIRECTORY = (
        "logs"
        if os.environ.get("OTF_LOG_DIRECTORY") is None
        else os.environ.get("OTF_LOG_DIRECTORY")
    )

    # Set a custom handler to write to a specific file
    # Get the appropriate timestamp for the log file
    prefix = datetime.now().strftime("%Y%m%d-%H%M%S.%f")[:-3]
    if os.environ.get("OTF_LOG_RUN_PREFIX") is not None:
        # This might have already been set by task_run, so pull it
        # in from the environment
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
    # Set the log format
    formatter = logging.Formatter(OTF_LOG_FORMAT)

    # Check if there's a root logger already
    if not logging.getLogger().hasHandlers():
        sfh = logging.StreamHandler()

        formatter = (
            JSONFormatter(task_id)
            if os.environ.get("OTF_LOG_JSON") and os.environ.get("OTF_LOG_JSON") == "1"
            else formatter
        )

        sfh.setFormatter(formatter)

        # Set the root logger
        logging.basicConfig(
            format=OTF_LOG_FORMAT,
            level=logging.INFO,
            handlers=[
                sfh,
            ],
        )

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

    otf_logger.debug("Logging initialised")

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
        and re.match(r"\d{8}-\d{6}\.\d{3}", f.split("_")[0])
    ]

    # Unless another date is given, only look at today's logs
    batch_resume_date = datetime.now().date()
    if os.environ.get("OTF_BATCH_RESUME_LOG_DATE"):
        batch_resume_date = datetime.strptime(
            os.environ.get("OTF_BATCH_RESUME_LOG_DATE"), "%Y%m%d"
        ).date()

    # Remove any logs that are not from the given date
    log_files = [
        f
        for f in log_files
        if datetime.strptime(f.split("_")[0], "%Y%m%d-%H%M%S.%f").date()
        == batch_resume_date
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
    log_file_name = None
    # Close the log file
    for handler in logger__.handlers:
        # If its a task file handler, and the log file still exists
        if isinstance(handler, TaskFileHandler) and os.path.exists(
            handler.baseFilename
        ):
            log_file_name = handler.baseFilename

    log_handlers = []

    if log_file_name:
        new_log_filename = None
        if result:
            new_log_filename = log_file_name.replace("_running", "")
        elif result is not None and not result:
            new_log_filename = log_file_name.replace("_running", "_failed")

        # Loop through every logger that exists and has a handler of this filename, and
        # call the close method on it. Only the last one should rename the file
        for logger_ in list(logging.Logger.manager.loggerDict.values()):
            if isinstance(logger_, logging.Logger):
                for handler in logger_.handlers:
                    if (
                        isinstance(handler, TaskFileHandler)
                        and handler.baseFilename == log_file_name
                    ):
                        log_handlers.append(handler)
                        handler.close()

        # Now everything is closed, we can rename the log file
        # If result is True, then rename the file and remove _running from the name
        if new_log_filename:
            os.rename(log_file_name, new_log_filename)

            # Change the basename of the handler to match the new filename, in case it
            # wants to log anything else
            for handler in log_handlers:
                handler.baseFilename = new_log_filename


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
