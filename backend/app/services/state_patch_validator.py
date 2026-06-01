import json
import logging

logger = logging.getLogger(__name__)

def validate_and_assess_risk(patch_data: dict) -> dict:
    """
    Validate the state patch JSON structure and assess its risk level.
    Returns the validated and possibly modified patch data, or marks it as failed if invalid.
    """
    # 1. Type validation
    required_fields = ["project_id", "chapter_id", "chapter_index", "status"]
    for field in required_fields:
        if field not in patch_data:
            return _fail_patch(patch_data, f"Missing required field: {field}")
            
    # List fields validation
    list_fields = [
        "new_characters", "character_updates", "relationship_updates",
        "name_usage_updates", "revealed_secrets", "new_secrets",
        "plot_progress", "new_plot_threads", "resolved_plot_threads",
        "worldbuilding_updates", "outline_updates", "continuity_warnings",
        "next_chapter_notes"
    ]
    for field in list_fields:
        if field in patch_data and not isinstance(patch_data[field], list):
            return _fail_patch(patch_data, f"Field {field} must be a list")
        if field not in patch_data:
            patch_data[field] = []
            
    if "summary_update" in patch_data and not isinstance(patch_data["summary_update"], str):
        patch_data["summary_update"] = str(patch_data["summary_update"])
    elif "summary_update" not in patch_data:
        patch_data["summary_update"] = ""
        
    # 2. Assess Risk Level
    risk_level = "low"
    
    # Check for High Risk
    if patch_data.get("name_usage_updates"):
        risk_level = "high" # 改变称呼规则
    if patch_data.get("revealed_secrets"):
        risk_level = "high" # 揭露秘密（十四叔本名曝光等）
    
    # Check for character updates that are high risk (e.g. true name revealed, hidden identity)
    for char_update in patch_data.get("character_updates", []):
        if char_update.get("true_name_revealed_to_reader") is True:
            risk_level = "high"
        if char_update.get("hidden_identity") or char_update.get("true_name"):
            risk_level = "high"
        # 改变阵营或核心人物关系
        if char_update.get("role_in_story_changed") or char_update.get("alignment_changed"):
            risk_level = "high"
            
    if patch_data.get("outline_updates"):
        risk_level = "high" # 影响未来大纲
        
    if patch_data.get("continuity_warnings"):
        risk_level = "high" # 与已有状态冲突
        
    # Check for Medium Risk (if not already high)
    if risk_level != "high":
        if patch_data.get("new_characters"):
            risk_level = "medium"
        if patch_data.get("relationship_updates"):
            risk_level = "medium"
        if patch_data.get("new_plot_threads"):
            risk_level = "medium"
        if patch_data.get("resolved_plot_threads"):
            risk_level = "medium"
        if patch_data.get("character_updates"):
            risk_level = "medium" # Some character update
            
    patch_data["risk_level"] = risk_level
    patch_data["status"] = "pending_review"
    
    return patch_data

def _fail_patch(patch_data: dict, error_msg: str) -> dict:
    logger.error(f"Patch validation failed: {error_msg}")
    return {
        "status": "failed",
        "error_msg": error_msg,
        "raw_model_output": json.dumps(patch_data, ensure_ascii=False) if isinstance(patch_data, dict) else str(patch_data)
    }
