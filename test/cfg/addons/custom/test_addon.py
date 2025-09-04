"""Test addon.

This addon returns a random number and then returns OK.
"""

from random import randint

import opentaskpy.otflogging
from opentaskpy.remotehandlers.remotehandler import RemoteExecutionHandler


class RandomNumberGenerator(RemoteExecutionHandler):
    """Random number generator."""

    TASK_TYPE = "E"

    def __init__(self, spec: dict):
        """Initialise the handler.

        Args:
            spec (dict): The spec for the execution.
        """
        self.logger = opentaskpy.otflogging.init_logging(
            __name__, spec["task_id"], self.TASK_TYPE
        )

        super().__init__(spec)

    def execute(self) -> bool:
        """Generate a random number."""
        self.logger.info("Generating a random number.")
        self.logger.info(f"Random number is {randint(0, 100)}")
        return True

    def tidy(self) -> None:
        """Tidy up the remote connection."""
