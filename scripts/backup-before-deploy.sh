#!/bin/bash
# ============================================================================
# Pre-deployment Backup Script
# ============================================================================
# 用法:
#   bash scripts/backup-before-deploy.sh              # 仅本地备份
#   bash scripts/backup-before-deploy.sh --remote     # 本地备份 + Railway 远程备份
#
# 说明:
#   在执行 `railway up` 部署之前运行此脚本，它会:
#   1. 将本地 data/ 目录备份到 data_backup_deploy_<timestamp>/
#   2. (可选) 通过 Railway CLI 触发远程容器内的备份
#
# 依赖:
#   - 本地备份: 无额外依赖
#   - 远程备份: 需要安装 Railway CLI (npm i -g @railway/cli) 并登录
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOCAL_BACKUP_DIR="$PROJECT_DIR/data_backup_deploy_$TIMESTAMP"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Pre-deployment Backup${NC}"
echo -e "${CYAN}============================================${NC}"
echo "  Time: $(date)"
echo ""

# ==========================================
# 1. Local backup
# ==========================================
echo -e "${YELLOW}[1/2] Backing up local data/ directory...${NC}"

if [ ! -d "$PROJECT_DIR/data" ]; then
    echo -e "${RED}  ⚠  Local data/ directory not found at $PROJECT_DIR/data${NC}"
    echo "     Skipping local backup."
else
    # Count projects and size before backup
    PROJECT_COUNT=$(find "$PROJECT_DIR/data/projects" -maxdepth 1 -type d 2>/dev/null | wc -l)
    PROJECT_COUNT=$((PROJECT_COUNT - 1))  # subtract the parent dir itself
    DATA_SIZE=$(du -sh "$PROJECT_DIR/data" 2>/dev/null | cut -f1)

    cp -r "$PROJECT_DIR/data" "$LOCAL_BACKUP_DIR"
    echo -e "  ${GREEN}✔  Backup saved to:${NC} $LOCAL_BACKUP_DIR"
    echo "     Projects: $PROJECT_COUNT | Size: $DATA_SIZE"
fi

# ==========================================
# 2. Remote Railway backup (optional)
# ==========================================
REMOTE_DONE=false
if [ "${1:-}" = "--remote" ]; then
    echo ""
    echo -e "${YELLOW}[2/2] Triggering remote backup on Railway...${NC}"

    if command -v railway &> /dev/null; then
        echo "  Railway CLI found, checking login status..."
        if railway whoami &>/dev/null; then
            echo "  Logged in. Sending backup command to Railway container..."
            if railway exec -- "mkdir -p /app/data/backups && python /app/utils/backup.py backup 2>/dev/null || bash -c 'tar -czf /app/data/backups/predeploy_${TIMESTAMP}.tar.gz -C /app/data projects.db projects 2>/dev/null'"; then
                echo -e "  ${GREEN}✔  Remote backup triggered successfully!${NC}"
                REMOTE_DONE=true
            else
                echo -e "  ${RED}⚠  Railway exec command failed.${NC}"
                echo "     The container might not have python /app/utils/backup.py"
                echo "     (it's not copied into the Docker image by default)."
                echo "     The inline tar fallback may have succeeded."
            fi
        else
            echo -e "  ${RED}⚠  Not logged into Railway. Run 'railway login' first.${NC}"
        fi
    else
        echo -e "  ${RED}⚠  Railway CLI not found.${NC}"
        echo "     Install: npm i -g @railway/cli"
        echo "     Or manually backup from https://railway.app/dashboard → Volumes"
    fi
else
    echo ""
    echo -e "${YELLOW}[2/2] Skipped (pass --remote to also backup Railway)${NC}"
    echo "  Usage: bash scripts/backup-before-deploy.sh --remote"
fi

# ==========================================
# Summary
# ==========================================
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}  Backup Complete!${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "  Local backup:  $LOCAL_BACKUP_DIR"
if [ "$REMOTE_DONE" = true ]; then
    echo "  Remote backup: ✔  Triggered on Railway"
fi
echo ""
echo -e "${YELLOW}  Now you can safely run: railway up${NC}"
echo ""
