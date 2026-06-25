import os
import json
import pytest
import shutil
from backend.tests.mock_llm import patch_llm_for_tests, MOCK_SCENARIO
import backend.tests.mock_llm as mock_module
from backend.app.services.generation_context_service import build_generation_context_for_chapter
from backend.app.services.state_patch_merger import merge_state_patch
from backend.app.services.outline_evolution_service import propose_outline_evolution
from backend.app.services.project_health_service import check_project_health
from backend.app.services.state_file_service import get_memory_dir, ensure_memory_files

def _write_memory_file(project_id: str, filename: str, data: any):
    memory_dir = get_memory_dir(project_id)
    os.makedirs(memory_dir, exist_ok=True)
    filepath = os.path.join(memory_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)

def test_pending_patch_isolation_in_generation_context(test_project):
    """
    1. 确保 pending_review 状态的补丁（State Patch）绝对不进入下一章的草稿生成上下文。
    """
    pid = test_project["id"]
    ensure_memory_files(pid)

    # 写入已合并的初始人物状态 (十四叔, 处于未揭露真名状态)
    _write_memory_file(pid, "character_state.json", {
        "version": 1,
        "characters": [
            {
                "id": "char_shisi",
                "display_name": "十四叔",
                "role_in_story": "守护者",
                "current_status": "活跃",
                "true_name": "林惊羽",
                "true_name_revealed_to_reader": False
            }
        ],
        "last_updated_chapter": 0
    })

    # 创建一个 pending_review 的补丁，里面泄露了真名
    memory_dir = get_memory_dir(pid)
    patches_dir = os.path.join(memory_dir, "patches")
    os.makedirs(patches_dir, exist_ok=True)

    patch_id = "chapter_001_state_patch_pending"
    patch_file = os.path.join(patches_dir, f"{patch_id}.json")
    pending_patch = {
        "patch_id": patch_id,
        "project_id": pid,
        "chapter_index": 1,
        "status": "pending_review",
        "character_updates": [
            {
                "id": "char_shisi",
                "true_name_revealed_to_reader": True,
                "current_status": "已揭露真名"
            }
        ]
    }
    with open(patch_file, "w", encoding="utf-8") as f:
        json.dump(pending_patch, f, ensure_ascii=False, indent=2)

    # 生成第 2 章上下文
    ctx = build_generation_context_for_chapter(pid, 2)
    
    # 验证 pending patch 计数被正确统计
    assert ctx["pending_patch_ignored_count"] == 1
    
    # 验证人物状态摘要依旧保持未合并状态（true_name_revealed_to_reader 仍为 False）
    char_brief = ctx["context"]["character_state_brief"]
    assert "真名绝对禁止在正文和旁白出现" in char_brief
    assert "已揭露真名" not in char_brief


def test_merge_pre_and_post_automatic_backup(test_project):
    """
    2. 合并 State Patch 时自动触发对所有核心 memory 文件的备份。
    """
    pid = test_project["id"]
    ensure_memory_files(pid)

    # 写入初始文件
    _write_memory_file(pid, "character_state.json", {"characters": [], "last_updated_chapter": 0})
    _write_memory_file(pid, "global_summary.md", "# 全局摘要\n")

    # 创建待合并补丁
    memory_dir = get_memory_dir(pid)
    patches_dir = os.path.join(memory_dir, "patches")
    os.makedirs(patches_dir, exist_ok=True)

    patch_id = "chapter_005_state_patch_to_merge"
    patch_file = os.path.join(patches_dir, f"{patch_id}.json")
    patch_data = {
        "patch_id": patch_id,
        "chapter_index": 5,
        "status": "pending_review",
        "summary_update": "打败了赵九指。",
        "new_characters": [],
        "character_updates": [],
        "new_plot_threads": [],
        "resolved_plot_threads": []
    }
    with open(patch_file, "w", encoding="utf-8") as f:
        json.dump(patch_data, f, ensure_ascii=False, indent=2)

    # 执行合并
    res = merge_state_patch(pid, patch_id)
    assert res["success"] is True

    # 校验 backups 目录中是否生成了备份文件
    backups_dir = os.path.join(memory_dir, "backups")
    assert os.path.exists(backups_dir)
    
    backup_files = os.listdir(backups_dir)
    assert any("character_state_before_chapter_005" in f for f in backup_files)
    assert any("global_summary_before_chapter_005" in f for f in backup_files)


