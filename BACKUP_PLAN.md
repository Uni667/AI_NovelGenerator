# 数据备份方案

> 创建: 2026-06-03 | 更新: 2026-06-03

---

## 三层备份体系

```
┌─ 第1层: 容器启动自动备份 ─────────────────────────────┐
│  每次 Railway 部署/重启 → start.sh 自动执行            │
│  → tar -czf /app/data/backups/deploy_<ts>.tar.gz       │
│  → 保留最近 10 份，自动清理旧的                         │
│  → 备份失败不阻断启动（|| true）                        │
│  位置: Dockerfile (内嵌在 start.sh)                     │
└────────────────────────────────────────────────────────┘

┌─ 第2层: 本地预部署脚本 ────────────────────────────────┐
│  railway up 之前手动运行                                 │
│  → 备份本地 data/ 到 data_backup_deploy_<ts>/           │
│  → 可选 --remote 通过 Railway CLI 触发远程备份           │
│  文件: scripts/backup-before-deploy.sh                   │
└────────────────────────────────────────────────────────┘

┌─ 第3层: 手动备份 ──────────────────────────────────────┐
│  任何时候运行                                            │
│  → 本地: python utils/backup.py backup                   │
│  → 列出备份: python utils/backup.py list                 │
│  → 恢复: python utils/backup.py restore <file>           │
└────────────────────────────────────────────────────────┘
```

---

## 文件清单

| 文件 | 作用 |
|------|------|
| `Dockerfile` | 内嵌 start.sh，在容器启动时自动 tar.gz 备份数据到 `/app/data/backups/` |
| `scripts/backup-before-deploy.sh` | 部署前本地备份脚本（含可选 Railway 远程备份） |
| `utils/backup.py` | 已有备份工具，支持 backup / restore / list |
| `utils/backup_db.sh` | 已有 SQLite 专用备份脚本 |
| `BACKUP_PLAN.md` | 本文档 |

---

## 使用方式

### 日常部署流程

```bash
# 1. (可选) 先备份远程 Railway 数据
bash scripts/backup-before-deploy.sh --remote

# 2. 部署到 Railway
railway up

# 3. 容器启动时会自动执行备份 + 启动服务
#    备份文件在 Railway Volume 的 /app/data/backups/deploy_*.tar.gz
```

### 仅本地备份

```bash
bash scripts/backup-before-deploy.sh
# 输出: data_backup_deploy_20260603_223000/
```

### 查看备份历史

```bash
# 本地备份列表
ls -d data_backup_*/

# 查看备份数据库中的项目
python utils/backup.py list
```

---

## 恢复步骤

### 从容器自动备份恢复

备份文件在 Railway Volume 的 `/app/data/backups/` 下，名为 `deploy_<timestamp>.tar.gz`。

```bash
# 方式1: 通过 Railway CLI 进入容器
railway exec

# 在容器内:
cd /app/data/backups
tar -xzf deploy_20260603_223000.tar.gz -C /tmp/restore
cp /tmp/restore/projects.db /app/data/
cp -r /tmp/restore/projects /app/data/
```

### 从本地备份恢复

```bash
# 停止后端后执行
cp -r data_backup_deploy_20260603_223000/* data/
# 或使用 utils/backup.py
python utils/backup.py restore data_backup_deploy_20260603_223000/backup_xxxx.zip
```

---

## 备份内容说明

| 数据 | 路径 | 说明 |
|------|------|------|
| SQLite 数据库 | `projects.db` | 项目元数据、配置、状态 |
| 项目文件 | `projects/<uuid>/chapters/` | 章节内容 |
| 项目文件 | `projects/<uuid>/knowledge/` | 知识库 |
| 项目文件 | `projects/<uuid>/Novel_architecture.txt` | 小说架构 |
| 备份归档 | `backups/` | 历史备份 (zip) |

---

## .gitignore 保护

已添加以下模式到 `.gitignore`：

```
data_backup_*/
data_backup_deploy_*/
```

确保所有备份文件夹不会被 git 提交。
