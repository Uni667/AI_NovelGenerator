import asyncio
import pytest
from backend.app.services.local_absorption_task_manager import (
    start_absorption_task,
    pause_absorption_task,
    resume_absorption_task,
    cancel_absorption_task,
    retry_failed_task,
    get_task_status,
    _active_tasks
)
from backend.app.database import get_db

@pytest.fixture
def dummy_book():
    import uuid
    import datetime
    book_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO local_reference_book (
                id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (book_id, "Task Test Book", "t.txt", ".txt", "h", now, "/dummy/t.txt", "utf-8", 100, "pending", now, now))
        conn.commit()
    return book_id

@pytest.fixture(autouse=True)
def mock_pipeline(monkeypatch):
    async def dummy_pipeline(task_id, book_id, task_type, start_progress, state, update_db_cb):
        total = 100
        for i in range(start_progress, total, 10):
            if state and state.get("cancel_requested"):
                raise asyncio.CancelledError()
            if state and state.get("pause_event").is_set():
                return
            await asyncio.sleep(0.01)
            update_db_cb(task_id, progress_current=i + 10, progress_total=total, current_step="mocking")
        
        import time
        update_db_cb(task_id, status="completed", progress_current=100, finished_at=time.time())
            
    monkeypatch.setattr("backend.app.services.local_absorption_service.run_absorption_pipeline", dummy_pipeline)

@pytest.mark.asyncio
async def test_task_lifecycle(dummy_book):
    task_id = start_absorption_task(dummy_book, "full_absorb")
    
    status = get_task_status(task_id)
    assert status["status"] == "running"
    
    # Wait for completion (since our dummy is 10 steps of 0.1s, total 1s)
    # We can just wait a bit and check progress
    await asyncio.sleep(0.15)
    status = get_task_status(task_id)
    assert status["progress_current"] >= 10
    
    # Wait for end
    await asyncio.sleep(0.3)
    status = get_task_status(task_id)
    assert status["status"] == "completed"
    assert status["progress_current"] == 100
    assert task_id not in _active_tasks

@pytest.mark.asyncio
async def test_pause_and_resume(dummy_book):
    task_id = start_absorption_task(dummy_book, "scan")
    
    await asyncio.sleep(0.15) # let it run a bit
    pause_absorption_task(task_id)
    
    # Wait a bit to ensure worker catches the event
    await asyncio.sleep(0.2)
    status = get_task_status(task_id)
    assert status["status"] == "paused"
    progress_at_pause = status["progress_current"]
    assert task_id not in _active_tasks
    
    resume_absorption_task(task_id)
    status = get_task_status(task_id)
    assert status["status"] == "running"
    
    await asyncio.sleep(0.15)
    status2 = get_task_status(task_id)
    assert status2["progress_current"] > progress_at_pause
    
    # Clean up
    cancel_absorption_task(task_id)

@pytest.mark.asyncio
async def test_cancel_task(dummy_book):
    task_id = start_absorption_task(dummy_book, "parse")
    
    await asyncio.sleep(0.1)
    cancel_absorption_task(task_id)
    
    await asyncio.sleep(0.1)
    status = get_task_status(task_id)
    assert status["status"] == "cancelled"
    assert task_id not in _active_tasks

@pytest.mark.asyncio
async def test_retry_failed(dummy_book):
    # First create a task and artificially fail it
    task_id = start_absorption_task(dummy_book, "build_style_bible")
    cancel_absorption_task(task_id) # Just to stop the worker
    await asyncio.sleep(0.1)
    
    from backend.app.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE reference_absorption_task SET status = 'failed', progress_current = 50 WHERE task_id = ?", (task_id,))
        conn.commit()
        
    status = get_task_status(task_id)
    assert status["status"] == "failed"
    
    retry_failed_task(task_id)
    status = get_task_status(task_id)
    assert status["status"] == "running"
    assert status["progress_current"] == 50 # should resume from breakpoint
    
    cancel_absorption_task(task_id)
