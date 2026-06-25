import asyncio
import uuid
import time
import logging
import threading
from datetime import datetime, timezone
from backend.app.database import get_db

logger = logging.getLogger(__name__)

# In-memory tracking of active tasks and their pause events
# task_id -> {"task": asyncio.Task, "pause_event": threading.Event, "cancel_requested": bool}
_active_tasks = {}

def _update_task_db(task_id: str, **kwargs):
    """Utility to update task fields in DB."""
    with get_db() as conn:
        cursor = conn.cursor()
        fields = []
        values = []
        for k, v in kwargs.items():
            fields.append(f"{k} = ?")
            values.append(v)
        if not fields:
            return
            
        values.append(task_id)
        query = f"UPDATE reference_absorption_task SET {', '.join(fields)} WHERE task_id = ?"
        cursor.execute(query, values)
        conn.commit()

def _get_task_db(task_id: str) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reference_absorption_task WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))

async def _worker_loop(task_id: str, book_id: str, task_type: str, start_progress: int = 0):
    """
    Executes the actual whole book absorption pipeline.
    """
    from backend.app.services.local_absorption_service import run_absorption_pipeline
    
    state = _active_tasks.get(task_id)
    if not state:
        return
        
    try:
        await run_absorption_pipeline(task_id, book_id, task_type, start_progress, state, _update_task_db)
    except asyncio.CancelledError:
        _update_task_db(task_id, status="cancelled", finished_at=time.time())
        raise
    except Exception as e:
        logger.exception(f"Task {task_id} failed: {e}")
        _update_task_db(task_id, status="failed", error_message=str(e), finished_at=time.time())
    finally:
        # Cleanup
        if task_id in _active_tasks:
            del _active_tasks[task_id]

def _launch_worker(task_id: str, book_id: str, task_type: str, start_progress: int):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return loop.create_task(_worker_loop(task_id, book_id, task_type, start_progress))
    else:
        import threading
        def _thread_target():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(_worker_loop(task_id, book_id, task_type, start_progress))
            new_loop.close()
            
        t = threading.Thread(target=_thread_target, daemon=True)
        t.start()
        
        class MockTask:
            def cancel(self):
                pass
        return MockTask()

def start_absorption_task(book_id: str, task_type: str) -> str:
    task_id = f"task_absorb_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        # Verify book exists
        cursor.execute("SELECT id FROM local_reference_book WHERE id = ?", (book_id,))
        if not cursor.fetchone():
            raise ValueError("Book not found.")
            
        cursor.execute("""
            INSERT INTO reference_absorption_task (
                id, task_id, book_id, task_type, status, progress_current, progress_total, current_step, started_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), task_id, book_id, task_type, "running", 0, 100, "init", time.time(), now))
        conn.commit()
        
    state = {
        "pause_event": threading.Event(),
        "cancel_requested": False
    }
    _active_tasks[task_id] = state
    state["task"] = _launch_worker(task_id, book_id, task_type, 0)
    
    return task_id

def pause_absorption_task(task_id: str):
    db_task = _get_task_db(task_id)
    if not db_task:
        raise ValueError("Task not found.")
    if db_task["status"] != "running":
        raise ValueError(f"Cannot pause task in status {db_task['status']}.")
        
    state = _active_tasks.get(task_id)
    if state:
        state["pause_event"].set()
        
    # Optimistic DB update, worker will confirm it
    _update_task_db(task_id, status="paused")

def resume_absorption_task(task_id: str):
    db_task = _get_task_db(task_id)
    if not db_task:
        raise ValueError("Task not found.")
    if db_task["status"] not in ("paused", "partial"):
        raise ValueError(f"Cannot resume task in status {db_task['status']}.")
        
    if task_id in _active_tasks:
        # Should not happen if it's genuinely paused/completed
        pass
        
    _update_task_db(task_id, status="running")
    
    state = {
        "pause_event": threading.Event(),
        "cancel_requested": False
    }
    _active_tasks[task_id] = state
    state["task"] = _launch_worker(task_id, db_task["book_id"], db_task["task_type"], db_task["progress_current"])

def cancel_absorption_task(task_id: str):
    db_task = _get_task_db(task_id)
    if not db_task:
        raise ValueError("Task not found.")
        
    state = _active_tasks.get(task_id)
    if state:
        state["cancel_requested"] = True
        if hasattr(state["task"], "cancel"):
            try:
                state["task"].cancel()
            except Exception:
                pass
        
    _update_task_db(task_id, status="cancelled", finished_at=time.time())

def retry_failed_task(task_id: str):
    db_task = _get_task_db(task_id)
    if not db_task:
        raise ValueError("Task not found.")
    if db_task["status"] != "failed":
        raise ValueError(f"Cannot retry task in status {db_task['status']}.")
        
    start_progress = db_task["progress_current"]
    
    _update_task_db(task_id, status="running", error_message=None)
    state = {
        "pause_event": threading.Event(),
        "cancel_requested": False
    }
    _active_tasks[task_id] = state
    state["task"] = _launch_worker(task_id, db_task["book_id"], db_task["task_type"], start_progress)

def get_task_status(task_id: str) -> dict:
    task = _get_task_db(task_id)
    if not task:
        raise ValueError("Task not found.")
    return task
