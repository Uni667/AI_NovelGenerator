import pytest
from fastapi.testclient import TestClient

def test_preview_reference_context(client: TestClient, auth_headers: dict, test_project: dict, tmp_path):
    from backend.app.database import get_db
    import uuid
    import datetime
    from backend.app.services.local_essence_writer_service import initialize_essence_directory, write_essence_file
    
    pid = test_project["id"]
    book_id = str(uuid.uuid4())
    book_file = tmp_path / "binding_dummy1.txt"
    book_file.write_text("dummy", encoding="utf-8")
    
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO local_reference_book (
                id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (book_id, "Dummy 1", "binding_dummy1.txt", ".txt", "dummyhash1", now, str(book_file), "utf-8", 10, "parsed", now, now))
        conn.commit()
        
    initialize_essence_directory(book_id)
    write_essence_file(book_id, "style_bible.md", "# 风格圣经\n这是文风。\n")
    write_essence_file(book_id, "scene_patterns.json", '{"patterns": []}')
    
    # Not bound yet
    res_preview = client.post(f"/api/v1/projects/{pid}/reference-context/preview", headers=auth_headers)
    assert res_preview.status_code == 200
    assert res_preview.json() == {}
    
    # Bind
    payload = {
        "book_id": book_id,
        "weight": 1.0,
        "use_style_bible": True,
        "use_scene_patterns": False
    }
    client.post(f"/api/v1/projects/{pid}/local-reference-books/{book_id}/attach", json=payload, headers=auth_headers)
    
    res_preview = client.post(f"/api/v1/projects/{pid}/reference-context/preview", headers=auth_headers)
    assert res_preview.status_code == 200
    data = res_preview.json()
    assert book_id in data
    assert "style_bible" in data[book_id]["data"]
    assert "这是文风。" in data[book_id]["data"]["style_bible"]
    assert "scene_patterns" not in data[book_id]["data"]

def test_context_ignores_disabled_bindings(client: TestClient, auth_headers: dict, test_project: dict, tmp_path):
    from backend.app.database import get_db
    import uuid
    import datetime
    from backend.app.services.local_essence_writer_service import initialize_essence_directory, write_essence_file
    
    pid = test_project["id"]
    book_id = str(uuid.uuid4())
    book_file = tmp_path / "binding_dummy2.txt"
    book_file.write_text("dummy", encoding="utf-8")
    
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO local_reference_book (
                id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (book_id, "Dummy 2", "binding_dummy2.txt", ".txt", "h2", now, str(book_file), "utf-8", 10, "parsed", now, now))
        conn.commit()
        
    initialize_essence_directory(book_id)
    write_essence_file(book_id, "style_bible.md", "...")
    
    client.post(f"/api/v1/projects/{pid}/local-reference-books/{book_id}/attach", json={"book_id": book_id, "enabled": False}, headers=auth_headers)
    res_preview = client.post(f"/api/v1/projects/{pid}/reference-context/preview", headers=auth_headers)
    assert res_preview.json() == {}
