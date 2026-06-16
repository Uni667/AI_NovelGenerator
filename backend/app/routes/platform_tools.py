import os
import json
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from backend.app.services import project_service, chapter_service

from backend.app.auth import get_current_user
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)

router = APIRouter(tags=["番茄平台工具"])

# ── 番茄小说平台风格提示词 ──────────────────────────────────────────

TITLE_GENERATION_PROMPT = """你是一位深谙番茄免费小说平台规则的爆款书名专家。请根据以下小说设定，生成 10 个适配番茄平台的书名候选。

## 平台书名规则
- 禁用隐喻、文艺短名，必须直白冲突
- 用读者会搜的高频词：重生、穿越、系统、虐渣、闪婚、马甲、无敌、开局、金手指、反派、反派千金、暴富、算命、降维打击
- 书名像微短剧标题，3秒让读者看懂全书最大爽点
- 三大公式：
  1. 身份反转+冲突：「破产后，我成了首富继承人」
  2. 悬念+关键词：「直播算命：大哥你媳妇在坟里睁眼了」
  3. 情绪拉满+结果前置：「重生一世，我让渣男家破人亡」

## 小说设定
- 主题：{topic}
- 类型：{genre}
- 章节数：{num_chapters}章，每章{word_number}字
- 用户指导：{user_guidance}

## 输出格式
请生成 10 个书名，每行一个，按吸引力从高到低排序。每个书名后面用括号标注使用了什么公式。
只输出书名列表，不要其他内容。"""


BLURB_GENERATION_PROMPT = """你是一位番茄免费小说平台的爆款简介撰写专家。请根据以下小说设定，生成 3 个版本的小说简介。

## 平台简介规则
简介不是剧情摘要，而是「冲突压缩体 + 广告语」。
万能公式：核心冲突 + 金手指 + 爽点预告 + 悬念钩子
- 前两行就要把最爽的结果亮出来
- 三要素：主角是谁 / 面临什么冲突 / 失败代价是什么
- 用具体数字比形容词更有冲击力
- 150-250 字最佳

## 示例
"被丈夫挖肾救白月光，她含恨而死。重生后绑定千亿神豪系统！虐渣男、踹白月光，夺回属于自己的一切！可谁能告诉她，那个权势滔天的大佬，为什么总缠着她不放？"

## 小说设定
- 主题：{topic}
- 类型：{genre}
- 章节数：{num_chapters}章，每章{word_number}字
- 用户指导：{user_guidance}
- 小说架构摘要：{architecture_summary}

## 输出格式
生成3个版本，用「---」分隔。每个版本之间独立，不要编号。"""


HOOK_CHECK_PROMPT = """你是一位番茄免费小说平台的资深编辑，专门评估小说开篇钩子质量。请分析以下文本。

## 评估标准（番茄平台）
1. **前200字冲突检测**：是否在开头立刻抛出强冲突（死亡/背叛/侮辱/巨额损失/身份崩塌）？
2. **悬念设置**：是否让读者产生「然后呢？」的强烈好奇？
3. **情绪冲击**：前200字是否触发了愤怒/震惊/紧张/爽感？
4. **信息密度**：是否有大段景物描写、背景铺垫、人物介绍？（这些都是扣分项）
5. **黄金三秒法则**：如果这是番茄信息流中的一个卡片，读者3秒内会点进来吗？

## 分析的小说开头
{chapter_text}

## 输出格式
用 JSON 格式输出：
{{
  "score": 综合评分(1-10),
  "has_conflict_in_200": true/false,
  "conflict_type": "冲突类型",
  "hook_strength": "强/中/弱/无",
  "issues": ["问题1", "问题2"],
  "rewrite_suggestion": "改写建议（50字以内）",
  "rewritten_opening": "改写后的前200字示例"
}}
只输出 JSON，不要其他内容。"""


CHAPTER_HOOK_CHECK_PROMPT = """你是一位番茄免费小说平台的资深编辑。检查以下章节结尾是否留了悬念钩子。

## 钩子类型
1. **危机型**：主角面临危险/威胁，不点下一章不知道结果
2. **揭秘型**：抛出关键信息的线索/暗示，但不完整
3. **欲望型**：主角即将获得重要奖励/突破/升级
4. **反转型**：出现意料之外的事件/身份揭露

## 检查内容
{chapter_ending}

## 输出格式
用 JSON 格式：
{{
  "has_hook": true/false,
  "hook_type": "危机型/揭秘型/欲望型/反转型/无",
  "hook_description": "钩子描述（30字以内）",
  "suggestion": "如果没有钩子，给出添加建议（50字以内）；如果有，给优化建议"
}}
只输出 JSON。"""


