# AI Novel Generator — 平台化小说生成助手

[中文文档](./README_zh-CN.md) | English

> 不只是小说生成器。这是一个理解网文平台、读者偏好、热点趋势、连载节奏和商业逻辑的 **小说创作辅助工具**。

<div align="center">

## Architecture

```
┌─────────────┐     HTTP/SSE      ┌──────────────┐     SQL     ┌─────────┐
│  Next.js 16  │ ────────────────> │  FastAPI      │ ─────────> │ SQLite  │
│  Frontend    │ <──────────────── │  Backend      │ <───────── │  DB     │
│  port 3000   │   Server-Sent     │  port 8001    │            │         │
└─────────────┘   Events (SSE)    └──────────────┘            └─────────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │  LLM Adapter  │ ──────> OpenAI / DeepSeek / Ollama
                                    │  + Embedding  │
                                    └──────────────┘
```

## Project Positioning

**平台化网文生成与改稿助手** — 不是随机生成小说，而是：
- 理解目标发布平台的读者偏好和内容规则
- 将社会情绪/热点抽象转译为小说世界内部矛盾
- 诊断章节的追读性、爽点密度、节奏问题
- 辅助作者做决策，不替作者做决定

</div>

---

## Core Features

| Module | Key Capabilities |
|--------|------------------|
| Platform Profiles | 4 种平台画像 (起点/番茄/晋江/短剧IP) + 读者偏好 + 创作约束 |
| Trend Translation | 7 种热点转译引擎，将现实情绪转为虚构冲突 |
| Novel Setting Workshop | 世界观构建 / 角色设计 / 三幕式情节蓝图 |
| Intelligent Chapter Generation | 多阶段生成，含平台质检、去 AI 味修订、自动返修 |
| Chapter Diagnosis | 15 维度章节评分，含改写示范和钩子建议 |
| Multi-Mode Generation | 12 种创作模式：章节生成/改写/诊断/大纲/名场面/短剧分镜/钩子/爽点 |
| State Tracking | 角色发展轨迹 / 伏笔暗线台账 / 全局摘要自动更新 |
| Semantic Search | 向量知识库检索，长期上下文一致性 |
| Platform Tools | 书名生成 / 简介生成 / 标签推荐 / 开篇钩子检测 / 结尾钩子检测 |
| Web Workbench | 全流程 Web GUI (Next.js 16) |

---

## Supported Platform Profiles

| Platform | Key | Reader Focus |
|----------|-----|-------------|
| **起点 / QQ 阅读男频** | `qidian` | 世界观、升级体系、长线伏笔、阶段性胜利、智斗 |
| **番茄 / 七猫免费阅读** | `tomato` | 强开局、短章爽点、强反转、情绪刺激、结尾钩子 |
| **晋江 / 女频仙侠** | `jjwxc` | 人物关系、情绪张力、女主主体性、双强拉扯、宿命感 |
| **短剧 / IP 改编向** | `short_drama` | 名场面、视觉冲突、爆点台词、可剪辑爆点、节奏密集 |

---

## Supported Trend Translations

热点转译系统将现实社会情绪转为小说世界内部矛盾，**不直接照搬真实新闻**。

| Trend | Real Emotion | Fictional Translation |
|-------|-------------|----------------------|
| 资源焦虑 | 学历/阶层/资源分配焦虑 | 宗门名额垄断、学院路榜、灵脉按身份分配 |
| 规则压迫 | 算法/制度/平台带来的压迫感 | 天道刻度评分、命牌限制选择、司籍署审查 |
| 公平焦虑 | 对机会公平的焦虑 | 寒门修士对抗世家、榜单黑幕、试炼名次篡改 |
| 打工人规训 | 被制度标价和消耗 | 白籍被标价、修士被强制派役、贡献点决定选择权 |
| AI/人性焦虑 | 技术替代与人性重塑 | 天机傀儡、命算法干预人生、人格改造术 |
| 女性主体性 | 女性独立选择与边界 | 女主独立大道、高光、不是奖励品、温柔有边界 |
| 反内卷情绪 | 不愿被单一标准耗尽 | 主角质疑强弱标准、建立自己秩序、重新解释修行 |

---

## Supported Creation Modes

| Mode | Description |
|------|-------------|
| `generate_chapter` | 生成新章节 |
| `rewrite_chapter` | 改写已有章节 |
| `diagnose` | 诊断章节问题（15 维度评分 + 改写示范） |
| `outline` | 生成章节大纲 |
| `volume_outline` | 生成卷纲 |
| `character_bio` | 生成角色小传 |
| `platform_opening` | 生成平台化开篇 |
| `selling_points` | 生成爽点设计 |
| `ending_hook` | 生成结尾钩子 |
| `set_piece` | 生成名场面 |
| `short_drama` | 生成短剧化分镜 |
| `platform_rewrite` | 根据目标平台重写同一章 |

