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
    is_cancel_requested,
)


class TaskManagerTests(unittest.TestCase):
    def setUp(self):
        task_manager._TASKS.clear()
        task_manager._CANCEL_TOKENS.clear()

        # Insert dummy user and project to satisfy foreign key constraints
        from backend.app.database import get_db
        with get_db() as conn:
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute(
                "INSERT OR IGNORE INTO user (id, username, password_hash, created_at) VALUES ('user-1', 'test_user', 'hash', '2026-05-28')"
            )
            conn.execute(
                "INSERT OR IGNORE INTO project (id, user_id, name, description, filepath, status, created_at, updated_at) VALUES ('project-1', 'user-1', 'test_proj', 'desc', 'path', 'draft', '2026-05-28', '2026-05-28')"
            )

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

    def test_get_task_from_db(self):
        """get_task should load the task state from the database if not in memory."""
        from backend.app.database import get_db
        import datetime

        task_id = "db-task-1"
        project_id = "project-1"
        now_str = datetime.datetime.now().isoformat()

        with get_db() as conn:
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute(
                """INSERT OR REPLACE INTO generation_task
                   (id, project_id, type, status, created_at, updated_at)
                   VALUES (?, ?, 'generate_architecture', 'running', ?, ?)""",
                (task_id, project_id, now_str, now_str)
            )

        # Make sure it's NOT in memory
        task_manager._TASKS.pop(task_id, None)

        # Retrieve via get_task
        state = get_task(task_id)
        self.assertIsNotNone(state)
        self.assertEqual(state.task_id, task_id)
        self.assertEqual(state.status, "running")
        # Now it should be in memory
        self.assertIn(task_id, task_manager._TASKS)

    def test_is_cancel_requested_from_db(self):
        """is_cancel_requested should check database and return True if status is cancelling."""
        from backend.app.database import get_db
        import datetime

        task_id = "db-task-2"
        project_id = "project-1"
        now_str = datetime.datetime.now().isoformat()

        with get_db() as conn:
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute(
                """INSERT OR REPLACE INTO generation_task
                   (id, project_id, type, status, created_at, updated_at)
                   VALUES (?, ?, 'generate_chapter', 'cancelling', ?, ?)""",
                (task_id, project_id, now_str, now_str)
            )

        # Retrieve and verify cancel request status
        self.assertTrue(is_cancel_requested(task_id))

    def test_load_tasks_from_db_with_cancelling_status(self):
        """load_tasks_from_db should load tasks in 'cancelling' status and mark them failed."""
        from backend.app.database import get_db
        import datetime

        task_id = "db-task-3"
        project_id = "project-1"
        now_str = datetime.datetime.now().isoformat()

        with get_db() as conn:
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute(
                """INSERT OR REPLACE INTO generation_task
                   (id, project_id, type, status, created_at, updated_at)
                   VALUES (?, ?, 'generate_chapter', 'cancelling', ?, ?)""",
                (task_id, project_id, now_str, now_str)
            )

        # Trigger load
        task_manager.load_tasks_from_db()

        # Verify state in memory and database is 'failed'
        state = get_task(task_id)
        self.assertIsNotNone(state)
        self.assertEqual(state.status, "failed")
        self.assertEqual(state.message, "服务器重启导致任务中断")

        with get_db() as conn:
            row = conn.execute("SELECT status FROM generation_task WHERE id = ?", (task_id,)).fetchone()
        self.assertEqual(row["status"], "failed")

    def tearDown(self):
        from backend.app.database import get_db
        try:
            with get_db() as conn:
                conn.execute("PRAGMA foreign_keys=OFF")
                conn.execute("DELETE FROM generation_task WHERE id LIKE 'db-task-%'")
                conn.execute("DELETE FROM project WHERE id = 'project-1'")
                conn.execute("DELETE FROM user WHERE id = 'user-1'")
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