TAGS_GENERATION_PROMPT = """你是一位番茄免费小说平台的运营专家。根据以下小说设定，生成适配番茄平台搜索优化的标签和关键词。

## 小说设定
- 主题：{topic}
- 类型：{genre}
- 用户指导：{user_guidance}
- 小说架构摘要：{architecture_summary}

## 输出格式
用 JSON 格式：
{{
  "main_tags": ["标签1", "标签2", "标签3", "标签4", "标签5"],
  "search_keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
  "category_recommendation": "推荐分类",
  "target_audience": "目标读者画像（30字）"
}}
标签从以下高频词中选择或组合：虐渣、闪婚、系统、穿越、重生、马甲、无敌、开局、金手指、反派、暴富、算命、降维打击、脑洞、无限流、大女主、无CP、年代、种田、高武、修仙、赘婿、逆袭、甜宠、追妻火葬场、权谋、宫斗、悬疑、恐怖、科幻、末世、电竞
只输出 JSON。"""


CHAPTER_TITLE_PROMPT = """你是一位番茄免费小说平台的编辑。请根据章节内容，生成 3 个番茄平台风格的情绪化章节标题。

## 规则
- 禁用「第一章」「第二章」这种编号式标题
- 用情绪化短句，让读者一眼就想点进去
- 可加入感叹号、问号增强情绪
- 15-25 字为宜
- 示例：「她签完离婚协议，总裁把婚戒塞进她手心」
- 「系统激活！废柴开局竟藏SSS级天赋？」

## 章节信息
- 章节号：第{chapter_number}章
- 章节标题（原）：{chapter_title}
- 章节摘要：{chapter_summary}
- 章节内容开头 500 字：
{chapter_preview}

## 输出格式
每行一个标题候选，共3行。不要编号，不要其他内容。"""


# ── Helper ──────────────────────────────────────────────────────────

def _get_llm_and_config(user_id: str, project_id: str, temperature: float | None = None):
    """Get LLM adapter and config through ModelRuntimeService."""
    from backend.app.services.model_runtime import _build_chat_adapter
    from backend.app.services.config_resolver import get_runtime_config, ConfigError

    try:
        rt = get_runtime_config(user_id, "draft", project_id)
    except ConfigError as e:
        logger.exception("Platform tool failed")
        raise HTTPException(status_code=500, detail="操作失败，请稍后重试")

    adapter = _build_chat_adapter(rt, temperature, None)
    return adapter, rt


def _read_architecture(filepath: str) -> str:
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    if os.path.exists(arch_file):
        with open(arch_file, "r", encoding="utf-8") as f:
            return f.read()[:3000]
    return ""


def _trim_response(text: str, max_chars: int = 3000) -> str:
    return text[:max_chars]


# ── 1. 书名生成 ─────────────────────────────────────────────────────

@router.post("/api/v1/projects/{project_id}/tools/titles")
def generate_titles(project_id: str, request: Request):
    user_id = get_current_user(request)
    llm, rt = _get_llm_and_config(user_id, project_id)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    prompt = TITLE_GENERATION_PROMPT.format(
        topic=pconfig.get("topic", ""),
        genre=pconfig.get("genre", ""),
        num_chapters=pconfig.get("num_chapters", 0),
        word_number=pconfig.get("word_number", 3000),
        user_guidance=pconfig.get("user_guidance", "")
    )

    try:
        result = llm.invoke(prompt)
        titles = [t.strip() for t in result.split("\n") if t.strip() and not t.strip().startswith("#")]
        return {"titles": titles[:10]}
    except Exception as e:
        logger.exception("Platform tool generation failed")
        raise HTTPException(status_code=500, detail="生成失败，请稍后重试")


# ── 2. 简介生成 ─────────────────────────────────────────────────────

