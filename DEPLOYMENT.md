# 部署上线指南

> **AI 注意**：这是部署的权威文档。部署请求时优先读此文件和配置文件，而非依赖记忆。

## 架构

| 部分 | 平台 | 地址 |
|------|------|------|
| 后端 FastAPI | Railway | `https://ai-novel-backend-production.up.railway.app` |
| 前端 Next.js | Vercel | `https://frontend-chi-one-84.vercel.app` |

---

## 前提条件

### 1. 安装 CLI 工具

```bash
# Railway CLI
npm i -g @railway/cli

# Vercel CLI
npm i -g vercel
```

### 2. 登录验证

```bash
railway login
vercel login
```

### 3. 确认项目关联

```bash
# Railway — 应在项目根目录
railway status
# 预期输出: Project: ai-novel-backend, Environment: production

# Vercel — 应在 frontend/ 目录
cd frontend && vercel list
# 预期输出: uni667s-projects/frontend 的部署列表
```

---

## 部署顺序

**严格遵守：先后端，再前端。**
前端运行时依赖后端 API，且构建时注入 `NEXT_PUBLIC_API_URL`。

---

## 一、后端部署 (Railway)

### 命令行部署（生产环境）

```bash
# 在项目根目录执行
railway up
```

Railway 读取根目录的 `railway.toml` 和 `Dockerfile`，自动完成：构建 Docker 镜像 → 推送到 Railway → 启动容器 → 健康检查。

### 关键配置文件

| 文件 | 作用 |
|------|------|
| `railway.toml` | 服务名 `ai-novel-backend`，持久卷 `/app/data`，健康检查 `/api/v1/health` |
| `Dockerfile` | 基于 `python:3.12-slim`，安装 `requirements-cloud.txt`，启动 uvicorn |
| `backend/requirements-cloud.txt` | 云环境精简依赖（不含 torch/transformers/chromadb） |
| `backend/app/main.py` | FastAPI 入口，CORS 配置（L39-42），路由注册 |

### Railway 环境变量（在 Dashboard 设置）

| 变量 | 必填 | 说明 |
|------|------|------|
| `ALLOWED_ORIGINS` | 是 | CORS 允许域名，逗号分隔，**必须包含当前前端地址** |
| `NEXTAUTH_SECRET` | 是 | JWT 签名密钥（64 字符 hex），切勿用默认值 |
| `API_SECRET_ENCRYPTION_KEY` | 是 | API Key 加密 AES-256-GCM 密钥（64 字符 hex） |
| `PYTHONUTF8` | 推荐 | 设为 `1`，强制 UTF-8 |
| `PORT` | 否 | Railway 自动注入 |

> **安全警告**：严禁将真实密钥提交至 Git。所有密钥通过 Railway Dashboard 环境变量配置。

### ⚠️ Railway 免费套餐限制

Railway 免费套餐在 **`us-west2` 地区高峰时段不可部署**：
- 高峰时段：太平洋时间 8:00 AM – 8:00 PM（北京时间 23:00 – 次日 11:00）
- 可部署时段：太平洋时间 8:00 PM – 8:00 AM（北京时间 11:00 – 次日 23:00）

遇到 `Free-tier deploys to us-west2 are not available during peak hours` 错误时：
1. 等到北京时间 11:00 之后重试
2. 或使用「开机自动部署」功能（见下文）

### 验证部署

```bash
curl https://ai-novel-backend-production.up.railway.app/api/v1/health
# 应返回: {"status":"ok","service":"AI 小说生成器"}
```

---

## 二、前端部署 (Vercel)

### 命令行部署

```bash
cd frontend
vercel --prod
```

**注意**：环境变量 `NEXT_PUBLIC_API_URL` 已在 Vercel Dashboard 设置为 `https://ai-novel-backend-production.up.railway.app`，部署时无需通过 `--env` 指定。

### 关键配置文件

