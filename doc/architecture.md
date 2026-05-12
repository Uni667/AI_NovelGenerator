# AI Novel Generator 架构文档

## 整体架构

```
┌─────────────┐     HTTP/SSE      ┌──────────────┐     SQL     ┌─────────┐
│  Next.js 16  │ ────────────────> │  FastAPI      │ ─────────> │ SQLite  │
│  Frontend    │ <──────────────── │  Backend      │ <───────── │  DB     │
│  port 3000   │   Server-Sent     │  port 8001    │            │         │
└─────────────┘   Events (SSE)    └──────────────┘            └─────────┘
                                           │
                                           ▼
                                   ┌──────────────┐
                                   │  LLM Adapter  │ ──────> OpenAI / DeepSeek / ...
                                   │  + Embedding  │ ──────> Ollama / 硅基流动
                                   └──────────────┘
```

## 后端模块

| 模块 | 说明 |
|------|------|
| `backend/app/main.py` | FastAPI 应用入口，注册 13 个路由模块 |
| `backend/app/routes/generation.py` | 核心生成管线（架构/目录/章节/定稿），SSE 流式推送 |
| `backend/app/routes/auth.py` | JWT 注册/登录 |
| `backend/app/routes/projects.py` | 项目管理 CRUD |
| `backend/app/services/model_runtime.py` | 模型配置解析、运行时构建、多提供商适配 |
| `backend/app/database.py` | SQLite 数据库初始化与迁移（12 张表） |

## 前端模块

| 模块 | 说明 |
|------|------|
| `frontend/app/page.tsx` | 首页（项目列表） |
| `frontend/app/projects/[id]/page.tsx` | 项目工作台（9 个标签页：概览/工作台/AI生成/文件/知识库/人物/读者反馈/平台工具/设置） |
| `frontend/app/login/page.tsx` | 登录页 |
| `frontend/app/settings/page.tsx` | 模型配置页 |
| `frontend/lib/api-client.ts` | API 客户端（覆盖全部后端路由） |
| `frontend/lib/hooks/use-sse.ts` | SSE 流式事件消费 hook |

## AI 生成引擎

| 模块 | 说明 |
|------|------|
| `novel_generator/architecture.py` | 小说架构生成（核心种子/角色/世界观/情节） |
| `novel_generator/blueprint.py` | 章节目录生成（支持分块生成 1000+ 章） |
| `novel_generator/chapter.py` | 章节草稿生成（含语义上下文检索） |
| `novel_generator/finalization.py` | 章节定稿（更新全局摘要/角色状态/向量库） |
| `novel_generator/task_manager.py` | 异步任务注册与取消（含 DB 持久化） |
| `novel_generator/vectorstore_utils.py` | 向量检索存储 |
