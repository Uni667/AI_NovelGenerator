import os
import hashlib
import logging
import datetime
import uuid
from pathlib import Path
from backend.app.database import get_db
from backend.app.services.local_library_config import get_local_library_config
from backend.app.services.local_file_guard import resolve_safe_path

logger = logging.getLogger(__name__)

def detect_encoding(file_path: str) -> str:
    """Detect file encoding using a simple cascading heuristic."""
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(4096)
    except Exception as e:
        logger.error(f"Error reading {file_path} for encoding detection: {e}")
        return "utf-8"

    if raw.startswith(b'\xef\xbb\xbf'):
        return "utf-8-sig"
    
    try:
        raw.decode('utf-8')
        return "utf-8"
    except UnicodeDecodeError:
        pass
    
    try:
        raw.decode('gb18030')
        return "gb18030"
    except UnicodeDecodeError:
        pass

    try:
        raw.decode('big5')
        return "big5"
    except UnicodeDecodeError:
        pass

    return "utf-8"

def calculate_sha256(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def scan_local_directory() -> dict:
    """
    扫描配置的小说原文目录。
    检测新增、更新、删除的文件，计算 sha256 签名，生成扫描报告。
    """
    config = get_local_library_config()
    source_dir = config.get("source_dir", "")
    
    if not config.get("allow_local_file_access"):
        raise PermissionError("本地文件访问功能已禁用。")
        
    try:
        safe_source_dir = resolve_safe_path(source_dir, source_dir)
    except ValueError as e:
        raise PermissionError(f"目录无效: {e}")

    report = {
        "source_dir": source_dir,
        "total_files": 0,
        "new_books": 0,
        "changed_books": 0,
        "deleted_books": 0,
        "unchanged_books": 0,
        "errors": []
    }
    
    if not os.path.exists(safe_source_dir) or not os.path.isdir(safe_source_dir):
        report["errors"].append(f"Directory not found: {source_dir}")
        return report

    allowed_exts = set(ext.lower() for ext in config.get("allowed_extensions", []))
    max_size_bytes = config.get("max_file_mb", 500) * 1024 * 1024

    current_files = set()

    with get_db() as conn:
        cursor = conn.cursor()
        
        # We need to process each file
        for root, dirs, files in os.walk(safe_source_dir):
            for file in files:
                # ignore sensitive files
                if file.startswith('.') or file.endswith('.env') or file.endswith('.db'):
                    continue
                
                ext = os.path.splitext(file)[1].lower()
                if ext not in allowed_exts:
                    continue
                
                file_path = os.path.join(root, file)
                # Normalize path for DB comparison
                norm_file_path = str(Path(file_path).resolve().as_posix())
                current_files.add(norm_file_path)
                
                try:
                    stat = os.stat(file_path)
                    file_size = stat.st_size
                    file_mtime = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.timezone.utc).isoformat()
                    
                    if file_size > max_size_bytes:
                        report["errors"].append(f"File exceeds {config.get('max_file_mb')}MB limit: {file_path}")
                        continue
                        
                    file_hash = calculate_sha256(file_path)
                except Exception as e:
                    report["errors"].append(f"Error accessing file {file_path}: {e}")
                    continue
                
                report["total_files"] += 1
                
                # Check DB
                cursor.execute("SELECT id, source_file_hash, source_file_size, source_file_mtime FROM local_reference_book WHERE source_file_path = ?", (norm_file_path,))
                row = cursor.fetchone()
                
                if not row:
                    # New book
                    encoding = detect_encoding(file_path)
                    book_id = str(uuid.uuid4())
                    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    title = os.path.splitext(file)[0]
                    
                    cursor.execute("""
                        INSERT INTO local_reference_book (
                            id, title, source_file_path, source_file_name, source_file_ext,
                            source_file_hash, source_file_size, source_file_mtime, source_encoding,
                            parse_status, absorb_status, similarity_status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', 'not_started', 'not_built', ?, ?)
                    """, (
                        book_id, title, norm_file_path, file, ext,
                        file_hash, file_size, file_mtime, encoding,
                        now, now
                    ))
                    report["new_books"] += 1
                else:
                    # Existing book
                    db_id, db_hash, db_size, db_mtime = row
                    if db_hash != file_hash or db_size != file_size or db_mtime != file_mtime:
                        # Changed
                        encoding = detect_encoding(file_path)
                        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        cursor.execute("""
                            UPDATE local_reference_book 
                            SET source_file_hash = ?, source_file_size = ?, source_file_mtime = ?, source_encoding = ?,
                                parse_status = 'new', absorb_status = 'not_started', updated_at = ?
                            WHERE id = ?
                        """, (file_hash, file_size, file_mtime, encoding, now, db_id))
                        report["changed_books"] += 1
                    else:
                        report["unchanged_books"] += 1

        # Check for deleted files
        # We need to filter deleted books strictly by `source_dir` just in case config changed,
        # but here we just check if any existing path is not in current_files AND still starts with the safe_source_dir
        # Actually it's simpler: if db_path starts with `safe_source_dir` but not in `current_files`, it's deleted.
        safe_source_dir_posix = Path(safe_source_dir).resolve().as_posix()
        cursor.execute("SELECT id, source_file_path, parse_status FROM local_reference_book")
        all_books = cursor.fetchall()
        for db_id, db_path, db_status in all_books:
            if db_path.startswith(safe_source_dir_posix):
                if db_path not in current_files and db_status != 'deleted':
                    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    cursor.execute("""
                        UPDATE local_reference_book
                        SET parse_status = 'deleted', updated_at = ?
                        WHERE id = ?
                    """, (now, db_id))
                    report["deleted_books"] += 1

        conn.commit()
    
    return report
