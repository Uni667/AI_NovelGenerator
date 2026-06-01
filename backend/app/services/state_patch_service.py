import os
import json
import logging
from datetime import datetime
from backend.app.services import state_file_service, project_service, chapter_service

from backend.app.services.state_patch_validator import validate_and_assess_risk

logger = logging.getLogger(__name__)

PATCH_GENERATION_PROMPT = """你是一个长篇小说状态管理 AI。你的任务是分析最新定稿的一章正文，提取其中的状态变化（人物、秘密、称呼、伏笔等），并生成状态更新补丁（State Patch）。

## 核心规则
1. **你不是在续写小说，而是在做状态提取。**
2. 只能根据本章【实际发生的正文】和【旧状态文件】提取变化。
3. **不能把猜测当事实。**
4. **不能把未来大纲计划当成已经发生的剧情。**
5. 对于不确定的信息，放入 continuity_warnings 或 open_questions 中。
6. “十四叔”这类角色：如果正文中没有揭露他的本名，你的 true_name 必须是 null，true_name_revealed_to_reader 必须是 false，不要去编造或推理。

## 提供的信息

### 1. 当前小说架构（供参考）
{architecture}

### 2. 相关目录摘要（供参考）
{directory}

### 3. 系统当前状态（旧状态）
- Character State: {character_state}
- Name Usage Rules: {name_usage_rules}
- Global Summary: {global_summary}

### 4. 【本章已定稿正文】（优先级最高，事实依据）
章节：第 {chapter_index} 章
{chapter_content}

## 输出要求
请输出一个合法的 JSON，结构如下：
{{
  "summary_update": "对本章剧情的简要总结（100字内），将附加到全局摘要中",
  "new_characters": [
    {{
      "id": "自动生成的唯一ID，如 char_xxx",
      "display_name": "人物展示名",
      "role_in_story": "角色定位",
      "current_status": "当前状态简述"
    }}
  ],
  "character_updates": [
    {{
      "id": "已存在的人物ID",
      "true_name": "如果本章揭露了真名，填在这里，否则忽略",
      "true_name_revealed_to_reader": true/false,
      "current_status": "更新后的状态"
    }}
  ],
  "relationship_updates": [],
  "name_usage_updates": [
    {{
      "character_id": "人物ID",
      "new_rule": "新的称呼规则描述，如：本章后旁白应改叫其真名"
    }}
  ],
  "revealed_secrets": ["本章揭露的秘密"],
  "new_secrets": ["本章新挖的坑"],
  "plot_progress": ["主线推进点"],
  "new_plot_threads": [],
  "resolved_plot_threads": [],
  "worldbuilding_updates": [],
  "continuity_warnings": ["发现正文与旧设定矛盾的地方"],
  "next_chapter_notes": ["下一章必须遵守的事实（如人物受重伤不能跑跳）"]
}}

只输出 JSON 字符串，不要包含任何 markdown 代码块（不要 ```json ）。"""

def _get_llm_and_config(user_id: str, project_id: str):
    from backend.app.services.model_runtime import _build_chat_adapter
    from backend.app.services.config_resolver import get_runtime_config
    rt = get_runtime_config(user_id, "draft", project_id)
    adapter = _build_chat_adapter(rt, None, None)
    return adapter, rt

def _trim_context(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[内容已截断]..."

def generate_state_patch_for_finalized_chapter(project_id: str, chapter_id: int) -> dict:
    """
    读取已定稿章节正文和当前状态文件，生成本章 State Patch。
    不直接合并，生成 pending_review 的 patch 文件。
    """
    from backend.app.database import get_db
    with get_db() as conn:
        project_row = conn.execute("SELECT user_id FROM project WHERE id=?", (project_id,)).fetchone()
        if not project_row:
            return {"success": False, "error_msg": "Project not found"}
        user_id = project_row["user_id"]
    
    state_file_service.ensure_memory_files(project_id)
    
    # 1. Read Chapter Content
    project = project_service.get_project(project_id, user_id)
    filepath = project["filepath"]
    content = chapter_service.get_chapter_content(project_id, chapter_id, filepath)
    if not content:
        return {"success": False, "error_msg": "Chapter content is empty or not found"}
        
    # Trim chapter content if outrageously long, though usually a chapter is 2-4k chars.
    content = _trim_context(content, 10000)
    
    # 2. Read existing state safely trimmed
    char_state = state_file_service.read_character_state(project_id)
    name_rules = state_file_service.read_name_usage_rules(project_id)
    global_sum = state_file_service.read_global_summary(project_id)
    
    char_state_str = _trim_context(json.dumps(char_state, ensure_ascii=False), 3000)
    name_rules_str = _trim_context(json.dumps(name_rules, ensure_ascii=False), 1000)
    global_sum_str = _trim_context(global_sum, 2000)
    
    # 3. Read Arch/Dir trimmed
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    dir_file = os.path.join(filepath, "Novel_directory.txt")
    
    arch_content = ""
    if os.path.exists(arch_file):
        with open(arch_file, "r", encoding="utf-8") as f:
            arch_content = _trim_context(f.read().strip(), 1000)
            
    dir_content = ""
    if os.path.exists(dir_file):
        with open(dir_file, "r", encoding="utf-8") as f:
            dir_content = _trim_context(f.read().strip(), 1000)
            
    # 4. Run LLM
    try:
        llm, _ = _get_llm_and_config(user_id, project_id)
    except Exception as e:
        logger.error(f"Failed to get LLM config: {e}")
        return {"success": False, "error_msg": f"LLM Config Error: {str(e)}"}

    prompt = PATCH_GENERATION_PROMPT.format(
        architecture=arch_content,
        directory=dir_content,
        character_state=char_state_str,
        name_usage_rules=name_rules_str,
        global_summary=global_sum_str,
        chapter_index=chapter_id,
        chapter_content=content
    )
    
    try:
        result_text = llm.invoke(prompt)
        # Parse JSON
        result_text = result_text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
            
        patch_data = json.loads(result_text)
    except Exception as e:
        logger.error(f"Failed to parse LLM output as JSON: {e}")
        patch_data = {"status": "failed", "error_msg": "Invalid JSON from model"}
        
    # 5. Build full patch object
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Multi-version patch_id
    patch_id = f"chapter_{chapter_id:03d}_state_patch_{timestamp}"
    
    full_patch = {
        "patch_id": patch_id,
        "project_id": project_id,
        "chapter_id": chapter_id,
        "chapter_index": chapter_id,
        "source": "finalized_chapter",
        "created_at": datetime.now().isoformat(),
        "status": "pending_review",
        **patch_data
    }
    
    # 6. Validate and Assess Risk
    full_patch = validate_and_assess_risk(full_patch)
    
    # 7. Save Patch file
    memory_dir = state_file_service.get_memory_dir(project_id)
    patches_dir = os.path.join(memory_dir, "patches")
    os.makedirs(patches_dir, exist_ok=True)
    patch_file = os.path.join(patches_dir, f"{patch_id}.json")
    
    with open(patch_file, "w", encoding="utf-8") as f:
        json.dump(full_patch, f, ensure_ascii=False, indent=2)
        
    return {
        "success": True,
        "chapter_status": "final",
        "state_patch_generated": full_patch["status"] != "failed",
        "patch_id": patch_id,
        "patch_risk_level": full_patch.get("risk_level", "unknown"),
        "patch_status": full_patch["status"],
        "patch_error": full_patch.get("error_msg")
    }