@router.post("/api/v1/projects/{project_id}/tools/blurb")
def generate_blurb(project_id: str, request: Request):
    user_id = get_current_user(request)
    llm, rt = _get_llm_and_config(user_id, project_id)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")
    arch_summary = _read_architecture(project["filepath"])

    prompt = BLURB_GENERATION_PROMPT.format(
        topic=pconfig.get("topic", ""),
        genre=pconfig.get("genre", ""),
        num_chapters=pconfig.get("num_chapters", 0),
        word_number=pconfig.get("word_number", 3000),
        user_guidance=pconfig.get("user_guidance", ""),
        architecture_summary=arch_summary
    )

    try:
        result = llm.invoke(prompt)
        versions = [v.strip() for v in result.split("---") if v.strip()]
        return {"blurbs": versions[:3]}
    except Exception as e:
        logger.exception("Platform tool generation failed")
        raise HTTPException(status_code=500, detail="生成失败，请稍后重试")


# ── 3. 开篇钩子检测 ─────────────────────────────────────────────────

@router.post("/api/v1/projects/{project_id}/tools/hook-check")
def check_opening_hook(project_id: str, request: Request, chapter_number: int = 1):
    user_id = get_current_user(request)
    llm, rt = _get_llm_and_config(user_id, project_id)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    chapter_content = chapter_service.get_chapter_content(
        project_id, chapter_number, project["filepath"]
    )
    if not chapter_content:
        raise HTTPException(status_code=404, detail=f"第{chapter_number}章内容不存在")

    prompt = HOOK_CHECK_PROMPT.format(chapter_text=chapter_content[:2000])

    try:
        result = llm.invoke(prompt)
        # 尝试提取 JSON
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start != -1:
            analysis = json.loads(result[json_start:json_end])
        else:
            analysis = {"score": 0, "issues": ["无法解析结果"], "suggestion": result}
        return {"analysis": analysis}
    except Exception as e:
        logger.exception("Platform tool detection failed")
        raise HTTPException(status_code=500, detail="检测失败，请稍后重试")


# ── 4. 章节结尾钩子检测 ─────────────────────────────────────────────

@router.post("/api/v1/projects/{project_id}/tools/chapter-hook-check")
def check_chapter_ending_hook(project_id: str, chapter_number: int, request: Request):
    user_id = get_current_user(request)
    llm, rt = _get_llm_and_config(user_id, project_id)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    chapter_content = chapter_service.get_chapter_content(
        project_id, chapter_number, project["filepath"]
    )
    if not chapter_content:
        raise HTTPException(status_code=404, detail=f"第{chapter_number}章内容不存在")

    # 取章节最后500字作为结尾
    ending = chapter_content[-500:] if len(chapter_content) > 500 else chapter_content

    prompt = CHAPTER_HOOK_CHECK_PROMPT.format(chapter_ending=ending)

    try:
        result = llm.invoke(prompt)
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        analysis = json.loads(result[json_start:json_end]) if json_start != -1 else {"has_hook": False, "suggestion": "无法解析"}
        return {"analysis": analysis}
    except Exception as e:
        logger.exception("Platform tool detection failed")
        raise HTTPException(status_code=500, detail="检测失败，请稍后重试")


# ── 5. 批量章节钩子检测 ─────────────────────────────────────────────

@router.post("/api/v1/projects/{project_id}/tools/batch-hook-check")
def batch_check_chapter_hooks(project_id: str, request: Request):
    user_id = get_current_user(request)
    llm, rt = _get_llm_and_config(user_id, project_id)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    chapters = chapter_service.list_chapters(project_id, user_id)
    if not chapters:
        raise HTTPException(status_code=404, detail="没有章节")

    results = []
    for ch in chapters:
        num = ch.get("chapter_number", 0)
        content = chapter_service.get_chapter_content(project_id, num, project["filepath"])
        if not content:
            results.append({"chapter_number": num, "has_hook": False, "hook_type": "无内容"})
            continue

        ending = content[-500:] if len(content) > 500 else content
        prompt = CHAPTER_HOOK_CHECK_PROMPT.format(chapter_ending=ending)

        try:
            result = llm.invoke(prompt)
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            analysis = json.loads(result[json_start:json_end]) if json_start != -1 else {"has_hook": False}
            results.append({
                "chapter_number": num,
                "has_hook": analysis.get("has_hook", False),
                "hook_type": analysis.get("hook_type", "无"),
                "suggestion": analysis.get("suggestion", "")
            })
        except Exception:
            results.append({"chapter_number": num, "has_hook": False, "hook_type": "检测失败", "suggestion": ""})

    return {"chapters": results}


