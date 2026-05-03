import unittest

from novel_generator import task_manager
from novel_generator.task_manager import (
    TaskCancelledError,
    finish_task,
    get_task,
    register_task,
    request_cancel,
    raise_if_cancelled,
)


class TaskManagerTests(unittest.TestCase):
    def setUp(self):
        task_manager._TASKS.clear()

    def test_cancel_flow_sets_consistent_state(self):
        register_task("task-1", "project-1", "architecture", {"label": "test"})

        cancelled = request_cancel("task-1")
        self.assertIsNotNone(cancelled)
        self.assertEqual(cancelled.status, "cancelling")
        self.assertTrue(cancelled.cancel_requested)

        with self.assertRaises(TaskCancelledError):
            raise_if_cancelled("task-1")

        finish_task("task-1", "cancelled", "stopped")
        final_state = get_task("task-1")
        self.assertEqual(final_state.status, "cancelled")
        self.assertEqual(final_state.message, "stopped")


if __name__ == "__main__":
    unittest.main()
