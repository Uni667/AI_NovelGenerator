import os
import logging
from backend.app.services import project_service, chapter_service
from utils import read_file

logger = logging.getLogger(__name__)

def trim_context(text: str, max_chars: int) -> str:
    """截断文本，确保不超过最大字符数"""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[内容已截断]..."

def build_project_context_for_tools(project_id: str, user_id: str, max_chars: int = 12000) -> dict:
    """
    为书名、简介、标签、钩子诊断等平台工具构建轻量项目上下文。
    只读取必要信息，不修改任何数据。
    """
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise ValueError("项目不存在")
        
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise ValueError("项目配置不存在")
        
    filepath = project["filepath"]
    
    # 1. 读取架构
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    architecture = read_file(arch_file).strip() if os.path.exists(arch_file) else ""
    architecture = trim_context(architecture, 3000)
    
    # 2. 读取目录 (仅供参考未来大纲方向)
    dir_file = os.path.join(filepath, "Novel_directory.txt")
    directory = read_file(dir_file).strip() if os.path.exists(dir_file) else ""
    directory = trim_context(directory, 2000)
    
    # 3. 读取已定稿章节
    all_chapters = chapter_service.list_chapters(project_id, user_id)
    # 只取 final / finalized 状态的章节作为“已发生事实”
    finalized_chapters = [ch for ch in all_chapters if ch.get("status") in ("final", "finalized")]
    
    has_real_content = len(finalized_chapters) > 0
    
    chapter_digest = ""
    latest_finalized_chapters = []
    
    if has_real_content:
        # 按章节号排序
        finalized_chapters.sort(key=lambda x: x["chapter_number"])
        
        digest_lines = []
        digest_lines.append(f"当前已定稿章节数量：{len(finalized_chapters)} 章")
        digest_lines.append("\n【已发生剧情摘要与关键事件】")
        
        # 将所有定稿章节的 summary 加入（作为全局事实骨架）
        for ch in finalized_chapters:
            cn = ch["chapter_number"]
            title = ch.get("chapter_title", "未命名")
            summary = ch.get("chapter_summary", "")
            if summary:
                digest_lines.append(f"第{cn}章({title})：{summary}")
            
        digest_lines.append("\n【正文切片提取】")
        
        # 提取第1章开头片段 (约1500字)
        first_ch = finalized_chapters[0]
        first_content = chapter_service.get_chapter_content(project_id, first_ch["chapter_number"], filepath)
        if first_content:
            digest_lines.append("第1章开头：")
            digest_lines.append(trim_context(first_content, 1500))
            
        # 提取最近一章全文/截断 (约2500字) 以及结尾片段
        latest_ch = finalized_chapters[-1]
        latest_finalized_chapters.append(latest_ch["chapter_number"])
        if latest_ch["chapter_number"] != first_ch["chapter_number"]:
            latest_content = chapter_service.get_chapter_content(project_id, latest_ch["chapter_number"], filepath)
            if latest_content:
                digest_lines.append(f"\n最新定稿章（第{latest_ch['chapter_number']}章）重点情节：")
                digest_lines.append(trim_context(latest_content, 2500))
                # 最新一章结尾重点提取，用于判断当前钩子和剧情点
                if len(latest_content) > 1000:
                    digest_lines.append(f"\n最新定稿章结尾部分：\n{latest_content[-1000:]}")
                else:
                    digest_lines.append(f"\n最新定稿章结尾部分：\n{latest_content}")
                    
        chapter_digest = "\n".join(digest_lines)
        chapter_digest = trim_context(chapter_digest, max_chars - 4000) # 预留4000给架构和目录
    
    context = {
        "project_meta": pconfig,
        "architecture": architecture,
        "directory": directory,
        "finalized_chapter_count": len(finalized_chapters),
        "latest_finalized_chapters": latest_finalized_chapters,
        "chapter_digest": chapter_digest,
        "has_real_content": has_real_content
    }
    
    return context
