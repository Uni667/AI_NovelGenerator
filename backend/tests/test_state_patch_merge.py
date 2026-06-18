import os
import json
import pytest
from backend.app.services.state_patch_merger import merge_state_patch
from backend.app.services.state_file_service import get_memory_dir

def _write_memory_file(project_id: str, filename: str, data: any):
    memory_dir = get_memory_dir(project_id)
    os.makedirs(memory_dir, exist_ok=True)
    with open(os.path.join(memory_dir, filename), "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False)

def test_merge_state_patch_with_string_threads(test_project):
    pid = test_project["id"]
    
    # 1. Initialize memory files
    _write_memory_file(pid, "character_state.json", {"characters": [], "last_updated_chapter": 0})
    _write_memory_file(pid, "global_summary.md", "# 全局摘要\n")
    _write_memory_file(pid, "plot_threads.json", {"threads": [], "last_updated_chapter": 0})
    _write_memory_file(pid, "name_usage_rules.json", {"rules": [], "last_updated_chapter": 0})
    _write_memory_file(pid, "outline_state.json", {"chapters": [], "last_updated_chapter": 0})
    
    # 2. Create patch directory and patch file
    memory_dir = get_memory_dir(pid)
    patches_dir = os.path.join(memory_dir, "patches")
    os.makedirs(patches_dir, exist_ok=True)
    
    patch_id = "chapter_012_state_patch_test"
    patch_file = os.path.join(patches_dir, f"{patch_id}.json")
    
    patch_data = {
        "patch_id": patch_id,
        "chapter_index": 12,
        "status": "pending_review",
        "summary_update": "林测与十四叔遭遇赵九指手下。",
        "new_characters": [],
        "character_updates": [],
        "relationship_updates": [],
        "revealed_secrets": [],
        "new_secrets": [],
        "new_plot_threads": ["赵九指持有假地图，真路线需以命守护"],
        "resolved_plot_threads": [],
        "name_usage_updates": []
    }
    
    with open(patch_file, "w", encoding="utf-8") as f:
        json.dump(patch_data, f, ensure_ascii=False, indent=2)
        
    # 3. Perform Merge
    res = merge_state_patch(pid, patch_id)
    assert res["success"] is True
    assert res["status"] == "merged"
    
    # 4. Verify plot_threads.json contents
    with open(os.path.join(memory_dir, "plot_threads.json"), "r", encoding="utf-8") as f:
        threads_data = json.load(f)
        
    threads = threads_data.get("threads", [])
    assert len(threads) == 1
    assert threads[0]["title"] == "赵九指持有假地图，真路线需以命守护"
    assert threads[0]["introduced_chapter"] == 12
    assert threads[0]["status"] == "active"
    assert threads[0]["id"].startswith("thread_")
    
    # 5. Verify patch file updated status and formatted thread
    with open(patch_file, "r", encoding="utf-8") as f:
        updated_patch = json.load(f)
    assert updated_patch["status"] == "merged"
    assert isinstance(updated_patch["new_plot_threads"][0], dict)
    assert updated_patch["new_plot_threads"][0]["title"] == "赵九指持有假地图，真路线需以命守护"
    assert updated_patch["new_plot_threads"][0]["id"] == threads[0]["id"]
    
    print("PASSED: test_merge_state_patch_with_string_threads")
