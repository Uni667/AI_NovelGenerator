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
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_chapter_project ON chapter(project_id, chapter_number);
            CREATE INDEX IF NOT EXISTS idx_knowledge_project ON knowledge_file(project_id);
            CREATE INDEX IF NOT EXISTS idx_character_project ON character_profile(project_id);
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
