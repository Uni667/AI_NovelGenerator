import sqlite3
import os
import json
import logging
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
DB_PATH = os.path.join(DB_DIR, "projects.db")

os.makedirs(DB_DIR, exist_ok=True)

DEFAULT_USER_ID = "default-admin"
DEFAULT_USERNAME = "admin"


def _seed_config_json(conn) -> None:
    """种子：从 config.json 导入 LLM/Embedding 配置到数据库（仅当 DB 为空时）。"""
    config_path = os.path.join(os.path.dirname(DB_DIR), "config.json")
    if not os.path.exists(config_path):
        logger.info("config.json not found, skipping seed")
        return

    # 已有 LLM 配置则跳过
    existing = conn.execute("SELECT COUNT(*) FROM user_llm_config").fetchone()
    if existing and existing[0] > 0:
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        logger.warning("Failed to read config.json for seed", exc_info=True)
        return

    # 确保默认用户存在
    existing_user = conn.execute("SELECT id FROM user WHERE id=?", (DEFAULT_USER_ID,)).fetchone()
    if not existing_user:
        conn.execute(
            "INSERT INTO user (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_USERNAME, "seeded-not-for-login", datetime.now().isoformat()),
        )

    now = datetime.now().isoformat()

    # 导入 LLM 配置
    llm_configs = cfg.get("llm_configs", {})
    for name, c in llm_configs.items():
        if not c.get("api_key"):
            continue
        conn.execute(
            """INSERT OR IGNORE INTO user_llm_config
               (user_id, name, interface_format, api_key, base_url, model_name,
                temperature, max_tokens, timeout, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                DEFAULT_USER_ID,
                name,
                c.get("interface_format", "OpenAI"),
                c.get("api_key", ""),
                c.get("base_url", ""),
                c.get("model_name", ""),
                c.get("temperature", 0.7),
                c.get("max_tokens", 8192),
                c.get("timeout", 600),
                now,
                now,
            ),
        )
        logger.info("Seeded LLM config: %s", name)

    # 导入 Embedding 配置
    emb_configs = cfg.get("embedding_configs", {})
    for name, c in emb_configs.items():
        if not c.get("api_key"):
            continue
        conn.execute(
            """INSERT OR IGNORE INTO user_embedding_config
               (user_id, name, interface_format, api_key, base_url, model_name,
                retrieval_k, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                DEFAULT_USER_ID,
                name,
                c.get("interface_format", "OpenAI"),
                c.get("api_key", ""),
                c.get("base_url", ""),
                c.get("model_name", ""),
                c.get("retrieval_k", 4),
                now,
                now,
            ),
        )
        logger.info("Seeded embedding config: %s", name)

    logger.info("config.json seed complete")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        # 修复旧版 model_profile 表：如果存在但缺少 api_credential_id 列则删除重建
        try:
            cur = conn.execute("SELECT api_credential_id FROM model_profile LIMIT 0")
        except Exception:
            try:
                conn.execute("DROP TABLE IF EXISTS model_profile")
                conn.execute("DROP TABLE IF EXISTS project_model_assignment")
                conn.execute("DROP TABLE IF EXISTS model_invocation_log")
            except Exception:
                pass

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_llm_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                interface_format TEXT NOT NULL DEFAULT 'OpenAI',
                api_key TEXT NOT NULL,
                base_url TEXT DEFAULT '',
                model_name TEXT DEFAULT '',
                temperature REAL DEFAULT 0.7,
                max_tokens INTEGER DEFAULT 8192,
                timeout INTEGER DEFAULT 600,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, name)
            );

            CREATE TABLE IF NOT EXISTS user_embedding_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                interface_format TEXT NOT NULL DEFAULT 'OpenAI',
                api_key TEXT NOT NULL,
                base_url TEXT DEFAULT '',
                model_name TEXT DEFAULT '',
                retrieval_k INTEGER DEFAULT 4,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, name)
            );

            CREATE TABLE IF NOT EXISTS project (
                id TEXT PRIMARY KEY,
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
                architecture_llm TEXT DEFAULT '',
                chapter_outline_llm TEXT DEFAULT '',
                prompt_draft_llm TEXT DEFAULT '',
                final_chapter_llm TEXT DEFAULT '',
                consistency_review_llm TEXT DEFAULT '',
                embedding_config TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS chapter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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

            CREATE TABLE IF NOT EXISTS knowledge_file (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                imported INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
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

            CREATE INDEX IF NOT EXISTS idx_chapter_project ON chapter(project_id, chapter_number);
            CREATE INDEX IF NOT EXISTS idx_knowledge_project ON knowledge_file(project_id);
            CREATE INDEX IF NOT EXISTS idx_character_project ON character_profile(project_id);

            -- 角色关系图
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

            -- 冲突网
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

            -- 冲突参与方
            CREATE TABLE IF NOT EXISTS character_conflict_participant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conflict_id INTEGER NOT NULL REFERENCES character_conflict(id) ON DELETE CASCADE,
                character_id INTEGER NOT NULL REFERENCES character_profile(id) ON DELETE CASCADE,
                role TEXT DEFAULT 'participant',
                UNIQUE(conflict_id, character_id)
            );

            -- 登场时间线
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

            CREATE INDEX IF NOT EXISTS idx_rel_project ON character_relationship(project_id);
            CREATE INDEX IF NOT EXISTS idx_rel_chars ON character_relationship(character_id_a, character_id_b);
            CREATE INDEX IF NOT EXISTS idx_conflict_project ON character_conflict(project_id);
            CREATE INDEX IF NOT EXISTS idx_conflict_participant ON character_conflict_participant(conflict_id);
            CREATE INDEX IF NOT EXISTS idx_appearance_project ON character_appearance(project_id);
            CREATE INDEX IF NOT EXISTS idx_appearance_char ON character_appearance(character_id, chapter_number);

            -- 项目文件（架构、目录等产物的数据库记录）
            CREATE TABLE IF NOT EXISTS project_file (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
                type TEXT NOT NULL CHECK(type IN ('architecture','core_seed','characters',
                    'worldview','outline','summary','chapter','character_state','plot_arcs',
                    'user_upload')),
                title TEXT NOT NULL DEFAULT '',
                filename TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'ai_generated'
                    CHECK(source IN ('ai_generated','user_imported','user_edited')),
                is_current INTEGER NOT NULL DEFAULT 0,
                file_size INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_project_file_project ON project_file(project_id, type);

            -- 生成任务持久化
            CREATE TABLE IF NOT EXISTS generation_task (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
                type TEXT NOT NULL CHECK(type IN ('generate_architecture','generate_outline',
                    'generate_chapter','generate_chapter_batch','finalize_chapter')),
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','running','completed','failed','cancelled')),
                input_snapshot TEXT DEFAULT '',
                output_file_id TEXT REFERENCES project_file(id) ON DELETE SET NULL,
                error_message TEXT,
                error_code TEXT,
                error_category TEXT,
                retryable INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                finished_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_generation_task_project ON generation_task(project_id);

            -- API 凭证（多对一，每用户多个 API 接入源）
            CREATE TABLE IF NOT EXISTS api_credential (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'openai'
                    CHECK(provider IN ('openai','deepseek','qwen','anthropic','custom','local')),
                api_key_encrypted TEXT,
                api_key_last4 TEXT DEFAULT '',
                api_key_hash TEXT DEFAULT '',
                base_url TEXT NOT NULL DEFAULT '',
                headers_encrypted TEXT,
                status TEXT NOT NULL DEFAULT 'untested'
                    CHECK(status IN ('untested','active','invalid','disabled')),
                is_default INTEGER NOT NULL DEFAULT 0,
                last_tested_at TEXT,
                last_used_at TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_api_credential_user ON api_credential(user_id);

            -- 模型别名/配置（不存 API Key，只存模型用途和模型名）
            CREATE TABLE IF NOT EXISTS model_profile (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'chat' CHECK(type IN ('chat','embedding','rerank')),
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
                health_status TEXT NOT NULL DEFAULT 'untested'
                    CHECK(health_status IN ('untested','active','invalid','disabled')),
                last_tested_at TEXT,
                last_used_at TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_model_profile_user ON model_profile(user_id);
            CREATE INDEX IF NOT EXISTS idx_model_profile_cred ON model_profile(api_credential_id);

            -- 项目模型分配（每个阶段用哪个 ModelProfile）
            CREATE TABLE IF NOT EXISTS project_model_assignment (
                id TEXT PRIMARY KEY,
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


            -- 模型调用日志
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
            CREATE INDEX IF NOT EXISTS idx_invocation_user ON model_invocation_log(user_id);
            CREATE INDEX IF NOT EXISTS idx_invocation_project ON model_invocation_log(project_id);
            CREATE INDEX IF NOT EXISTS idx_invocation_task ON model_invocation_log(task_id);
        """)

        # 迁移：新增 platform 和 category 列（如果不存在则忽略）
        try:
            conn.execute("ALTER TABLE project_config ADD COLUMN platform TEXT DEFAULT 'tomato'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE project_config ADD COLUMN category TEXT DEFAULT ''")
        except Exception:
            pass
        # 迁移：新增 user_id 列（多用户）
        try:
            conn.execute("ALTER TABLE project ADD COLUMN user_id TEXT REFERENCES user(id)")
        except Exception:
            pass
        # 迁移：新增 usage 列（LLM 配置用途）
        try:
            conn.execute("ALTER TABLE user_llm_config ADD COLUMN usage TEXT DEFAULT 'general'")
        except Exception:
            pass
        # 迁移：新增角色规划字段
        try:
            conn.execute("ALTER TABLE character_profile ADD COLUMN status TEXT DEFAULT 'appeared'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE character_profile ADD COLUMN source TEXT DEFAULT 'user'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE character_profile ADD COLUMN first_appearance_chapter INTEGER")
        except Exception:
            pass

        # ── 迁移：model_profile 新增字段（必须在 _migrate_user_api_config_to_credential 之前）──
        for col, defn in [
            ("purpose", "TEXT DEFAULT 'general'"),
            ("api_credential_id", "TEXT REFERENCES api_credential(id) ON DELETE SET NULL"),
            ("temperature", "REAL"),
            ("max_tokens", "INTEGER"),
            ("top_p", "REAL"),
            ("supports_streaming", "INTEGER NOT NULL DEFAULT 1"),
            ("supports_json", "INTEGER NOT NULL DEFAULT 1"),
            ("context_window", "INTEGER"),
            ("health_status", "TEXT NOT NULL DEFAULT 'untested'"),
            ("last_tested_at", "TEXT"),
            ("last_used_at", "TEXT"),
            ("last_error", "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE model_profile ADD COLUMN {col} {defn}")
            except Exception:
                pass

        # ── 迁移：旧 user_api_config → 新 api_credential ──
        try:
            _migrate_user_api_config_to_credential(conn)
        except Exception:
            pass

        # ── 迁移：project_model_assignment 新增阶段字段 ──
        for col in ["worldbuilding_profile_id", "character_profile_id", "summary_profile_id",
                     "feedback_profile_id", "rerank_profile_id"]:
            try:
                conn.execute(
                    f"ALTER TABLE project_model_assignment ADD COLUMN {col} TEXT REFERENCES model_profile(id) ON DELETE SET NULL"
                )
            except Exception:
                pass

        # ── 迁移：generation_task 新增 model/credential 追踪字段 ──
        for col, defn in [
            ("purpose", "TEXT DEFAULT ''"),
            ("model_profile_id", "TEXT"),
            ("api_credential_id", "TEXT"),
            ("progress", "INTEGER DEFAULT 0"),
            ("started_at", "TEXT"),
            ("completed_at", "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE generation_task ADD COLUMN {col} {defn}")
            except Exception:
                pass

        # 种子导入：config.json → 数据库（仅在 LLM 配置为空时）
        _seed_config_json(conn)


def _migrate_user_api_config_to_credential(conn) -> None:
    """将旧的 user_api_config 迁移为 api_credential + 更新 model_profile 绑定。"""
    # 检查旧表是否存在
    try:
        rows = conn.execute("SELECT * FROM user_api_config").fetchall()
    except Exception:
        return
    if not rows:
        return

    logger.info("Migrating %d user_api_config rows → api_credential...", len(rows))
    for row in rows:
        r = dict(row)
        user_id = r["user_id"]
        # 检查是否已迁移
        existing = conn.execute(
            "SELECT id FROM api_credential WHERE user_id=? AND api_key_hash=?",
            (user_id, r.get("api_key_hash", "")),
        ).fetchone()
        if existing:
            cred_id = existing[0]
        else:
            import uuid as _uuid
            cred_id = _uuid.uuid4().hex
            now = r.get("updated_at") or r.get("created_at")
            conn.execute(
                """INSERT INTO api_credential
                   (id, user_id, name, provider, api_key_encrypted, api_key_last4, api_key_hash,
                    base_url, status, is_default, last_tested_at, last_used_at, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (cred_id, user_id,
                 f"{r.get('provider','openai')}-default",
                 r.get("provider", "openai"),
                 r.get("api_key_encrypted", ""),
                 r.get("api_key_last4", ""),
                 r.get("api_key_hash", ""),
                 r.get("base_url", ""),
                 r.get("status", "untested"),
                 1,  # is_default
                 r.get("last_tested_at"),
                 r.get("last_used_at"),
                 now, now),
            )

        # 更新已有 model_profile 绑定到新 credential
        conn.execute(
            "UPDATE model_profile SET api_credential_id=? WHERE user_id=? AND api_credential_id IS NULL",
            (cred_id, user_id),
        )

    logger.info("Migration complete: user_api_config → api_credential")
