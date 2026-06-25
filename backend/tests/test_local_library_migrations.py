import sqlite3
import pytest
import os
from backend.app.database import bootstrap_schema_version, run_migrations, init_db


def test_fresh_setup_has_v2_tables(tmp_path):
    """测试全新初始化的数据库直接包含 V2 版本的所有表。"""
    db_file = os.path.join(tmp_path, "fresh.db")
    
    # 模拟环境中的数据库路径
    import backend.app.database as db_module
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = db_file
    
    try:
        init_db()
        
        # 建立连接并验证
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        
        # 1. 验证版本号已为 2
        version_row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert version_row is not None
        assert version_row["version"] == 2
        
        # 2. 验证 8 个新表均已存在
        tables = [
            "local_library_config",
            "local_reference_book",
            "local_reference_volume",
            "local_reference_chapter",
            "local_reference_analysis",
            "local_reference_scene_pattern",
            "project_reference_binding",
            "reference_absorption_task",
        ]
        for table in tables:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            assert row is not None, f"表 {table} 在全新初始化库中未找到"
        
        conn.close()
    finally:
        db_module.DB_PATH = original_db_path


def test_migration_from_v1_to_v2_keeps_data(tmp_path):
    """测试数据库从 V1 升级到 V2，老数据保留，新表全部生成，且版本提升为 2。"""
    db_file = os.path.join(tmp_path, "migration_v1_v2.db")
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    
    # 1. 模拟旧版 V1 数据库结构（不含本地书库的 8 张表，但包含用户和项目表）
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
            filepath TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chapter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
            chapter_number INTEGER NOT NULL,
            chapter_title TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
        INSERT INTO schema_version (version) VALUES (1);
    """)
    
    # 2. 插入测试数据以确保数据保留
    conn.execute(
        "INSERT INTO user (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("user_1", "admin", "hash123", "2026-06-24T00:00:00Z")
    )
    conn.execute(
        "INSERT INTO project (id, user_id, name, filepath, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("proj_1", "user_1", "测试项目", "D:/projects/test", "2026-06-24T00:00:00Z", "2026-06-24T00:00:00Z")
    )
    conn.execute(
        "INSERT INTO chapter (id, project_id, chapter_number, chapter_title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (1, "proj_1", 1, "第一章", "2026-06-24T00:00:00Z", "2026-06-24T00:00:00Z")
    )
    conn.commit()
    
    # 3. 运行版本化迁移函数
    run_migrations(conn)
    
    # 4. 验证版本更新为 2
    version_row = conn.execute("SELECT version FROM schema_version").fetchone()
    assert version_row is not None
    assert version_row["version"] == 2
    
    # 5. 验证 8 个新表是否存在
    tables = [
        "local_library_config",
        "local_reference_book",
        "local_reference_volume",
        "local_reference_chapter",
        "local_reference_analysis",
        "local_reference_scene_pattern",
        "project_reference_binding",
        "reference_absorption_task",
    ]
    for table in tables:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        assert row is not None, f"表 {table} 在升级后未正确创建"
        
    # 6. 验证原有数据完好无损
    user_row = conn.execute("SELECT username FROM user WHERE id='user_1'").fetchone()
    assert user_row is not None
    assert user_row["username"] == "admin"
    
    proj_row = conn.execute("SELECT name FROM project WHERE id='proj_1'").fetchone()
    assert proj_row is not None
    assert proj_row["name"] == "测试项目"
    
    chap_row = conn.execute("SELECT chapter_title FROM chapter WHERE id=1").fetchone()
    assert chap_row is not None
    assert chap_row["chapter_title"] == "第一章"
    
    conn.close()


def test_migration_idempotence(tmp_path):
    """测试迁移函数是否具有幂等性，多次执行不会抛出错误。"""
    db_file = os.path.join(tmp_path, "idempotent.db")
    conn = sqlite3.connect(db_file)
    
    # 1. 引导到版本 1
    bootstrap_schema_version(conn)
    
    # 2. 第一次运行迁移
    run_migrations(conn)
    
    # 3. 第二次运行迁移，应该什么都不做，且不报错
    run_migrations(conn)
    
    # 4. 检查版本仍为 2
    conn.row_factory = sqlite3.Row
    version_row = conn.execute("SELECT version FROM schema_version").fetchone()
    assert version_row["version"] == 2
    
    conn.close()
