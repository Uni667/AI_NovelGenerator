import sqlite3
import os
from contextlib import contextmanager

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
DB_PATH = os.path.join(DB_DIR, "projects.db")

os.makedirs(DB_DIR, exist_ok=True)

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
