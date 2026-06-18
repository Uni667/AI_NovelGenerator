"""情感分析模块与 API 路由测试。"""
import pytest
from unittest.mock import patch
from emotion_analyzer import (
    analyze_by_snownlp,
    analyze_by_keyword,
    analyze_chapter_emotion,
    LABEL_POSITIVE,
    LABEL_NEGATIVE,
    LABEL_NEUTRAL,
)


def test_snownlp_analyzer_basic():
    """测试 SnowNLP 情感分析基础功能（支持降级处理）。"""
    text_pos = "他走在清晨的朝阳里，心中充满了莫名的期待，十分高兴。"
    res_pos = analyze_by_snownlp(text_pos)
    assert "score" in res_pos
    assert "label" in res_pos
    assert "method" in res_pos
    assert res_pos["method"] == "snownlp"


def test_keyword_analyzer_basic():
    """测试自定义文学词典分析。"""
    text_pos = "欢喜喜悦高兴快乐幸福温暖朝阳"
    res_pos = analyze_by_keyword(text_pos)
    assert res_pos["score"] > 0.5
    assert res_pos["label"] == LABEL_POSITIVE
    assert res_pos["pos_count"] > 0

    text_neg = "悲伤痛苦绝望恐惧愤怒黄昏残阳"
    res_neg = analyze_by_keyword(text_neg)
    assert res_neg["score"] < 0.5
    assert res_neg["label"] in [LABEL_NEGATIVE, "悲伤", "消极"]
    assert res_neg["neg_count"] > 0

    # 否定词处理
    text_negated = "我不高兴，也没有温暖"
    res_negated = analyze_by_keyword(text_negated)
    # 不高兴 (否定词+高兴 -> 消极词计数增加)
    assert res_negated["neg_count"] > 0


def test_analyze_chapter_emotion_combined():
    """测试综合情感分析接口。"""
    text = "这是一段普通的中性测试段落。"
    res_snownlp = analyze_chapter_emotion(text, method="snownlp")
    assert res_snownlp["method"] == "snownlp"

    res_kw = analyze_chapter_emotion(text, method="keyword")
    assert res_kw["method"] == "keyword"

    # 测试空文本降级
    res_empty = analyze_chapter_emotion("", method="snownlp")
    assert "error" in res_empty
    assert res_empty["score"] == 0.5


class TestEmotionRoutes:
    """测试情感分析相关的 FastAPI 路由。"""

    def test_quick_analyze_success(self, client):
        """测试快速情感测试接口。"""
        response = client.post(
            "/api/v1/emotion/quick-analyze",
            json={"text": "今天真是个好日子，阳光明媚，心情特别愉快！", "method": "snownlp"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert "score" in data["analysis"]
        assert "label" in data["analysis"]
        assert data["char_count"] > 0

    def test_quick_analyze_invalid_method(self, client):
        """测试快速情感接口不支持 LLM 方法（安全防范）。"""
        response = client.post(
            "/api/v1/emotion/quick-analyze",
            json={"text": "测试", "method": "llm"}
        )
        assert response.status_code == 400

    def test_quick_analyze_empty_text(self, client):
        """测试文本为空应返回 400。"""
        response = client.post(
            "/api/v1/emotion/quick-analyze",
            json={"text": "", "method": "snownlp"}
        )
        assert response.status_code == 400

    def test_chapter_emotion_analysis(self, client, auth_headers, test_project):
        """测试指定项目章节的情感分析接口。"""
        pid = test_project["id"]
        # 首先确保该章节在数据库和文件系统中存在
        from backend.app.services.chapter_service import update_chapter_content
        update_chapter_content(pid, 1, test_project["filepath"], "林震天独自看着朝阳，面带喜悦。", "draft")

        response = client.post(
            f"/api/v1/projects/{pid}/chapters/1/emotion",
            json={"method": "snownlp"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == pid
        assert data["chapter_number"] == 1
        assert "analysis" in data
        assert "score" in data["analysis"]

    def test_emotion_arc_analysis(self, client, auth_headers, test_project):
        """测试小说情感弧线分析接口。"""
        pid = test_project["id"]
        # 写入多个章节内容
        from backend.app.services.chapter_service import update_chapter_content
        from backend.app.database import get_db

        update_chapter_content(pid, 1, test_project["filepath"], "他感到十分快乐和满足。", "finalized")
        update_chapter_content(pid, 2, test_project["filepath"], "深渊中的绝望笼罩着每一个人。", "finalized")

        # 确保数据库中有这两章的记录
        uid = test_project["user_id"]
        with get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO chapter (user_id, project_id, chapter_number, chapter_title, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (uid, pid, 1, '第一章', 'finalized', '2026-05-28T00:00:00', '2026-05-28T00:00:00')
            )
            conn.execute(
                """INSERT OR REPLACE INTO chapter (user_id, project_id, chapter_number, chapter_title, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (uid, pid, 2, '第二章', 'finalized', '2026-05-28T00:00:00', '2026-05-28T00:00:00')
            )
            conn.commit()

        response = client.get(
            f"/api/v1/projects/{pid}/emotion-arc?method=snownlp",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "arc" in data
        assert "summary" in data
        assert len(data["arc"]) == 2
        assert data["arc"][0]["chapter_number"] == 1
        assert data["arc"][1]["chapter_number"] == 2
        assert "avg_score" in data["summary"]

    def test_build_chapter_prompt_with_target_emotion(self, test_project):
        """测试构建章节提示词时是否正确融入了情感基调目标。"""
        pid = test_project["id"]
        uid = test_project["user_id"]
        
        # 1. 写入目标情感基调到数据库中
        from backend.app.database import get_db
        with get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO chapter (user_id, project_id, chapter_number, chapter_title, target_emotion, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (uid, pid, 3, '第三章', '紧张/悬疑', 'draft', '2026-05-28T00:00:00', '2026-05-28T00:00:00')
            )
            conn.commit()

        # 2. 模拟运行 build_chapter_prompt
        from novel_generator.context import GenerationContext, ChapterParams
        from novel_generator.chapter_pipeline.prompt_builder import build_chapter_prompt
        
        class MockLLMConfig:
            interface_format = "openai"
            base_url = "http://mock"
            model_name = "mock"
            api_key = "mock"
            max_tokens = 100
            timeout = 10

        class MockEmbeddingConfig:
            interface_format = "openai"
            api_key = ""
            base_url = ""
            model_name = ""
            retrieval_k = 2

        ctx = GenerationContext(
            project_id=pid,
            user_id=uid,
            filepath=test_project["filepath"]
        )
        ctx.llm = MockLLMConfig()
        ctx.embedding = MockEmbeddingConfig()

        params = ChapterParams(
            chapter_number=3,
            word_number=2000,
            user_guidance="写一段日常对话。"
        )

        # 确保项目架构和目录文件存在，防止 build_chapter_prompt 读取报错
        import os
        os.makedirs(test_project["filepath"], exist_ok=True)
        with open(os.path.join(test_project["filepath"], "Novel_architecture.txt"), "w") as f:
            f.write("架构测试")
        with open(os.path.join(test_project["filepath"], "Novel_directory.txt"), "w") as f:
            f.write("第3章 第三章")

        # 3. 运行并断言提示词包含了情感基调指令
        prompt = build_chapter_prompt(ctx, params)
        assert "【本章情感基调要求】" in prompt
        assert "紧张/悬疑" in prompt

