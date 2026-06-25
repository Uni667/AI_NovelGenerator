import pytest
from fastapi.testclient import TestClient

def test_bind_single_book(client: TestClient, auth_headers: dict, test_project: dict, tmp_path):
    from backend.app.database import get_db
    import uuid
    import datetime
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
        
    payload = {
        "book_id": book_id,
        "weight": 1.5,
        "use_style_bible": True
    }
    res = client.post(f"/api/v1/projects/{pid}/local-reference-books/{book_id}/attach", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["book_id"] == book_id
    assert data["weight"] == 1.5
    
    res_list = client.get(f"/api/v1/projects/{pid}/local-reference-books", headers=auth_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1
    assert res_list.json()[0]["book_id"] == book_id

def test_bind_multiple_books(client: TestClient, auth_headers: dict, test_project: dict, tmp_path):
    from backend.app.database import get_db
    import uuid
    import datetime
    pid = test_project["id"]
    book_id1 = str(uuid.uuid4())
    book_id2 = str(uuid.uuid4())
    
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO local_reference_book (
                id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (book_id1, "Dummy 1", "b1.txt", ".txt", "h1", now, "b1.txt", "utf-8", 10, "parsed", now, now))
        cursor.execute("""
            INSERT INTO local_reference_book (
                id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (book_id2, "Dummy 2", "b2.txt", ".txt", "h2", now, "b2.txt", "utf-8", 10, "parsed", now, now))
        conn.commit()

    # Bind 1
    client.post(f"/api/v1/projects/{pid}/local-reference-books/{book_id1}/attach", json={"book_id": book_id1, "weight": 1.0}, headers=auth_headers)
    # Bind 2 with higher weight
    client.post(f"/api/v1/projects/{pid}/local-reference-books/{book_id2}/attach", json={"book_id": book_id2, "weight": 2.0}, headers=auth_headers)
    
    res_list = client.get(f"/api/v1/projects/{pid}/local-reference-books", headers=auth_headers)
    bindings = res_list.json()
    assert len(bindings) == 2
    # Check sorting by weight DESC
    assert bindings[0]["book_id"] == book_id2
    assert bindings[1]["book_id"] == book_id1

def test_disable_book(client: TestClient, auth_headers: dict, test_project: dict, tmp_path):
    from backend.app.database import get_db
    import uuid
    import datetime
    pid = test_project["id"]
    book_id = str(uuid.uuid4())
    
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO local_reference_book (
                id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (book_id, "Dummy 1", "b.txt", ".txt", "h", now, "b.txt", "utf-8", 10, "parsed", now, now))
        conn.commit()

    client.post(f"/api/v1/projects/{pid}/local-reference-books/{book_id}/attach", json={"book_id": book_id, "enabled": True}, headers=auth_headers)
    
    # Disable
    res = client.patch(f"/api/v1/projects/{pid}/local-reference-books/{book_id}", json={"book_id": book_id, "enabled": False}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["enabled"] is False
    
    # Verify in list
    res_list = client.get(f"/api/v1/projects/{pid}/local-reference-books", headers=auth_headers)
    assert res_list.json()[0]["enabled"] is False