---

## Chapter Diagnosis Dimensions

章节诊断功能从以下 15 个维度评分和给出建议：

1. 平台适配度
2. 开篇钩子
3. 本章核心冲突
4. 本章爽点
5. 本章情绪点
6. 人物高光
7. 女主主体性
8. 反派压迫感
9. 设定是否过密
10. 信息释放是否合理
11. 是否有阶段性推进
12. 结尾是否有追读钩子
13. 是否存在空泛哲理
14. 是否存在节奏拖慢
15. 是否适合目标平台连载

输出格式：【总体评分】【平台适配】【本章最大问题】【最该保留的亮点】【需要压缩的内容】【需要新增的冲突】【建议强化的爽点】【结尾钩子建议】【改写示范】

---

## User-Controlled Parameters

系统只辅助诊断、建议、生成备选方案，**不强制覆盖作者原设定**。以下参数全部由用户控制：

- 小说名称 / 类型 / 目标平台 / 目标读者 / 读者方向
- 世界观设定 / 人物设定 / 主角目标 / 主要矛盾
- 当前章节任务 / 本章爽点 / 本章情绪点 / 结尾钩子
- 热点情绪选择 / 热点转译方式 / 自定义热点
- 禁止事项 / 文风要求 / 字数范围
- 创作模式选择

---

## Project Structure

```
AI_NovelGenerator/
├── frontend/                 # Next.js 16 Web Application (port 3000)
│   ├── app/                 # App Router pages
│   │   ├── login/          # Login page
│   │   └── projects/[id]/  # Project detail page
│   ├── lib/                 # API client, hooks, types
│   │   └── types/          # TypeScript type definitions
│   └── package.json
├── backend/                 # FastAPI Backend (port 8001)
│   ├── app/
│   │   ├── routes/          # API routes
│   │   ├── services/        # Business logic
│   │   └── models/          # Data models
│   ├── tests/               # Backend tests (pytest)
│   └── requirements.txt
├── novel_generator/         # AI Generation Engine
│   ├── architecture.py      # Novel architecture generation
│   ├── blueprint.py         # Chapter outline generation
│   ├── chapter.py           # Chapter draft generation + quality check
│   ├── finalization.py     # Chapter finalization
│   ├── commercial_profiles.py  # Platform profiles + trend translators
│   ├── commercial_prompts.py   # Modular prompt builder
│   ├── platform_guidance.py    # Platform-aware guidance injection
│   └── vectorstore_utils.py
├── prompt_definitions.py    # Core prompt templates
├── database/                # Database schema
│   └── init_schema.sql
├── run_server.py           # Backend startup script
├── start.sh                # One-click startup (Linux/Mac/WSL)
└── config.json             # Legacy GUI config (deprecated)
```

---

## Installation

1. **Clone the project**
   ```bash
   git clone https://github.com/YILING0013/AI_NovelGenerator
   cd AI_NovelGenerator
   ```

2. **Install backend dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your JWT_SECRET and API_SECRET_ENCRYPTION_KEY
   ```

---

## Environment Variables (.env)

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXTAUTH_SECRET` | JWT secret key for authentication | Production |
| `API_SECRET_ENCRYPTION_KEY` | Key for encrypting stored API credentials | Production |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | Optional |

---

## Running

### Quick Start (Linux/Mac/WSL)
```bash
bash start.sh
```

### Manual Start

**Terminal 1 - Backend:**
```bash
python run_server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Access: http://localhost:3000
API Docs: http://localhost:8001/docs

---

## Testing

### Backend (pytest)
```bash
python -m pytest
# or
pytest backend/tests/ -v
```

### Frontend (Vitest)
```bash
cd frontend
npm run test
```

### Specific test files
```bash
# Platform profiles and trend translators
pytest backend/tests/test_commercial_profiles.py -v

# Commercial prompt builder
pytest backend/tests/test_commercial_prompts.py -v