# ── 6. 标签/关键词生成 ──────────────────────────────────────────────

@router.post("/api/v1/projects/{project_id}/tools/tags")
def generate_tags(project_id: str, request: Request):
    user_id = get_current_user(request)
    llm, rt = _get_llm_and_config(user_id, project_id)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")
    arch_summary = _read_architecture(project["filepath"])

    prompt = TAGS_GENERATION_PROMPT.format(
        topic=pconfig.get("topic", ""),
        genre=pconfig.get("genre", ""),
        user_guidance=pconfig.get("user_guidance", ""),
        architecture_summary=arch_summary
    )

    try:
        result = llm.invoke(prompt)
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        tags = json.loads(result[json_start:json_end]) if json_start != -1 else {"main_tags": [], "search_keywords": []}
        return {"tags": tags}
    except Exception as e:
        logger.exception("Platform tool generation failed")
        raise HTTPException(status_code=500, detail="生成失败，请稍后重试")


# ── 7. 章节标题生成 ─────────────────────────────────────────────────

@router.post("/api/v1/projects/{project_id}/tools/chapter-title")
def generate_chapter_title(project_id: str, chapter_number: int, request: Request):
    user_id = get_current_user(request)
    llm, rt = _get_llm_and_config(user_id, project_id)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    chapter_meta = chapter_service.get_chapter(project_id, chapter_number)
    chapter_content = chapter_service.get_chapter_content(project_id, chapter_number, project["filepath"])

    prompt = CHAPTER_TITLE_PROMPT.format(
        chapter_number=chapter_number,
        chapter_title=chapter_meta.get("chapter_title", "") if chapter_meta else "",
        chapter_summary=chapter_meta.get("chapter_summary", "") if chapter_meta else "",
        chapter_preview=chapter_content[:500] if chapter_content else ""
    )

    try:
        result = llm.invoke(prompt)
        titles = [t.strip() for t in result.split("\n") if t.strip() and len(t.strip()) > 5]
        return {"titles": titles[:3]}
    except Exception as e:
        logger.exception("Chapter title generation failed")
        raise HTTPException(status_code=500, detail="生成失败，请稍后重试")


# ── 8. 章节诊断 ───────────────────────────────────────────────────────

DIAGNOSIS_SYSTEM_PROMPT = """你是一位网文平台主编 + 商业化编辑 + 连载节奏医生。你的任务是诊断一章小说内容，从平台适配、爽点、钩子、节奏、人物、设定释放等多个维度给出专业诊断和改进建议。

你必须：
1. 先理解目标平台读者偏好。
2. 再分析本章的实际表现。
3. 只给诊断和建议，不替作者修改世界观、人物关系或主线立意。
4. 不直接照搬现实新闻做类比。
5. 诊断要具体到段落和情节，不要空泛概括。

按以下格式输出：
【总体评分】1-100分
【平台适配】
【本章最大问题】
【最该保留的亮点】
【需要压缩的内容】
【需要新增的冲突】
【建议强化的爽点】
【结尾钩子建议】
【改写示范】给出1-2句改写示例"""


@router.post("/api/v1/projects/{project_id}/tools/diagnose")
def diagnose_chapter(project_id: str, chapter_number: int, request: Request):
    """诊断章节质量：从平台适配、爽点、钩子、节奏等多维度评分和建议。"""
    user_id = get_current_user(request)
    llm, rt = _get_llm_and_config(user_id, project_id, temperature=0.1)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    chapter_content = chapter_service.get_chapter_content(project_id, chapter_number, project["filepath"])
    if not chapter_content:
        raise HTTPException(status_code=404, detail=f"第{chapter_number}章内容不存在")

    chapter_meta = chapter_service.get_chapter(project_id, chapter_number)

    from novel_generator.commercial_profiles import format_profile_for_prompt
    from novel_generator.commercial_prompts import chapter_diagnosis_dimensions, safety_prompt

    platform_key = pconfig.get("platform", "tomato")
    platform_text = format_profile_for_prompt(platform_key)
    dimensions_text = chapter_diagnosis_dimensions(platform_key)
    safety_text = safety_prompt()

    diagnosis_prompt = "\n\n".join([
        DIAGNOSIS_SYSTEM_PROMPT,
        platform_text,
        dimensions_text,
        "---",
        f"小说名称：{pconfig.get('topic', '未指定')}",
        f"小说类型：{pconfig.get('genre', '未指定')}",
        f"读者方向：{pconfig.get('reader_direction', '未指定')}",
        f"禁止改动设定：{pconfig.get('forbidden', '未指定')}",
        f"文风要求：{pconfig.get('style_requirement', '未指定')}",
        f"当前章节：第{chapter_number}章 {chapter_meta.get('chapter_title', '') if chapter_meta else ''}",
        f"章节定位：{chapter_meta.get('chapter_role', '') if chapter_meta else ''}",
        f"章节简述：{chapter_meta.get('chapter_summary', '') if chapter_meta else ''}",
        "---",
        "待诊断章节正文：",
        chapter_content[:6000],
        safety_text,
    ])

    try:
        result = llm.invoke(diagnosis_prompt)
        return {
            "chapter_number": chapter_number,
            "diagnosis": result,
            "platform": platform_key,
        }
    except Exception as e:
        logger.exception("Chapter diagnosis failed")
        raise HTTPException(status_code=500, detail="诊断失败，请稍后重试")


