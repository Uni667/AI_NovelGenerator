import logging
import uuid
import json
from backend.app.services import state_file_service, project_service

logger = logging.getLogger(__name__)

def _get_llm_and_config(user_id: str, project_id: str):
    from backend.app.services.model_runtime import _build_chat_adapter
    from backend.app.services.config_resolver import get_runtime_config
    rt = get_runtime_config(user_id, "draft", project_id)
    adapter = _build_chat_adapter(rt, None, None)
    return adapter, rt

def detect_state_conflicts(project_id: str, enable_ai_conflict_check: bool = False, user_id: str = None) -> dict:
    """
    检测 memory 状态文件之间的逻辑冲突。默认使用规则检测，AI 检测仅为增强。
    """
    conflicts = []
    
    # 1. 提取所有已合并状态
    outline_state = state_file_service.read_outline_state(project_id)
    character_state = state_file_service.read_character_state(project_id)
    global_summary = state_file_service.read_global_summary(project_id)
    plot_threads = state_file_service.read_plot_threads(project_id)
    name_usage_rules = state_file_service.read_name_usage_rules(project_id)
    
    # 构建快速索引
    char_map = {ch.get("id"): ch for ch in character_state.get("characters", [])}
    rule_map = {r.get("character_id"): r for r in name_usage_rules.get("rules", [])}
    
    # 2. 强规则检测
    
    # 规则 1 & 2: 真实姓名未揭露，但称呼规则允许使用真名
    for ch in character_state.get("characters", []):
        cid = ch.get("id")
        t_name = ch.get("true_name")
        revealed_public = ch.get("true_name_revealed_to_reader")
        revealed_chars = ch.get("true_name_revealed_to_characters", [])
        
        rule = rule_map.get(cid)
        if not rule or not t_name:
            continue
            
        # 如果未对读者揭露，旁白一定不能用真名
        if not revealed_public:
            if t_name in str(rule.get("current_default_narration_name", "")):
                conflicts.append({
                    "conflict_id": f"conflict_{uuid.uuid4().hex[:6]}",
                    "type": "name_usage_conflict",
                    "risk_level": "high",
                    "title": f"[{cid}] 真名揭露与旁白称呼冲突",
                    "description": f"人物状态显示 {cid} 真名未向读者揭露，但称呼规则允许旁白使用真名 {t_name}。",
                    "related_files": ["character_state.json", "name_usage_rules.json"],
                    "related_entities": [cid],
                    "suggested_actions": [
                        {"action": "update_name_usage_rule", "label": "禁止旁白使用本名"},
                        {"action": "update_character_state", "label": "确认本名已向读者揭露(高风险)"}
                    ]
                })
                
        # 如果真名未向任何角色揭露，公众/私下对话不能用真名
        if not revealed_chars and not revealed_public:
            pub_dial = str(rule.get("public_dialogue", ""))
            pri_dial = str(rule.get("private_dialogue", ""))
            if t_name in pub_dial or t_name in pri_dial:
                conflicts.append({
                    "conflict_id": f"conflict_{uuid.uuid4().hex[:6]}",
                    "type": "name_usage_conflict",
                    "risk_level": "high",
                    "title": f"[{cid}] 真名揭露与对话称呼冲突",
                    "description": f"{cid} 真名未向任何角色揭露，但规则允许对话中使用真名 {t_name}。",
                    "related_files": ["character_state.json", "name_usage_rules.json"],
                    "related_entities": [cid],
                    "suggested_actions": [
                        {"action": "update_name_usage_rule", "label": "修改对话称呼规则"}
                    ]
                })
                
    # 规则 3: 角色已死亡，但未来章节正常行动
    for ch in character_state.get("characters", []):
        if ch.get("life_status") == "dead" or "死亡" in str(ch.get("current_status", "")):
            cname = ch.get("display_name") or ch.get("id")
            for out_ch in outline_state.get("chapters", []):
                if out_ch.get("status") == "planned":
                    summary = str(out_ch.get("planned_summary", ""))
                    if cname in summary and ("行动" in summary or "对话" in summary):
                        conflicts.append({
                            "conflict_id": f"conflict_{uuid.uuid4().hex[:6]}",
                            "type": "logic_conflict",
                            "risk_level": "medium",
                            "title": f"[{cname}] 角色死亡与大纲冲突",
                            "description": f"角色 {cname} 状态为死亡，但未来第 {out_ch.get('chapter_index')} 章计划大纲中仍在行动。",
                            "related_files": ["character_state.json", "outline_state.json"],
                            "related_entities": [ch.get("id"), str(out_ch.get("chapter_index"))],
                            "suggested_actions": [
                                {"action": "update_character_state", "label": "修改角色状态为存活/假死"},
                                {"action": "update_outline_chapter", "label": f"修改第{out_ch.get('chapter_index')}章大纲"}
                            ]
                        })
                        
    # 规则 4: 伏笔/秘密 active，但全局摘要写已揭露
    for th in plot_threads.get("threads", []):
        if th.get("status") == "active":
            t_title = str(th.get("title", ""))
            if t_title in global_summary and "已揭露" in global_summary:
                conflicts.append({
                    "conflict_id": f"conflict_{uuid.uuid4().hex[:6]}",
                    "type": "logic_conflict",
                    "risk_level": "medium",
                    "title": f"伏笔状态冲突: {t_title}",
                    "description": f"伏笔仍处于 active，但全局摘要中似乎已被揭露。",
                    "related_files": ["plot_threads.json", "global_summary.md"],
                    "related_entities": [th.get("id")],
                    "suggested_actions": [
                        {"action": "update_plot_thread", "label": "将伏笔置为 resolved"},
                        {"action": "update_global_summary", "label": "修改全局摘要"}
                    ]
                })

    # 规则 5: name_usage_rules 的 id 不存在
    for rule in rule_map.values():
        cid = rule.get("character_id")
        if cid and cid not in char_map:
            conflicts.append({
                "conflict_id": f"conflict_{uuid.uuid4().hex[:6]}",
                "type": "reference_conflict",
                "risk_level": "low",
                "title": f"幽灵称呼规则: {cid}",
                "description": f"称呼规则中包含人物 {cid}，但 character_state 中不存在该人物。",
                "related_files": ["character_state.json", "name_usage_rules.json"],
                "related_entities": [cid],
                "suggested_actions": []
            })
            
    # 规则 6: 十四叔揭名后的大纲冲突特定检测（十四叔真名已揭露，但大纲写首次揭露）
    for ch in character_state.get("characters", []):
        if ch.get("true_name_revealed_to_reader") and ch.get("true_name"):
            t_name = ch.get("true_name")
            for out_ch in outline_state.get("chapters", []):
                if out_ch.get("status") == "planned":
                    summary = str(out_ch.get("planned_summary", ""))
                    if ("首次揭露" in summary or "真实身份曝光" in summary) and (t_name in summary or str(ch.get("id")) in summary):
                        conflicts.append({
                            "conflict_id": f"conflict_{uuid.uuid4().hex[:6]}",
                            "type": "outline_conflict",
                            "risk_level": "high",
                            "title": f"[{ch.get('id')}] 真名揭露大纲冲突",
                            "description": f"人物真名已揭露，但未来第 {out_ch.get('chapter_index')} 章大纲仍计划首次揭露。",
                            "related_files": ["character_state.json", "outline_state.json"],
                            "related_entities": [ch.get("id")],
                            "suggested_actions": [
                                {"action": "update_outline_chapter", "label": "修改大纲删除揭名情节"}
                            ]
                        })

    # 3. LLM 辅助检测 (可选)
    if enable_ai_conflict_check and user_id:
        try:
            llm, _ = _get_llm_and_config(user_id, project_id)
            llm.model.temperature = 0.2
            prompt = f"""
请分析以下项目状态是否存在严重的逻辑矛盾或冲突。
[人物快照]
{json.dumps(character_state.get('characters', []), ensure_ascii=False)}

[伏笔状态]
{json.dumps(plot_threads.get('threads', []), ensure_ascii=False)}

[全局摘要]
{global_summary}

请只返回一个合法的 JSON 数组，包含所有发现的逻辑冲突（如果没有冲突，返回空数组 []）。不要输出任何 markdown 包装。
格式：
[{{ "title": "冲突标题", "description": "冲突详情", "risk_level": "high|medium|low" }}]
"""
            res_text = llm.invoke(prompt)
            clean_text = res_text.strip()
            if clean_text.startswith("```json"): clean_text = clean_text[7:]
            if clean_text.startswith("```"): clean_text = clean_text[3:]
            if clean_text.endswith("```"): clean_text = clean_text[:-3]
            ai_conflicts = json.loads(clean_text.strip())
            
            for ac in ai_conflicts:
                conflicts.append({
                    "conflict_id": f"ai_conflict_{uuid.uuid4().hex[:6]}",
                    "type": "ai_detected_conflict",
                    "risk_level": ac.get("risk_level", "medium"),
                    "title": f"[AI 发现] {ac.get('title')}",
                    "description": ac.get("description"),
                    "related_files": ["multiple"],
                    "related_entities": [],
                    "suggested_actions": []
                })
        except Exception as e:
            logger.error(f"AI Conflict check failed: {e}")
            conflicts.append({
                "conflict_id": f"ai_err_{uuid.uuid4().hex[:6]}",
                "type": "error",
                "risk_level": "low",
                "title": "AI 辅助检测失败",
                "description": str(e),
                "related_files": [],
                "related_entities": [],
                "suggested_actions": []
            })
            
    return {
        "rule_based": True,
        "ai_based": enable_ai_conflict_check,
        "conflicts": conflicts
    }