# Auth / Project API
pytest backend/tests/test_auth_routes.py backend/tests/test_project_routes.py -v
```

---

## API Endpoints

### Platform Profiles (public)
```
GET /api/v1/platform/profiles
```
Returns all platform profiles and trend translator definitions.

### Chapter Diagnosis
```
POST /api/v1/projects/{project_id}/tools/diagnose?chapter_number=1
```
Returns 15-dimension diagnosis with scoring, issues, highlights, and rewrite examples.

### Multi-Mode Commercial Generation
```
POST /api/v1/projects/{project_id}/tools/commercial-generate
```
Accepts `mode` parameter (diagnose/rewrite_chapter/platform_rewrite/outline/... etc.) and extensive user-controlled params.

### Existing Platform Tools
```
POST /api/v1/projects/{project_id}/tools/titles    # Title generation
POST /api/v1/projects/{project_id}/tools/blurb     # Synopsis generation
POST /api/v1/projects/{project_id}/tools/hook-check       # Opening hook check
POST /api/v1/projects/{project_id}/tools/chapter-hook-check # Ending hook check
POST /api/v1/projects/{project_id}/tools/batch-hook-check  # Batch hook check
POST /api/v1/projects/{project_id}/tools/tags      # Tag/keyword generation
POST /api/v1/projects/{project_id}/tools/chapter-title    # Chapter title generation
```

---

## Design Principles

### Author Control
系统**不自动替作者决定**世界观、人物关系、主线立意和感情走向。只能：
- 诊断问题
- 提出建议
- 生成备选方案
- 提示风险

### Safety
- 不写真实人物谣言，不消费灾难
- 不生成仇恨、色情、违法擦边、极端暴力内容
- 不直接照搬现实新闻，只抽象为小说世界内部矛盾
- 不确定处必须标明可选

### Platform-Aware
- 不同平台的读者画像、节奏要求、爽点偏好不同
- 生成和诊断都基于目标平台画像
- 作者可选择或自定义平台策略

### Hotspot Translation
- 将现实社会情绪（如公平焦虑、规则压迫）转为虚构世界冲突
- 内置 7 种转译规则，每条都包含虚构方案和禁止事项
- 支持用户自定义热点，但要求抽象为世界内部矛盾

---

## Notes

1. Configuring API credentials (LLM + Embedding) is done through the Web UI Settings page after login.
2. The `config.json` file is deprecated and no longer used by the web version.
3. For Railway deployment, see `railway.toml` and `backend/railway_start.sh`.
4. For Vercel deployment, see `.vercel/` directory.

---

## Changelog

### 2026-05-22 — Prompt Enhancement & Bug Fixes

- **next_chapter_draft_prompt 增强** — 和 `first_chapter_draft_prompt` 对齐，加入编辑角色定位、平台连载自查清单、作者控制边界
- **修复弯引号 SyntaxError** — `prompt_definitions.py` 中 3 处 Python 字符串界定符误用 Unicode 弯引号 (U+201C/U+201D)，导致模块导入失败
- **测试全绿** — 81 passed, 0 warnings

### 2026-05-20 — Platform-Aware Upgrade v2

- **FastAPI 生命周期迁移** — `on_event("startup")` → `lifespan` 异步上下文管理器，消除 deprecation warning
- **datetime.utcnow() 修复** — 全部替换为 `datetime.now(timezone.utc)`，消除 27 个 deprecation warning
- **平台画像 API** — `GET /api/v1/platform/profiles` 返回 4 种平台配置 + 7 种热点转译规则
- **章节诊断 API** — `POST /api/v1/projects/{id}/tools/diagnose` 15 维度评分 + 改写示范
- **多模式商业生成** — `POST /api/v1/projects/{id}/tools/commercial-generate` 支持 12 种创作模式
- **first_chapter_draft_prompt 增强** — 加入编辑角色定位、平台连载自查、作者控制边界
- **前端新建项目表单** — 新增读者方向、目标读者、热点情绪参考、文风要求、禁止设定 5 个高级字段
- **前端章节工作台** — 新增「诊断本章质量」按钮，带格式化评分展示
- **测试扩充** — 36 → 81 个测试 (45 new: 19 platform profiles + 26 prompt builder)
- **README 重写** — 项目定位、平台画像、创作模式、诊断维度、设计原则

---

## Future Roadmap

- [ ] Fine-grained reader persona modeling per platform sub-genre
- [ ] Chapter batch diagnosis with trend analysis over multiple chapters
- [ ] Competitive analysis against popular works on the same platform
- [ ] Opening chapter A/B testing with different platform strategies
- [ ] Character arc health monitoring across long serialization
- [ ] Export to platform-specific formats (e.g., 番茄 author backend)
- [ ] Collaborative editing and review workflow
- [ ] Real-time serialization performance prediction

---

## License

See [LICENSE](./LICENSE) file.

---

If you have questions or feature requests, please open an issue on the project repository.
