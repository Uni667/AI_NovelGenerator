import os
import json
import pytest
from backend.tests.mock_llm import patch_llm_for_tests, MOCK_SCENARIO
import backend.tests.mock_llm as mock_module
from backend.app.services.outline_evolution_service import propose_outline_evolution
from backend.app.services.state_file_service import get_memory_dir

def _write_memory_file(project_id: str, filename: str, data: any):
    memory_dir = get_memory_dir(project_id)
    os.makedirs(memory_dir, exist_ok=True)
    with open(os.path.join(memory_dir, filename), "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False)

def test_outline_evolution_conflict(test_project):
    pid = test_project["id"]
    uid = test_project["user_id"]
    
    # 1. Prepare memory state with name revealed
    memory_dir = get_memory_dir(pid)
    os.makedirs(memory_dir, exist_ok=True)
    
    _write_memory_file(pid, "character_state.json", {
        "characters": [
            {
                "id": "char_shisi",
                "true_name": "林惊羽",
                "true_name_revealed_to_reader": True
            }
        ]
    })
    
    _write_memory_file(pid, "outline_state.json", {
        "chapters": [
            {"chapter_index": 1, "status": "finalized", "title": "C1"},
            {"chapter_index": 5, "status": "finalized", "title": "C5"},
            {"chapter_index": 12, "status": "planned", "title": "C12", "chapter_goal": "首次揭露十四叔本名"}
        ]
    })
    
    # 2. Trigger evolution with mocked conflict
    with patch_llm_for_tests():
        mock_module.MOCK_SCENARIO = "outline_conflict"
        diff = propose_outline_evolution(pid, uid, from_chapter=6)
        
        # 3. Assertions
        assert diff["status"] == "pending_review"
        
        changes = diff["changes"]
        assert len(changes) > 0
        assert changes[0]["chapter_index"] == 12
        assert changes[0]["field"] == "chapter_goal"
        assert changes[0]["after"] == "利用旧名施压"
        
        print("PASSED: test_outline_evolution_conflict")

def test_legacy_project_compatibility(test_project):
    pid = test_project["id"]
    uid = test_project["user_id"]
    filepath = test_project["filepath"]
    
    # Create legacy project without memory dir
    memory_dir = get_memory_dir(pid)
    if os.path.exists(memory_dir):
        import shutil
        shutil.rmtree(memory_dir)
        
    os.makedirs(filepath, exist_ok=True)
    with open(os.path.join(filepath, "Novel_directory.txt"), "w", encoding="utf-8") as f:
        f.write("Chapter 1\nChapter 2\n")
        
    # Trigger outline evolution on legacy, should auto-init memory safely
    with patch_llm_for_tests():
        mock_module.MOCK_SCENARIO = "normal"
        diff = propose_outline_evolution(pid, uid, from_chapter=1)
        
        assert os.path.exists(memory_dir)
        assert os.path.exists(os.path.join(memory_dir, "outline_state.json"))
        assert diff["status"] == "pending_review"
        
        print("PASSED: test_legacy_project_compatibility")
