#!/bin/env python3
"""A simple script to do batch task validation."""

import argparse
import logging
import os
import sys

from opentaskpy.config.loader import ConfigLoader
from opentaskpy.otflogging import OTF_LOG_FORMAT

CONFIG_PATH = f"{os.getcwd()}/cfg"


def main(
    taskId: str | None = None,
    verbosity: int | None = None,
    configDir: str | None = None,
) -> bool:
    """Run the batch task validator.

    Args:
        taskId (str, optional): The task ID to validate. Defaults to None.
        verbosity (int, optional): The verbosity level. Defaults to None.
        configDir (str, optional): The config directory. Defaults to None.
    """
    # If given TaskId etc, then use those, otherwise use args parse
    if taskId:
        args = argparse.Namespace(
            taskId=taskId, verbosity=verbosity, configDir=configDir
        )
    else:
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "-t",
            "--taskId",
            help="Name of the JSON config to run",
            type=str,
            required=True,
        )
        parser.add_argument(
            "-v",
            "--verbosity",
            help="Increase verbosity:\n3 - DEBUG\n2 - VERBOSE2\n1 - VERBOSE1",
            type=int,
        )
        parser.add_argument(
            "-c",
            "--configDir",
            help="Directory containing task configurations",
            type=str,
        )

        args = parser.parse_args()

    if args.configDir:
        global CONFIG_PATH  # pylint: disable=global-statement
        CONFIG_PATH = args.configDir

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

    # Set noop mode for other classes that expect it
    os.environ["OTF_NOOP"] = "true"

    logger = logging.getLogger()
    logger.setLevel(logging_level)

    logger = logging.getLogger(__name__)
    logger.log(11, f"Log verbosity: {args.verbosity}")

    # Create a config loader object
    config_loader = ConfigLoader(CONFIG_PATH)

    batch_task_definition = config_loader.load_task_definition(args.taskId)

    # Looking at the task definition, validate that any dependencies for tasks are defined as theur own task
    tasks = {}
    for task in batch_task_definition["tasks"]:
        task_definition = config_loader.load_task_definition(task["task_id"])

        order_id = task["order_id"]

        # Add it to the list of tasks
        tasks[order_id] = task_definition

    # Loop through the tasks and make sure the IDs are consecutive
    for i in range(1, len(tasks) + 1):
        if i not in tasks:
            logger.error(f"Task {i} is missing from the batch definition")
            return False

    # Loop through the tasks and ensure that the dependencies are valid
    for task in batch_task_definition["tasks"]:
        logger.debug(f"Checking dependencies for task {task['order_id']}")
        if "dependencies" not in task:
            continue
        for dependency in task["dependencies"]:
            if dependency not in tasks:
                logger.error(
                    f"Task {task['order_id']} has a dependency on task {dependency} which is not defined"
                )
                return False

    logger.info("Batch definition is valid")
    return True


if __name__ == "__main__":
    result = main()
    if not result:
        sys.exit(1)
