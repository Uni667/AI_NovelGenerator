#!/bin/bash
# SQLite 数据库备份脚本
# 用法: bash utils/backup_db.sh [备份目录]
# 默认备份到 data/backups/

set -euo pipefail

BACKUP_DIR="${1:-data/backups}"
DB_PATH="${DB_PATH:-data/projects.db}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/projects_${TIMESTAMP}.db"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "[backup] 数据库文件不存在: $DB_PATH，跳过备份"
    exit 0
fi

# 使用 sqlite3 的 .backup 命令进行安全备份（在线备份，不锁表）
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# 保留最近 48 小时的备份，清理更早的
find "$BACKUP_DIR" -name "projects_*.db" -mtime +2 -delete

echo "[backup] 备份完成: $BACKUP_FILE"
echo "[backup] 当前备份数: $(find "$BACKUP_DIR" -name 'projects_*.db' | wc -l)"
