import os
import sys
import uuid
import gc
import time
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_connection, DB_PATH
from backend.app.auth import create_access_token


@pytest.fixture(autouse=True)
def setup_test_db():
    """为每个测试创建独立的测试数据库。"""
    test_db_path = f"{DB_PATH}.test"
    original_db_path = DB_PATH

    # 临时替换 DB_PATH
    import backend.app.database as db_module
    db_module.DB_PATH = test_db_path

    # 创建测试数据库并执行完整的引导/迁移逻辑
    db_module.init_db()

    yield

    # 清理测试数据库
    if os.path.exists(test_db_path):
        pass
    db_module.DB_PATH = original_db_path
    gc.collect()
    for suffix in ("", "-wal", "-shm"):
        path = f"{test_db_path}{suffix}"
        if not os.path.exists(path):
            continue
        for attempt in range(5):
            try:
                os.remove(path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.1)


@pytest.fixture
def client():
    """提供测试客户端。"""
    return TestClient(app)


@pytest.fixture
def test_user_id():
    """提供测试用户 ID。"""
    return str(uuid.uuid4())


@pytest.fixture
def test_user(test_user_id):
    """创建测试用户并返回用户信息。"""
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO user (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (test_user_id, "testuser", "hashed_password", now)
    )
    conn.commit()
    conn.close()
    return {"id": test_user_id, "username": "testuser"}


@pytest.fixture
def auth_token(test_user):
    """为测试用户生成 JWT token。"""
    return create_access_token(test_user["id"])


@pytest.fixture
def auth_headers(auth_token):
    """提供带认证的请求头。"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def test_project(test_user):
    """创建测试项目并返回项目信息。"""
    import uuid
    test_user_id = test_user["id"]
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT INTO project (id, user_id, name, description, filepath, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (project_id, test_user_id, "测试项目", "测试描述", f"/tmp/test_{project_id}", "draft", now, now)
    )
    conn.execute(
        "INSERT INTO project_config (project_id, topic, genre, num_chapters, word_number) VALUES (?, ?, ?, ?, ?)",
        (project_id, "测试主题", "奇幻", 10, 3000)
    )
    conn.commit()
    conn.close()
    return {
        "id": project_id,
        "user_id": test_user_id,
        "name": "测试项目",
        "filepath": f"/tmp/test_{project_id}"
    }


class MockCancelToken:
    def raise_if_set(self):
        pass
    def bind(self, obj):
        pass
    def is_set(self):
        return False


class MockLLMAdapter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        
    def invoke(self, prompt: str, **kwargs) -> str:
        if "【层级压缩与无损瘦身】" in prompt:
            return "This is a compressed summary."
        if "更新前文摘要" in prompt:
            return "A" * 2000
        if "单章微型剧情摘要" in prompt:
            return "This is a single chapter summary."
        if "以下是新完成的章节文本" in prompt:
            return "This is updated state."
        if "drafting" in prompt or "生成第" in prompt or "修订" in prompt or "返修" in prompt:
            return "This is a generated chapter draft"
        if "质检" in prompt or "分析" in prompt:
            return '{"score": 8, "has_hook": true, "suggestion": "Looks good"}'
        return "Mock response"


@pytest.fixture
def mock_llm_adapter(monkeypatch):
    def _mock_create_adapter(*args, **kwargs):
        return MockLLMAdapter(**kwargs)
        
    # Mock at the entry points where it is actually called
    monkeypatch.setattr("backend.app.services.model_runtime.create_chat_adapter_from_config", _mock_create_adapter)
    monkeypatch.setattr("novel_generator.chapter.create_llm_adapter", _mock_create_adapter)
    monkeypatch.setattr("novel_generator.finalization.create_llm_adapter", _mock_create_adapter)
    monkeypatch.setattr("novel_generator.chapter_pipeline.adapters.create_llm_adapter", _mock_create_adapter)
    monkeypatch.setattr("novel_generator.chapter_pipeline.prompt_builder.create_llm_adapter", _mock_create_adapter)
    return MockLLMAdapter


@pytest.fixture
def test_project_dir(tmp_path):
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create required files
    (project_dir / "Novel_directory.txt").write_text("Chapter 1: The Beginning")
    (project_dir / "global_summary.txt").write_text("Initial global summary")
    (project_dir / "character_state.txt").write_text("Initial char state")
    (project_dir / "plot_arcs.txt").write_text("Initial plot arcs")
    (project_dir / "chapters").mkdir()
    
    return str(project_dir)


@pytest.fixture
def mock_generation_context(test_project_dir):
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
        api_key = "" # Empty to skip embedding
        
    class MockGenerationContext:
        def __init__(self):
            self.filepath = test_project_dir
            self.project_id = "test_123"
            self.user_id = "user_123"
            self.llm = MockLLMConfig()
            self.embedding = MockEmbeddingConfig()
            self.cancel_token = MockCancelToken()

    return MockGenerationContext()

