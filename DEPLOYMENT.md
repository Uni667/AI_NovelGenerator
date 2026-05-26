# 部署上线指南

## 架构

| 部分 | 平台 | 地址 |
|------|------|------|
| 后端 FastAPI | Railway | `https://ai-novel-backend-production.up.railway.app` |
| 前端 Next.js | Vercel | `https://frontend-chi-one-84.vercel.app` |

---

## 前提条件

安装 CLI 工具：

```bash
# Railway CLI
npm i -g @railway/cli

# Vercel CLI
npm i -g vercel
```

登录：

```bash
railway login
vercel login
```

---

## 后端部署 (Railway)

### 1. 确认当前状态

```bash
railway status
```

### 2. 部署

```bash
railway up
```

这会读取项目根目录的 `railway.toml` 和 `Dockerfile` 自动构建并部署。

### 3. 关键文件

- `Dockerfile` — 基于 `python:3.12-slim`，安装 `requirements-cloud.txt`，启动 uvicorn
- `railway.toml` — 服务名 `ai-novel-backend`，挂载 `/app/data` 持久卷，健康检查 `/api/v1/health`
- `backend/requirements-cloud.txt` — 云环境精简依赖（不含 torch/transformers/chromadb）

### 4. 环境变量（在 Railway Dashboard 中设置）

| 变量 | 是否必填 | 说明 |
|------|---------|------|
| `ALLOWED_ORIGINS` | 是 | CORS 允许的域名，逗号分隔，必须包含 Vercel 前端地址 |
| `NEXTAUTH_SECRET` | 是 | JWT 签名密钥（生产环境切勿使用默认值，建议使用随机密钥） |
| `API_SECRET_ENCRYPTION_KEY` | 是 | API Key 加密密钥（AES-256-GCM，必须是 64 字符的十六进制 32 字节密钥） |
| `PYTHONUTF8` | 否 | 强制 Python 运行时使用 UTF-8 编码（建议设为 `1`） |
| `PORT` | 否 | Railway 自动注入，无需手动设置 |

> [!CAUTION]
> 在生产环境中，**严禁将真实的密钥提交至 Git 仓库**。请确保所有的 API Key 签名与加密密钥都通过部署平台（如 Railway）的环境变量进行配置，并进行定期轮换。

### 5. 验证

```bash
curl https://ai-novel-backend-production.up.railway.app/api/v1/health
# 返回: {"status":"ok","service":"AI 小说生成器"}
```

---

## 前端部署 (Vercel)

### 1. 确认当前状态

项目已关联 Vercel：
- Project ID: `prj_KMaSbUByhQcASiAALIW9mnorZvtb`
- Org ID: `team_UJpayLzCLFQVBRDKXvdd3eQU`

### 2. 部署

```bash
cd frontend
vercel --prod --env NEXT_PUBLIC_API_URL="https://ai-novel-backend-production.up.railway.app"
```

首次部署时 `vercel` 会引导选择 scope 和 project，后续部署直接使用已有配置。

### 3. 关键文件

- `frontend/vercel.json` — framework 设为 `nextjs`，构建命令 `next build`
- `frontend/package.json` — Next.js 16.2.4 + React 19

### 4. 环境变量（在 Vercel Dashboard 或 CLI 设置）

| 变量 | 值 |
|------|-----|
| `NEXT_PUBLIC_API_URL` | `https://ai-novel-backend-production.up.railway.app` |

### 5. 验证

打开浏览器访问 `https://frontend-chi-one-84.vercel.app`，确认页面正常加载并能调用后端 API。

---

## 首次部署（从零开始）

如果是全新部署（没有已有项目），需要额外步骤：

### Railway（后端）

```bash
# 在项目目录下初始化
railway init
railway link
# 创建数据卷
railway volume add -m /app/data data
# 部署
railway up
```

### Vercel（前端）

```bash
cd frontend
vercel --prod --env NEXT_PUBLIC_API_URL="<后端地址>"
```

---

## 数据库自动迁移与版本管理

为了在迭代更新时不丢失用户数据，系统设计了渐进式数据库迁移机制。

### 1. 迁移触发与机制
- 数据库迁移在后端服务（`init_db`）启动时**自动触发**。
- 系统首次运行时，会自动创建一个 `schema_version` 表并动态引导（bootstrap）至版本 `1`（legacy 基础版本）。
- 历史表结构的兼容性代码被保留作为 fallback。未来任何新增字段、表的变更，都必须在 `backend/app/database.py` 的 `run_migrations` 和 `migrations` 字典中登记为增量版本。

### 2. 生产数据库的备份与恢复
部署更新前，建议先通过 CLI 工具对生产数据库进行备份。
- 进入容器终端：
  ```bash
  python utils/backup.py backup
  ```
- 备份包保存在持久卷中的 `/app/data/backups/` 目录下。

---

## 常见问题

### 后端 CORS 错误
确认 Railway 环境变量 `ALLOWED_ORIGINS` 包含前端 Vercel 地址。配置在 `backend/app/main.py` 第 39-42 行。

### Railway 容器重启后数据丢失
用户上传的文件和生成数据存放在 `/app/data`，已通过 `railway.toml` 的 `[volume]` 配置持久化。

### 健康检查失败
Railway 健康检查路径是 `/api/v1/health`（在 `railway.toml` 中配置）。

### 前端构建失败
确保 `cd frontend && npm install` 后再部署。Node 版本建议 20+。

---

## 部署顺序

**先部署后端，再部署前端。** 前端构建时需要知道后端地址，且上线后用户访问前端时后端必须已就绪。
