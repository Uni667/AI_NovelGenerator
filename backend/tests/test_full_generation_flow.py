import os
import json
import pytest
from backend.tests.mock_llm import patch_llm_for_tests, MOCK_SCENARIO
import backend.tests.mock_llm as mock_module
from backend.app.services.generation_context_service import build_generation_context_for_chapter
from backend.app.services.state_patch_service import generate_state_patch_for_finalized_chapter
from backend.app.services.state_file_service import get_memory_dir

def _write_memory_file(project_id: str, filename: str, data: any):
    memory_dir = get_memory_dir(project_id)
    os.makedirs(memory_dir, exist_ok=True)
    with open(os.path.join(memory_dir, filename), "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False)

# Use test_project from conftest
def test_full_generation_flow(test_project):
    pid = test_project["id"]
    uid = test_project["user_id"]
    filepath = test_project["filepath"]
    
    # 1. Prepare minimal outline and chapter 1
    os.makedirs(filepath, exist_ok=True)
    os.makedirs(os.path.join(filepath, "chapters"), exist_ok=True)
    with open(os.path.join(filepath, "chapters", "chapter_1_draft.txt"), "w", encoding="utf-8") as f:
        f.write("十四叔走在大街上，神色凝重。")
        
    with open(os.path.join(filepath, "Novel_directory.txt"), "w", encoding="utf-8") as f:
        f.write("1. 第一章\n2. 第二章\n")
        
    with patch_llm_for_tests():
        mock_module.MOCK_SCENARIO = "normal"
        
        # 2. Finalize chapter 1 & generate state patch
        # In real code, finalize_chapter renames it to chapter_1.txt
        os.rename(os.path.join(filepath, "chapters", "chapter_1_draft.txt"), 
                  os.path.join(filepath, "chapters", "chapter_1.txt"))
                  
        res = generate_state_patch_for_finalized_chapter(pid, 1)
        assert res["success"] is True
        assert res["patch_status"] == "pending_review"
        patch_id = res["patch_id"]
        
        # 3. Verify it is pending review, should NOT be in merged context yet
        ctx = build_generation_context_for_chapter(pid, 2)
        assert "十四叔本章现身" not in ctx.get("context", {}).get("global_summary", "")
        
        # 4. Merge the patch manually (simulating user clicking merge)
        memory_dir = get_memory_dir(pid)
        patch_path = os.path.join(memory_dir, "patches", f"{patch_id}.json")
        with open(patch_path, "r", encoding="utf-8") as pf:
            patch = json.load(pf)
            
        patch["status"] = "merged"
        with open(patch_path, "w", encoding="utf-8") as pf:
            json.dump(patch, pf, ensure_ascii=False)
            
        # Simulate merge logic updating global summary
        _write_memory_file(pid, "global_summary.md", patch["summary_update"])
        
        # 5. Verify context again
        ctx2 = build_generation_context_for_chapter(pid, 2)
        assert "十四叔本章现身" in ctx2.get("context", {}).get("global_summary", "")
        
        # 6. Title and summary generation linkage
        # (Assuming we have routes for them, we just check context includes merged data)
        # Because title/summary use get_generation_context implicitly.
        
        print("PASSED: test_full_generation_flow")

