#!/bin/env python3

import argparse
import logging
import os
from datetime import datetime

from opentaskpy import task_run
from opentaskpy.logging import OTF_LOG_FORMAT

CONFIG_PATH = f"{os.getcwd()}/cfg"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t", "--taskId", help="Name of the JSON config to run", type=str, required=True
    )
    parser.add_argument(
        "-r",
        "--runId",
        help="Unique identifier to correlate logs with. e.g. if being triggered by an external scheduler",
        type=str,
        required=False,
    )
    parser.add_argument("-v", "--verbosity", help="Increase verbosity", type=int)
    parser.add_argument(
        "-c", "--configDir", help="Directory containing task configurations", type=str
    )

    args = parser.parse_args()

    if args.configDir:
        global CONFIG_PATH
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
    task_run_obj = task_run.TaskRun(args.taskId, CONFIG_PATH)

    try:
        task_run_obj.run()
    except Exception as e:
        logger.error(f"Error running task: {e}")
        if logger.getEffectiveLevel() <= 12:
            raise e


if __name__ == "__main__":
    main()
