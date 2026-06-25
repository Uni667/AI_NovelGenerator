import os
import pytest
from backend.app.services.local_essence_writer_service import (
    generate_slug,
    initialize_essence_directory,
    write_essence_file,
    read_essence_file,
    get_manifest
)
from backend.app.database import get_db

def test_generate_slug():
    assert generate_slug("斗破虚空") == "斗破虚空"
    assert generate_slug("Chapter 1: The Beginning!") == "Chapter_1_The_Beginning"
    assert generate_slug("   hello  world   ") == "hello_world"
    assert generate_slug("!@#$") == "book_essence"

def test_initialize_and_manifest(client, auth_headers, tmp_path, monkeypatch):
    # Mock essence_dir
    monkeypatch.setenv("ALLOW_LOCAL_FILE_ACCESS", "true")
    
    from backend.app.database import get_db
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
        """, (book_id, "测试小说", "test.txt", ".txt", "hash123", now, "/dummy/test.txt", "utf-8", 100, "pending", now, now))
        conn.commit()
        
    target_dir, manifest_path = initialize_essence_directory(book_id)
    
    assert os.path.exists(target_dir)
    assert os.path.exists(os.path.join(target_dir, "chapter_summaries"))
    assert os.path.exists(manifest_path)
    
    manifest = get_manifest(book_id)
    assert manifest["schema_version"] == "v1"
    assert manifest["source_hash"] == "hash123"
    assert manifest["absorb_status"] == "not_started"

def test_write_and_read_essence(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_FILE_ACCESS", "true")
    
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
        """, (book_id, "原子写入测试", "atomic.txt", ".txt", "hashabc", now, "/dummy/atomic.txt", "utf-8", 100, "pending", now, now))
        conn.commit()
        
    initialize_essence_directory(book_id)
    
    # Test atomic write
    write_essence_file(book_id, "style_bible.md", "这里是风格圣经")
    
    # Assert tmp was removed and target is created
    content = read_essence_file(book_id, "style_bible.md")
    assert content == "这里是风格圣经"
    
    manifest = get_manifest(book_id)
    assert "style_bible.md" in manifest["files"]
    
    # Test path whitelist (should fail if trying to traverse)
    with pytest.raises(Exception):
        write_essence_file(book_id, "../escaped.md", "escaped")

def test_api_essence_read(client, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_FILE_ACCESS", "true")
    
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
        """, (book_id, "API读测试", "api.txt", ".txt", "hashxyz", now, "/dummy/api.txt", "utf-8", 100, "pending", now, now))
        conn.commit()
        
    initialize_essence_directory(book_id)
    write_essence_file(book_id, "chapter_summaries/001.md", "第一章摘要")
    
    response = client.get(f"/api/v1/local-library/books/{book_id}/essence", headers=auth_headers)
    assert response.status_code == 200
    assert "manifest" in response.json()
    assert "chapter_summaries" in response.json()["manifest"]["files"]
    
    response2 = client.get(f"/api/v1/local-library/books/{book_id}/essence?file_key=chapter_summaries/001.md", headers=auth_headers)
    assert response2.status_code == 200
    assert response2.json()["content"] == "第一章摘要"
