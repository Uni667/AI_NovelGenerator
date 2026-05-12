-- AI Novel Generator Database Schema
-- SQLite 数据库初始化脚本
-- 用于从零创建数据库结构

-- 用户表
CREATE TABLE IF NOT EXISTS user (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 项目表
CREATE TABLE IF NOT EXISTS project (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    topic TEXT DEFAULT '',
    genre TEXT DEFAULT '',
    platform TEXT DEFAULT 'tomato',
    category TEXT DEFAULT '',
    num_chapters INTEGER DEFAULT 0,
    word_number INTEGER DEFAULT 3000,
    user_guidance TEXT DEFAULT '',
    language TEXT DEFAULT 'zh',
    filepath TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- 章节表
CREATE TABLE IF NOT EXISTS chapter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    chapter_number INTEGER NOT NULL,
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    outline TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    word_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES project(id),
    UNIQUE(project_id, chapter_number)
);

-- 角色表
CREATE TABLE IF NOT EXISTS character (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'appeared',
    source TEXT DEFAULT 'user',
    first_appearance_chapter INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES project(id)
);

-- API 凭证表
CREATE TABLE IF NOT EXISTS api_credential (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    base_url TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    last_tested_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- 模型配置表
CREATE TABLE IF NOT EXISTS model_profile (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    api_credential_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'chat',
    model_name TEXT NOT NULL,
    provider TEXT DEFAULT '',
    base_url TEXT DEFAULT '',
    temperature REAL DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4096,
    timeout INTEGER DEFAULT 300,
    is_active INTEGER DEFAULT 1,
    is_default INTEGER DEFAULT 0,
    health_status TEXT DEFAULT 'unknown',
    last_tested_at TEXT,
    last_error TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (api_credential_id) REFERENCES api_credential(id)
);

-- 项目模型分配表
CREATE TABLE IF NOT EXISTS project_model_assignment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    architecture_profile_id TEXT,
    worldbuilding_profile_id TEXT,
    character_profile_id TEXT,
    outline_profile_id TEXT,
    draft_profile_id TEXT,
    polish_profile_id TEXT,
    review_profile_id TEXT,
    summary_profile_id TEXT,
    feedback_profile_id TEXT,
    embedding_profile_id TEXT,
    rerank_profile_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES project(id),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- 生成任务表
CREATE TABLE IF NOT EXISTS generation_task (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    input_snapshot TEXT DEFAULT '',
    output_file_id TEXT,
    error_message TEXT,
    error_code TEXT,
    error_category TEXT,
    retryable INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    FOREIGN KEY (project_id) REFERENCES project(id),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- 知识库文件表
CREATE TABLE IF NOT EXISTS knowledge_file (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES project(id)
);

-- 项目文件表
CREATE TABLE IF NOT EXISTS project_file (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    file_type TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES project(id),
    UNIQUE(project_id, filename)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_project_user_id ON project(user_id);
CREATE INDEX IF NOT EXISTS idx_chapter_project_id ON chapter(project_id);
CREATE INDEX IF NOT EXISTS idx_character_project_id ON character(project_id);
CREATE INDEX IF NOT EXISTS idx_api_credential_user_id ON api_credential(user_id);
CREATE INDEX IF NOT EXISTS idx_model_profile_user_id ON model_profile(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_task_project ON generation_task(project_id);
CREATE INDEX IF NOT EXISTS idx_generation_task_status ON generation_task(status);
CREATE INDEX IF NOT EXISTS idx_project_file_project_id ON project_file(project_id);
