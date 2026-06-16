# -*- coding: utf-8 -*-
import os
import re
import uuid
import shutil
import json
import sqlite3
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.database import get_db, DB_DIR
from backend.app.auth import get_current_user
from backend.app.services import project_service, chapter_service, file_service
from chapter_directory_parser import parse_chapter_blueprint

logger = logging.getLogger(__name__)

router = APIRouter(tags=["本地文件夹导入导出"])

DEFAULT_PROJECTS_DIR = os.path.join(DB_DIR, "projects")

class ImportFolderRequest(BaseModel):
    folder_path: str
    project_name: str | None = None
    platform: str | None = "tomato"
    genre: str | None = "都市"

class ExportFolderRequest(BaseModel):
    folder_path: str


def _parse_chapter_info(filename: str) -> tuple[int | None, str]:
    """
    从文件名提取章节号和章节名称。
    支持格式:
      - 第1章_启程.txt -> 1, "启程"
      - chapter_2_突围.txt -> 2, "突围"
      - 003 冲突.txt -> 3, "冲突"
      - 第4章.txt -> 4, ""
    """
    name = os.path.splitext(filename)[0].strip()
    
    # Pattern 1: 第<num>章[_- \s]<title>
    m = re.match(r"^第\s*(\d+)\s*章(?:[_\-\s]+(.*?))?$", name)
    if m:
        num = int(m.group(1))
        title = (m.group(2) or "").strip()
        return num, title
        
    # Pattern 2: chapter[_-]<num>[_- \s]<title>
    m = re.match(r"^chapter[_\-\s]*(\d+)(?:[_\-\s]+(.*?))?$", name, re.IGNORECASE)
    if m:
        num = int(m.group(1))
        title = (m.group(2) or "").strip()
        return num, title
        
    # Pattern 3: <num>[_- \s]<title>
    m = re.match(r"^(\d+)(?:[_\-\s]+(.*?))?$", name)
    if m:
        num = int(m.group(1))
        title = (m.group(2) or "").strip()
        return num, title
        
    return None, ""


def _copy_dir_contents(src: str, dst: str, exclude_files: list[str] = None):
    """递归拷贝文件夹内容，不包括指定的文件"""
    if exclude_files is None:
        exclude_files = []
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            _copy_dir_contents(s, d, exclude_files)
        else:
            if item in exclude_files:
                continue
            shutil.copy2(s, d)


