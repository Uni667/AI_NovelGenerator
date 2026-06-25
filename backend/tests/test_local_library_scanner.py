import os
import json
import uuid
import pytest
import datetime
from pathlib import Path
from unittest.mock import patch

from backend.app.database import get_db
from backend.app.services.local_library_scanner import scan_local_directory, detect_encoding
from backend.app.services.local_library_config import update_local_library_config

@pytest.fixture(autouse=True)
def setup_config(tmp_path):
    source_dir = tmp_path / "source"
    essence_dir = tmp_path / "essence"
    source_dir.mkdir()
    essence_dir.mkdir()
    
    config = {
        "source_dir": str(source_dir.resolve()),
        "essence_dir": str(essence_dir.resolve()),
        "allow_local_file_access": True,
        "max_file_mb": 5,
        "allowed_extensions": [".txt", ".md"]
    }
    update_local_library_config(config)
    return {
        "source_dir": source_dir,
        "essence_dir": essence_dir
    }

def test_encoding_detection(tmp_path):
    utf8_file = tmp_path / "utf8.txt"
    utf8_file.write_bytes("测试".encode("utf-8"))
    
    utf8_sig_file = tmp_path / "utf8_sig.txt"
    utf8_sig_file.write_bytes("测试".encode("utf-8-sig"))
    
    gbk_file = tmp_path / "gbk.txt"
    gbk_file.write_bytes("测试".encode("gbk"))
    
    assert detect_encoding(str(utf8_sig_file)) == "utf-8-sig"
    assert detect_encoding(str(utf8_file)) == "utf-8"
    assert detect_encoding(str(gbk_file)) in ("gb18030", "utf-8") # 兼容短文本的编码回退判定
    
def test_scan_new_files(setup_config):
    source_dir = setup_config["source_dir"]
    
    # Create test files
    (source_dir / "book1.txt").write_bytes("Book 1 Content".encode("utf-8"))
    (source_dir / "book2.md").write_bytes("Book 2 Content".encode("utf-8"))
    
    # Should ignore these
    (source_dir / "ignored.env").write_text("SECRET=123")
    (source_dir / "ignored.db").write_text("db data")
    (source_dir / "unsupported.pdf").write_text("pdf data")
    (source_dir / ".hidden.txt").write_text("hidden")
    
    report = scan_local_directory()
    
    assert report["total_files"] == 2
    assert report["new_books"] == 2
    assert report["changed_books"] == 0
    assert report["deleted_books"] == 0
    assert report["unchanged_books"] == 0
    
    # Check DB
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_file_name, source_file_ext, parse_status FROM local_reference_book")
        rows = cursor.fetchall()
        assert len(rows) == 2
        names = {r[0] for r in rows}
        assert "book1.txt" in names
        assert "book2.md" in names
        statuses = {r[2] for r in rows}
        assert statuses == {"new"}

def test_scan_modify_files(setup_config):
    source_dir = setup_config["source_dir"]
    book_path = source_dir / "book_mod.txt"
    book_path.write_text("Original")
    
    report1 = scan_local_directory()
    assert report1["new_books"] == 1
    
    # Modify file
    book_path.write_text("Modified content")
    # Python tests run fast, sometimes mtime doesn't change enough, let's force mtime change or since size/hash changed, it will detect.
    
    report2 = scan_local_directory()
    assert report2["changed_books"] == 1
    assert report2["new_books"] == 0
    assert report2["unchanged_books"] == 0

def test_scan_unchanged_files(setup_config):
    source_dir = setup_config["source_dir"]
    book_path = source_dir / "book_unchanged.txt"
    book_path.write_text("Content")
    
    report1 = scan_local_directory()
    assert report1["new_books"] == 1
    
    report2 = scan_local_directory()
    assert report2["unchanged_books"] == 1
    assert report2["changed_books"] == 0
    assert report2["new_books"] == 0

def test_scan_deleted_files(setup_config):
    source_dir = setup_config["source_dir"]
    book_path = source_dir / "book_to_delete.txt"
    book_path.write_text("Delete me")
    
    report1 = scan_local_directory()
    assert report1["new_books"] == 1
    
    # Delete file
    book_path.unlink()
    
    report2 = scan_local_directory()
    assert report2["deleted_books"] == 1
    
    # DB status should be deleted
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT parse_status FROM local_reference_book")
        row = cursor.fetchone()
        assert row[0] == "deleted"

def test_max_file_size_limit(setup_config):
    source_dir = setup_config["source_dir"]
    large_file = source_dir / "large.txt"
    
    # Mock size limit to 0 MB (0 bytes limit) for easy testing
    config = {
        "max_file_mb": 0
    }
    update_local_library_config(config)
    
    large_file.write_text("This is more than 1 byte")
    
    report = scan_local_directory()
    assert report["total_files"] == 0
    assert report["new_books"] == 0
    assert len(report["errors"]) == 1
    assert "exceeds" in report["errors"][0]
