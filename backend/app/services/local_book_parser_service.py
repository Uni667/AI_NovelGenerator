import logging
import uuid
import datetime
from backend.app.database import get_db
from backend.app.services import local_chapter_boundary_service

logger = logging.getLogger(__name__)

def parse_book(book_id: str) -> dict:
    """
    触发对指定小说的解析，读取原文并将其分解为卷和章节。
    更新数据库记录。
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. 查询小说信息
        cursor.execute("""
            SELECT source_file_path, source_encoding, parse_status 
            FROM local_reference_book WHERE id = ?
        """, (book_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError(f"Book with id {book_id} not found.")
            
        file_path, encoding, parse_status = row
        
        # 2. 清理现有此书的分卷和章节（重建逻辑）
        cursor.execute("DELETE FROM local_reference_chapter WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM local_reference_volume WHERE book_id = ?", (book_id,))
        
        # 3. 调用边界解析服务
        result = local_chapter_boundary_service.parse_book_file(file_path, encoding)
        
        if result.get("error"):
            # Update book status to error
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cursor.execute("""
                UPDATE local_reference_book 
                SET parse_status = 'error', error_message = ?, updated_at = ?
                WHERE id = ?
            """, (result["error"], now, book_id))
            conn.commit()
            raise RuntimeError(f"Parse failed: {result['error']}")
            
        # 4. 写入卷和章节
        volumes_data = result["volumes"]
        chapters_data = result["chapters"]
        
        volume_id_map = {} # map index to volume id
        
        for i, vol in enumerate(volumes_data):
            vid = str(uuid.uuid4())
            volume_id_map[i] = vid
            
            # Start/End index for the volume (based on chapter list)
            vol_chapters = vol["chapters"]
            start_idx = vol_chapters[0] if vol_chapters else 0
            end_idx = vol_chapters[-1] if vol_chapters else 0
            
            cursor.execute("""
                INSERT INTO local_reference_volume (
                    id, book_id, volume_index, title, start_chapter_index, end_chapter_index, word_count
                ) VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (vid, book_id, i, vol["title"], start_idx, end_idx))
            
        total_chapters = len(chapters_data)
        
        for i, ch in enumerate(chapters_data):
            cid = str(uuid.uuid4())
            vol_idx = ch["volume_index"]
            vid = volume_id_map.get(vol_idx) if vol_idx >= 0 else None
            
            cursor.execute("""
                INSERT INTO local_reference_chapter (
                    id, book_id, volume_id, chapter_index, title, 
                    source_start_offset, source_end_offset, word_count, parse_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cid, book_id, vid, i, ch["title"], 
                ch["start_offset"], ch["end_offset"], ch["word_count"], result["confidence"]
            ))
            
            # Update volume word count if part of volume
            if vid:
                cursor.execute("""
                    UPDATE local_reference_volume SET word_count = word_count + ? WHERE id = ?
                """, (ch["word_count"], vid))
                
        # 5. 更新书籍状态
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        needs_review = result["confidence"] < 0.8
        new_status = 'needs_review' if needs_review else 'completed'
        
        cursor.execute("""
            UPDATE local_reference_book 
            SET parse_status = ?, total_chapters = ?, total_volumes = ?, total_words = ?, 
                parse_confidence = ?, last_parsed_at = ?, updated_at = ?, error_message = NULL
            WHERE id = ?
        """, (
            new_status, total_chapters, len(volumes_data), result["total_words"], 
            result["confidence"], now, now, book_id
        ))
        
        conn.commit()
        
        return {
            "book_id": book_id,
            "status": new_status,
            "total_volumes": len(volumes_data),
            "total_chapters": total_chapters,
            "total_words": result["total_words"],
            "confidence": result["confidence"]
        }
