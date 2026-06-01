import os
import pytest
from backend.app.services.model_runtime import _build_chat_adapter
from backend.app.services.config_resolver import get_runtime_config
from backend.app.services.state_patch_service import generate_state_patch_for_finalized_chapter
from backend.app.services.chapter_service import update_chapter_content, get_chapter_content
import json

pytestmark = pytest.mark.real_llm

@pytest.fixture
def check_real_llm_enabled():
    if os.environ.get("RUN_REAL_LLM_TESTS", "").lower() != "true":
        pytest.skip("RUN_REAL_LLM_TESTS not set to true, skipping real LLM test")

def test_real_llm_smoke(check_real_llm_enabled, test_project):
    pid = test_project["id"]
    uid = test_project["user_id"]
    filepath = test_project["filepath"]
    
    # Check if API key is actually configured in the project config
    try:
        config = get_runtime_config(uid, "draft", pid)
        # Assuming if it successfully built config, there's some LLM config
    except Exception as e:
        pytest.skip(f"No valid LLM config found, skipping real LLM test: {e}")
    
    # 1. Provide a short finalized chapter text
    content = "第1章\n林动走在街上。突然一个黑衣人冲出来，交给他一个玉佩。\n'这是家族的秘密，千万收好。'黑衣人说完就咽气了。"
    update_chapter_content(pid, 1, filepath, content, status="draft")
    from backend.app.database import get_db
    with get_db() as conn:
        conn.execute("UPDATE chapter SET status='finalized' WHERE project_id=? AND chapter_number=1", (pid,))
        conn.commit()
    
    # 2. Call generate_state_patch_for_finalized_chapter (uses real LLM)
    res = generate_state_patch_for_finalized_chapter(pid, 1)
    
    assert res["success"] is True
    patch = res["patch"]
    
    # 3. Verify real LLM output format
    assert patch["source_chapter_number"] == 1
    assert patch["status"] == "pending_review"
    assert "玉佩" in json.dumps(patch, ensure_ascii=False)
