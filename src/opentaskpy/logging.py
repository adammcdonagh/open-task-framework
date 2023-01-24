import logging
import os
from datetime import datetime

OTF_LOG_FORMAT = "%(asctime)s — %(name)s [%(threadName)s] — %(levelname)s — %(message)s"
LOG_DIRECTORY = (
    "logs"
    if os.environ.get("OTF_LOG_DIRECTORY") is None
    else os.environ.get("OTF_LOG_DIRECTORY")
)


def init_logging(name, task_id=None):

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
        logger = logging.getLogger(f"{name}")
    else:
        logger = logging.getLogger(f"{name}.{task_id}")

    # Set verbosity
    logger.setLevel(logging.getLogger().getEffectiveLevel())

    # If the log level is set in the environment, then use that
    if os.environ.get("OTF_LOG_LEVEL") is not None:
        logger.setLevel(os.environ.get("OTF_LOG_LEVEL"))

    # If OTF_NO_LOG is set, then don't create the handler
    if os.environ.get("OTF_NO_LOG") is not None or not task_id:
        return logger

    # Set a custom handler to write to a specific file
    # Get the appropriate timestamp for the log file
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S.%f")
    if os.environ.get("OTF_LOG_RUN_PREFIX") is not None:
        timestamp = os.environ.get("OTF_LOG_RUN_PREFIX")
    else:
        os.environ["OTF_LOG_RUN_PREFIX"] = timestamp

    directory = f"{LOG_DIRECTORY}"
    if os.environ.get("OTF_RUN_ID") is not None:
        directory = f"{directory}/{os.environ.get('OTF_RUN_ID')}"
        filename = f"{timestamp}_{task_id}_running.log"
    else:
        if task_id is None:
            task_id = "no_task_id"
        directory = f"{directory}/{task_id}"
        filename = f"{timestamp}_running.log"

    tfh = TaskFileHandler(f"{directory}/{filename}")
    # Check there are no handlers of this class already with the same baseFilename
    if not any(
        isinstance(handler, TaskFileHandler)
        and handler.baseFilename == tfh.baseFilename
        for handler in logger.handlers
    ):
        logger.addHandler(tfh)
        tfh.setFormatter(formatter)

    return logger


def _mkdir(path):
    """http://stackoverflow.com/a/600612/190597 (tzot)"""

    os.makedirs(path, exist_ok=True)  # Python>3.2


class TaskFileHandler(logging.FileHandler):
    def __init__(self, filename, mode="a", encoding=None, delay=0):
        _mkdir(os.path.dirname(filename))
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)

    # Override the close method
    def close(self, result=None):
        logging.FileHandler.close(self)
        # If result is True, then rename the file and remove _running from the name
        if result:
            os.rename(self.baseFilename, self.baseFilename.replace("_running", ""))
        elif result is not None and not result:
            # Replace _running with _failed
            os.rename(
                self.baseFilename, self.baseFilename.replace("_running", "_failed")
            )
