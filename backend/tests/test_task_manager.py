import time
import unittest

from novel_generator import task_manager
from novel_generator.task_manager import (
    TERMINAL_STATUSES,
    TaskCancelledError,
    finish_task,
    get_task,
    register_task,
    request_cancel,
    raise_if_cancelled,
    update_task_status,
)


class TaskManagerTests(unittest.TestCase):
    def setUp(self):
        task_manager._TASKS.clear()
        task_manager._CANCEL_TOKENS.clear()

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

    def test_update_task_status_sets_finished_at_for_terminal(self):
        """终结状态更新时应自动补填 finished_at。"""
        register_task("task-2", "proj-1", "chapter")
        state = update_task_status("task-2", "done")
        self.assertIsNotNone(state)
        self.assertEqual(state.status, "done")
        self.assertIsNotNone(state.finished_at)

    def test_update_task_status_skips_finished_at_for_non_terminal(self):
        """非终结状态更新时不应设 finished_at。"""
        register_task("task-3", "proj-1", "chapter")
        state = update_task_status("task-3", "running")
        self.assertIsNotNone(state)
        self.assertEqual(state.status, "running")
        self.assertIsNone(state.finished_at)

    def test_max_tasks_eviction_removes_oldest_finished(self):
        """超过 _MAX_TASKS 时应驱逐最早的已完成任务。"""
        old_max = task_manager._MAX_TASKS
        task_manager._MAX_TASKS = 3
        try:
            # 创建 4 个任务并全部标记完成
            for i in range(4):
                tid = f"evict-{i}"
                register_task(tid, "proj-1", "test")
                finish_task(tid, "done", f"done-{i}")
                time.sleep(0.01)

            # 触发驱逐：get_task 内部调用 _cleanup_finished_tasks_locked
            get_task("evict-0")

            self.assertLessEqual(len(task_manager._TASKS), 3)
            # 最早的任务 "evict-0" 应被驱逐
            self.assertIsNone(get_task("evict-0"))
            # 最新的任务 "evict-3" 应保留
            self.assertIsNotNone(get_task("evict-3"))
        finally:
            task_manager._MAX_TASKS = old_max


if __name__ == "__main__":
    unittest.main()
