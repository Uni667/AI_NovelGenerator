import logging
import json
from typing import List
from fastapi import APIRouter, HTTPException, Request

from backend.app.auth import get_current_user
from backend.app.database import get_db
from backend.app.models.local_library import (
    LocalLibraryConfigResponse,
    LocalLibraryConfigUpdate,
    LocalReferenceBookResponse,
    LocalReferenceChapterResponse,
    LocalReferenceChapterUpdate,
    ReferenceAbsorptionTaskResponse,
    ScanReportResponse,
)
from backend.app.services import (
    local_library_config,
    local_library_scanner,
    local_book_parser_service,
)

router = APIRouter(tags=["本地书库管理"])
logger = logging.getLogger(__name__)


def assert_local_file_access_enabled():
    """验证是否开启了本地目录访问。若未开启，所有非 config 接口将抛出 403。"""
    from backend.app.services.local_file_guard import get_file_access_flag
    if not get_file_access_flag():
        raise HTTPException(
            status_code=403,
            detail="本地文件访问功能已禁用(Feature Flag ALLOW_LOCAL_FILE_ACCESS 为 false)。"
        )


@router.get("/api/v1/local-library/config", response_model=LocalLibraryConfigResponse)
def get_config(request: Request):
    get_current_user(request)
    config = local_library_config.get_local_library_config()
    return config


@router.put("/api/v1/local-library/config", response_model=LocalLibraryConfigResponse)
def update_config(data: LocalLibraryConfigUpdate, request: Request):
    get_current_user(request)
    config = local_library_config.update_local_library_config(data.model_dump(exclude_unset=True))
    return config


@router.post("/api/v1/local-library/config/test")
def test_directory_status(data: LocalLibraryConfigUpdate, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    source_status = local_library_config.check_directory_status(data.source_dir)
    essence_status = local_library_config.check_directory_status(data.essence_dir)
    return {
        "source_dir": source_status,
        "essence_dir": essence_status,
        "success": source_status["exists"] and essence_status["exists"] and source_status["writable"] and essence_status["writable"],
    }


@router.post("/api/v1/local-library/scan", response_model=ScanReportResponse)
def scan_library(request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    try:
        report = local_library_scanner.scan_local_directory()
        return report
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/api/v1/local-library/books", response_model=List[LocalReferenceBookResponse])
def get_books(request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    
    books = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM local_reference_book")
        columns = [column[0] for column in cursor.description]
        
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            if isinstance(row_dict.get('tags'), str):
                try:
                    row_dict['tags'] = json.loads(row_dict['tags'])
                except json.JSONDecodeError:
                    row_dict['tags'] = []
            books.append(row_dict)
            
    return books


@router.get("/api/v1/local-library/books/{book_id}", response_model=LocalReferenceBookResponse)
def get_book_details(book_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM local_reference_book WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="参考书不存在")
            
        columns = [column[0] for column in cursor.description]
        row_dict = dict(zip(columns, row))
        
        if isinstance(row_dict.get('tags'), str):
            try:
                row_dict['tags'] = json.loads(row_dict['tags'])
            except json.JSONDecodeError:
                row_dict['tags'] = []
                
        return row_dict


@router.post("/api/v1/local-library/books/{book_id}/parse")
def parse_book_chapters(book_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    try:
        result = local_book_parser_service.parse_book(book_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/local-library/books/{book_id}/chapters/rebuild")
def rebuild_book_chapters(book_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    try:
        result = local_book_parser_service.parse_book(book_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/local-library/books/{book_id}/chapters", response_model=List[LocalReferenceChapterResponse])
def get_book_chapters(book_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    
    chapters = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM local_reference_chapter WHERE book_id = ? ORDER BY chapter_index ASC", (book_id,))
        columns = [column[0] for column in cursor.description]
        
        for row in cursor.fetchall():
            chapters.append(dict(zip(columns, row)))
            
    return chapters


@router.patch("/api/v1/local-library/books/{book_id}/chapters/{chapter_id}", response_model=LocalReferenceChapterResponse)
def update_book_chapter(book_id: str, chapter_id: str, data: LocalReferenceChapterUpdate, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        
        if data.title is not None:
            update_fields.append("title = ?")
            update_values.append(data.title)
        if data.chapter_index is not None:
            update_fields.append("chapter_index = ?")
            update_values.append(data.chapter_index)
            
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
            
        update_values.extend([chapter_id, book_id])
        query = f"UPDATE local_reference_chapter SET {', '.join(update_fields)} WHERE id = ? AND book_id = ?"
        
        cursor.execute(query, update_values)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Chapter not found")
            
        conn.commit()
        
        cursor.execute("SELECT * FROM local_reference_chapter WHERE id = ?", (chapter_id,))
        row = cursor.fetchone()
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))


@router.post("/api/v1/local-library/books/{book_id}/absorb", response_model=ReferenceAbsorptionTaskResponse)
def absorb_book(book_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    from backend.app.services.local_absorption_task_manager import start_absorption_task, get_task_status
    try:
        task_id = start_absorption_task(book_id, "full_absorb")
        return get_task_status(task_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/v1/local-library/books/{book_id}/absorb/pause")
def pause_absorption(book_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    from backend.app.services.local_absorption_task_manager import pause_absorption_task
    # We need task_id. For now assume the client manages task_id or we get the latest active task for the book.
    # To keep the API signature as is, we can fetch the active task for the book from DB.
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_id FROM reference_absorption_task WHERE book_id = ? AND status = 'running' ORDER BY created_at DESC LIMIT 1", (book_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No running task found for this book")
        task_id = row[0]
    
    try:
        pause_absorption_task(task_id)
        return {"status": "paused", "book_id": book_id, "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/v1/local-library/books/{book_id}/absorb/resume")
def resume_absorption(book_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    from backend.app.services.local_absorption_task_manager import resume_absorption_task
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_id FROM reference_absorption_task WHERE book_id = ? AND status IN ('paused', 'partial') ORDER BY created_at DESC LIMIT 1", (book_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No paused task found for this book")
        task_id = row[0]
        
    try:
        resume_absorption_task(task_id)
        return {"status": "running", "book_id": book_id, "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/v1/local-library/books/{book_id}/absorb/cancel")
def cancel_absorption(book_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    from backend.app.services.local_absorption_task_manager import cancel_absorption_task
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_id FROM reference_absorption_task WHERE book_id = ? AND status IN ('running', 'paused', 'queued') ORDER BY created_at DESC LIMIT 1", (book_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No active task found for this book")
        task_id = row[0]
        
    try:
        cancel_absorption_task(task_id)
        return {"status": "cancelled", "book_id": book_id, "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/v1/local-library/books/{book_id}/absorb/retry-failed")
def retry_failed_absorption(book_id: str, request: Request):
    get_current_user(request)
    assert_local_file_access_enabled()
    from backend.app.services.local_absorption_task_manager import retry_failed_task
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_id FROM reference_absorption_task WHERE book_id = ? AND status = 'failed' ORDER BY created_at DESC LIMIT 1", (book_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No failed task found for this book")
        task_id = row[0]
        
    try:
        retry_failed_task(task_id)
        return {"status": "running", "book_id": book_id, "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/local-library/books/{book_id}/essence")
def get_essence_details(book_id: str, request: Request, file_key: str = None):
    get_current_user(request)
    assert_local_file_access_enabled()
    
    from backend.app.services.local_essence_writer_service import read_essence_file, get_manifest
    
    try:
        if file_key:
            content = read_essence_file(book_id, file_key)
            return {"file_key": file_key, "content": content}
        else:
            manifest = get_manifest(book_id)
            return {"manifest": manifest}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
