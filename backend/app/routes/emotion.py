# backend/app/routes/emotion.py
# -*- coding: utf-8 -*-
"""
情感分析 API 路由
提供章节情感分析和全书情感弧线两个接口。
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from backend.app.auth import get_current_user
from backend.app.services import project_service, chapter_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["情感分析"])


# ============================================================
# 请求/响应模型
# ============================================================

class EmotionAnalyzeRequest(BaseModel):
    method: str = "snownlp"          # "snownlp" | "keyword" | "llm" | "all"
    text: Optional[str] = None       # 若不填则自动读取该章节内容


class EmotionArcRequest(BaseModel):
    method: str = "snownlp"
    chapter_numbers: Optional[list[int]] = None  # 不填则分析所有章节


# ============================================================
# 工具：获取项目的LLM配置
# ============================================================

def _get_llm_config(project_id: str, user_id: str) -> Optional[dict]:
    """从数据库读取用户的LLM API配置"""
    try:
        from backend.app.database import get_db
        with get_db() as conn:
            row = conn.execute(
                """SELECT interface_format, base_url, model_name, api_key
                   FROM user_api_config
                   WHERE user_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id,)
            ).fetchone()
        if not row:
            return None

        # API key 可能经过加密，尝试解密
        api_key = row["api_key"] or ""
        try:
            from backend.app.services.encryption_service import decrypt_api_key
            api_key = decrypt_api_key(api_key)
        except Exception:
            pass  # 未加密则直接使用

        return {
            "api_key": api_key,
            "base_url": row["base_url"] or "",
            "model_name": row["model_name"] or "",
            "interface_format": row["interface_format"] or "openai",
        }
    except Exception as e:
        logger.warning(f"读取LLM配置失败: {e}")
        return None


# ============================================================
# 接口一：单章节情感分析
# ============================================================

@router.post("/api/v1/projects/{project_id}/chapters/{chapter_number}/emotion")
def analyze_chapter_emotion(
    project_id: str,
    chapter_number: int,
    body: EmotionAnalyzeRequest,
    request: Request,
):
    """
    对指定章节进行情感分析。
    
    - method=snownlp  : 词典法，快速，适合批量分析
    - method=keyword  : 文学词典法，适合文学文本
    - method=llm      : 大模型零样本法，最准确但需要API
    - method=all      : 三种方法全部运行，返回综合结果
    """
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取文本（优先使用请求body中的text，其次读取章节文件）
    text = body.text
    if not text:
        text = chapter_service.get_chapter_content(
            project_id, chapter_number, project["filepath"]
        )
    if not text:
        raise HTTPException(status_code=404, detail=f"第{chapter_number}章内容为空或不存在")

    # LLM配置（method含llm时才需要）
    llm_config = None
    if "llm" in body.method:
        llm_config = _get_llm_config(project_id, user_id)
        if not llm_config and body.method == "llm":
            raise HTTPException(status_code=400, detail="未找到LLM API配置，请先在设置中配置API Key")

    try:
        from emotion_analyzer import analyze_chapter_emotion as _analyze
        result = _analyze(text=text, method=body.method, llm_config=llm_config)
        return {
            "project_id": project_id,
            "chapter_number": chapter_number,
            "char_count": len(text),
            "analysis": result,
        }
    except Exception as e:
        logger.error(f"情感分析失败 chapter={chapter_number}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"情感分析失败: {str(e)}")


# ============================================================
# 接口二：全书情感弧线
# ============================================================

@router.get("/api/v1/projects/{project_id}/emotion-arc")
def get_emotion_arc(
    project_id: str,
    request: Request,
    method: str = Query(default="snownlp", description="分析方法: snownlp|keyword|llm"),
):
    """
    分析全书所有章节，返回情感弧线数据（供前端绘制折线图）。
    
    返回格式：
    {
      "arc": [
        {"chapter_number": 1, "title": "...", "score": 0.72, "label": "积极"},
        ...
      ],
      "summary": {"avg_score": 0.6, "max_chapter": 5, "min_chapter": 3}
    }
    """
    user_id = get_current_user(request)
    project = project_service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取所有章节元数据
    chapter_list = chapter_service.list_chapters(project_id, user_id)
    if not chapter_list:
        return {"arc": [], "summary": {}}

    # 读取每章内容
    chapters_data = []
    for ch in chapter_list:
        ch_num = ch.get("chapter_number")
        if not ch_num:
            continue
        content = chapter_service.get_chapter_content(
            project_id, ch_num, project["filepath"]
        ) or ""
        chapters_data.append({
            "chapter_number": ch_num,
            "title": ch.get("chapter_title") or f"第{ch_num}章",
            "content": content,
        })

    if not chapters_data:
        return {"arc": [], "summary": {}}

    # LLM配置（可选）
    llm_config = None
    if method == "llm":
        llm_config = _get_llm_config(project_id, user_id)
        if not llm_config:
            raise HTTPException(status_code=400, detail="LLM方法需要先配置API Key")

    try:
        from emotion_analyzer import analyze_novel_arc
        arc = analyze_novel_arc(chapters_data, method=method, llm_config=llm_config)

        # 汇总统计
        scores = [item["score"] for item in arc]
        if scores:
            avg_score = round(sum(scores) / len(scores), 4)
            max_ch = arc[scores.index(max(scores))]["chapter_number"]
            min_ch = arc[scores.index(min(scores))]["chapter_number"]
            summary = {
                "avg_score": avg_score,
                "max_score_chapter": max_ch,
                "min_score_chapter": min_ch,
                "chapter_count": len(arc),
            }
        else:
            summary = {}

        return {"arc": arc, "summary": summary, "method": method}

    except Exception as e:
        logger.error(f"情感弧线分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"情感弧线分析失败: {str(e)}")


# ============================================================
# 接口三：快速文本情感测试（无需鉴权，供论文演示用）
# ============================================================

class QuickAnalyzeRequest(BaseModel):
    text: str
    method: str = "snownlp"


@router.post("/api/v1/emotion/quick-analyze")
def quick_analyze(body: QuickAnalyzeRequest):
    """
    快速情感分析接口（无需登录），用于演示和测试。
    仅支持 snownlp 和 keyword 方法（不需要LLM API）。
    """
    if body.method == "llm":
        raise HTTPException(status_code=400, detail="quick-analyze不支持llm方法，请使用项目接口")
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    try:
        from emotion_analyzer import analyze_chapter_emotion
        result = analyze_chapter_emotion(text=body.text, method=body.method)
        return {"analysis": result, "char_count": len(body.text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
