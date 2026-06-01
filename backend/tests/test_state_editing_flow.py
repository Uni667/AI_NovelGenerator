import os
import json
import pytest
from backend.app.services.state_edit_service import (
    update_character_state, StateEditError, get_backups, restore_backup
)
from backend.app.services.state_conflict_service import detect_state_conflicts
from backend.app.services.state_file_service import get_memory_dir
def _write_memory_file(project_id: str, filename: str, data: any):
    memory_dir = get_memory_dir(project_id)
    os.makedirs(memory_dir, exist_ok=True)
    with open(os.path.join(memory_dir, filename), "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False)

def test_editing_security_and_rollback(test_project):
    pid = test_project["id"]
    uid = test_project["user_id"]
    
    _write_memory_file(pid, "character_state.json", {
        "characters": [{"id": "char_01", "true_name": "OldName", "current_status": "alive"}]
    })
    
    # 1. Missing reason
    with pytest.raises(StateEditError) as exc:
        update_character_state(pid, "char_01", {"current_status": "dead"}, "")
    assert exc.value.code == "reason_required"
    
    # 2. Unconfirmed high risk
    with pytest.raises(StateEditError) as exc:
        update_character_state(pid, "char_01", {"true_name": "NewName"}, "Testing high risk", confirm_high_risk=False)
    assert exc.value.code == "high_risk_required"
    
    # 3. Successful high risk edit
    res = update_character_state(pid, "char_01", {"true_name": "NewName"}, "Testing high risk ok", confirm_high_risk=True)
    assert res["success"] is True
    
    # 4. Check backups
    backups = get_backups(pid)
    assert len(backups) > 0
    backup_id = backups[0]["backup_id"]
    
    # 5. Path traversal block
    with pytest.raises(StateEditError) as exc:
        restore_backup(pid, "../../../etc/passwd", "hack")
    assert exc.value.code == "invalid_path"
    
    # 6. Restore backup
    res_restore = restore_backup(pid, backup_id, "rollback test")
    assert res_restore["success"] is True
    
    print("PASSED: test_editing_security_and_rollback")

def test_conflict_detection_logic(test_project):
    pid = test_project["id"]
    
    _write_memory_file(pid, "character_state.json", {
        "characters": [
            {
                "id": "char_14",
                "display_name": "十四叔",
                "true_name": "林惊羽",
                "true_name_revealed_to_reader": False
            }
        ]
    })
    _write_memory_file(pid, "name_usage_rules.json", {
        "rules": [
            {
                "character_id": "char_14",
                "current_default_narration_name": "林惊羽"
            }
        ]
    })
    _write_memory_file(pid, "outline_state.json", {"chapters": []})
    _write_memory_file(pid, "plot_threads.json", {"threads": []})
    
    res = detect_state_conflicts(pid, enable_ai_conflict_check=False)
    conflicts = res.get("conflicts", [])
    
    assert any(c["type"] == "name_usage_conflict" for c in conflicts)
    print("PASSED: test_conflict_detection_logic")