@router.post("/api/v1/projects/import-local-folder")
def import_local_folder(data: ImportFolderRequest, request: Request):
    """
    从本地电脑上的文件夹导入项目数据。
    支持导入结构化的备份（包含 metadata.json）和原始文本文件夹（包含 txt 章节文件）。
    """
    user_id = get_current_user(request)
    folder_path = data.folder_path.strip()
    
    if not folder_path or not os.path.exists(folder_path):
        raise HTTPException(status_code=400, detail=f"本地文件夹路径不存在: {folder_path}")
        
    if not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail="指定的路径不是一个有效的文件夹")
        
    metadata_file = os.path.join(folder_path, "metadata.json")
    new_project_id = str(uuid.uuid4())
    now_str = datetime.now().isoformat()
    target_filepath = os.path.join(DEFAULT_PROJECTS_DIR, new_project_id)
    
    try:
        # A. 结构化备份模式 (有 metadata.json)
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"解析 metadata.json 失败: {str(e)}")
                
            proj_meta = metadata.get("project", {})
            config_meta = metadata.get("config", {})
            chars_meta = metadata.get("characters", [])
            chapters_meta = metadata.get("chapters", [])
            
            project_name = data.project_name or proj_meta.get("name") or os.path.basename(os.path.normpath(folder_path))
            
            # 1. 复制物理文件到新项目路径
            _copy_dir_contents(folder_path, target_filepath, exclude_files=["metadata.json"])
            
            # 2. 插入数据库记录
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO project (id, user_id, name, description, status, filepath, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (new_project_id, user_id, project_name, proj_meta.get("description", ""), proj_meta.get("status", "draft"), target_filepath, now_str, now_str)
                )
                
                config_fields = [
                    "topic", "genre", "num_chapters", "word_number", "user_guidance",
                    "language", "platform", "category", "target_reader", "reader_direction",
                    "trend_key", "custom_trend", "trend_translation", "forbidden", "style_requirement"
                ]
                cfg_vals = [config_meta.get(f, "") for f in config_fields]
                conn.execute(
                    f"""INSERT INTO project_config (project_id, {', '.join(config_fields)})
                       VALUES (?, {', '.join('?' for _ in config_fields)})""",
                    [new_project_id] + cfg_vals
                )
                
                db_char_id_map = {}
                for char in chars_meta:
                    cursor = conn.execute(
                        """INSERT INTO character_profile (project_id, name, description, status, source, first_appearance_chapter, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (new_project_id, char["name"], char.get("description", ""), char.get("status", "appeared"), char.get("source", "user"), char.get("first_appearance_chapter"), now_str)
                    )
                    db_char_id_map[char["id"]] = cursor.lastrowid
                    
                for ch in chapters_meta:
                    conn.execute(
                        """INSERT INTO chapter (project_id, user_id, chapter_number, chapter_title, chapter_role, chapter_purpose, 
                                               suspense_level, foreshadowing, plot_twist_level, chapter_summary, status, word_count, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (new_project_id, user_id, ch["chapter_number"], ch.get("chapter_title", ""), ch.get("chapter_role", ""), ch.get("chapter_purpose", ""),
                         ch.get("suspense_level", ""), ch.get("foreshadowing", ""), ch.get("plot_twist_level", ""), ch.get("chapter_summary", ""),
                         ch.get("status", "draft"), ch.get("word_count", 0), now_str, now_str)
                    )
                conn.commit()
                
            # 3. 迁移和同步小说可视化文件
            try:
                from backend.app.routes.visualizer import _migrate_and_sync_visualizer_data
                _migrate_and_sync_visualizer_data(target_filepath, new_project_id)
            except Exception as vis_err:
                logger.warning(f"小说可视化数据同步失败: {vis_err}")
                
            return {
                "message": "本地备份项目导入成功",
                "projectId": new_project_id,
                "name": project_name
            }
            
        # B. 原始文本文件夹模式
        else:
            project_name = data.project_name or os.path.basename(os.path.normpath(folder_path))
            
            # 搜寻所有的 txt 章节文件 (在根目录或者在子目录 chapters 中)
            scan_dirs = [folder_path]
            chapters_subdir = os.path.join(folder_path, "chapters")
            if os.path.exists(chapters_subdir) and os.path.isdir(chapters_subdir):
                scan_dirs.append(chapters_subdir)
                
            chapters_files = []
            for s_dir in scan_dirs:
                for file in os.listdir(s_dir):
                    if file.endswith(".txt") and os.path.isfile(os.path.join(s_dir, file)):
                        # 规避一些结构化架构底稿文件
                        if file in ("Novel_architecture.txt", "Novel_directory.txt", "global_summary.txt", "character_state.txt", "plot_arcs.txt"):
                            continue
                        chapters_files.append((s_dir, file))
            
            parsed_chapters = []
            for s_dir, file in chapters_files:
                num, title = _parse_chapter_info(file)
                if num is not None and num >= 1:
                    filepath_full = os.path.join(s_dir, file)
                    try:
                        with open(filepath_full, "r", encoding="utf-8", errors="replace") as ch_f:
                            content = ch_f.read().strip()
                        parsed_chapters.append({
                            "chapter_number": num,
                            "chapter_title": title,
                            "content": content
                        })
                    except Exception as e:
                        logger.warning(f"无法读取文件 {filepath_full}: {e}")
                        
            # 如果没有找到章节，但用户还是想以此建立一个空项目
            if not parsed_chapters and len(os.listdir(folder_path)) == 0:
                logger.info("未在文件夹中识别到有效章节，将建立一个空白项目。")
            
            # 创建物理目录
            os.makedirs(target_filepath, exist_ok=True)
            os.makedirs(os.path.join(target_filepath, "chapters"), exist_ok=True)
            os.makedirs(os.path.join(target_filepath, "knowledge"), exist_ok=True)
            
            # 保存所有的章节内容到新项目的 chapters 文件夹下
            from utils import save_string_to_txt, get_word_count
            for ch in parsed_chapters:
                ch_path = os.path.join(target_filepath, "chapters", f"chapter_{ch['chapter_number']}.txt")
                save_string_to_txt(ch["content"], ch_path)
                ch["word_count"] = get_word_count(ch["content"])
                
            # 检查是否有原先的 Novel_architecture.txt
            arch_src = os.path.join(folder_path, "Novel_architecture.txt")
            if os.path.exists(arch_src):
                shutil.copy2(arch_src, os.path.join(target_filepath, "Novel_architecture.txt"))
                
            # 检查是否有 Novel_directory.txt / outline.txt
            directory_src = os.path.join(folder_path, "Novel_directory.txt")
            if not os.path.exists(directory_src):
                directory_src = os.path.join(folder_path, "outline.txt")
                
            if os.path.exists(directory_src):
                shutil.copy2(directory_src, os.path.join(target_filepath, "Novel_directory.txt"))
                
            # 3. 插入数据库
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO project (id, user_id, name, description, status, filepath, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (new_project_id, user_id, project_name, f"从本地路径 {folder_path} 导入的文本项目", "draft", target_filepath, now_str, now_str)
                )
                
                # 初始化 project_config
                conn.execute(
                    """INSERT INTO project_config (project_id, genre, platform, num_chapters, word_number)
                       VALUES (?, ?, ?, ?, ?)""",
                    (new_project_id, data.genre or "都市", data.platform or "tomato", max([c["chapter_number"] for c in parsed_chapters]) if parsed_chapters else 10, 3000)
                )
                
                # 插入章节记录
                for ch in parsed_chapters:
                    conn.execute(
                        """INSERT INTO chapter (project_id, user_id, chapter_number, chapter_title, status, word_count, created_at, updated_at)
                           VALUES (?, ?, ?, ?, 'draft', ?, ?, ?)""",
                        (new_project_id, user_id, ch["chapter_number"], ch["chapter_title"], ch["word_count"], now_str, now_str)
                    )
                conn.commit()

            # 在数据库连接释放后，安全写入 project_file
            for ch in parsed_chapters:
                try:
                    file_service.create_project_file(
                        project_id=new_project_id,
                        user_id=user_id,
                        type="chapter",
                        title=f"第{ch['chapter_number']}章",
                        filename=f"chapters/chapter_{ch['chapter_number']}.txt",
                        content=ch["content"],
                        source="user_imported",
                        is_current=True
                    )
                except Exception as e:
                    logger.warning(f"写入章节文件 {ch['chapter_number']} 到数据库记录失败: {e}")
                
            # 如果有 Novel_directory.txt，直接触发一次大纲的同步，从大纲更新章节的元信息 (如章节名、本章定位等)
            if os.path.exists(os.path.join(target_filepath, "Novel_directory.txt")):
                try:
                    chapter_service.sync_chapters_from_directory(new_project_id, target_filepath, user_id)
                except Exception as sync_e:
                    logger.warning(f"从 Novel_directory.txt 同步大纲失败: {sync_e}")
                    
            # 如果有 Novel_architecture.txt，添加 project_file 的记录
            if os.path.exists(arch_src):
                try:
                    with open(arch_src, "r", encoding="utf-8") as f:
                        arch_content = f.read()
                    file_service.create_project_file(
                        project_id=new_project_id,
                        user_id=user_id,
                        type="architecture",
                        title="小说架构",
                        filename="Novel_architecture.txt",
                        content=arch_content,
                        source="user_imported",
                        is_current=True
                    )
                except Exception as e:
                    logger.warning(f"写入 Novel_architecture.txt 到数据库记录失败: {e}")
                    
            return {
                "message": f"成功从文件夹导入 {len(parsed_chapters)} 章文本",
                "projectId": new_project_id,
                "name": project_name,
                "imported_chapters": len(parsed_chapters)
            }
            
    except HTTPException:
        raise
    except Exception as err:
        logger.exception("导入本地文件夹失败")
        raise HTTPException(status_code=500, detail=f"导入本地文件夹失败: {str(err)}")


@router.post("/api/v1/projects/{project_id}/export-local-folder")
def export_local_folder(project_id: str, data: ExportFolderRequest, request: Request):
    """
    导出项目全量数据和数据库元数据到电脑上的任意本地文件夹中。
    """
    user_id = get_current_user(request)
    folder_path = data.folder_path.strip()
    
    if not folder_path:
        raise HTTPException(status_code=400, detail="本地导出文件夹路径不能为空")
        
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
        
    src_filepath = project["filepath"]
    if not src_filepath or not os.path.exists(src_filepath):
        raise HTTPException(status_code=404, detail="项目文件存储路径不存在")
        
    # 先做一遍项目文件从数据库同步到磁盘，以防有漏掉的最新章节正文
    try:
        file_service.sync_project_files_to_disk(project_id, src_filepath, user_id)
    except Exception as e:
        logger.warning(f"同步项目文件至磁盘失败: {e}")
        
    try:
        os.makedirs(folder_path, exist_ok=True)
        
        # 1. 搜集数据库元数据
        config = project_service.get_project_config(project_id) or {}
        
        with get_db() as conn:
            db_chars = conn.execute("SELECT * FROM character_profile WHERE project_id = ?", (project_id,)).fetchall()
            db_chars_list = [dict(c) for c in db_chars]
            
            db_relationships = conn.execute("SELECT * FROM character_relationship WHERE project_id = ?", (project_id,)).fetchall()
            db_relationships_list = [dict(r) for r in db_relationships]
            
            db_conflicts = conn.execute("SELECT * FROM character_conflict WHERE project_id = ?", (project_id,)).fetchall()
            db_conflicts_list = [dict(c) for c in db_conflicts]
            
            db_appearances = conn.execute("SELECT * FROM character_appearance WHERE project_id = ?", (project_id,)).fetchall()
            db_appearances_list = [dict(a) for a in db_appearances]
            
            chapters = conn.execute("SELECT * FROM chapter WHERE project_id = ?", (project_id,)).fetchall()
            chapters_list = [dict(ch) for ch in chapters]
            
        metadata = {
            "project": {
                "name": project["name"],
                "description": project.get("description", ""),
                "status": project.get("status", "draft"),
            },
            "config": config,
            "characters": db_chars_list,
            "relationships": db_relationships_list,
            "conflicts": db_conflicts_list,
            "appearances": db_appearances_list,
            "chapters": chapters_list
        }
        
        # 2. 写入 metadata.json
        metadata_file = os.path.join(folder_path, "metadata.json")
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        # 3. 递归拷贝项目的所有物理内容
        _copy_dir_contents(src_filepath, folder_path, exclude_files=["metadata.json"])
        
        return {
            "success": True,
            "message": "项目已成功导出到本地路径",
            "path": folder_path
        }
        
    except Exception as err:
        logger.exception("导出项目到本地文件夹失败")
        raise HTTPException(status_code=500, detail=f"导出到本地失败: {str(err)}")
