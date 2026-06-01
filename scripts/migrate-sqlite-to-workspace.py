#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database and Project File Migration Script
Usage:
  python scripts/migrate-sqlite-to-workspace.py --dry-run
  python scripts/migrate-sqlite-to-workspace.py --execute
"""
import os
import sys
import re
import json
import sqlite3
import shutil
import hashlib
import zipfile
import argparse
from datetime import datetime
import yaml

# Hardcode standard output/error encoding on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Paths configuration
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(WORKSPACE_ROOT, "data", "projects.db")
BACKEND_PROJECTS_DIR = os.path.join(WORKSPACE_ROOT, "backend", "projects")
DATA_PROJECTS_DIR = os.path.join(WORKSPACE_ROOT, "data", "projects")

TARGET_WORKSPACE = os.path.join(WORKSPACE_ROOT, "AI-Novel-Workspace")
TARGET_PROJECTS = os.path.join(TARGET_WORKSPACE, "projects")
TARGET_BACKUPS = os.path.join(TARGET_WORKSPACE, "backups")

def safe_filename(name: str, fallback: str = "untitled") -> str:
    """
    Sanitizes string for use in path/file names.
    Removes invalid characters and directory traversal markers.
    """
    if not name:
        return fallback
    # Remove Windows/Linux forbidden characters: / \ : * ? " < > |
    cleaned = re.sub(r'[\\/:*?"<>|]', '', name)
    # Remove relative path traversal dots
    cleaned = cleaned.replace("..", "")
    # Trim whitespace
    cleaned = cleaned.strip()
    return cleaned if cleaned else fallback

def calculate_sha256(filepath: str) -> str:
    """Calculates SHA-256 hash of a file."""
    if not os.path.exists(filepath):
        return ""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"Error computing hash for {filepath}: {e}")
        return ""

def zip_directory(src_dir: str, zip_path: str) -> bool:
    """Compresses a directory into a zip archive."""
    if not os.path.exists(src_dir):
        return False
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, src_dir)
                    zf.write(full_path, rel_path)
        return True
    except Exception as e:
        print(f"Failed to compress {src_dir} to {zip_path}: {e}")
        return False

def convert_outline_json_to_md(outline_json: dict) -> str:
    """Converts structured outline_state.json chapters list to markdown outline."""
    chapters = outline_json.get("chapters", [])
    if not chapters:
        return ""
    md = "# 目录与章节大纲 (Outline)\n\n"
    for ch in chapters:
        num = ch.get("chapter_number", ch.get("number", 0))
        title = ch.get("chapter_title", ch.get("title", ""))
        md += f"## 第 {num} 章: {title}\n"
        if "chapter_role" in ch or "role" in ch:
            md += f"- **主角/视角**: {ch.get('chapter_role', ch.get('role', ''))}\n"
        if "chapter_purpose" in ch or "purpose" in ch:
            md += f"- **写作目的**: {ch.get('chapter_purpose', ch.get('purpose', ''))}\n"
        if "suspense_level" in ch:
            md += f"- **悬念等级**: {ch.get('suspense_level', '')}\n"
        if "chapter_summary" in ch or "summary" in ch:
            md += f"- **章节摘要**: {ch.get('chapter_summary', ch.get('summary', ''))}\n"
        md += "\n"
    return md

def perform_full_scan(db_conn: sqlite3.Connection):
    """
    1. Lists all database tables and counts.
    2. Scans files under the project directory root.
    3. Outputs full-scan-report.json.
    """
    cursor = db_conn.cursor()
    
    # 1. Database table row counts
    sqlite_tables_summary = {}
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        for t in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            sqlite_tables_summary[t] = cursor.fetchone()[0]
    except Exception as e:
        print(f"Database scan failed: {e}")
        
    # 2. File scanner
    discovered_files = []
    
    directories_to_scan = [
        ("backend/projects", BACKEND_PROJECTS_DIR),
        ("data/projects", DATA_PROJECTS_DIR),
        ("projects", os.path.join(WORKSPACE_ROOT, "projects")),
        ("uploads", os.path.join(WORKSPACE_ROOT, "uploads")),
        ("memory", os.path.join(WORKSPACE_ROOT, "memory")),
        ("chapters", os.path.join(WORKSPACE_ROOT, "chapters")),
        ("prompts", os.path.join(WORKSPACE_ROOT, "prompts")),
        ("data", os.path.join(WORKSPACE_ROOT, "data"))
    ]
    
    for label, dir_path in directories_to_scan:
        if os.path.exists(dir_path):
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in (".db", ".sqlite", ".json", ".md", ".txt"):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, WORKSPACE_ROOT)
                        size = os.path.getsize(full_path)
                        
                        # Determine if this file will be migrated/copied/skipped
                        migrated = False
                        copied_legacy = False
                        
                        # Check chapter txt files
                        if "chapters" in rel_path and file.startswith("chapter_") and ext == ".txt":
                            migrated = True
                        # Check worldview config txt files
                        elif file in ("Novel_architecture.txt", "Novel_directory.txt", "global_summary.txt", "architecture_world_building.txt", "custom_prompts.json"):
                            migrated = True
                        # Check memory files
                        elif "memory" in rel_path and file in ("global_summary.md", "outline_state.json", "plot_threads.json", "character_state.json", "name_usage_rules.json"):
                            migrated = True
                        # Check other memory backups/patches
                        elif "memory" in rel_path:
                            copied_legacy = True
                        elif label == "data" and file == "projects.db":
                            migrated = True # copied as DB backup
                            
                        discovered_files.append({
                            "path": rel_path,
                            "size_bytes": size,
                            "type": ext[1:],
                            "label": label,
                            "migrated": migrated,
                            "copied_legacy": copied_legacy
                        })
                        
    # Write full-scan-report.json
    full_scan_report = {
        "scan_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sqlite_tables_summary": sqlite_tables_summary,
        "discovered_files_count": len(discovered_files),
        "discovered_files": discovered_files
    }
    
    full_scan_path = os.path.join(WORKSPACE_ROOT, "full-scan-report.json")
    with open(full_scan_path, "w", encoding="utf-8") as f:
        json.dump(full_scan_report, f, ensure_ascii=False, indent=2)
        
    return sqlite_tables_summary, discovered_files

def scan_data(db_conn: sqlite3.Connection):
    """
    Prepares data mapping and statistis. Maps memory folder files, splits characters,
    audits chapter bodies, and records skipped/migrated files.
    """
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM project")
    projects_rows = cursor.fetchall()
    
    sqlite_tables_summary, discovered_files = perform_full_scan(db_conn)
    
    report_data = {
        "sqlite_tables_summary": sqlite_tables_summary,
        "discovered_files": [],
        "migrated_files": [],
        "copied_legacy_files": [],
        "skipped_files_with_reason": [],
        "unmapped_files": [],
        "chapter_source_detail": [],
        
        "total_projects": len(projects_rows),
        "total_chapters": 0,
        "total_characters": 0,
        "total_worldviews": 0,
        "total_prompts": 0,
        "total_history": 0,
        "failed_parsed_fields": [],
        "manual_check_items": [],
        "projects": []
    }
    
    # Map discovered files into the report structure
    for df in discovered_files:
        report_data["discovered_files"].append(df["path"])
        if df["migrated"]:
            # Destination will be set inside project loop, but we tag it here
            pass
        elif df["copied_legacy"]:
            # Target is legacy/
            pass
        else:
            report_data["unmapped_files"].append(df["path"])
            
    # Process projects
    for proj_row in projects_rows:
        proj = dict(proj_row)
        proj_id = proj["id"]
        proj_name = proj["name"]
        
        # Build slugified project folder name
        slug_base = safe_filename(proj_name, fallback=f"project-{proj_id[:8]}")
        proj_slug = f"{slug_base}-{proj_id[:8]}"
        
        # Fetch configurations and assignments
        cursor.execute("SELECT * FROM project_config WHERE project_id = ?", (proj_id,))
        config_row = cursor.fetchone()
        config = dict(config_row) if config_row else {}
        
        cursor.execute("SELECT * FROM project_model_assignment WHERE project_id = ?", (proj_id,))
        assignment_row = cursor.fetchone()
        assignment = dict(assignment_row) if assignment_row else {}
        
        # 1. Chapters scanning
        cursor.execute("SELECT * FROM chapter WHERE project_id = ?", (proj_id,))
        chapter_rows = cursor.fetchall()
        
        # Check files on disk too, to verify chapter numbers
        disk_chapters = []
        proj_chapters_dir = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "chapters")
        if os.path.exists(proj_chapters_dir):
            for file in os.listdir(proj_chapters_dir):
                m = re.match(r"chapter_(\d+)\.txt", file)
                if m:
                    disk_chapters.append(int(m.group(1)))
                    
        # Concat db chapter numbers and disk chapter numbers
        db_chapters = [c["chapter_number"] for c in chapter_rows]
        all_chapter_nums = sorted(list(set(db_chapters + disk_chapters)))
        
        # Check chapter 999 sandbox warnings
        if all_chapter_nums == [999]:
            report_data["manual_check_items"].append({
                "type": "chapter_999_sandbox_warning",
                "project_id": proj_id,
                "project_name": proj_name,
                "message": f"项目 [{proj_name}] 仅包含第 999 章草稿。此章节可能是开发测试时使用的沙盒或草稿占位符，未检测到真实的章节顺序配置。"
            })
            
        chapters_list = []
        for ch_num in all_chapter_nums:
            # Find in DB
            db_ch_row = next((c for c in chapter_rows if c["chapter_number"] == ch_num), None)
            db_ch = dict(db_ch_row) if db_ch_row else {}
            ch_title = db_ch.get("chapter_title") or ""
            ch_id = db_ch.get("id")
            
            text_source = None
            warning = None
            chapter_text = ""
            
            # Check old directory paths for drafts
            possible_paths = [
                os.path.join(BACKEND_PROJECTS_DIR, proj_id, "chapters", f"chapter_{ch_num}.txt"),
                os.path.join(DATA_PROJECTS_DIR, proj_id, "chapters", f"chapter_{ch_num}.txt"),
                os.path.join(BACKEND_PROJECTS_DIR, proj_id, f"chapter_{ch_num}.txt"),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    text_source = os.path.relpath(path, WORKSPACE_ROOT)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            chapter_text = f.read()
                    except Exception as e:
                        warning = f"Failed to read chapter file {path}: {str(e)}"
                    break
            
            if not text_source:
                cursor.execute(
                    "SELECT content FROM project_file WHERE project_id = ? AND type = 'chapter' AND filename LIKE ?",
                    (proj_id, f"%chapter_{ch_num}%")
                )
                pf_row = cursor.fetchone()
                if pf_row:
                    text_source = f"database (project_file content for chapter {ch_num})"
                    chapter_text = pf_row[0]
                else:
                    warning = "章节正文文件缺失 (Missing body text file)"
                    report_data["manual_check_items"].append({
                        "type": "chapter_text_missing",
                        "project_id": proj_id,
                        "project_name": proj_name,
                        "chapter_number": ch_num,
                        "message": f"项目 [{proj_name}] 第 {ch_num} 章正文来源缺失！请检查文件是否存在。"
                    })
            
            ch_title_safe = safe_filename(ch_title, fallback="")
            ch_dest_filename = f"{ch_num:03d}-{ch_title_safe}.md" if ch_title_safe else f"{ch_num:03d}.md"
            ch_dest_path = f"projects/{proj_slug}/chapters/{ch_dest_filename}"
            
            if text_source:
                report_data["migrated_files"].append({
                    "src": text_source,
                    "dest": ch_dest_path
                })
                
            chapters_list.append({
                "chapter_number": ch_num,
                "title": ch_title,
                "text_source": text_source,
                "text_word_count": len(chapter_text),
                "warning": warning
            })
            
            report_data["chapter_source_detail"].append({
                "project_slug": proj_slug,
                "chapter_number": ch_num,
                "source_type": "file" if text_source and not text_source.startswith("database") else ("database" if text_source else "missing"),
                "source_path": text_source or "N/A",
                "is_valid": text_source is not None
            })
            
            report_data["total_chapters"] += 1
            
        # 2. Characters scanning
        cursor.execute("SELECT * FROM character_profile WHERE project_id = ?", (proj_id,))
        char_rows = cursor.fetchall()
        for char_row in char_rows:
            report_data["total_characters"] += 1
            
        # Check character_state.json from memory folder
        char_state_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "memory", "character_state.json")
        if os.path.exists(char_state_path):
            try:
                with open(char_state_path, "r", encoding="utf-8") as f:
                    char_state = json.load(f)
                memory_chars = char_state.get("characters", [])
                for mc in memory_chars:
                    # These characters parsed from memory state JSON will be split into cards
                    mc_name = mc.get("name")
                    if mc_name:
                        mc_name_safe = safe_filename(mc_name)
                        report_data["migrated_files"].append({
                            "src": os.path.relpath(char_state_path, WORKSPACE_ROOT),
                            "dest": f"projects/{proj_slug}/characters/{mc_name_safe}.json"
                        })
                        report_data["total_characters"] += 1
            except Exception as e:
                report_data["failed_parsed_fields"].append({
                    "file": char_state_path,
                    "error": f"Failed to parse character_state.json: {e}"
                })
                
        # 3. Worldview files scanning
        worldview_filenames = {
            "Novel_architecture.txt": "architecture.md",
            "architecture_core_seed.txt": "core_seed.md",
            "architecture_character_dynamics.txt": "character_dynamics.md",
            "architecture_world_building.txt": "worldview.md",
            "architecture_plot.txt": "plot_architecture.md",
            "plot_arcs.txt": "plot_arcs.md",
            "character_state.txt": "character_state.md"
        }
        for old_file, new_file in worldview_filenames.items():
            disk_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, old_file)
            if os.path.exists(disk_path):
                report_data["migrated_files"].append({
                    "src": os.path.relpath(disk_path, WORKSPACE_ROOT),
                    "dest": f"projects/{proj_slug}/world/{new_file}"
                })
                report_data["total_worldviews"] += 1
                
        # Worldview memory files scanning
        memory_world_files = {
            "outline_state.json": "world/outline_state.json",
            "plot_threads.json": "world/plot_threads.json",
            "name_usage_rules.json": "world/name_usage_rules.json"
        }
        for mem_file, new_dest in memory_world_files.items():
            mem_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "memory", mem_file)
            if os.path.exists(mem_path):
                report_data["migrated_files"].append({
                    "src": os.path.relpath(mem_path, WORKSPACE_ROOT),
                    "dest": f"projects/{proj_slug}/{new_dest}"
                })
                report_data["total_worldviews"] += 1
                
                # outline_state conversion
                if mem_file == "outline_state.json":
                    report_data["migrated_files"].append({
                        "src": os.path.relpath(mem_path, WORKSPACE_ROOT),
                        "dest": f"projects/{proj_slug}/outline.md"
                    })
                    
        # memory/global_summary.md -> synopsis.md
        mem_summary_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "memory", "global_summary.md")
        if os.path.exists(mem_summary_path):
            report_data["migrated_files"].append({
                "src": os.path.relpath(mem_summary_path, WORKSPACE_ROOT),
                "dest": f"projects/{proj_slug}/synopsis.md"
            })
            report_data["total_worldviews"] += 1
            
        # 4. Prompts scanning
        custom_prompt_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "custom_prompts.json")
        if os.path.exists(custom_prompt_path):
            try:
                with open(custom_prompt_path, "r", encoding="utf-8") as pf:
                    prompts_dict = json.load(pf)
                for key in prompts_dict.keys():
                    key_safe = safe_filename(key, fallback="prompt")
                    report_data["migrated_files"].append({
                        "src": os.path.relpath(custom_prompt_path, WORKSPACE_ROOT),
                        "dest": f"projects/{proj_slug}/prompts/{key_safe}.txt"
                    })
                    report_data["total_prompts"] += 1
            except:
                pass
                
        # 5. History / Task logs scanning
        cursor.execute("SELECT COUNT(*) FROM generation_task WHERE project_id = ?", (proj_id,))
        report_data["total_history"] += cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM model_invocation_log WHERE project_id = ?", (proj_id,))
        report_data["total_history"] += cursor.fetchone()[0]
        
        # 6. Legacy memory folder scan (anything else under memory/)
        proj_mem_dir = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "memory")
        if os.path.exists(proj_mem_dir):
            for root, dirs, files in os.walk(proj_mem_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_to_mem = os.path.relpath(file_path, proj_mem_dir)
                    
                    # We list files in copied_legacy_files
                    # If it's one of the processed/migrated memory files, we still copy them to legacy for safety
                    # Or we copy other things like backups/ and patches/ folders
                    dest_legacy = f"projects/{proj_slug}/legacy/memory/{rel_to_mem.replace(os.sep, '/')}"
                    report_data["copied_legacy_files"].append({
                        "src": os.path.relpath(file_path, WORKSPACE_ROOT),
                        "dest": dest_legacy
                    })
                    
        # Check backups/ folder or others
        # Skip custom_prompts_backup from migration but list it in skipped_files_with_reason
        backup_prompts_dir = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "custom_prompts_backup")
        if os.path.exists(backup_prompts_dir):
            for file in os.listdir(backup_prompts_dir):
                report_data["skipped_files_with_reason"].append({
                    "path": os.path.relpath(os.path.join(backup_prompts_dir, file), WORKSPACE_ROOT),
                    "reason": "提示词历史快照不直接转换到新工作区。原始快照将保存在 backups ZIP 备份中。"
                })

        report_data["projects"].append({
            "old_id": proj_id,
            "name": proj_name,
            "slug": proj_slug,
            "chapters_count": len(all_chapter_nums),
            "characters_count": len(char_rows)
        })
        
    return report_data

def migrate_data(db_conn: sqlite3.Connection, timestamp: str):
    """
    Executes actual migration. Translates memory JSONs, splits characters,
    copies legacy folders, compresses old files, and creates timestamped backups.
    """
    # Initialize workspace
    os.makedirs(TARGET_WORKSPACE, exist_ok=True)
    os.makedirs(TARGET_PROJECTS, exist_ok=True)
    os.makedirs(TARGET_BACKUPS, exist_ok=True)
    
    # Calculate database SHA-256
    source_sha = calculate_sha256(DB_PATH)
    
    # 1. Duplicate database backup
    backup_db_name = f"backup-old-database-{timestamp}.sqlite"
    backup_db_path = os.path.join(TARGET_BACKUPS, backup_db_name)
    shutil.copy2(DB_PATH, backup_db_path)
    
    db_dir = os.path.dirname(DB_PATH)
    shutil.copy2(DB_PATH, os.path.join(db_dir, backup_db_name))
    
    backup_sha = calculate_sha256(backup_db_path)
    
    # 2. Package physical folder backup
    backup_zip_name = f"backup-old-projects-{timestamp}.zip"
    backup_zip_path = os.path.join(TARGET_BACKUPS, backup_zip_name)
    
    with zipfile.ZipFile(backup_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(BACKEND_PROJECTS_DIR):
            for root, dirs, files in os.walk(BACKEND_PROJECTS_DIR):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, os.path.dirname(BACKEND_PROJECTS_DIR))
                    zf.write(full_path, rel_path)
        if os.path.exists(DATA_PROJECTS_DIR):
            for root, dirs, files in os.walk(DATA_PROJECTS_DIR):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, os.path.dirname(DATA_PROJECTS_DIR))
                    zf.write(full_path, rel_path)
                    
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM project")
    projects_rows = cursor.fetchall()
    
    migration_summary = {
        "projects_migrated": 0,
        "chapters_migrated": 0,
        "characters_migrated": 0,
        "worldview_files_migrated": 0,
        "prompts_migrated": 0,
        "history_migrated": 0,
        "legacy_files_copied": 0
    }
    
    report_data = scan_data(db_conn)
    
    for proj_row in projects_rows:
        proj = dict(proj_row)
        proj_id = proj["id"]
        proj_name = proj["name"]
        
        # Build slug
        slug_base = safe_filename(proj_name, fallback=f"project-{proj_id[:8]}")
        proj_slug = f"{slug_base}-{proj_id[:8]}"
        
        # Create directories
        proj_dir = os.path.join(TARGET_PROJECTS, proj_slug)
        os.makedirs(proj_dir, exist_ok=True)
        
        chapters_dir = os.path.join(proj_dir, "chapters")
        characters_dir = os.path.join(proj_dir, "characters")
        world_dir = os.path.join(proj_dir, "world")
        prompts_dir = os.path.join(proj_dir, "prompts")
        history_dir = os.path.join(proj_dir, "history")
        exports_dir = os.path.join(proj_dir, "exports")
        legacy_mem_dir = os.path.join(proj_dir, "legacy", "memory")
        
        os.makedirs(chapters_dir, exist_ok=True)
        os.makedirs(characters_dir, exist_ok=True)
        os.makedirs(world_dir, exist_ok=True)
        os.makedirs(prompts_dir, exist_ok=True)
        os.makedirs(history_dir, exist_ok=True)
        os.makedirs(exports_dir, exist_ok=True)
        os.makedirs(legacy_mem_dir, exist_ok=True)
        
        # Fetch info
        cursor.execute("SELECT * FROM project_config WHERE project_id = ?", (proj_id,))
        config_row = cursor.fetchone()
        config = dict(config_row) if config_row else {}
        
        cursor.execute("SELECT * FROM project_model_assignment WHERE project_id = ?", (proj_id,))
        assignment_row = cursor.fetchone()
        assignment = dict(assignment_row) if assignment_row else {}
        
        # Write project.json
        project_json_content = {
            "old_project_id": proj_id,
            "new_project_id": proj_id,
            "name": proj_name,
            "slug": proj_slug,
            "description": proj.get("description", ""),
            "status": proj.get("status", "draft"),
            "created_at": proj.get("created_at", ""),
            "updated_at": proj.get("updated_at", ""),
            "user_id": proj.get("user_id", ""),
            "config": config,
            "model_assignment": assignment
        }
        
        project_json_path = os.path.join(proj_dir, "project.json")
        with open(project_json_path, "w", encoding="utf-8") as jf:
            json.dump(project_json_content, jf, ensure_ascii=False, indent=2)
        migration_summary["projects_migrated"] += 1
            
        # 1. Migrate Synopsis
        # Try global_summary.md in memory folder first
        synopsis_content = ""
        mem_summary_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "memory", "global_summary.md")
        if os.path.exists(mem_summary_path):
            try:
                with open(mem_summary_path, "r", encoding="utf-8") as f:
                    synopsis_content = f.read()
            except:
                pass
        # Fallback to global_summary.txt
        if not synopsis_content:
            old_summary_paths = [
                os.path.join(BACKEND_PROJECTS_DIR, proj_id, "global_summary.txt"),
                os.path.join(DATA_PROJECTS_DIR, proj_id, "global_summary.txt")
            ]
            for path in old_summary_paths:
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            synopsis_content = f.read()
                        break
                    except:
                        pass
        # Database fallback
        if not synopsis_content:
            cursor.execute("SELECT content FROM project_file WHERE project_id = ? AND type = 'summary' AND is_current = 1", (proj_id,))
            pf_row = cursor.fetchone()
            if pf_row:
                synopsis_content = pf_row[0]
                
        with open(os.path.join(proj_dir, "synopsis.md"), "w", encoding="utf-8") as f:
            f.write(synopsis_content)
            
        # 2. Migrate Outline (from outline_state.json or Novel_directory.txt)
        outline_content = ""
        mem_outline_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "memory", "outline_state.json")
        if os.path.exists(mem_outline_path):
            try:
                with open(mem_outline_path, "r", encoding="utf-8") as f:
                    outline_json = json.load(f)
                outline_content = convert_outline_json_to_md(outline_json)
            except:
                pass
                
        if not outline_content:
            old_outline_paths = [
                os.path.join(BACKEND_PROJECTS_DIR, proj_id, "Novel_directory.txt"),
                os.path.join(DATA_PROJECTS_DIR, proj_id, "Novel_directory.txt")
            ]
            for path in old_outline_paths:
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            outline_content = f.read()
                        break
                    except:
                        pass
        if not outline_content:
            cursor.execute("SELECT content FROM project_file WHERE project_id = ? AND type = 'outline' AND is_current = 1", (proj_id,))
            pf_row = cursor.fetchone()
            if pf_row:
                outline_content = pf_row[0]
                
        with open(os.path.join(proj_dir, "outline.md"), "w", encoding="utf-8") as f:
            f.write(outline_content)
            
        # 3. Migrate Chapters
        # Get unique chapter list from scan_report
        proj_detail = next((p for p in report_data["projects"] if p["old_id"] == proj_id), None)
        chapters_to_migrate = proj_detail["chapters"] if proj_detail else []
        
        cursor.execute("SELECT * FROM chapter WHERE project_id = ?", (proj_id,))
        chapter_rows = {r["chapter_number"]: dict(r) for r in cursor.fetchall()}
        
        for ch_info in chapters_to_migrate:
            ch_num = ch_info["chapter_number"]
            ch_title = ch_info["title"]
            
            db_ch = chapter_rows.get(ch_num, {})
            ch_id = db_ch.get("id")
            
            chapter_text = ""
            text_src = ch_info["text_source"]
            if text_src:
                if text_src.startswith("database"):
                    # Find inside project_file table
                    cursor.execute(
                        "SELECT content FROM project_file WHERE project_id = ? AND type = 'chapter' AND filename LIKE ?",
                        (proj_id, f"%chapter_{ch_num}%")
                    )
                    pf_row = cursor.fetchone()
                    if pf_row:
                        chapter_text = pf_row[0]
                else:
                    # Find inside disk
                    full_src_path = os.path.join(WORKSPACE_ROOT, text_src)
                    if os.path.exists(full_src_path):
                        try:
                            with open(full_src_path, "r", encoding="utf-8") as f:
                                chapter_text = f.read()
                        except:
                            pass
                            
            ch_title_safe = safe_filename(ch_title, fallback="")
            ch_filename = f"{ch_num:03d}-{ch_title_safe}.md" if ch_title_safe else f"{ch_num:03d}.md"
            
            # YAML frontmatter
            frontmatter = {
                "old_chapter_id": ch_id,
                "chapter_number": ch_num,
                "title": ch_title,
                "chapter_role": db_ch.get("chapter_role", ""),
                "chapter_purpose": db_ch.get("chapter_purpose", ""),
                "suspense_level": db_ch.get("suspense_level", ""),
                "foreshadowing": db_ch.get("foreshadowing", ""),
                "plot_twist_level": db_ch.get("plot_twist_level", ""),
                "summary": db_ch.get("chapter_summary", ""),
                "word_count": db_ch.get("word_count", 0),
                "status": db_ch.get("status", "pending"),
                "created_at": db_ch.get("created_at", ""),
                "updated_at": db_ch.get("updated_at", "")
            }
            
            frontmatter_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, default_flow_style=False)
            markdown_content = f"---\n{frontmatter_yaml}---\n\n{chapter_text}"
            
            with open(os.path.join(chapters_dir, ch_filename), "w", encoding="utf-8") as cf:
                cf.write(markdown_content)
            migration_summary["chapters_migrated"] += 1
            
        # 4. Migrate Characters
        # A. Database characters
        cursor.execute("SELECT * FROM character_profile WHERE project_id = ?", (proj_id,))
        db_chars = cursor.fetchall()
        for char_row in db_chars:
            char = dict(char_row)
            char_id = char["id"]
            char_name = char["name"]
            char_name_safe = safe_filename(char_name, fallback=f"character-{char_id}")
            
            cursor.execute(
                "SELECT * FROM character_relationship WHERE project_id = ? AND (character_id_a = ? OR character_id_b = ?)",
                (proj_id, char_id, char_id)
            )
            relationships = [dict(r) for r in cursor.fetchall()]
            
            cursor.execute(
                """SELECT c.* FROM character_conflict c
                   JOIN character_conflict_participant p ON c.id = p.conflict_id
                   WHERE c.project_id = ? AND p.character_id = ?""",
                (proj_id, char_id)
            )
            conflicts = [dict(c) for c in cursor.fetchall()]
            
            cursor.execute(
                "SELECT * FROM character_appearance WHERE project_id = ? AND character_id = ?",
                (proj_id, char_id)
            )
            appearances = [dict(a) for a in cursor.fetchall()]
            
            character_data = {
                "id": char_id,
                "name": char_name,
                "description": char.get("description", ""),
                "status": char.get("status", ""),
                "source": char.get("source", ""),
                "first_appearance_chapter": char.get("first_appearance_chapter"),
                "updated_at": char.get("updated_at", ""),
                "relationships": relationships,
                "conflicts": conflicts,
                "appearances": appearances
            }
            
            # Save character JSON
            with open(os.path.join(characters_dir, f"{char_name_safe}.json"), "w", encoding="utf-8") as jf:
                json.dump(character_data, jf, ensure_ascii=False, indent=2)
                
            # MD visualization profile
            with open(os.path.join(characters_dir, f"{char_name_safe}.md"), "w", encoding="utf-8") as mf:
                mf.write(f"# 角色档案: {char_name}\n\n")
                mf.write(f"- **状态**: {char.get('status', 'appeared')}\n")
                mf.write(f"- **数据来源**: {char.get('source', 'user')}\n")
                mf.write(f"- **首次登场章节**: {char.get('first_appearance_chapter') or '未知'}\n")
                mf.write(f"- **更新时间**: {char.get('updated_at', '')}\n\n")
                mf.write("## 角色背景与描述\n\n")
                mf.write(f"{char.get('description', '暂无描述。')}\n\n")
                
                if relationships:
                    mf.write("## 角色关系网\n\n")
                    for rel in relationships:
                        direction = "双方互为" if rel.get('direction') == 'bidirectional' else "单向"
                        mf.write(f"- 与人物 ID {rel['character_id_a'] if rel['character_id_b'] == char_id else rel['character_id_b']}: {direction} `{rel['rel_type']}` ({rel.get('description', '')}) [强度: {rel.get('strength', 0.5)}]\n")
                    mf.write("\n")
                if conflicts:
                    mf.write("## 冲突网\n\n")
                    for con in conflicts:
                        mf.write(f"- **{con['title']}**: {con.get('description', '')} [类型: {con.get('conflict_type', '')}, 状态: {con.get('status', '')}]\n")
                    mf.write("\n")
                if appearances:
                    mf.write("## 登场时间线\n\n")
                    for app in sorted(appearances, key=lambda x: x.get('chapter_number', 0)):
                        mf.write(f"- **第 {app['chapter_number']} 章**: {app.get('summary', '')} ({app.get('appearance_type', 'present')})\n")
                    mf.write("\n")
            migration_summary["characters_migrated"] += 1
            
        # B. character_state.json split
        char_state_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "memory", "character_state.json")
        if os.path.exists(char_state_path):
            try:
                # Copy raw character_state.json
                shutil.copy2(char_state_path, os.path.join(characters_dir, "character_state.json"))
                
                with open(char_state_path, "r", encoding="utf-8") as f:
                    char_state = json.load(f)
                memory_chars = char_state.get("characters", [])
                for mc in memory_chars:
                    mc_name = mc.get("name")
                    if mc_name:
                        mc_name_safe = safe_filename(mc_name)
                        # Save sub-JSON
                        with open(os.path.join(characters_dir, f"{mc_name_safe}.json"), "w", encoding="utf-8") as f:
                            json.dump(mc, f, ensure_ascii=False, indent=2)
                        # Save sub-MD
                        with open(os.path.join(characters_dir, f"{mc_name_safe}.md"), "w", encoding="utf-8") as f:
                            f.write(f"# 角色卡: {mc_name}\n\n")
                            f.write(f"- **立场/身份**: {mc.get('identity', mc.get('role', ''))}\n")
                            f.write(f"- **当前状态**: {mc.get('state', '')}\n\n")
                            f.write("## 描述与设定\n\n")
                            f.write(f"{mc.get('description', '')}\n\n")
                            if "secrets" in mc:
                                f.write("## 角色秘密\n\n")
                                f.write(f"{mc.get('secrets', '')}\n\n")
                        migration_summary["characters_migrated"] += 1
            except Exception as e:
                print(f"Failed to split characters from character_state.json: {e}")
                
        # 5. Migrate worldview files
        # Check files from disk
        worldview_filenames = {
            "Novel_architecture.txt": "architecture.md",
            "architecture_core_seed.txt": "core_seed.md",
            "architecture_character_dynamics.txt": "character_dynamics.md",
            "architecture_world_building.txt": "worldview.md",
            "architecture_plot.txt": "plot_architecture.md",
            "plot_arcs.txt": "plot_arcs.md",
            "character_state.txt": "character_state.md"
        }
        for old_file, new_file in worldview_filenames.items():
            content = ""
            disk_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, old_file)
            if os.path.exists(disk_path):
                try:
                    with open(disk_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except:
                    pass
            if not content:
                db_type_map = {
                    "Novel_architecture.txt": "architecture",
                    "architecture_core_seed.txt": "core_seed",
                    "architecture_character_dynamics.txt": "characters",
                    "architecture_world_building.txt": "worldview",
                    "architecture_plot.txt": "plot_arcs",
                    "plot_arcs.txt": "plot_arcs",
                    "character_state.txt": "character_state"
                }
                if old_file in db_type_map:
                    cursor.execute("SELECT content FROM project_file WHERE project_id = ? AND type = ? AND is_current = 1", (proj_id, db_type_map[old_file]))
                    pf_row = cursor.fetchone()
                    if pf_row:
                        content = pf_row[0]
            if content:
                with open(os.path.join(world_dir, new_file), "w", encoding="utf-8") as f:
                    f.write(content)
                migration_summary["worldview_files_migrated"] += 1
                
        # Write worldview memory files
        memory_world_files = {
            "outline_state.json": "world/outline_state.json",
            "plot_threads.json": "world/plot_threads.json",
            "name_usage_rules.json": "world/name_usage_rules.json"
        }
        for mem_file, new_dest in memory_world_files.items():
            mem_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "memory", mem_file)
            if os.path.exists(mem_path):
                try:
                    shutil.copy2(mem_path, os.path.join(proj_dir, new_dest))
                    migration_summary["worldview_files_migrated"] += 1
                except Exception as e:
                    print(f"Failed to copy worldview memory file {mem_file}: {e}")
                    
        # 6. Migrate Custom Prompts
        custom_prompt_path = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "custom_prompts.json")
        if os.path.exists(custom_prompt_path):
            try:
                with open(custom_prompt_path, "r", encoding="utf-8") as pf:
                    prompts_dict = json.load(pf)
                for key, val in prompts_dict.items():
                    key_safe = safe_filename(key, fallback="prompt")
                    with open(os.path.join(prompts_dir, f"{key_safe}.txt"), "w", encoding="utf-8") as f:
                        f.write(val)
                    migration_summary["prompts_migrated"] += 1
                shutil.copy2(custom_prompt_path, os.path.join(prompts_dir, "custom_prompts.json"))
            except Exception as e:
                print(f"Error copying custom prompts for project {proj_id}: {e}")
                
        # 7. Migrate history (generation tasks and logs)
        cursor.execute("SELECT * FROM generation_task WHERE project_id = ?", (proj_id,))
        task_rows = cursor.fetchall()
        tasks_list = [dict(t) for t in task_rows]
        with open(os.path.join(history_dir, "tasks.json"), "w", encoding="utf-8") as jf:
            json.dump(tasks_list, jf, ensure_ascii=False, indent=2)
        migration_summary["history_migrated"] += len(tasks_list)
            
        cursor.execute("SELECT * FROM model_invocation_log WHERE project_id = ?", (proj_id,))
        log_rows = cursor.fetchall()
        logs_list = [dict(l) for l in log_rows]
        with open(os.path.join(history_dir, "invocation_logs.json"), "w", encoding="utf-8") as jf:
            json.dump(logs_list, jf, ensure_ascii=False, indent=2)
        migration_summary["history_migrated"] += len(logs_list)
        
        # 8. Copy legacy memory folder contents recursively
        proj_mem_dir = os.path.join(BACKEND_PROJECTS_DIR, proj_id, "memory")
        if os.path.exists(proj_mem_dir):
            for root, dirs, files in os.walk(proj_mem_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_to_mem = os.path.relpath(file_path, proj_mem_dir)
                    
                    # Target path
                    dest_legacy = os.path.join(legacy_mem_dir, rel_to_mem)
                    os.makedirs(os.path.dirname(dest_legacy), exist_ok=True)
                    try:
                        shutil.copy2(file_path, dest_legacy)
                        migration_summary["legacy_files_copied"] += 1
                    except Exception as e:
                        print(f"Failed to copy legacy file {file_path} to {dest_legacy}: {e}")
                        
        # 9. Copy exports (if any exist)
        old_proj_root = os.path.join(BACKEND_PROJECTS_DIR, proj_id)
        if os.path.exists(old_proj_root):
            for file in os.listdir(old_proj_root):
                if file.endswith((".zip", ".html", ".txt")) and not file.startswith(("Novel_", "architecture_", "global_", "plot_", "character_")):
                    file_path = os.path.join(old_proj_root, file)
                    if os.path.isfile(file_path):
                        shutil.copy2(file_path, os.path.join(exports_dir, file))
                        
    # Build final migration-report.json
    final_report = {
        "migration_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "integrity": {
            "source_db_path": os.path.relpath(DB_PATH, WORKSPACE_ROOT),
            "source_db_sha256": source_sha,
            "backup_db_path": os.path.relpath(backup_db_path, WORKSPACE_ROOT),
            "backup_db_sha256": backup_sha,
            "backup_projects_zip_path": os.path.relpath(backup_zip_path, WORKSPACE_ROOT)
        },
        "statistics": {
            "projects_found": report_data["total_projects"],
            "projects_migrated": migration_summary["projects_migrated"],
            "chapters_found": report_data["total_chapters"],
            "chapters_migrated": migration_summary["chapters_migrated"],
            "characters_found": report_data["total_characters"],
            "characters_migrated": migration_summary["characters_migrated"],
            "worldview_files_migrated": migration_summary["worldview_files_migrated"],
            "custom_prompts_migrated": migration_summary["prompts_migrated"],
            "history_records_migrated": migration_summary["history_migrated"],
            "legacy_files_copied": migration_summary["legacy_files_copied"]
        },
        "sqlite_tables_summary": report_data["sqlite_tables_summary"],
        "discovered_files": report_data["discovered_files"],
        "migrated_files": report_data["migrated_files"],
        "copied_legacy_files": report_data["copied_legacy_files"],
        "skipped_files_with_reason": report_data["skipped_files_with_reason"],
        "unmapped_files": report_data["unmapped_files"],
        "chapter_source_detail": report_data["chapter_source_detail"],
        "projects_detail": report_data["projects"],
        "failed_parsed_fields": report_data["failed_parsed_fields"],
        "manual_check_items": report_data["manual_check_items"]
    }
    
    report_path = os.path.join(TARGET_WORKSPACE, "migration-report.json")
    with open(report_path, "w", encoding="utf-8") as rf:
        json.dump(final_report, rf, ensure_ascii=False, indent=2)
        
    return final_report

def main():
    parser = argparse.ArgumentParser(description="AI Novel Generator Data Migration Tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Scans existing data sources and writes statistics without changes")
    group.add_argument("--execute", action="store_true", help="Backs up and writes actual workspace files")
    
    args = parser.parse_args()
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Source database does not exist at {DB_PATH}")
        sys.exit(1)
        
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
    except Exception as e:
        print(f"Error connecting to source database: {e}")
        sys.exit(1)
        
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    if args.dry_run:
        print("Starting dry-run scanning mode...")
        scan_results = scan_data(conn)
        
        # Build dry-run report structure
        dry_run_report = {
            "scan_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "integrity": {
                "source_db_path": os.path.relpath(DB_PATH, WORKSPACE_ROOT),
                "source_db_sha256": calculate_sha256(DB_PATH)
            },
            "statistics": {
                "projects_found": scan_results["total_projects"],
                "chapters_found": scan_results["total_chapters"],
                "characters_found": scan_results["total_characters"],
                "worldview_files_found": scan_results["total_worldviews"],
                "custom_prompts_found": scan_results["total_prompts"],
                "history_records_found": scan_results["total_history"]
            },
            "sqlite_tables_summary": scan_results["sqlite_tables_summary"],
            "discovered_files": scan_results["discovered_files"],
            "migrated_files": scan_results["migrated_files"],
            "copied_legacy_files": scan_results["copied_legacy_files"],
            "skipped_files_with_reason": scan_results["skipped_files_with_reason"],
            "unmapped_files": scan_results["unmapped_files"],
            "chapter_source_detail": scan_results["chapter_source_detail"],
            "projects_detail": scan_results["projects"],
            "failed_parsed_fields": scan_results["failed_parsed_fields"],
            "manual_check_items": scan_results["manual_check_items"]
        }
        
        report_path = os.path.join(WORKSPACE_ROOT, "migration-report.dry-run.json")
        with open(report_path, "w", encoding="utf-8") as rf:
            json.dump(dry_run_report, rf, ensure_ascii=False, indent=2)
            
        print("=" * 60)
        print("DRY-RUN SCAN COMPLETED SUCCESSFULLY!")
        print(f"Dry-run report saved to: {report_path}")
        print(f"  Projects found: {scan_results['total_projects']}")
        print(f"  Chapters found: {scan_results['total_chapters']}")
        print(f"  Characters found: {scan_results['total_characters']}")
        print(f"  Custom Prompts found: {scan_results['total_prompts']}")
        print(f"  Warning items to review: {len(scan_results['manual_check_items'])}")
        print("=" * 60)
        
    elif args.execute:
        print(f"Starting actual migration execution (Timestamp: {timestamp})...")
        print("Creating backup ZIP and copying database...")
        try:
            report = migrate_data(conn, timestamp)
            print("=" * 60)
            print("MIGRATION COMPLETED SUCCESSFULLY!")
            print(f"Formal migration report saved to: {os.path.join(TARGET_WORKSPACE, 'migration-report.json')}")
            print(f"  Database backup: backup-old-database-{timestamp}.sqlite")
            print(f"  Filesystem backup: backup-old-projects-{timestamp}.zip")
            print(f"  Migrated projects count: {report['statistics']['projects_migrated']}")
            print(f"  Migrated chapters count: {report['statistics']['chapters_migrated']}")
            print(f"  Migrated characters count: {report['statistics']['characters_migrated']}")
            print("=" * 60)
        except Exception as e:
            print(f"Fatal error during migration execution: {e}")
            import traceback
            traceback.print_exc()
            conn.close()
            sys.exit(1)
            
    conn.close()

if __name__ == "__main__":
    main()
