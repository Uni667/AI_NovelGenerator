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

| 变量 | 说明 |
|------|------|
| `ALLOWED_ORIGINS` | CORS 允许的域名，逗号分隔，必须包含 Vercel 前端地址 |
| `PORT` | Railway 自动注入，无需手动设置 |

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