# ── 9. 多模式商业生成（章节改写/大纲/名场面/短剧分镜/平台重写）───

@router.post("/api/v1/projects/{project_id}/tools/commercial-generate")
def commercial_generate(
    project_id: str,
    request: Request,
    mode: str = "diagnose",
    chapter_number: int = 0,
    chapter_text: str = "",
    novel_name: str = "",
    novel_type: str = "",
    target_reader: str = "",
    reader_direction: str = "",
    previous_summary: str = "",
    world_setting: str = "",
    character_setting: str = "",
    protagonist_goal: str = "",
    main_conflict: str = "",
    chapter_task: str = "",
    chapter_selling_point: str = "",
    chapter_emotion: str = "",
    chapter_hook: str = "",
    trend_key: str = "",
    custom_trend: str = "",
    trend_translation: str = "",
    forbidden: str = "",
    style_requirement: str = "",
    word_range: str = "",
    output_revision_notes: bool = True,
):
    """多模式商业小说生成：支持章节诊断/改写/大纲/名场面/短剧分镜/平台重写。

    核心模式：diagnose, rewrite_chapter, platform_rewrite, outline,
    volume_outline, character_bio, platform_opening, selling_points,
    ending_hook, set_piece, short_drama, generate_chapter
    """
    user_id = get_current_user(request)
    llm, rt = _get_llm_and_config(user_id, project_id)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    pconfig = project_service.get_project_config(project_id)
    if not pconfig:
        raise HTTPException(status_code=404, detail="项目配置不存在")

    from novel_generator.commercial_prompts import CommercialPromptInput, build_commercial_prompt

    resolved_text = chapter_text
    if not resolved_text.strip() and chapter_number > 0:
        resolved_text = chapter_service.get_chapter_content(
            project_id, chapter_number, project["filepath"]
        ) or ""

    resolved_summary = previous_summary
    if not resolved_summary.strip():
        import os
        summ_path = os.path.join(project["filepath"], "global_summary.txt")
        if os.path.exists(summ_path):
            with open(summ_path, "r", encoding="utf-8") as f:
                resolved_summary = f.read()[:3000]

    resolved_world = world_setting
    if not resolved_world.strip():
        import os
        arch_path = os.path.join(project["filepath"], "Novel_architecture.txt")
        if os.path.exists(arch_path):
            with open(arch_path, "r", encoding="utf-8") as f:
                resolved_world = f.read()[:3000]

    data = CommercialPromptInput(
        mode=mode,
        novel_name=novel_name or pconfig.get("topic", ""),
        novel_type=novel_type or pconfig.get("genre", ""),
        platform=pconfig.get("platform", "tomato"),
        target_reader=target_reader or pconfig.get("target_reader", ""),
        reader_direction=reader_direction or pconfig.get("reader_direction", ""),
        current_chapter=f"第{chapter_number}章" if chapter_number > 0 else "",
        previous_summary=resolved_summary,
        world_setting=resolved_world,
        character_setting=character_setting or pconfig.get("user_guidance", ""),
        protagonist_goal=protagonist_goal,
        main_conflict=main_conflict,
        chapter_task=chapter_task,
        chapter_selling_point=chapter_selling_point,
        chapter_emotion=chapter_emotion,
        chapter_hook=chapter_hook,
        trend_key=trend_key or pconfig.get("trend_key", ""),
        custom_trend=custom_trend or pconfig.get("custom_trend", ""),
        trend_translation=trend_translation or pconfig.get("trend_translation", ""),
        forbidden=forbidden or pconfig.get("forbidden", ""),
        style_requirement=style_requirement or pconfig.get("style_requirement", ""),
        word_range=word_range or f"{pconfig.get('word_number', 3000)}字",
        chapter_text=resolved_text,
        output_revision_notes=output_revision_notes,
    )

    full_prompt = build_commercial_prompt(data)

    try:
        result = llm.invoke(full_prompt)
        return {
            "mode": mode,
            "result": result,
            "platform": pconfig.get("platform", "tomato"),
        }
    except Exception as e:
        logger.exception("Commercial generation failed")
        raise HTTPException(status_code=500, detail="生成失败，请稍后重试")


