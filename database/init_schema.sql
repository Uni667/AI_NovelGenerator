-- AI Novel Generator Database Schema
-- SQLite 数据库初始化脚本
-- 用于从零创建数据库结构
-- 此文件与 backend/app/database.py 保持同步，是数据库结构的单一真相源

-- 用户表
CREATE TABLE IF NOT EXISTS user (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 项目表
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
CREATE INDEX IF NOT EXISTS idx_project_user_id ON project(user_id);

-- 项目配置表（从 project 拆分）
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
    category TEXT DEFAULT ''
);

-- 章节表
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
CREATE INDEX IF NOT EXISTS idx_chapter_project ON chapter(project_id, chapter_number);
CREATE INDEX IF NOT EXISTS idx_chapter_user ON chapter(user_id);

-- 角色档案表
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
CREATE INDEX IF NOT EXISTS idx_rel_project ON character_relationship(project_id);
CREATE INDEX IF NOT EXISTS idx_rel_chars ON character_relationship(character_id_a, character_id_b);

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
CREATE INDEX IF NOT EXISTS idx_conflict_project ON character_conflict(project_id);

-- 冲突参与方
CREATE TABLE IF NOT EXISTS character_conflict_participant (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conflict_id INTEGER NOT NULL REFERENCES character_conflict(id) ON DELETE CASCADE,
    character_id INTEGER NOT NULL REFERENCES character_profile(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'participant',
    UNIQUE(conflict_id, character_id)
);
CREATE INDEX IF NOT EXISTS idx_conflict_participant ON character_conflict_participant(conflict_id);

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
CREATE INDEX IF NOT EXISTS idx_appearance_project ON character_appearance(project_id);
CREATE INDEX IF NOT EXISTS idx_appearance_char ON character_appearance(character_id, chapter_number);

-- API 凭证表
CREATE TABLE IF NOT EXISTS api_credential (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'openai'
        CHECK(provider IN ('openai','deepseek','qwen','anthropic','siliconflow','custom','local')),
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

-- 模型配置表
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

-- 项目模型分配表
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
CREATE INDEX IF NOT EXISTS idx_project_assignment_user ON project_model_assignment(user_id);

-- 生成任务表
CREATE TABLE IF NOT EXISTS generation_task (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES user(id) ON DELETE CASCADE,
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
CREATE INDEX IF NOT EXISTS idx_generation_task_project ON generation_task(project_id);
CREATE INDEX IF NOT EXISTS idx_generation_task_user ON generation_task(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_task_status ON generation_task(status);

-- 知识库文件表
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
CREATE INDEX IF NOT EXISTS idx_knowledge_project ON knowledge_file(project_id);

-- 项目文件表（架构、目录等产物的数据库记录）
CREATE TABLE IF NOT EXISTS project_file (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES user(id) ON DELETE CASCADE,
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
CREATE INDEX IF NOT EXISTS idx_project_file_user ON project_file(user_id);

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
