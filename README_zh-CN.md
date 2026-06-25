# 📖 AI 小说生成器

> 一款基于大语言模型的 Web 版小说创作辅助工具，支持从世界观架构到章节生成的完整管线。

<div align="center">

✨ **核心功能** ✨

| 功能模块          | 关键能力                          |
|-------------------|----------------------------------|
| 🎨 小说设定工坊    | 世界观架构 / 角色设定 / 剧情蓝图   |
| 📖 智能章节生成    | 多阶段生成保障剧情连贯性           |
| 🧠 状态追踪系统    | 角色发展轨迹 / 伏笔管理系统         |
| 🔍 语义检索引擎    | 基于向量的长程上下文一致性维护      |
| 📚 知识库集成      | 支持本地文档参考         |
| ✅ 自动审校机制    | 检测剧情矛盾与逻辑冲突          |
| 🖥 Web 可视化工作台 | 全流程 GUI 操作，配置/生成/审校一体化 |

</div>

---

## 技术栈

- **前端**：Next.js 16 + React 19 + Tailwind CSS 4 + shadcn/ui
- **后端**：Python FastAPI + SQLite + Uvicorn
- **AI 引擎**：OpenAI / DeepSeek / Anthropic / Ollama / 硅基流动 多提供商支持
- **向量检索**：兼容多种 Embedding 模型的语义搜索

---

## 端口信息

| 服务 | 端口 |
|------|------|
| 前端 (Next.js) | 3000 |
| 后端 (FastAPI) | 8001 |
| API 文档 | http://localhost:8001/docs |

---

## 快速开始

### 1. 环境准备

- Python 3.10+
- Node.js 18+
- pip / npm

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写：

```bash
cp .env.example .env
```

必填项：
- `NEXTAUTH_SECRET` — JWT 签名密钥
- `API_SECRET_ENCRYPTION_KEY` — API Key 加密密钥（AES-256-GCM）

### 3. 启动后端

```bash
pip install -r backend/requirements.txt
python run_server.py
```

> [!NOTE]
> `run_server.py` 会自动配置控制台为 UTF-8 编码，并设置 `PYTHONUTF8=1` 环境变量，以解决 Windows 系统下的中文乱码问题。

后端将在 `http://localhost:8001` 启动，API 文档访问 `http://localhost:8001/docs`

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端将在 `http://localhost:3000` 启动

### 5. 使用

1. 打开浏览器访问 `http://localhost:3000`
2. 注册账号并登录
3. 进入「设置」页面配置 LLM API Key（支持 DeepSeek / OpenAI / 硅基流动 等）
4. 创建项目，填写小说主题、类型、章节数等参数
5. 依次执行：生成架构 → 生成章节目录 → 生成章节草稿 → 定稿

---

## 项目目录结构

```
AI_NovelGenerator/
├── backend/              # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py       # 服务入口
│   │   ├── auth.py       # JWT 认证
│   │   ├── database.py   # 数据库初始化与迁移
│   │   ├── errors.py     # 统一错误码
│   │   ├── models/       # Pydantic 模型
│   │   ├── routes/       # API 路由（13 个模块）
│   │   ├── services/     # 业务逻辑层
│   │   └── utils/        # 工具函数
│   ├── tests/            # 测试文件
│   └── requirements.txt
├── frontend/             # Next.js 前端
│   ├── app/              # 页面路由
│   ├── components/       # UI 组件
│   └── lib/              # API 客户端与 hooks
├── novel_generator/      # AI 生成引擎核心
├── database/             # 数据库 Schema 脚本
├── doc/                  # 文档
├── utils/                # 工具脚本
└── data/                 # 运行时数据
```

---

## API 概览

| 端点 | 说明 |
|------|------|
| `POST /api/v1/auth/register` | 注册 |
| `POST /api/v1/auth/login` | 登录 |
| `GET /api/v1/projects` | 项目列表 |
| `POST /api/v1/projects` | 创建项目 |
| `POST /api/v1/projects/{id}/generate/architecture` | 生成小说架构（SSE 流式） |
| `POST /api/v1/projects/{id}/generate/blueprint` | 生成章节目录（SSE 流式） |
| `POST /api/v1/projects/{id}/generate/chapter/{num}` | 生成章节（SSE 流式） |
| `POST /api/v1/projects/{id}/generate/finalize/{num}` | 定稿章节（SSE 流式） |
| `GET /api/v1/projects/{id}/files/{filename}` | 读取生成文件 |
| `GET /api/v1/health` | 健康检查 |

完整的 API 文档请访问 `http://localhost:8001/docs`。

---

## 数据备份与恢复

项目提供了一个跨平台的命令行备份工具 [backup.py](file:///d:/Personal/Desktop/plan/AI_NovelGenerator/utils/backup.py)，可以备份/恢复 SQLite 数据库及本地小说文件资产。

### 1. 备份数据
```bash
python utils/backup.py backup
```
这将在 `data/backups/` 目录下生成一个形如 `backup_YYYYMMDD_HHMMSS.zip` 的压缩包，包含数据库 `projects.db` 和所有项目文件资产。

### 2. 查看备份列表
```bash
python utils/backup.py list
```

### 3. 恢复数据
```bash
python utils/backup.py restore <backup_file_or_path>
```
*例如：`python utils/backup.py restore backup_20260526_194116.zip`*
> [!WARNING]
> 恢复操作会先自动对当前状态进行安全备份（生成 `pre_restore_safety_*.zip`），然后覆盖现有的数据库和项目文件。

---

## 常见问题

### Q: 启动报错 "module not found"
确认已安装依赖：
```bash
pip install -r backend/requirements.txt
cd frontend && npm install
```

### Q: 前端编译错误
项目使用 Next.js 16，部分 API 有 breaking changes。参考 `node_modules/next/dist/docs/` 中的指南。

### Q: 如何切换 LLM 提供商？
在 Web 界面的「设置」页添加 API 凭证，支持 DeepSeek / OpenAI / 硅基流动 / Ollama 等。

## 本地参考书库与防照抄守卫
系统已全面接入本地长篇小说深度吸收管线。你可以直接将数十本完本小说丢给系统进行“吸收”，提炼为高纯度的【风格圣经】与【场景模板】，并在创作时引入为生成依据。
另外，系统内置了最高级别的**防照抄守卫 (Similarity Guard)**，能够在生成管线的最后一环检测融梗与照搬现象，自动打碎重写，避免版权风险。
