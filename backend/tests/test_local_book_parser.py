import pytest
from backend.app.services.local_chapter_boundary_service import parse_book_file
from backend.app.services.local_book_parser_service import parse_book
from backend.app.database import get_db

def test_chapter_boundary_service(tmp_path):
    # Test Chinese formats
    file_path = tmp_path / "book.txt"
    content = """第一卷 穿越
第一章 陨落的奇才
这里是正文，共20字。
第002章 斗气化马
这章字数也不多。
楔子 传说
番外 另一个故事
Chapter 1 Hello
"""
    file_path.write_bytes(content.encode('utf-8'))
    
    result = parse_book_file(str(file_path), "utf-8")
    
    # Assert volumes
    assert len(result["volumes"]) == 1
    assert result["volumes"][0]["title"] == "第一卷 穿越"
    
    # Assert chapters
    assert len(result["chapters"]) == 5
    titles = [ch["title"] for ch in result["chapters"]]
    assert "第一章 陨落的奇才" in titles
    assert "第002章 斗气化马" in titles
    assert "楔子 传说" in titles
    assert "番外 另一个故事" in titles
    assert "Chapter 1 Hello" in titles
    
    # Assert confidence
    # since word count is very small, confidence might be penalized
    assert result["confidence"] < 1.0
    
def test_long_chapter_penalty(tmp_path):
    file_path = tmp_path / "long.txt"
    content = "第一章 超长\n" + "A" * 150000
    file_path.write_bytes(content.encode('utf-8'))
    
    result = parse_book_file(str(file_path), "utf-8")
    assert len(result["chapters"]) == 1
    # 超过 100k，应该有惩罚
    assert result["confidence"] <= 0.6
    
def test_byte_offsets(tmp_path):
    file_path = tmp_path / "offset.txt"
    content = "第一章 测试\n内容A\n第二章 测试2\n内容B"
    file_path.write_bytes(content.encode('utf-8'))
    
    result = parse_book_file(str(file_path), "utf-8")
    ch1 = result["chapters"][0]
    ch2 = result["chapters"][1]
    
    with open(str(file_path), 'rb') as f:
        f.seek(ch1["start_offset"])
        text1 = f.read(ch1["end_offset"] - ch1["start_offset"]).decode('utf-8')
        assert "第一章" in text1
        
        f.seek(ch2["start_offset"])
        text2 = f.read(ch2["end_offset"] - ch2["start_offset"]).decode('utf-8')
        assert "第二章" in text2

def test_rebuild_and_manual_patch(client, auth_headers, tmp_path):
    import uuid
    import datetime
    book_id = str(uuid.uuid4())
    book_file = tmp_path / "doupo2.txt"
    book_file.write_text("第一章 原本的标题\n这里是正文\n", encoding="utf-8")
    
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO local_reference_book (
                id, title, source_file_name, source_file_ext, source_file_hash, source_file_mtime, source_file_path, source_encoding, source_file_size, parse_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (book_id, "斗破虚空2", "doupo2.txt", ".txt", "dummyhash", now, str(book_file), "utf-8", 100, "pending", now, now))
        conn.commit()

    # Call parse
    response = client.post(f"/api/v1/local-library/books/{book_id}/parse", headers=auth_headers)
    assert response.status_code == 200
    
    # Get chapters
    response = client.get(f"/api/v1/local-library/books/{book_id}/chapters", headers=auth_headers)
    chapters = response.json()
    assert len(chapters) == 1
    chapter_id = chapters[0]["id"]
    
    # Patch chapter
    res_patch = client.patch(
        f"/api/v1/local-library/books/{book_id}/chapters/{chapter_id}",
        json={"title": "第一章 修改后的标题"},
        headers=auth_headers
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["title"] == "第一章 修改后的标题"
    
    # Rebuild
    res_rebuild = client.post(f"/api/v1/local-library/books/{book_id}/chapters/rebuild", headers=auth_headers)
    assert res_rebuild.status_code == 200
    
    # Get chapters again, should revert to original
    response2 = client.get(f"/api/v1/local-library/books/{book_id}/chapters", headers=auth_headers)
    chapters2 = response2.json()
    assert chapters2[0]["title"] == "第一章 原本的标题"