def test_outline_evolution_only_affects_future_chapters(test_project):
    """
    3. 大纲增量演化（propose_outline_evolution）只影响 status=planned 的未锁定章节。
    """
    pid = test_project["id"]
    uid = test_project["user_id"]
    ensure_memory_files(pid)

    # 写入大纲文件，包含已定稿章节、草稿章节和计划中章节
    _write_memory_file(pid, "outline_state.json", {
        "version": 1,
        "chapters": [
            {"chapter_index": 1, "status": "finalized", "locked": True, "title": "C1", "chapter_goal": "林尘觉醒"},
            {"chapter_index": 2, "status": "drafted", "locked": False, "title": "C2", "chapter_goal": "遭遇强敌"},
            {"chapter_index": 3, "status": "planned", "locked": False, "title": "C3", "chapter_goal": "逃入森林"}
        ],
        "last_updated_chapter": 1
    })

    with patch_llm_for_tests():
        # 为验证大纲演化规则中的校验层（validate_outline_evolution_diff），我们手工测试校验函数：
        from backend.app.services.outline_evolution_validator import validate_outline_evolution_diff
        
        outline_state = {
            "version": 1,
            "chapters": [
                {"chapter_index": 1, "status": "finalized", "locked": True, "title": "C1", "chapter_goal": "林尘觉醒"},
                {"chapter_index": 2, "status": "drafted", "locked": False, "title": "C2", "chapter_goal": "遭遇强敌"},
                {"chapter_index": 3, "status": "planned", "locked": False, "title": "C3", "chapter_goal": "逃入森林"}
            ]
        }
        
        # 尝试修改锁定的 C1
        bad_diff_1 = {
            "changes": [
                {"chapter_index": 1, "change_type": "modify", "field": "chapter_goal", "after": "林尘没觉醒"}
            ]
        }
        is_valid, errors, risk = validate_outline_evolution_diff(bad_diff_1, outline_state, {}, {})
        assert not is_valid
        assert any("已锁定" in e or "已定稿" in e for e in errors)

        # 尝试修改草稿状态的 C2
        bad_diff_2 = {
            "changes": [
                {"chapter_index": 2, "change_type": "modify", "field": "chapter_goal", "after": "修改草稿目标"}
            ]
        }
        is_valid, errors, risk = validate_outline_evolution_diff(bad_diff_2, outline_state, {}, {})
        assert not is_valid
        assert any("已有草稿" in e for e in errors)


def test_corrupted_json_health_check_alarm(test_project):
    """
    4. 删除或损坏核心 JSON 文件时，健康检查能够报警并指示为 broken 状态。
    """
    pid = test_project["id"]
    uid = test_project["user_id"]
    filepath = test_project["filepath"]
    
    # 写入旧版 Novel_directory.txt 确保健康检查不因为缺少它而报错 (或者在 tests conftest.py 里已经有了，但这里我们确保它存在)
    os.makedirs(filepath, exist_ok=True)
    with open(os.path.join(filepath, "Novel_directory.txt"), "w", encoding="utf-8") as f:
        f.write("1. 第1章")

    ensure_memory_files(pid)

    # 1. 正常状态健康检查
    res = check_project_health(pid, uid)
    assert res["status"] in ("healthy", "warning") # 如果有 pending patch 是 warning

    # 2. 损坏 character_state.json
    memory_dir = get_memory_dir(pid)
    char_file = os.path.join(memory_dir, "character_state.json")
    
    with open(char_file, "w", encoding="utf-8") as f:
        f.write("invalid json content: {[[}")

    res_corrupt = check_project_health(pid, uid)
    assert res_corrupt["status"] == "broken"
    assert any("character_state.json 损坏或无法解析" in c["message"] for c in res_corrupt["checks"])
