#!/bin/env python3
"""CLI script wrapper for handling env vars and triggering the TaskRun class."""

import argparse
import logging
import os
import sys
from datetime import datetime

from opentaskpy import taskrun  # type: ignore[attr-defined]
from opentaskpy.otflogging import OTF_LOG_FORMAT

CONFIG_PATH = f"{os.getcwd()}/cfg"


def main() -> None:
    """Parse args and call TaskRun class."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t", "--taskId", help="Name of the JSON config to run", type=str, required=True
    )
    parser.add_argument(
        "-r",
        "--runId",
        help=(
            "Unique identifier to correlate logs with. e.g. if being triggered by an"
            " external scheduler"
        ),
        type=str,
        required=False,
    )
    parser.add_argument("-v", "--verbosity", help="Increase verbosity", type=int)
    parser.add_argument(
        "-c", "--configDir", help="Directory containing task configurations", type=str
    )

    args = parser.parse_args()

    if args.configDir:
        global CONFIG_PATH  # pylint: disable=global-statement
        CONFIG_PATH = args.configDir

    # If given a runId, then set the environment variable
    if args.runId:
        os.environ["OTF_RUN_ID"] = args.runId

    os.environ["OTF_LOG_RUN_PREFIX"] = datetime.now().strftime("%Y%m%d-%H%M%S.%f")

    logging_level = logging.INFO
    if args.verbosity == 3:
        logging_level = logging.DEBUG
    elif args.verbosity == 2:
        logging_level = 11
    elif args.verbosity == 1:
        logging_level = 12

    logging.addLevelName(11, "VERBOSE2")
    logging.addLevelName(12, "VERBOSE1")

    logging.basicConfig(
        format=OTF_LOG_FORMAT,
        level=logging_level,
        handlers=[logging.StreamHandler()],
    )

    logger = logging.getLogger()
    logger.setLevel(logging_level)

    logger = logging.getLogger(__name__)
    logger.log(11, f"Log verbosity: {args.verbosity}")

    # Create the TaskRun object
    task_run_obj = taskrun.TaskRun(args.taskId, CONFIG_PATH)

    try:
        task_run_obj.run()
    except Exception as ex:  # pylint: disable=broad-exception-caught
        logger.error(f"Error running task: {ex}")
        if logger.getEffectiveLevel() <= 12:
            raise ex
        sys.exit(1)


if __name__ == "__main__":
    main()
