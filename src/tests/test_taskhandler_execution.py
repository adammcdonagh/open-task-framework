import unittest
from opentaskpy.taskhandlers import execution


class TaskHandlerExecutionTest(unittest.TestCase):

    # Create a task definition
    df_task_definition = {
        "type": "execution",
        "hosts": ["172.16.0.11", "172.16.0.12"],
        "username": "application",
        "directory": "/tmp",
        "command": "df -h",
        "protocol": {"name": "ssh", "credentials": {"username": "application"}},
    }

    def test_basic_execution(self):
        execution_obj = execution.Execution("df-basic", self.df_task_definition)
        execution_obj._set_remote_handlers()

        # Validate some things were set as expected
        self.assertEqual(execution_obj.remote_handlers[0].__class__.__name__, "SSH")
        self.assertEqual(execution_obj.remote_handlers[1].__class__.__name__, "SSH")

        # Run the execution and expect a true status
        self.assertTrue(execution_obj.run())
