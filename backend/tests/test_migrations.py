import sqlite3
import pytest
from backend.app.database import bootstrap_schema_version, run_migrations

def test_migration_bootstrap_flow(tmp_path, monkeypatch):
    # Create an in-memory or temp file SQLite DB
    db_file = str(tmp_path / "test_migrate.db")
    conn = sqlite3.connect(db_file)
    
    # 1. Run bootstrap on fresh connection
    version = bootstrap_schema_version(conn)
    assert version == 1
    
    # Check if table was created and has version 1
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    assert row is not None
    assert row[0] == 1
    
    # 2. Re-run bootstrap, should be idempotent
    version_second = bootstrap_schema_version(conn)
    assert version_second == 1
    
    conn.close()

def test_migration_runner(tmp_path):
    db_file = str(tmp_path / "test_migrate_runner.db")
    conn = sqlite3.connect(db_file)
    
    # Bootstrap to version 1
    bootstrap_schema_version(conn)
    conn.close()
