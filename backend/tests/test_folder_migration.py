# -*- coding: utf-8 -*-
import os
import json
import shutil
import tempfile
import pytest

class TestFolderMigration:
    """测试本地文件夹导入导出 API"""

    def test_import_nonexistent_folder(self, client, auth_headers):
        """导入不存在的路径应报错"""
        payload = {
            "folder_path": "/nonexistent/path/to/folder",
            "project_name": "测试导入项目"
        }
        response = client.post("/api/v1/projects/import-local-folder", json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert "不存在" in response.json()["detail"]

    def test_import_raw_text_folder(self, client, auth_headers):
        """导入纯文本章节文件夹"""
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. 准备测试文本文件
            ch1_content = "第一章正文，仙逆苍穹！"
            ch2_content = "第二章正文，遇袭！"
            arch_content = "核心卖点：升级流、无敌文"
            
            with open(os.path.join(temp_dir, "第1章_启程.txt"), "w", encoding="utf-8") as f:
                f.write(ch1_content)
            with open(os.path.join(temp_dir, "chapter_2_遇袭.txt"), "w", encoding="utf-8") as f:
                f.write(ch2_content)
            with open(os.path.join(temp_dir, "Novel_architecture.txt"), "w", encoding="utf-8") as f:
                f.write(arch_content)
                
            # 2. 发起导入请求
            payload = {
                "folder_path": temp_dir,
                "project_name": "单元测试导入原始文本",
                "platform": "tomato",
                "genre": "仙侠"
            }
            response = client.post("/api/v1/projects/import-local-folder", json=payload, headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert "projectId" in data
            assert data["name"] == "单元测试导入原始文本"
            assert data["imported_chapters"] == 2
            
            project_id = data["projectId"]
            
            # 3. 验证导入的数据
            # 验证项目详情
            proj_res = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
            assert proj_res.status_code == 200
            proj_data = proj_res.json()
            assert proj_data["name"] == "单元测试导入原始文本"
            assert proj_data["genre"] == "仙侠"
            assert proj_data["platform"] == "tomato"
            
            # 验证章节
            ch_res = client.get(f"/api/v1/projects/{project_id}/chapters", headers=auth_headers)
            assert ch_res.status_code == 200
            chapters = ch_res.json()
            assert len(chapters) == 2
            assert chapters[0]["chapter_number"] == 1
            assert chapters[0]["chapter_title"] == "启程"
            assert chapters[1]["chapter_number"] == 2
            assert chapters[1]["chapter_title"] == "遇袭"
            
            # 验证章节正文
            ch1_detail = client.get(f"/api/v1/projects/{project_id}/chapters/1", headers=auth_headers)
            assert ch1_detail.status_code == 200
            assert ch1_detail.json()["content"] == ch1_content
            
        finally:
            shutil.rmtree(temp_dir)

    def test_export_and_import_backup_folder(self, client, auth_headers, test_project):
        """测试先将现有项目导出为备份文件夹，然后再将该备份文件夹导入为新项目"""
        export_dir = tempfile.mkdtemp()
        try:
            # 1. 写入测试章节
            ch_num = 1
            ch_content = "测试章节正文"
            
            # 先向数据库写入章节记录，以便后续 PUT 请求成功更新
            from backend.app.database import get_db
            import datetime
            now_str = datetime.datetime.now().isoformat()
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO chapter (project_id, chapter_number, chapter_title, status, created_at, updated_at) VALUES (?, ?, ?, 'draft', ?, ?)",
                    (test_project['id'], ch_num, "测试第1章", now_str, now_str)
                )
                
            client.put(
                f"/api/v1/projects/{test_project['id']}/chapters/{ch_num}",
                json={"content": ch_content, "chapter_title": "测试第1章"},
                headers=auth_headers
            )
            
            # 2. 导出到本地文件夹
            export_payload = {"folder_path": export_dir}
            export_res = client.post(
                f"/api/v1/projects/{test_project['id']}/export-local-folder",
                json=export_payload,
                headers=auth_headers
            )
            assert export_res.status_code == 200
            assert os.path.exists(os.path.join(export_dir, "metadata.json"))
            assert os.path.exists(os.path.join(export_dir, "chapters", "chapter_1.txt"))
            
            # 3. 导入该备份文件夹作为新项目
            import_payload = {
                "folder_path": export_dir,
                "project_name": "从备份导入的项目"
            }
            import_res = client.post(
                "/api/v1/projects/import-local-folder",
                json=import_payload,
                headers=auth_headers
            )
            assert import_res.status_code == 200
            new_project_id = import_res.json()["projectId"]
            
            # 4. 验证新项目属性及章节是否被成功复原
            proj_res = client.get(f"/api/v1/projects/{new_project_id}", headers=auth_headers)
            assert proj_res.status_code == 200
            assert proj_res.json()["name"] == "从备份导入的项目"
            
            ch_res = client.get(f"/api/v1/projects/{new_project_id}/chapters", headers=auth_headers)
            assert ch_res.status_code == 200
            chapters = ch_res.json()
            assert len(chapters) == 1
            assert chapters[0]["chapter_number"] == 1
            assert chapters[0]["chapter_title"] == "测试第1章"
            
            ch_detail = client.get(f"/api/v1/projects/{new_project_id}/chapters/1", headers=auth_headers)
            assert ch_detail.json()["content"] == ch_content
            
        finally:
            shutil.rmtree(export_dir)
