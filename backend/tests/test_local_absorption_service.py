import asyncio
import os
import pytest
from backend.app.database import get_db
from backend.app.services.local_absorption_service import run_absorption_pipeline
from backend.app.services.local_essence_writer_service import read_essence_file, get_manifest

@pytest.fixture
def setup_dummy_book(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_LLM_MODE", "true")
    monkeypatch.setenv("ALLOW_LOCAL_FILE_ACCESS", "true")
    
    from backend.tests.mock_llm import get_mock_adapter
    monkeypatch.setattr("backend.app.services.model_runtime.create_chat_adapter_from_config", lambda *args, **kwargs: get_mock_adapter())
    
    import uuid
    import datetime
    
    book_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Create dummy source file
    source_file = tmp_path / "source.txt"
    source_content = "Chapter 1 text. " * 10 + "Chapter 2 text. " * 10
    source_file.write_text(source_content, encoding="utf-8")
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO local_reference_book (
                id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (book_id, "Absorption Test", "source.txt", ".txt", "h", now, str(source_file), "utf-8", len(source_content), "pending", now, now))
        
        cursor.execute("""
            INSERT INTO local_reference_chapter (
                id, book_id, volume_id, chapter_index, title, source_start_offset, source_end_offset, word_count, parse_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), book_id, None, 1, "第1章", 0, 100, 100, 1.0))
        
        cursor.execute("""
            INSERT INTO local_reference_chapter (
                id, book_id, volume_id, chapter_index, title, source_start_offset, source_end_offset, word_count, parse_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), book_id, None, 2, "第2章 失败测试", 100, 200, 100, 1.0))
        
        conn.commit()
    yield book_id, str(source_file)

def mock_update_db(task_id, **kwargs):
    pass

@pytest.mark.asyncio
async def test_full_absorption_pipeline(setup_dummy_book):
    book_id, source_file = setup_dummy_book
    task_id = "test_task_123"
    
    state = {
        "cancel_requested": False,
        "pause_event": type("MockEvent", (), {"is_set": lambda self: False})()
    }
    
    await run_absorption_pipeline(task_id, book_id, "full_absorb", 0, state, mock_update_db)
    
    # Verify outputs
    manifest = get_manifest(book_id)
    files = manifest["files"]
    print("MANIFEST FILES:", files)
    
    # 13 required files + chapter summaries
    assert "chapter_summaries" in files
    assert "chapter_analysis" in files
    assert "volume_summaries" in files
    assert "book_summary.md" in files
    assert "style_bible.md" in files
    assert "plot_structure.md" in files
    assert "pacing_rules.md" in files
    assert "conflict_models.md" in files
    assert "character_arcs.md" in files
    assert "hook_models.md" in files
    assert "scene_patterns.json" in files
    assert "platform_adaptation.md" in files
    assert "anti_copy_rules.md" in files
    assert "quality_report.md" in files
    
    # Check JSON
    scene_json = read_essence_file(book_id, "scene_patterns.json")
    import json
    data = json.loads(scene_json)
    assert isinstance(data, list)
    assert data[0]["pattern_name"] == "打脸"
    
    # Check Markdown
    style_bible = read_essence_file(book_id, "style_bible.md")
    assert "Mock Extraction" in style_bible
    
    # Check single chapter failure logic:
    # If a chapter fails, it continues. (In our mock it won't fail normally, but we can check quality report)
    qr = read_essence_file(book_id, "quality_report.md")
    assert "Failed Chapters: 0" in qr

@pytest.mark.asyncio
async def test_absorption_pipeline_cancel_and_resume(setup_dummy_book):
    book_id, source_file = setup_dummy_book
    task_id = "test_task_456"
    
    class MutableEvent:
        def __init__(self):
            self.flag = False
        def is_set(self):
            return self.flag
    
    pause_evt = MutableEvent()
    pause_evt.flag = True # Pause immediately
    
    state = {
        "cancel_requested": False,
        "pause_event": pause_evt
    }
    
    # Will stop immediately
    await run_absorption_pipeline(task_id, book_id, "full_absorb", 0, state, mock_update_db)
    
    manifest = get_manifest(book_id)
    # Shouldn't have completed the whole book analysis since it paused at step 0
    assert "book_summary.md" not in manifest.get("files", {})

@pytest.mark.asyncio
async def test_single_chapter_failure_tolerance(setup_dummy_book, monkeypatch):
    book_id, source_file = setup_dummy_book
    task_id = "test_task_789"
    
    state = {
        "cancel_requested": False,
        "pause_event": type("MockEvent", (), {"is_set": lambda self: False})()
    }
    
    # Force _read_chapter_text to throw an error for chapter 1 to test tolerance
    from backend.app.services import local_absorption_service
    original_read = local_absorption_service._read_chapter_text
    
    def fake_read(fp, start, end, enc):
        if "source.txt" in fp and start == 0:
            raise ValueError("Simulated read error")
        return original_read(fp, start, end, enc)
        
    monkeypatch.setattr(local_absorption_service, "_read_chapter_text", fake_read)
    
    await run_absorption_pipeline(task_id, book_id, "full_absorb", 0, state, mock_update_db)
    
    # It should have finished despite chapter 1 failing
    qr = read_essence_file(book_id, "quality_report.md")
    assert "Failed Chapters: 1" in qr
