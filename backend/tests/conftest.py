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

    # 创建测试数据库
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS project (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            filepath TEXT NOT NULL UNIQUE,
            status TEXT DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS project_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            topic TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            num_chapters INTEGER DEFAULT 0,
            word_number INTEGER DEFAULT 3000,
            user_guidance TEXT DEFAULT '',
            language TEXT DEFAULT 'zh',
            platform TEXT DEFAULT 'tomato',
            category TEXT DEFAULT '',
            target_reader TEXT DEFAULT '',
            reader_direction TEXT DEFAULT '',
            trend_key TEXT DEFAULT '',
            custom_trend TEXT DEFAULT '',
            trend_translation TEXT DEFAULT '',
            forbidden TEXT DEFAULT '',
            style_requirement TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS chapter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT REFERENCES user(id) ON DELETE CASCADE,
            project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            chapter_number INTEGER NOT NULL,
            chapter_title TEXT DEFAULT '',
            chapter_role TEXT DEFAULT '',
            chapter_purpose TEXT DEFAULT '',
            suspense_level TEXT DEFAULT '',
            foreshadowing TEXT DEFAULT '',
            plot_twist_level TEXT DEFAULT '',
            chapter_summary TEXT DEFAULT '',
            word_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            draft_file TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, chapter_number)
        );
        CREATE TABLE IF NOT EXISTS character_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            file_path TEXT DEFAULT '',
            status TEXT DEFAULT 'appeared',
            source TEXT DEFAULT 'user',
            first_appearance_chapter INTEGER,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS api_credential (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'openai',
            api_key_encrypted TEXT,
            api_key_last4 TEXT DEFAULT '',
            api_key_hash TEXT DEFAULT '',
            base_url TEXT NOT NULL DEFAULT '',
            headers_encrypted TEXT,
            status TEXT NOT NULL DEFAULT 'untested',
            is_default INTEGER NOT NULL DEFAULT 0,
            last_tested_at TEXT,
            last_used_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS model_profile (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'chat',
            purpose TEXT NOT NULL DEFAULT 'general',
            provider TEXT NOT NULL DEFAULT 'openai',
            base_url TEXT DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            temperature REAL,
            max_tokens INTEGER,
            top_p REAL,
            supports_streaming INTEGER NOT NULL DEFAULT 1,
            supports_json INTEGER NOT NULL DEFAULT 1,
            context_window INTEGER,
            api_credential_id TEXT REFERENCES api_credential(id) ON DELETE SET NULL,
            is_default INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            health_status TEXT NOT NULL DEFAULT 'untested',
            last_tested_at TEXT,
            last_used_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS project_model_assignment (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
            project_id TEXT NOT NULL UNIQUE REFERENCES project(id) ON DELETE CASCADE,
            architecture_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            worldbuilding_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            character_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            outline_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            draft_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            polish_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            review_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            summary_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            feedback_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            embedding_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            rerank_profile_id TEXT REFERENCES model_profile(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS generation_task (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES user(id) ON DELETE CASCADE,
            project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            input_snapshot TEXT DEFAULT '',
            output_file_id TEXT,
            error_message TEXT,
            error_code TEXT,
            error_category TEXT,
            retryable INTEGER DEFAULT 0,
            purpose TEXT DEFAULT '',
            model_profile_id TEXT,
            api_credential_id TEXT,
            progress INTEGER DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            finished_at TEXT
        );
        CREATE TABLE IF NOT EXISTS knowledge_file (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT REFERENCES user(id) ON DELETE CASCADE,
            project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            imported INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS project_file (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES user(id) ON DELETE CASCADE,
            project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            filename TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'ai_generated',
            is_current INTEGER NOT NULL DEFAULT 0,
            file_size INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS character_relationship (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            character_id_a INTEGER NOT NULL REFERENCES character_profile(id) ON DELETE CASCADE,
            character_id_b INTEGER NOT NULL REFERENCES character_profile(id) ON DELETE CASCADE,
            rel_type TEXT NOT NULL DEFAULT '',
            description TEXT DEFAULT '',
            strength REAL DEFAULT 0.5,
            direction TEXT DEFAULT 'bidirectional',
            start_chapter INTEGER,
            status TEXT DEFAULT 'active',
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS character_conflict (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            conflict_type TEXT DEFAULT '',
            intensity REAL DEFAULT 0.5,
            start_chapter INTEGER,
            resolved_chapter INTEGER,
            resolution TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS character_conflict_participant (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conflict_id INTEGER NOT NULL REFERENCES character_conflict(id) ON DELETE CASCADE,
            character_id INTEGER NOT NULL REFERENCES character_profile(id) ON DELETE CASCADE,
            role TEXT DEFAULT 'participant',
            UNIQUE(conflict_id, character_id)
        );
        CREATE TABLE IF NOT EXISTS character_appearance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            character_id INTEGER NOT NULL REFERENCES character_profile(id) ON DELETE CASCADE,
            chapter_number INTEGER NOT NULL,
            appearance_type TEXT DEFAULT 'present',
            role_in_chapter TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            updated_at TEXT NOT NULL,
            UNIQUE(character_id, chapter_number)
        );
        CREATE TABLE IF NOT EXISTS model_invocation_log (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
            project_id TEXT REFERENCES project(id) ON DELETE SET NULL,
            task_id TEXT,
            api_credential_id TEXT,
            model_profile_id TEXT,
            provider TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            purpose TEXT NOT NULL DEFAULT 'general',
            input_chars INTEGER,
            output_chars INTEGER,
            latency_ms INTEGER,
            success INTEGER NOT NULL DEFAULT 0,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL
        );
    """)
    conn.close()

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
