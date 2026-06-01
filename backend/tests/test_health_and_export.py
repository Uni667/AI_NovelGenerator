import os
import json
import pytest
import hashlib
from backend.app.services.project_health_service import check_project_health
from backend.app.services.project_export_service import export_story_bible_markdown
from backend.app.services.state_patch_service import generate_state_patch_for_finalized_chapter
from backend.tests.mock_llm import patch_llm_for_tests
from backend.app.services.chapter_service import update_chapter_content

def get_dir_hash(directory: str) -> str:
    """计算目录下所有文件内容的简单hash，用于判断是否发生修改"""
    import hashlib
    h = hashlib.md5()
    if not os.path.exists(directory):
        return h.hexdigest()
        
    for root, dirs, files in os.walk(directory):
        for f in sorted(files):
            fpath = os.path.join(root, f)
            with open(fpath, "rb") as file:
                h.update(file.read())
    return h.hexdigest()

def test_health_check_readonly(test_project):
    pid = test_project["id"]
    uid = test_project["user_id"]
    filepath = test_project["filepath"]
    memory_dir = os.path.join(filepath, "memory")
    
    # Initialize memory files first so health check doesn't create them
    from backend.app.services.state_file_service import ensure_memory_files
    ensure_memory_files(pid)
    
    # 获取初始 hash
    initial_hash = get_dir_hash(memory_dir)
    
    # 调用 health check
    res = check_project_health(pid, uid)
    
    # 验证返回内容
    assert "status" in res
    assert res["status"] in ["healthy", "warning", "danger", "broken"]
    
    # 验证文件是否被修改 (Read Only)
    final_hash = get_dir_hash(memory_dir)
    assert initial_hash == final_hash

def test_story_bible_export_isolation(test_project):
    pid = test_project["id"]
    uid = test_project["user_id"]
    filepath = test_project["filepath"]
    
    with patch_llm_for_tests():
        # 1. 制造一个 pending patch
        content = "十四叔的本名叫做林震天。"
        update_chapter_content(pid, 1, filepath, content, status="draft")
        from backend.app.database import get_db
        with get_db() as conn:
            conn.execute("UPDATE chapter SET status='finalized' WHERE project_id=? AND chapter_number=1", (pid,))
            conn.commit()
            
        res = generate_state_patch_for_finalized_chapter(pid, 1)
        assert res["success"] is True
        
        # 2. 导出设定包
        md_content = export_story_bible_markdown(pid, uid)
        
        # 3. 验证 Pending 事项出现在待处理区，但不作为正式事实
        # 由于我们没有把这个 patch merge，所以 "林震天" 不应该出现在正式的 Global Summary 里
        assert "林震天" not in md_content.split("## 9. 待确认建议")[0]
        
        # 但是它应该在待确认建议区被提及 (比如提到了 Patch 的风险等级和存在)
        assert "待确认建议" in md_content
        assert "待合并 State Patches" in md_content
