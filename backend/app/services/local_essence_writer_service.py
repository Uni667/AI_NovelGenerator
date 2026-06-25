import os
import re
import json
from datetime import datetime, timezone
from backend.app.database import get_db
from backend.app.services.local_library_config import get_local_library_config
from backend.app.services.local_file_guard import resolve_safe_path

def generate_slug(title: str) -> str:
    """
    Converts Chinese/English titles to a safe folder name.
    Preserves alphanumeric characters and Chinese characters (\u4e00-\u9fa5),
    replacing any invalid or special characters with an underscore _.
    """
    # Replace anything that is not alphanumeric or Chinese with underscore
    slug = re.sub(r'[^\w\u4e00-\u9fa5]', '_', title)
    # Collapse multiple underscores
    slug = re.sub(r'_+', '_', slug).strip('_')
    if not slug:
        slug = "book_essence"
    return slug

def initialize_essence_directory(book_id: str):
    """
    Creates essence directory structure and manifest.
    """
    config = get_local_library_config()
    essence_base = config.get("essence_dir", "")
    if not essence_base:
        raise ValueError("Essence directory not configured.")
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, source_file_hash, parse_status, essence_dir_path FROM local_reference_book WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Book {book_id} not found.")
            
        title, source_hash, parse_status, existing_essence_dir = row
        
        # Determine slug and final path
        slug = generate_slug(title)
        
        # Check uniqueness, just append book_id to be safe if you want, but slug+hash could work
        # Let's use slug + first 8 chars of book_id
        folder_name = f"{slug}_{book_id[:8]}"
        
        # We must use local_file_guard to resolve target path
        target_dir = resolve_safe_path(essence_base, folder_name)
        
        # Create directories
        os.makedirs(target_dir, exist_ok=True)
        os.makedirs(os.path.join(target_dir, "chapter_summaries"), exist_ok=True)
        os.makedirs(os.path.join(target_dir, "chapter_analysis"), exist_ok=True)
        
        # Write manifest
        manifest_path = os.path.join(target_dir, "manifest.json")
        manifest_data = {
            "schema_version": "v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_hash": source_hash,
            "absorb_status": "not_started",
            "files": {
                "chapter_summaries": {},
                "chapter_analysis": {}
            }
        }
        
        # Atomic write
        tmp_manifest = manifest_path + ".tmp"
        with open(tmp_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_manifest, manifest_path)
        
        # Update DB
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            UPDATE local_reference_book
            SET essence_dir_path = ?, manifest_path = ?, updated_at = ?
            WHERE id = ?
        """, (target_dir, manifest_path, now, book_id))
        conn.commit()
        
    return target_dir, manifest_path

def write_essence_file(book_id: str, file_key: str, content: str):
    """
    Atomically writes to an essence file.
    file_key could be 'global_summary.md', 'chapter_summaries/001.md', etc.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT essence_dir_path, manifest_path FROM local_reference_book WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            raise ValueError("Essence directory not initialized for this book.")
        essence_dir = row[0]
        manifest_path = row[1]
        
    # Resolve safe path within essence_dir
    target_path = resolve_safe_path(essence_dir, file_key)
    
    # Ensure parent dir exists
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    # Atomic write
    tmp_path = target_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, target_path)
    
    # Update manifest
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    except FileNotFoundError:
        manifest_data = {"schema_version": "v1", "files": {}}
        
    # Just a simple record of what was written
    if "files" not in manifest_data:
        manifest_data["files"] = {}
        
    if '/' in file_key:
        folder, name = file_key.split('/', 1)
        if folder not in manifest_data["files"]:
            manifest_data["files"][folder] = {}
        manifest_data["files"][folder][name] = datetime.now(timezone.utc).isoformat()
    else:
        manifest_data["files"][file_key] = datetime.now(timezone.utc).isoformat()
        
    tmp_manifest = manifest_path + ".tmp"
    with open(tmp_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_manifest, manifest_path)

def read_essence_file(book_id: str, file_key: str) -> str:
    """
    Reads an essence file safely.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT essence_dir_path FROM local_reference_book WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            raise ValueError("Essence directory not initialized for this book.")
        essence_dir = row[0]
        
    # Resolve safe path within essence_dir
    target_path = resolve_safe_path(essence_dir, file_key)
    
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Essence file {file_key} not found.")
        
    with open(target_path, "r", encoding="utf-8") as f:
        return f.read()

def get_manifest(book_id: str) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT manifest_path FROM local_reference_book WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            raise ValueError("Manifest not found.")
        manifest_path = row[0]
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)
