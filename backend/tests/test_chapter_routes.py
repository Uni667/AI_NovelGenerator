"""章节管理路由集成测试。"""
import os
import shutil
import pytest
from backend.app.database import get_connection

@pytest.fixture
def test_chapter(test_project):
    # Insert a dummy chapter in SQLite database
    conn = get_connection()
    conn.execute(
        """INSERT INTO chapter (user_id, project_id, chapter_number, chapter_title, chapter_role, chapter_purpose,
           suspense_level, foreshadowing, plot_twist_level, chapter_summary, word_count, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (test_project["user_id"], test_project["id"], 1, "第1章 开始", "铺垫", "引入危机",
         "中", "埋线索", "★☆☆☆☆", "主角开局醒来", 12, "draft", "2026-05-28T00:00:00", "2026-05-28T00:00:00")
    )
    conn.commit()
    conn.close()
    
    # Create the physical chapter file
    filepath = test_project["filepath"]
    os.makedirs(os.path.join(filepath, "chapters"), exist_ok=True)
    with open(os.path.join(filepath, "chapters", "chapter_1.txt"), "w", encoding="utf-8") as f:
        f.write("这是测试正文内容。")
        
    yield {
        "project_id": test_project["id"],
        "chapter_number": 1,
        "chapter_title": "第1章 开始",
        "filepath": filepath
    }
    
    # Cleanup physical files
    if os.path.exists(filepath):
        shutil.rmtree(filepath, ignore_errors=True)


class TestChapterRoutes:
    def test_update_chapter_meta(self, client, auth_headers, test_chapter):
        """测试更新章节的元数据（标题、定位、作用等）。"""
        update_data = {
            "chapter_title": "修改后的章节标题",
            "chapter_role": "高潮",
            "chapter_purpose": "正面冲突",
            "suspense_level": "强",
            "foreshadowing": "回收伏笔",
            "plot_twist_level": "★★★☆☆",
            "chapter_summary": "主角正面迎敌，发现真相"
        }
        url = f"/api/v1/projects/{test_chapter['project_id']}/chapters/{test_chapter['chapter_number']}"
        response = client.put(url, json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "已保存"
        assert data["meta"]["chapter_title"] == "修改后的章节标题"
        assert data["meta"]["chapter_role"] == "高潮"
        assert data["meta"]["chapter_purpose"] == "正面冲突"
        assert data["meta"]["suspense_level"] == "强"
        assert data["meta"]["foreshadowing"] == "回收伏笔"
        assert data["meta"]["plot_twist_level"] == "★★★☆☆"
        assert data["meta"]["chapter_summary"] == "主角正面迎敌，发现真相"

    def test_copy_chapter(self, client, auth_headers, test_chapter):
        """测试复制/克隆章节功能。"""
        url = f"/api/v1/projects/{test_chapter['project_id']}/chapters/{test_chapter['chapter_number']}/copy"
        response = client.post(url, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "复制成功"
        assert data["meta"]["chapter_number"] == 2
        assert data["meta"]["chapter_title"] == "第1章 开始 - 副本"
        assert data["meta"]["chapter_role"] == "铺垫"
        assert data["meta"]["chapter_purpose"] == "引入危机"
        assert data["meta"]["word_count"] == 12
        assert data["meta"]["status"] == "draft"
        
        # 验证物理文件是否也被成功拷贝
        dst_file = os.path.join(test_chapter["filepath"], "chapters", "chapter_2.txt")
        assert os.path.exists(dst_file)
        with open(dst_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "这是测试正文内容。"


    def test_update_chapter_status(self, client, auth_headers, test_chapter):
        """测试更新章节状态，并验证定稿状态在普通保存时是否会被保留。"""
        url = f"/api/v1/projects/{test_chapter['project_id']}/chapters/{test_chapter['chapter_number']}"
        
        # 1. 保存正文并标记为定稿 final
        res1 = client.put(url, json={"content": "这是定稿内容", "status": "final"}, headers=auth_headers)
        assert res1.status_code == 200
        assert res1.json()["meta"]["status"] == "final"
        
        # 2. 再次普通保存（不传 status），验证状态依然是 final（保留）
        res2 = client.put(url, json={"content": "修改后的定稿内容"}, headers=auth_headers)
        assert res2.status_code == 200
        assert res2.json()["meta"]["status"] == "final"
        
        # 3. 显式修改为 draft 草稿
        res3 = client.put(url, json={"status": "draft"}, headers=auth_headers)
        assert res3.status_code == 200
        assert res3.json()["meta"]["status"] == "draft"

    def test_sync_subsequent_chapters(self, client, auth_headers, test_chapter, monkeypatch):
        """测试定稿修改后，同步后续章节大纲接口。"""
        # 向数据库插入第 2 章的测试数据
        from backend.app.database import get_connection
        conn = get_connection()
        conn.execute(
            """INSERT INTO chapter (user_id, project_id, chapter_number, chapter_title, chapter_role, chapter_purpose,
               suspense_level, foreshadowing, plot_twist_level, chapter_summary, word_count, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conn.execute("SELECT user_id FROM project").fetchone()["user_id"], test_chapter["project_id"], 2, "第2章 待同步", "高潮", "战斗",
             "中", "无", "★☆☆☆☆", "旧的大纲简述", 0, "draft", "2026-05-28T00:00:00", "2026-05-28T00:00:00")
        )
        conn.commit()
        conn.close()
        
        # 准备 Novel_directory.txt
        with open(os.path.join(test_chapter["filepath"], "Novel_directory.txt"), "w", encoding="utf-8") as f:
            f.write("第1章 - 开始\n本章定位：铺垫\n\n第2章 - 待同步\n本章定位：高潮\n")
            
        class MockLLMConfig:
            interface_format = "openai"
            base_url = "http://mock"
            model_name = "mock"
            api_key = "mock"
            temperature = 0.7
            max_tokens = 2000
            timeout = 60
        class MockEmbeddingConfig:
            interface_format = "openai"
            base_url = "http://mock"
            model_name = "mock"
            api_key = ""
        class MockCancelToken:
            def raise_if_set(self): pass
            def bind(self, obj): pass
            def is_set(self): return False
        class MockGenerationContext:
            def __init__(self):
                self.filepath = test_chapter["filepath"]
                self.project_id = test_chapter["project_id"]
                self.user_id = "user_123"
                self.llm = MockLLMConfig()
                self.embedding = MockEmbeddingConfig()
                self.cancel_token = MockCancelToken()

        mock_ctx = MockGenerationContext()
        
        def _mock_build(*args, **kwargs):
            class DummyProjectCfg:
                platform = "tomato"
            class DummyRuntimeCfg:
                api_credential_id = 1
                model_profile_id = 1
            return mock_ctx, DummyProjectCfg(), DummyRuntimeCfg()
            
        monkeypatch.setattr("backend.app.services.generation_context_builder.build_full_context", _mock_build)

        class LocalMockAdapter:
            def invoke(self, prompt, **kwargs):
                return """第2章 - 新章节标题
本章定位：高潮
核心作用：交代剧情
悬念密度：弱
伏笔操作：无
认知颠覆：★☆☆☆☆
本章简述：主角修改大纲后成功击败了魔王"""
                
        def _mock_adapter(*args, **kwargs):
            return LocalMockAdapter()
            
        monkeypatch.setattr("backend.app.services.model_runtime.create_chat_adapter_from_config", _mock_adapter)
        
        # 请求同步
        url = f"/api/v1/projects/{test_chapter['project_id']}/chapters/{test_chapter['chapter_number']}/sync-subsequent"
        response = client.post(url, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "同步成功"
        
        # 检查数据库中第 2 章的大纲是否已更新
        conn = get_connection()
        ch2 = conn.execute("SELECT * FROM chapter WHERE project_id=? AND chapter_number=2", (test_chapter["project_id"],)).fetchone()
        conn.close()
        assert ch2["chapter_title"] == "新章节标题"
        assert ch2["chapter_summary"] == "主角修改大纲后成功击败了魔王"

    def test_ask_ai(self, client, auth_headers, test_chapter, monkeypatch):
        """测试向 AI 提问本章节写作合理性流式接口。"""
        from backend.app.main import app
        from backend.app.dependencies import get_generation_context
        
        class MockLLMConfig:
            interface_format = "openai"
            base_url = "http://mock"
            model_name = "mock"
            api_key = "mock"
            temperature = 0.7
            max_tokens = 2000
            timeout = 60
        class MockEmbeddingConfig:
            interface_format = "openai"
            base_url = "http://mock"
            model_name = "mock"
            api_key = ""
        class MockCancelToken:
            def raise_if_set(self): pass
            def bind(self, obj): pass
            def is_set(self): return False
        class MockGenerationContext:
            def __init__(self):
                self.filepath = test_chapter["filepath"]
                self.project_id = test_chapter["project_id"]
                self.user_id = "user_123"
                self.llm = MockLLMConfig()
                self.embedding = MockEmbeddingConfig()
                self.cancel_token = MockCancelToken()

        mock_ctx = MockGenerationContext()
        app.dependency_overrides[get_generation_context] = lambda: mock_ctx
        
        class MockClient:
            def stream(self, prompt):
                yield type('MsgChunk', (object,), {"content": "测试AI合理性分析流内容。"})()

        class LocalMockAdapter:
            def __init__(self, **kwargs):
                self._client = MockClient()
            def invoke(self, prompt, **kwargs):
                return "测试AI合理性分析流内容。"
                
        def _mock(*args, **kwargs):
            return LocalMockAdapter(**kwargs)
            
        monkeypatch.setattr("novel_generator.chapter_pipeline.revision.create_specialized_chat_adapter", _mock)
        
        url = f"/api/v1/projects/{test_chapter['project_id']}/chapters/{test_chapter['chapter_number']}/ask-ai"
        params = {"question": "第1章开头这样写合理吗？"}
        
        try:
            # EventSource request via client GET
            response = client.get(url, params=params, headers=auth_headers)
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            assert "测试AI合理性分析流内容。" in response.text
        finally:
            app.dependency_overrides.clear()
