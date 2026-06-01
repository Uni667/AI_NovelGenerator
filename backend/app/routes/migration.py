# -*- coding: utf-8 -*-
"""
FastAPI Migration Router
Provides /api/v1/migration/export-all for exporting entire system data.
Disabled by default, requires MIGRATION_ENABLED=true and MIGRATION_TOKEN auth.
"""
import os
import base64
import sqlite3
import logging
from fastapi import APIRouter, HTTPException, Request
from backend.app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["数据迁移"])

def check_migration_auth(request: Request):
    """Checks migration environment variables and tokens."""
    # 1. Check if migration is enabled
    migration_enabled = os.getenv("MIGRATION_ENABLED", "false").lower()
    if migration_enabled != "true":
        raise HTTPException(status_code=403, detail="数据迁移服务未开启 (MIGRATION_ENABLED != true)")
        
    # 2. Check if token auth is required
    migration_token = os.getenv("MIGRATION_TOKEN", "").strip()
    if migration_token:
        # Check X-Migration-Token header
        header_token = request.headers.get("X-Migration-Token", "").strip()
        if not header_token:
            # Fallback to Authorization header
            auth_header = request.headers.get("Authorization", "").strip()
            if auth_header.startswith("Bearer "):
                header_token = auth_header.removeprefix("Bearer ")
            else:
                header_token = auth_header
                
        if header_token != migration_token:
            raise HTTPException(status_code=401, detail="数据迁移令牌校验失败")

@router.get("/api/v1/migration/export-all")
def export_all(request: Request):
    """
    Exports all database tables and physical files under the project paths.
    """
    check_migration_auth(request)
    
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    BACKEND_PROJECTS = os.path.join(ROOT_DIR, "backend", "projects")
    DATA_PROJECTS = os.path.join(ROOT_DIR, "data", "projects")
    
    # 1. Export database rows
    db_dump = {}
    tables = [
        "user", "project", "project_config", "chapter", "knowledge_file", 
        "character_profile", "character_relationship", "character_conflict", 
        "character_conflict_participant", "character_appearance", "project_file", 
        "generation_task", "api_credential", "model_profile", 
        "project_model_assignment", "model_invocation_log", "schema_version"
    ]
    
    try:
        with get_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Find what tables actually exist in sqlite_master
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            for t in tables:
                if t in existing_tables:
                    cursor.execute(f"SELECT * FROM {t}")
                    rows = cursor.fetchall()
                    db_dump[t] = [dict(row) for row in rows]
                else:
                    db_dump[t] = []
    except Exception as e:
        logger.exception("Failed to dump database tables")
        raise HTTPException(status_code=500, detail=f"数据库导出失败: {str(e)}")
        
    # 2. Export physical files
    files_dump = {}
    
    # Locate all active projects from project table to scan their filepaths
    project_ids = [p["id"] for p in db_dump.get("project", [])]
    
    # Helper to serialize files recursively
    def scan_project_dir(proj_id: str, base_dir: str):
        proj_root = os.path.join(base_dir, proj_id)
        if not os.path.exists(proj_root):
            return
            
        for root, dirs, files in os.walk(proj_root):
            for file in files:
                file_path = os.path.join(root, file)
                # Compute relative path in projects directory (e.g. {id}/chapters/chapter_1.txt)
                rel_path = os.path.relpath(file_path, base_dir)
                
                # Check file type: text files can be sent as string, binary files as base64
                ext = os.path.splitext(file)[1].lower()
                is_text = ext in (".txt", ".md", ".json", ".xml", ".html", ".css", ".js", ".ts", ".tsx")
                
                try:
                    if is_text:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                        files_dump[rel_path] = {
                            "type": "text",
                            "content": content
                        }
                    else:
                        with open(file_path, "rb") as f:
                            content_bytes = f.read()
                        encoded = base64.b64encode(content_bytes).decode("utf-8")
                        files_dump[rel_path] = {
                            "type": "base64",
                            "content": encoded
                        }
                except Exception as e:
                    logger.warning(f"Failed to read file {file_path} for export: {e}")
                    
    for pid in project_ids:
        scan_project_dir(pid, BACKEND_PROJECTS)
        scan_project_dir(pid, DATA_PROJECTS)
        
    return {
        "database": db_dump,
        "files": files_dump
    }
