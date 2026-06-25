# AI 小说生成器 - 项目状态

> 最后更新: 2026-05-26 (已完成安全加固、版本迁移、ESLint清理及备份工具建设)

## 在线地址

| 部分 | 平台 | 地址 |
|------|------|------|
| 前端 | Vercel | https://frontend-chi-one-84.vercel.app |
| 后端 | Railway | https://ai-novel-backend-production.up.railway.app |
| API 文档 | Railway | https://ai-novel-backend-production.up.railway.app/docs |

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | Python FastAPI + uvicorn |
| 前端框架 | Next.js 16 (React 19) + TypeScript + Tailwind CSS v4 |
| 数据库 | SQLite (WAL 模式, `data/projects.db`) |
| AI SDK | openai, langchain-openai, google-genai, azure-ai-inference |
| 部署 | Railway (Dockerfile) + Vercel |

## 项目结构

```
AI_NovelGenerator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 + CORS
│   │   ├── database.py           # SQLite + 14 表 schema
│   │   ├── dependencies.py       # 依赖注入
│   │   ├── rate_limiter.py       # 速率限制
│   │   ├── routes/               # 17 个路由模块
│   │   │   ├── auth.py           # 注册/登录/JWT
│   │   │   ├── projects.py       # 项目管理
│   │   │   ├── chapters.py       # 章节管理
│   │   │   ├── generation.py     # AI 生成 (架构/蓝图/章节/定稿)
│   │   │   ├── characters.py     # 角色管理
│   │   │   ├── character_relationships.py  # 角色关系图
│   │   │   ├── character_conflicts.py      # 角色冲突网
│   │   │   ├── character_appearances.py    # 角色登场时间线
│   │   │   ├── knowledge.py      # 知识库 + 图谱
│   │   │   ├── files.py          # 文件管理
│   │   │   ├── platform_tools.py # 番茄平台工具
│   │   │   ├── material_processor.py  # 素材加工
│   │   │   ├── interactive.py    # 交互式编辑
│   │   │   ├── prompts.py        # 提示词实验室
│   │   │   ├── analytics.py      # 调用分析
│   │   │   ├── plot_arcs.py      # 伏笔暗线
│   │   │   └── user_api_config.py # 模型/凭证配置
│   │   ├── services/             # 13 个服务模块
│   │   ├── models/               # Pydantic 模型
│   │   └── utils/                # 工具 (加密/SSE)
│   ├── tests/                    # 11 个测试文件
│   └── requirements-cloud.txt    # 云部署依赖 (精简)
├── novel_generator/              # 核心生成引擎
│   ├── architecture.py           # 架构生成
│   ├── blueprint.py              # 蓝图生成
│   ├── chapter.py                # 章节生成
│   ├── finalization.py           # 定稿
│   ├── knowledge.py              # 知识库生成
│   ├── knowledge_graph.py        # 知识图谱
│   ├── material_pipeline.py      # 素材加工流水线
│   ├── character_import.py       # 角色导入
│   ├── task_manager.py           # 任务管理
│   ├── sse_emitter.py            # SSE 事件
│   ├── context.py                # 上下文管理
│   ├── cancel_token.py           # 取消令牌
│   ├── json_parser.py            # JSON 解析
│   ├── common.py                 # 公共工具
│   ├── llm_errors.py             # LLM 错误处理
│   ├── platform_guidance.py      # 平台指引
│   ├── commercial_profiles.py    # 商业化配置
│   ├── commercial_prompts.py     # 商业化提示词
│   ├── vectorstore_utils.py      # 向量存储
│   ├── prompts/                  # 8 个提示词模块
│   │   ├── architecture.py
│   │   ├── blueprint.py
│   │   ├── brainstorming.py
│   │   ├── chapter.py
│   │   ├── knowledge.py
│   │   ├── material_prompts.py
│   │   ├── revision.py
│   │   └── state_update.py
│   └── chapter_pipeline/         # 章节流水线 (6 模块)
│       ├── adapters.py
│       ├── brainstorm.py
│       ├── context_retriever.py
│       ├── prompt_builder.py
│       ├── quality_checker.py
│       └── revision.py
├── frontend/
│   ├── app/                      # Next.js App Router
│   │   ├── page.tsx              # 首页
│   │   ├── login/page.tsx        # 登录
│   │   ├── settings/page.tsx     # 设置
│   │   ├── projects/new/page.tsx # 新建项目
│   │   └── projects/[id]/
│   │       ├── page.tsx          # 项目详情 (Tab 容器)
│   │       └── chapter/[num]/page.tsx  # 章节阅读
│   ├── components/
│   │   ├── ui/                   # 16 个 UI 原语 (shadcn)
│   │   ├── layout/               # sidebar, auth-guard, backend-status
│   │   ├── project/              # 14 个 Tab 组件
│   │   │   ├── OverviewTab.tsx
│   │   │   ├── GenerationTab.tsx
│   │   │   ├── WorkbenchTab.tsx
│   │   │   ├── CharactersTab.tsx
│   │   │   ├── KnowledgeTab.tsx
│   │   │   ├── FilesTab.tsx
│   │   │   ├── GraphTab.tsx
│   │   │   ├── AnalyticsTab.tsx
│   │   │   ├── SettingsTab.tsx
│   │   │   ├── PromptsTab.tsx
│   │   │   ├── PlotArcsTab.tsx
│   │   │   ├── MaterialPipelineTab.tsx
│   │   │   ├── PlatformToolsTab.tsx
│   │   │   └── ReaderTab.tsx
│   │   ├── character/            # 角色组件
│   │   └── project/workbench/    # 工作台子组件 (6)
│   └── lib/                      # hooks, api-client, types, auth
├── Dockerfile                    # Railway 部署
├── railway.toml                  # Railway 配置
└── llm_adapters.py               # LLM 适配器 (DeepSeek/OpenAI/Google/Azure)
```