| 文件 | 作用 |
|------|------|
| `frontend/vercel.json` | framework: `nextjs`，构建命令 `next build` |
| `frontend/next.config.ts` | `NEXT_PUBLIC_API_URL` 环境变量注入，`poweredByHeader: false` |
| `frontend/.vercel/project.json` | Vercel 项目关联（projectId + orgId） |

### Vercel 环境变量（在 Dashboard 设置）

| 变量 | 值 |
|------|-----|
| `NEXT_PUBLIC_API_URL` | `https://ai-novel-backend-production.up.railway.app` |

### 验证部署

打开浏览器访问 `https://frontend-chi-one-84.vercel.app`，确认：
1. 页面正常加载
2. 登录功能正常
3. 项目列表能加载（确认后端连通）

---

## 三、开机自动部署后端

当 Railway 遇到高峰限流无法即时部署时，可使用开机自动部署：

### 原理
- `scripts/deploy-backend-on-boot.ps1` — 部署脚本（含等待网络、执行、日志、自清理逻辑）
- `Startup\RailwayDeployBackend.bat` — Windows 启动项，登录后 30 秒自动执行

### 已启用
当前已配置：下次开机时自动运行 `railway up`，成功后将自动删除启动项。

### 重新启用（部署成功后自动清除，需要时手动恢复）
创建文件 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\RailwayDeployBackend.bat`，内容：
```bat
@echo off
timeout /t 30 /nobreak > nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File "D:\Personal\Desktop\plan\AI_NovelGenerator\scripts\deploy-backend-on-boot.ps1"
```

### 日志
部署日志写入 `logs/deploy-boot.log`。

---

## 四、首次部署（从零开始）

如果是全新项目（没有现有 Railway/Vercel 项目）：

### Railway
```bash
railway init          # 初始化项目
railway link          # 关联到当前目录
railway volume add -m /app/data data   # 创建持久卷
railway up            # 部署
```

### Vercel
```bash
cd frontend
vercel                # 首次引导：选择 scope → 创建/关联 project
vercel --prod         # 生产部署
```

---

## 五、常见问题

### 后端 CORS 错误
- 确认 Railway 环境变量 `ALLOWED_ORIGINS` 包含当前前端 Vercel 地址
- CORS 配置在 `backend/app/main.py` L39-42

### Railway 容器重启后数据丢失
- `/app/data` 已通过 `railway.toml` 的 `[volume]` 配置持久化，正常重启不会丢失
- 如果改变了 volume 配置，需手动恢复备份

### 健康检查失败
- Railway 健康检查路径：`/api/v1/health`（在 `railway.toml` 中配置）
- 检查 uvicorn 是否正确启动：端口 `${PORT:-8001}`

### 前端构建失败
- 确保在 `frontend/` 目录执行
- Node.js 版本 ≥ 20.x
- 运行 `npm install` 后再构建

### 前端页面空白 / API 调用失败
- 检查 Vercel 环境变量 `NEXT_PUBLIC_API_URL` 是否正确
- 检查后端 CORS 是否包含前端域名
- 检查后端 Railway 服务是否运行中

---

## 六、数据库迁移

后端启动时自动执行渐进式数据库迁移（`init_db` → `run_migrations`）。

### 部署前备份
```bash
# 通过 Railway CLI 进入容器
railway shell
python utils/backup.py backup
```
备份保存在持久卷 `/app/data/backups/` 目录下。

---

## 辅助索引

- `railway.toml` — 后端部署配置
- `Dockerfile` — 后端容器构建
- `backend/requirements-cloud.txt` — 云依赖
- `backend/app/main.py` — 后端入口 + CORS
- `frontend/vercel.json` — 前端部署配置
- `frontend/next.config.ts` — Next.js 配置
- `frontend/.vercel/project.json` — Vercel 项目关联
- `scripts/deploy-backend-on-boot.ps1` — 开机自部署脚本（保留，可重复启用）
- `docs/DEPLOYMENT_CHECKLIST.md` — 部署检查清单
