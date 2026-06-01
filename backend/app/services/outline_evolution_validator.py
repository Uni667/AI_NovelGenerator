import json
import logging

logger = logging.getLogger(__name__)

def validate_outline_evolution_diff(diff_json: dict, outline_state: dict, character_state: dict = None, name_usage_rules: dict = None) -> tuple[bool, list[str], str]:
    """
    校验模型返回的大纲演化 diff 是否安全、合规。
    返回: (is_valid, error_messages, risk_level)
    """
    errors = []
    risk_level = "low"
    
    if not isinstance(diff_json, dict):
        return False, ["返回的不是合法的 JSON 对象"], "high"
        
    changes = diff_json.get("changes", [])
    if not isinstance(changes, list):
        return False, ["changes 必须是一个数组"], "high"
        
    affected_chapters = diff_json.get("affected_chapters", [])
    
    # 构建当前 outline 的映射，方便查询
    outline_map = {ch["chapter_index"]: ch for ch in outline_state.get("chapters", [])}
    
    for change in changes:
        cn = change.get("chapter_index")
        if cn is None:
            errors.append("某个 change 缺少 chapter_index")
            continue
            
        change_type = change.get("change_type", "modify")
        ch = outline_map.get(cn)
        
        # 1. 拦截对已定稿/已锁定章节的修改
        if ch:
            if ch.get("locked"):
                errors.append(f"第 {cn} 章已锁定 (locked=true)，禁止大纲演化修改。")
            if ch.get("status") == "finalized":
                errors.append(f"第 {cn} 章已定稿 (finalized)，禁止大纲演化修改。")
            if ch.get("status") == "drafted" and change_type != "mark_conflict":
                errors.append(f"第 {cn} 章已有草稿 (drafted)，请勿直接修改大纲内容，只能 mark_conflict。")
                
        # 2. 判断高危改动
        risk = change.get("risk_level", "low").lower()
        if risk == "high":
            risk_level = "high"
        if risk == "medium" and risk_level == "low":
            risk_level = "medium"
            
        field = change.get("field")
        # 如果涉及敏感词修改，如“秘密”、“真名”、“身世”、“身份”、“死亡”等，自动提升为 high risk
        after_text = str(change.get("after", ""))
        high_risk_keywords = ["真名", "身份", "身世", "死亡", "揭露", "秘密", "阵营", "卧底"]
        if any(kw in after_text for kw in high_risk_keywords):
            risk_level = "high"
            
        # 检查是否试图修改禁止字段
        forbidden_fields = ["chapter_index", "actual_summary", "locked", "status"]
        if change_type == "modify" and field in forbidden_fields:
            errors.append(f"禁止修改核心控制字段: {field}")
            
        # 如果是 delete_planned，需判断是否真的可以删
        if change_type == "delete_planned":
            risk_level = "high"
            if ch and (ch.get("status") != "planned" or ch.get("locked")):
                errors.append(f"第 {cn} 章不是 planned 或已锁定，禁止删除。")
                
        # 如果是 insert_after
        if change_type == "insert_after":
            risk_level = "high"
            
    # 如果涉及到较多章节修改，提升风险等级
    if len(affected_chapters) >= 3:
        risk_level = "high"
        
    is_valid = len(errors) == 0
    return is_valid, errors, risk_level