## 数据库 Schema (14 表)

`user`, `project`, `project_config`, `chapter`, `knowledge_file`, `character_profile`, `character_relationship`, `character_conflict`, `character_conflict_participant`, `character_appearance`, `project_file`, `generation_task`, `api_credential`, `model_profile`, `project_model_assignment`, `model_invocation_log`

## API 路由 (17 个)

| 路由 | 前缀 |
|------|------|
| 项目管理 | `/api/v1/projects` |
| 章节管理 | `/api/v1/projects/{id}/chapters` |
| 文件管理 | `/api/v1/projects/{id}/files` |
| 知识库 | `/api/v1/projects/{id}/knowledge` |
| AI 生成 | `/api/v1/projects/{id}/generate` |
| 角色管理 | `/api/v1/projects/{id}/characters` |
| 角色关系 | `/api/v1/projects/{id}/character-relationships` |
| 角色冲突 | `/api/v1/projects/{id}/character-conflicts` |
| 角色登场 | `/api/v1/projects/{id}/character-appearances` |
| 平台工具 | `/api/v1/projects/{id}/tools` |
| 素材加工 | `/api/v1/projects/{id}/materials` |
| 交互式编辑 | `/projects/{id}/interactive` |
| 提示词实验室 | `/api/v1/projects/{id}/prompts` |
| 调用分析 | `/api/v1/projects/{id}/analytics` |
| 伏笔暗线 | `/api/v1/projects/{id}/plot_arcs` |
| 用户认证 | `/api/v1/auth` |
| 模型配置 | `/api/user/api-credentials`, `/api/user/model-profiles` |

## 部署命令

```bash
# 后端
railway up

# 前端
cd frontend && vercel --prod --env NEXT_PUBLIC_API_URL="https://ai-novel-backend-production.up.railway.app"
```

- `df94dbf` chore(ops): add backup utility and clean temporary files
- `e86a7df` fix(frontend): clean eslint warnings
- `9dd2c5c` feat(db): bootstrap schema versioning and align test database setup
- `2cbf300` feat(auth): add short-lived stream tokens for SSE
- `5c2a715` fix(core): harden utf-8 startup and environment examples
- `85ebb68` fix: replace api.getToken() with direct getToken import in PlotArcsTab
- `dac211b` refactor: 后端服务层重构 + 生成上下文构建器 + 调用日志
- `f42c594` fix: use base-ui Accordion API instead of Radix API
- `48e1955` feat: 素材加工流水线 + 工作台SSE + 章节流水线重构 + 前端组件化
- `c93a773` fix: remove deleted prompt_definitions.py from Dockerfile
- `c85e95b` feat: 平台化网文生成与改稿助手升级 v2

## 注意事项

- `config.json` 含明文密钥，不入 Docker 镜像
- 后端 CORS 需包含 Vercel 地址
- 重命名/移动 `novel_generator/` 模块后需更新 `Dockerfile` 中的 COPY 指令
- Railway 使用 `requirements-cloud.txt`（不含 torch/chromadb）

