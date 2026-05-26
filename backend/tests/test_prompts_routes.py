# -*- coding: utf-8 -*-
import pytest
import os
import json
import shutil
from unittest.mock import patch


class TestPromptsRoutes:
    """测试提示词实验室的 API 接口，包括白名单变量安全校验、历史快照与导入导出。"""

    def test_update_prompt_success(self, client, auth_headers, test_project):
        """用合法的格式化变量保存自定义提示词，应该成功并生成备份文件。"""
        # next_chapter_draft_prompt 模版仅允许特定占位符
        prompt_data = {
            "content": "这是一个新的后续章节初稿提示词。章节号：{novel_number}，字数要求：{word_number}，伏笔：{plot_arcs}。"
        }
        response = client.put(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt",
            json=prompt_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_overridden"] is True
        assert "备份" in data["message"]

        # 验证自定义配置已落盘到项目 custom_prompts.json
        custom_file = os.path.join(test_project["filepath"], "custom_prompts.json")
        assert os.path.exists(custom_file)
        with open(custom_file, "r", encoding="utf-8") as f:
            custom_data = json.load(f)
        assert "next_chapter_draft_prompt" in custom_data
        assert "{novel_number}" in custom_data["next_chapter_draft_prompt"]

    def test_update_prompt_invalid_variables(self, client, auth_headers, test_project):
        """传入非法的占位变量或错误的括号语法时，后端应拦截并返回 400。"""
        # {glbal_summary} 拼写错误，非白名单变量
        prompt_data = {
            "content": "剧情摘要：{glbal_summary}"
        }
        response = client.put(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt",
            json=prompt_data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "发现未知的占位变量" in response.json()["detail"]

        # 花括号未闭合语法错误
        prompt_data_error = {
            "content": "这是错误的括号: {novel_number"
        }
        response = client.put(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt",
            json=prompt_data_error,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "括号匹配或定义格式非法" in response.json()["detail"]

    def test_get_prompt_snapshots(self, client, auth_headers, test_project):
        """保存两次后，历史快照列表中应该能获取到历史版本。"""
        # 第一次保存
        client.put(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt",
            json={"content": "版本 A: {novel_number}"},
            headers=auth_headers
        )
        # 第二次保存（触发把版本 A 备份）
        client.put(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt",
            json={"content": "版本 B: {novel_number} {word_number}"},
            headers=auth_headers
        )

        response = client.get(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt/snapshots",
            headers=auth_headers
        )
        assert response.status_code == 200
        snapshots = response.json()["snapshots"]
        assert len(snapshots) >= 1
        assert "版本 A" in snapshots[0]["content"]

    def test_restore_prompt_snapshot(self, client, auth_headers, test_project):
        """验证快照恢复接口。"""
        # 保存并生成快照
        client.put(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt",
            json={"content": "历史版本: {novel_number}"},
            headers=auth_headers
        )
        client.put(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt",
            json={"content": "当前版本: {novel_number}"},
            headers=auth_headers
        )

        # 获取快照列表，找到历史版本的 ID
        res_snapshots = client.get(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt/snapshots",
            headers=auth_headers
        )
        snapshots = res_snapshots.json()["snapshots"]
        snapshot_id = snapshots[0]["id"] # 获取最新的备份快照 (其实是历史版本)

        # 触发恢复
        res_restore = client.post(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt/restore",
            json={"snapshot_id": snapshot_id},
            headers=auth_headers
        )
        assert res_restore.status_code == 200
        assert "历史版本: {novel_number}" in res_restore.json()["content"]

    def test_export_and_import_prompts(self, client, auth_headers, test_project):
        """测试整套自定义提示词配置的导入导出。"""
        # 先保存自定义提示词
        client.put(
            f"/api/v1/projects/{test_project['id']}/prompts/next_chapter_draft_prompt",
            json={"content": "导出测试: {novel_number}"},
            headers=auth_headers
        )

        # 1. 导出配置
        res_export = client.get(
            f"/api/v1/projects/{test_project['id']}/prompts/export",
            headers=auth_headers
        )
        assert res_export.status_code == 200
        export_data = res_export.json()
        assert "custom_prompts" in export_data
        assert "next_chapter_draft_prompt" in export_data["custom_prompts"]

        # 2. 导入配置
        import_data = {
            "custom_prompts": {
                "next_chapter_draft_prompt": "导入覆盖测试: {novel_number}",
                "first_chapter_draft_prompt": "第一章导入测试: {novel_number}"
            }
        }
        res_import = client.post(
            f"/api/v1/projects/{test_project['id']}/prompts/import",
            json=import_data,
            headers=auth_headers
        )
        assert res_import.status_code == 200
        assert "成功导入" in res_import.json()["message"]

        # 验证导入配置已生效
        custom_file = os.path.join(test_project["filepath"], "custom_prompts.json")
        with open(custom_file, "r", encoding="utf-8") as f:
            custom_data = json.load(f)
        assert custom_data["next_chapter_draft_prompt"] == "导入覆盖测试: {novel_number}"
        assert custom_data["first_chapter_draft_prompt"] == "第一章导入测试: {novel_number}"

        # 3. 导入非法配置报错
        bad_import_data = {
            "custom_prompts": {
                "next_chapter_draft_prompt": "非法变量导入: {glbal_summary}"
            }
        }
        res_bad_import = client.post(
            f"/api/v1/projects/{test_project['id']}/prompts/import",
            json=bad_import_data,
            headers=auth_headers
        )
        assert res_bad_import.status_code == 400
        assert "导入提示词包含格式校验错误" in res_bad_import.json()["detail"]
