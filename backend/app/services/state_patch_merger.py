import os
import json
import logging
from datetime import datetime
from backend.app.services import state_file_service

logger = logging.getLogger(__name__)

def merge_state_patch(project_id: str, patch_id: str) -> dict:
    """
    合并指定 State Patch 到状态文件。
    合并前备份旧状态文件。
    """
    memory_dir = state_file_service.get_memory_dir(project_id)
    patches_dir = os.path.join(memory_dir, "patches")
    patch_file = os.path.join(patches_dir, f"{patch_id}.json")
    
    if not os.path.exists(patch_file):
        raise ValueError(f"Patch {patch_id} not found")
        
    with open(patch_file, "r", encoding="utf-8") as f:
        patch_data = json.load(f)
        
    if patch_data.get("status") != "pending_review":
        raise ValueError(f"Patch status is {patch_data.get('status')}, cannot merge")
        
    chapter_index = patch_data.get("chapter_index", 0)
    
    # 1. Backup before merging
    state_file_service.backup_memory_files(project_id, patch_id, chapter_index)
    
    # 2. Read existing states
    char_state = state_file_service.read_character_state(project_id)
    global_sum = state_file_service.read_global_summary(project_id)
    plot_threads = state_file_service.read_plot_threads(project_id)
    name_rules = state_file_service.read_name_usage_rules(project_id)
    outline_state = state_file_service.read_outline_state(project_id)
    
    # 3. Merge Character State
    new_chars = patch_data.get("new_characters", [])
    for nc in new_chars:
        # Avoid duplicate IDs
        if not any(c.get("id") == nc.get("id") for c in char_state["characters"]):
            nc["first_appearance_chapter"] = chapter_index
            nc["latest_appearance_chapter"] = chapter_index
            char_state["characters"].append(nc)
            
    char_updates = patch_data.get("character_updates", [])
    for cu in char_updates:
        target_id = cu.get("id")
        for i, c in enumerate(char_state["characters"]):
            if c.get("id") == target_id:
                # Update specific fields
                if "true_name" in cu:
                    c["true_name"] = cu["true_name"]
                if "true_name_revealed_to_reader" in cu:
                    c["true_name_revealed_to_reader"] = cu["true_name_revealed_to_reader"]
                if "current_status" in cu:
                    c["current_status"] = cu["current_status"]
                c["latest_appearance_chapter"] = chapter_index
                break
                
    char_state["last_updated_chapter"] = chapter_index

    # 4. Merge Global Summary
    summary_update = patch_data.get("summary_update", "").strip()
    if summary_update:
        global_sum += f"\n\n### 第 {chapter_index} 章更新\n{summary_update}"
        
    revealed_secrets = patch_data.get("revealed_secrets", [])
    if revealed_secrets:
        global_sum += f"\n\n### 第 {chapter_index} 章揭露秘密\n" + "\n".join(f"- {s}" for s in revealed_secrets)
        
    # 5. Merge Plot Threads
    new_threads = patch_data.get("new_plot_threads", [])
    for nt in new_threads:
        if not any(t.get("id") == nt.get("id") for t in plot_threads["threads"]):
            nt["introduced_chapter"] = chapter_index
            nt["last_touched_chapter"] = chapter_index
            plot_threads["threads"].append(nt)
            
    resolved_threads = patch_data.get("resolved_plot_threads", [])
    for rt_id in resolved_threads:
        for t in plot_threads["threads"]:
            if t.get("id") == rt_id:
                t["status"] = "resolved"
                t["last_touched_chapter"] = chapter_index
                
    plot_threads["last_updated_chapter"] = chapter_index

    # 6. Merge Name Usage Rules
    name_updates = patch_data.get("name_usage_updates", [])
    for nu in name_updates:
        char_id = nu.get("character_id")
        # Find if rule exists
        rule_found = False
        for r in name_rules["rules"]:
            if r.get("character_id") == char_id:
                if "stages" not in r:
                    r["stages"] = []
                r["stages"].append({
                    "stage": f"post_chapter_{chapter_index}",
                    "new_rule": nu.get("new_rule")
                })
                rule_found = True
                break
        if not rule_found:
            name_rules["rules"].append({
                "character_id": char_id,
                "stages": [{
                    "stage": f"post_chapter_{chapter_index}",
                    "new_rule": nu.get("new_rule")
                }]
            })
            
    name_rules["last_updated_chapter"] = chapter_index

    # 7. Update Outline State
    # Only mark current chapter as finalized and locked
    chapter_found = False
    for ch in outline_state["chapters"]:
        if ch.get("chapter_index") == chapter_index:
            ch["status"] = "finalized"
            ch["locked"] = True
            ch["actual_summary"] = summary_update
            ch["can_regenerate"] = False
            ch["can_evolve"] = False
            chapter_found = True
            break
            
    if not chapter_found:
        outline_state["chapters"].append({
            "chapter_index": chapter_index,
            "status": "finalized",
            "locked": True,
            "actual_summary": summary_update,
            "can_regenerate": False,
            "can_evolve": False
        })
        
    outline_state["last_updated_chapter"] = chapter_index

    # 8. Write back files
    state_file_service.write_memory_file(project_id, "character_state.json", char_state)
    state_file_service.write_memory_file(project_id, "global_summary.md", global_sum, is_json=False)
    state_file_service.write_memory_file(project_id, "plot_threads.json", plot_threads)
    state_file_service.write_memory_file(project_id, "name_usage_rules.json", name_rules)
    state_file_service.write_memory_file(project_id, "outline_state.json", outline_state)
    
    # 9. Update Patch status
    patch_data["status"] = "merged"
    patch_data["merged_at"] = datetime.now().isoformat()
    with open(patch_file, "w", encoding="utf-8") as f:
        json.dump(patch_data, f, ensure_ascii=False, indent=2)
        
    return {"success": True, "status": "merged", "patch_id": patch_id}
