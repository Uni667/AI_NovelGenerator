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