# ── 10. 获取平台画像和热点转译规则 ──

@router.get("/api/v1/platform/profiles")
def get_platform_profiles():
    """获取所有支持的平台画像配置和热点转译规则。"""
    from novel_generator.commercial_profiles import list_platform_profiles, list_trend_translators
    return {
        "platforms": list_platform_profiles(),
        "trends": list_trend_translators(),
    }


# ── 10. 根据诊断优化本章（SSE 流式）──────────────────────────────────

FIX_SYSTEM_PROMPT = """你是一位网文平台编辑。根据以下诊断报告对本章进行针对性优化。

要求：
1. 保留原剧情、人物、事件顺序和关键信息。
2. 只修复诊断报告中指出的问题，不要擅自新增大剧情。
3. 不要改变章节核心走向。
4. 保持原有文风，但提升开篇抓力、情绪张力、节奏和钩子。
5. 如果有多项问题需要修改，请依次处理。
6. 输出完整的优化后章节正文。
7. 不要输出思考过程、不要输出标记，只输出修改后的正文。"""

class DiagnoseFixRequest(BaseModel):
    chapter_number: int
    chapter_content: str
    diagnosis: str
    selected_issues: List[str] = []

@router.post("/api/v1/projects/{project_id}/tools/diagnose-and-fix")
async def diagnose_and_fix(project_id: str, body: DiagnoseFixRequest, request: Request):
    """根据诊断报告对本章进行针对性优化，SSE 流式返回优化结果。"""
    user_id = get_current_user(request)
    llm, rt = _get_llm_and_config(user_id, project_id)
    
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    pconfig = project_service.get_project_config(project_id)
    
    platform_key = pconfig.get("platform", "tomato") if pconfig else "tomato"
    
    from novel_generator.commercial_profiles import format_profile_for_prompt
    platform_text = format_profile_for_prompt(platform_key)

    issues_text = "\n".join([f"- {issue}" for issue in body.selected_issues]) if body.selected_issues else "全部诊断问题"

    fix_prompt = "\n\n".join([
        FIX_SYSTEM_PROMPT,
        platform_text,
        "---",
        f"目标平台：{platform_key}",
        "---",
        "当前章节正文：",
        body.chapter_content,
        "---",
        "诊断报告：",
        body.diagnosis,
        "---",
        "用户要求重点优化的项目：",
        issues_text,
        "---",
        "请输出优化后的完整章节正文。",
    ])

    async def event_generator():
        try:
            yield {"event": "progress", "data": json.dumps({"step": "analyzing", "message": "正在分析诊断报告..."})}
            
            result = llm.invoke(fix_prompt)
            
            yield {"event": "partial", "data": json.dumps({"content": result})}
            
            yield {"event": "done", "data": json.dumps({"step": "done", "message": "优化完成"})}
        except Exception as e:
            logger.exception("Diagnose-and-fix failed")
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())


@router.get("/api/v1/debug-db-status")
def debug_db_status():
    from backend.app.database import get_db
    with get_db() as conn:
        assignments = [dict(r) for r in conn.execute("SELECT * FROM project_model_assignment").fetchall()]
        profiles = [dict(r) for r in conn.execute("SELECT id, name, purpose, provider, model, temperature, max_tokens, health_status FROM model_profile").fetchall()]
        credentials = [dict(r) for r in conn.execute("SELECT id, name, provider, base_url, status FROM api_credential").fetchall()]
    return {
        "assignments": assignments,
        "profiles": profiles,
        "credentials": credentials
    }
