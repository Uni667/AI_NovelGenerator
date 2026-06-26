import os
import json
import logging
from datetime import datetime
from backend.app.services import project_service, state_file_service, chapter_service, state_conflict_service

logger = logging.getLogger(__name__)

def export_story_bible_markdown(project_id: str, user_id: str) -> str:
    """
    导出设定包为 Markdown 格式。
    注意：不包含未合并的 patch，严格按照已合并的 memory 事实。
    """
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise ValueError("项目不存在")
        
    pconfig = project_service.get_project_config(project_id)
    filepath = project["filepath"]
    
    # 获取各个设定文件
    architecture_path = os.path.join(filepath, "Novel_architecture.txt")
    architecture = ""
    if os.path.exists(architecture_path):
        with open(architecture_path, "r", encoding="utf-8") as f:
            architecture = f.read().strip()
            
    global_summary = state_file_service.read_global_summary(project_id)
    character_state = state_file_service.read_character_state(project_id)
    plot_threads = state_file_service.read_plot_threads(project_id)
    name_rules = state_file_service.read_name_usage_rules(project_id)
    outline_state = state_file_service.read_outline_state(project_id)
    
    # 待处理 patch 和 outline diff
    memory_dir = os.path.join(filepath, "memory")
    patches_dir = os.path.join(memory_dir, "patches")
    diffs_dir = os.path.join(memory_dir, "outline_diffs")
    
    pending_patches = []
    if os.path.exists(patches_dir):
        for fname in os.listdir(patches_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(patches_dir, fname), "r", encoding="utf-8") as f:
                        p = json.load(f)
                        if p.get("status") == "pending_review":
                            pending_patches.append(p)
                except Exception:
                    logger.warning("Failed to load patch file %s during export", fname, exc_info=True)

    pending_diffs = []
    if os.path.exists(diffs_dir):
        for fname in os.listdir(diffs_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(diffs_dir, fname), "r", encoding="utf-8") as f:
                        d = json.load(f)
                        if d.get("status") == "pending_review":
                            pending_diffs.append(d)
                except Exception:
                    logger.warning("Failed to load outline diff file %s during export", fname, exc_info=True)
                    
    conflicts_res = state_conflict_service.detect_state_conflicts(project_id, enable_ai_conflict_check=False, user_id=user_id)
    conflicts = conflicts_res.get("conflicts", [])
    
    all_chapters = chapter_service.list_chapters(project_id, user_id)
    finalized_chapters = [ch for ch in all_chapters if ch.get("status") in ("final", "finalized")]
    finalized_chapters.sort(key=lambda x: x["chapter_number"])
    
    # 组装 markdown
    lines = []
    lines.append(f"# {pconfig.get('topic', '小说')} 设定包 (Story Bible)")
    lines.append(f"> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append("> 本文件包含的设定基于已合并的正式状态（Merged State）。")
    lines.append("> 未决定的建议（Pending Patches）和未来规划不会作为已发生事实混入正式设定。")
    lines.append("")
    
    lines.append("## 1. 项目基础信息")
    lines.append(f"- **类型**: {pconfig.get('genre', '未知')}")
    lines.append(f"- **目标字数**: {pconfig.get('word_number', '未知')}字")
    lines.append(f"- **总章数**: {pconfig.get('num_chapters', '未知')}章")
    if pconfig.get("user_guidance"):
        lines.append(f"- **作者指导**: {pconfig.get('user_guidance')}")
    lines.append("")
    
    lines.append("## 2. 小说架构")
    lines.append("```text")
    lines.append(architecture if architecture else "（无）")
    lines.append("```")
    lines.append("")
    
    lines.append("## 3. 全局摘要 (Global Summary)")
    lines.append("```text")
    lines.append(global_summary if global_summary else "（无）")
    lines.append("```")
    lines.append("")
    
    lines.append("## 4. 人物状态 (Characters)")
    if not character_state.get("characters"):
        lines.append("暂无人物设定。")
    else:
        for char in character_state["characters"]:
            lines.append(f"### {char.get('name', '未命名')}")
            lines.append(f"- **角色定位**: {char.get('role', '未知')}")
            if char.get("aliases"):
                lines.append(f"- **别名**: {', '.join(char.get('aliases'))}")
            lines.append(f"- **当前位置**: {char.get('current_location', '未知')}")
            lines.append(f"- **状态**: {char.get('status', '未知')}")
            if char.get("relationships"):
                lines.append("- **人物关系**:")
                for k, v in char.get("relationships").items():
                    lines.append(f"  - {k}: {v}")
            lines.append(f"- **关键动机/秘密**: {char.get('key_motivation_and_secrets', '无')}")
            lines.append("")
            
    lines.append("## 5. 称呼规则 (Name Usage Rules)")
    if not name_rules.get("rules"):
        lines.append("暂无特殊称呼规则。")
    else:
        for rule in name_rules["rules"]:
            lines.append(f"### {rule.get('target_character', '未知角色')}")
            lines.append(f"- **知情人范围**: {', '.join(rule.get('known_by', []))}")
            lines.append(f"- **旁白称呼**: {rule.get('narrator_usage', '未知')}")
            lines.append(f"- **公众称呼**: {rule.get('public_usage', '未知')}")
            lines.append(f"- **知情人称呼**: {rule.get('insider_usage', '未知')}")
            lines.append(f"- **当前是否属于隐藏身份期**: {'是' if rule.get('is_hidden_identity') else '否'}")
            lines.append("")
            
    lines.append("## 6. 伏笔与线索 (Plot Threads)")
    if not plot_threads.get("threads"):
        lines.append("暂无伏笔。")
    else:
        for pt in plot_threads["threads"]:
            lines.append(f"### {pt.get('title', '未命名伏笔')} [{pt.get('status', '未知')}]")
            lines.append(f"- **描述**: {pt.get('description', '无')}")
            if pt.get("related_characters"):
                lines.append(f"- **相关人物**: {', '.join(pt.get('related_characters'))}")
            if pt.get("resolution_clues"):
                lines.append("- **揭露线索**:")
                for c in pt.get("resolution_clues"):
                    lines.append(f"  - {c}")
            lines.append("")
            
    lines.append("## 7. 当前大纲状态 (Outline)")
    if not outline_state.get("chapters"):
        lines.append("暂无大纲。")
    else:
        for ch in outline_state["chapters"]:
            status_map = {"drafted": "规划中", "finalized": "已定稿锁定"}
            ch_status = status_map.get(ch.get("status"), ch.get("status", "未知"))
            lines.append(f"### 第 {ch.get('chapter_number')} 章: {ch.get('title', '未命名')} ({ch_status})")
            lines.append(f"- **核心目标**: {ch.get('chapter_goal', '无')}")
            lines.append(f"- **重点情节**: {ch.get('key_events', '无')}")
            lines.append("")
            
    lines.append("## 8. 已定稿章节列表")
    if not finalized_chapters:
        lines.append("暂无已定稿章节。")
    else:
        for ch in finalized_chapters:
            lines.append(f"- 第 {ch.get('chapter_number')} 章: {ch.get('chapter_title', '未命名')}")
    lines.append("")
    
    lines.append("## 9. 待确认建议 (Pending Reviews)")
    if not pending_patches and not pending_diffs and not conflicts:
        lines.append("当前系统状态健康，无待决事项。")
    else:
        if pending_patches:
            lines.append("### 待合并 State Patches (未作为正式设定)")
            for p in pending_patches:
                lines.append(f"- Patch `{p.get('id')}` [风险: {p.get('risk_level')}] (源于第 {p.get('source_chapter_number')} 章定稿)")
                
        if pending_diffs:
            lines.append("### 待确认 Outline Diffs (未生效的大纲调整)")
            for d in pending_diffs:
                lines.append(f"- Diff `{d.get('id')}` [风险: {d.get('risk_level')}]")
                
        if conflicts:
            lines.append("### 当前系统状态冲突")
            for c in conflicts:
                lines.append(f"- [冲突] {c.get('conflict_type')}: {c.get('description')} (涉及 {', '.join(c.get('related_files', []))})")
                
    return "\n".join(lines)
