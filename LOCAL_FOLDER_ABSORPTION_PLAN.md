# 本地文件夹整本小说吸收系统完整版计划

> 工程实施请优先读取：`LOCAL_FOLDER_ABSORPTION_ENGINEERING_PLAN.md`。本文档描述完整产品能力，工程计划文档描述阶段准备、阶段实施、阶段复查、阶段审查、兼容性、扩展性和阶段小结模板。

## 0. 总目标

在 `D:\Personal\Desktop\plan\AI_NovelGenerator` 中实现一个完整的“本地文件夹整本小说吸收系统”。

用户不需要把整本小说上传到云端数据库，也不需要占用后端大量存储。系统通过接口连接用户电脑上的本地文件夹：

```text
小说原文文件夹：存放整本小说原文
精华输出文件夹：存放系统吸收后的摘要、风格、场景、节奏、模板、索引
网页项目：负责扫描、解析、吸收、管理、绑定、生成调用
```

最终能力：

1. 用户把大量小说文件放到本地文件夹。
2. 网页点击扫描，系统自动发现新增、修改、删除的书。
3. 系统解析整本书章节、卷、番外、序章。
4. 系统分层吸收：章节、卷、全书、风格、场景、人物、爽点、节奏、伏笔。
5. 吸收结果写入精华文件夹，不把整本原文塞进数据库。
6. 项目可以绑定一本或多本参考书精华。
7. 生成章节时自动检索并注入对应写法规则。
8. 输出后做相似度检测，避免照抄参考书。
9. 支持本地运行和未来云端网页 + 本地 Agent 两种形态。

## 1. 产品定位

这个系统不是“文件上传器”，而是一个“本地小说学习与写作能力沉淀平台”。

它要完成三件事：

1. **吸收**：从整本小说中提炼写法能力。
2. **沉淀**：把能力保存成可复用精华文件。
3. **调用**：在用户写新小说时按场景调用对应规则。

系统不应把参考书当作直接续写材料，而应把参考书转化为：

- 风格圣经
- 章节结构模型
- 爽点模型
- 冲突模型
- 人物弧光模型
- 情绪曲线模型
- 场景模板
- 结尾钩子策略
- 平台化改写规则
- 禁止照抄规则

## 2. 总体架构

### 2.1 本地模式

第一种运行形态是用户在自己电脑上运行前后端：

```powershell
python run_server.py
cd frontend
npm run dev
```

此时 FastAPI 后端运行在用户电脑，可以安全读取白名单目录。

```text
浏览器
  ↓ HTTP
本地 FastAPI 后端
  ↓ 只读
小说原文文件夹
  ↓ 分析
精华输出文件夹
  ↓ 生成时读取
项目生成管线
```

### 2.2 云端网页 + 本地 Agent 模式

第二种运行形态是未来扩展：

```text
云端网页
  ↓ localhost bridge
本地文件 Agent
  ↓
用户电脑文件夹
```

本地 Agent 运行在 `127.0.0.1`，负责：

- 授权文件夹访问。
- 扫描本地书库。
- 上传必要片段给本地或云端分析接口。
- 写入精华文件夹。
- 与云端账号同步索引和精华摘要。

本计划必须在设计上预留 Agent 接口，但当前项目可先由本地后端直接实现同等能力。

## 3. 本地目录规范

### 3.1 推荐目录

```text
D:\NovelLibrary
├─ books
│  ├─ 男频
│  │  ├─ 斗破苍穹.txt
│  │  └─ 凡人修仙传.txt
│  ├─ 女频
│  │  └─ 示例女频小说.md
│  └─ 自己作品
│     └─ 我的旧书.txt
│
├─ essence
│  ├─ 斗破苍穹
│  │  ├─ manifest.json
│  │  ├─ book_summary.md
│  │  ├─ style_bible.md
│  │  ├─ scene_patterns.json
│  │  ├─ pacing_rules.md
│  │  ├─ conflict_models.md
│  │  ├─ character_arcs.md
│  │  ├─ hook_models.md
│  │  ├─ anti_copy_rules.md
│  │  ├─ chapter_summaries
│  │  ├─ chapter_analysis
│  │  ├─ volume_summaries
│  │  └─ embeddings
│  └─ 凡人修仙传
│
├─ cache
│  ├─ parse_cache
│  ├─ llm_cache
│  └─ similarity_cache
│
└─ logs
```

### 3.2 环境变量

```env
ALLOW_LOCAL_FILE_ACCESS=true
REFERENCE_BOOKS_DIR=D:\NovelLibrary\books
REFERENCE_ESSENCE_DIR=D:\NovelLibrary\essence
REFERENCE_CACHE_DIR=D:\NovelLibrary\cache
REFERENCE_LOG_DIR=D:\NovelLibrary\logs
REFERENCE_MAX_FILE_MB=500
REFERENCE_ALLOWED_EXTENSIONS=.txt,.md,.epub,.docx
REFERENCE_ENABLE_WATCHER=true
REFERENCE_ENABLE_AGENT=false
REFERENCE_ABSORB_CONCURRENCY=2
REFERENCE_SIMILARITY_THRESHOLD=0.82
```

### 3.3 默认目录

如果用户没有配置，默认使用：

```text
data/reference_library/books
data/reference_library/essence
data/reference_library/cache
data/reference_library/logs
```

## 4. 安全边界

本功能必须有严格文件访问控制。

### 4.1 读取规则

后端只能读取：

```text
REFERENCE_BOOKS_DIR
REFERENCE_CACHE_DIR
REFERENCE_ESSENCE_DIR
```

禁止读取：

- `.env`
- `.db`
- `.sqlite`
- `.sqlite3`
- `.key`
- `.pem`
- `.pfx`
- `.crt`
- `.log`
- 系统目录
- 用户桌面任意路径
- 白名单外路径

### 4.2 写入规则

后端只能写入：

```text
REFERENCE_ESSENCE_DIR
REFERENCE_CACHE_DIR
REFERENCE_LOG_DIR
```

禁止写入原文目录，除非用户显式开启“整理书库”功能。

### 4.3 路径防护

必须实现：

- `Path.resolve()` 后校验是否在白名单根目录下。
- 禁止 `..` 路径穿越。
- 禁止软链接跳出白名单目录。
- Windows 下校验盘符和 UNC 路径。
- 文件名净化，生成精华目录时使用 slug。

### 4.4 版权提示

网页必须提示：

用户只能处理自己拥有版权、获得授权或属于公版领域的作品。系统用于提炼写作结构、节奏、风格规则和创作方法，不用于复刻、传播或生成高度相似内容。

### 4.5 原文保护

系统内部生成 prompt 时：

- 不注入大段原文。
- 不注入连续原句。
- 不注入可复刻的专有设定组合。
- 不把原文同步到云端。
- 不在日志中输出原文片段。

## 5. 数据库存储策略

数据库只保存索引、状态、路径、哈希、统计、精华文件位置，不保存整本原文。

## 6. 数据库表设计

### 6.1 `local_library_config`

保存本地书库配置。

字段：

- id
- user_id nullable
- source_dir
- essence_dir
- cache_dir
- log_dir
- allow_local_file_access
- max_file_mb
- allowed_extensions_json
- watcher_enabled
- created_at
- updated_at

### 6.2 `local_reference_book`

保存本地参考书索引。

字段：

- id
- user_id nullable
- title
- author_label
- category
- tags_json
- source_file_path
- source_file_name
- source_file_ext
- source_file_hash
- source_file_size
- source_file_mtime
- source_encoding
- copyright_status
- parse_status
- absorb_status
- similarity_status
- essence_dir_path
- manifest_path
- total_chapters
- total_volumes
- total_words
- parse_confidence
- last_scanned_at
- last_parsed_at
- last_absorbed_at
- error_message
- created_at
- updated_at

状态：

```text
parse_status:
  new
  queued
  parsing
  parsed
  needs_review
  failed

absorb_status:
  not_started
  queued
  absorbing
  absorbed
  partial
  failed

similarity_status:
  not_built
  building
  ready
  failed
```

### 6.3 `local_reference_volume`

字段：

- id
- book_id
- volume_index
- title
- start_chapter_index
- end_chapter_index
- summary_path
- analysis_path
- word_count
- created_at
- updated_at

### 6.4 `local_reference_chapter`

字段：

- id
- book_id
- volume_id nullable
- chapter_index
- title
- source_start_offset
- source_end_offset
- word_count
- summary_path
- analysis_path
- scene_patterns_path
- parse_confidence
- created_at
- updated_at

### 6.5 `local_reference_analysis`

字段：

- id
- book_id
- chapter_id nullable
- volume_id nullable
- analysis_type
- content_path
- content_hash
- model_profile_id nullable
- prompt_version
- created_at

analysis_type：

- chapter_summary
- chapter_structure
- volume_summary
- book_summary
- style_bible
- plot_structure
- pacing_rules
- conflict_models
- hook_models
- character_arcs
- scene_patterns
- anti_copy_rules
- platform_adaptation

### 6.6 `local_reference_scene_pattern`

字段：

- id
- book_id
- chapter_id nullable
- volume_id nullable
- scene_type
- platform
- tags_json
- emotional_curve_json
- conflict_pattern
- pacing_pattern
- reusable_rules
- forbidden_copy_points
- source_fingerprint
- quality_score
- created_at

### 6.7 `project_reference_binding`

项目绑定参考书。

字段：

- id
- project_id
- book_id
- enabled
- weight
- use_style_bible
- use_scene_patterns
- use_pacing_rules
- use_character_arcs
- use_anti_copy_guard
- max_rules_per_generation
- created_at
- updated_at

### 6.8 `reference_absorption_task`

后台吸收任务。

字段：

- id
- task_id
- book_id
- task_type
- status
- progress_current
- progress_total
- current_step
- error_message
- started_at
- finished_at
- created_at

task_type：

- scan
- parse
- summarize_chapters
- summarize_volumes
- build_book_summary
- build_style_bible
- extract_scene_patterns
- build_similarity_index
- full_absorb
- refresh_changed_book

## 7. 精华文件格式

每本书吸收后输出：

```text
essence/<book_slug>/
├─ manifest.json
├─ book_summary.md
├─ style_bible.md
├─ plot_structure.md
├─ pacing_rules.md
├─ conflict_models.md
├─ character_arcs.md
├─ hook_models.md
├─ scene_patterns.json
├─ platform_adaptation.md
├─ anti_copy_rules.md
├─ quality_report.md
├─ volume_summaries/
│  ├─ volume_001.md
│  └─ volume_002.md
├─ chapter_summaries/
│  ├─ chapter_0001.md
│  └─ chapter_0002.md
├─ chapter_analysis/
│  ├─ chapter_0001.json
│  └─ chapter_0002.json
├─ scene_patterns/
│  ├─ humiliation_counterattack.json
│  ├─ tournament_breakthrough.json
│  └─ ending_hook.json
├─ fingerprints/
│  ├─ ngram_index.json
│  └─ phrase_fingerprints.json
└─ embeddings/
   ├─ rule_vectors.json
   └─ scene_vectors.json
```

### 7.1 `manifest.json`

```json
{
  "schema_version": 1,
  "title": "示例小说",
  "author_label": "unknown",
  "source_file_name": "example.txt",
  "source_hash": "sha256...",
  "source_size": 12345678,
  "source_mtime": "2026-06-21T00:00:00+08:00",
  "total_words": 1000000,
  "total_chapters": 500,
  "total_volumes": 10,
  "parse_confidence": 0.94,
  "absorb_status": "absorbed",
  "generated_at": "2026-06-21T00:00:00+08:00",
  "files": {
    "book_summary": "book_summary.md",
    "style_bible": "style_bible.md",
    "scene_patterns": "scene_patterns.json",
    "pacing_rules": "pacing_rules.md",
    "anti_copy_rules": "anti_copy_rules.md"
  }
}
```

### 7.2 `style_bible.md`

必须包含：

1. 全书一句话定位。
2. 目标读者爽感。
3. 叙事节奏。
4. 开篇策略。
5. 主角高光策略。
6. 反派压迫策略。
7. 情绪推动方式。
8. 信息释放密度。
9. 爽点铺垫与释放。
10. 对话风格。
11. 场景切换习惯。
12. 章节结尾钩子。
13. 长线伏笔管理。
14. 可复用写法规则。
15. 禁止照抄规则。

### 7.3 `scene_patterns.json`

```json
[
  {
    "id": "scene_001",
    "scene_type": "被羞辱后反击",
    "tags": ["压迫", "反击", "群体震惊"],
    "applicable_platforms": ["tomato", "qidian"],
    "emotional_curve": ["压低", "质疑", "爆发", "震惊", "追钩"],
    "conflict_pattern": "强者/规则压制主角，主角用提前埋下的能力或信息反击。",
    "pacing_pattern": "前三段给压迫，中段给误判，后段集中释放。",
    "reusable_rules": [
      "反派压迫必须具体化，不能只写冷笑。",
      "旁观者反应用于放大主角高光。",
      "反击前必须有至少一个轻微铺垫。"
    ],
    "forbidden_copy_points": [
      "不要复用原书人物名、势力名、招式名。",
      "不要复用原书连续桥段组合。"
    ],
    "source": {
      "book_id": "book_x",
      "chapter_range": "12-13"
    },
    "quality_score": 0.91
  }
]
```

## 8. 后端模块设计

新增模块：

```text
backend/app/routes/local_library.py
backend/app/routes/local_reference_books.py
backend/app/services/local_library_config.py
backend/app/services/local_file_guard.py
backend/app/services/local_library_scanner.py
backend/app/services/local_reference_book_service.py
backend/app/services/local_book_parser_service.py
backend/app/services/local_chapter_boundary_service.py
backend/app/services/local_absorption_service.py
backend/app/services/local_essence_writer_service.py
backend/app/services/local_style_mining_service.py
backend/app/services/local_scene_pattern_service.py
backend/app/services/local_similarity_guard_service.py
backend/app/services/local_reference_context_service.py
backend/app/services/local_library_watcher.py
```

接入现有模块：

```text
backend/app/main.py
backend/app/database.py
backend/app/services/generation_context_service.py
novel_generator/chapter_pipeline/prompt_builder.py
frontend/components/project/
frontend/lib/api-client.ts
frontend/lib/types/index.ts
```

## 9. 文件扫描设计

扫描流程：

1. 读取配置。
2. 校验本地访问是否开启。
3. 校验目录存在、可读、可写。
4. 递归扫描白名单扩展名。
5. 过滤隐藏文件、临时文件、敏感文件。
6. 计算文件大小、mtime、sha256。
7. 与数据库对比：
   - 新增
   - 未变化
   - 已修改
   - 已删除
8. 更新书库索引。
9. 返回扫描报告。

扫描报告：

```json
{
  "source_dir": "D:\\NovelLibrary\\books",
  "total_files": 120,
  "new_books": 4,
  "changed_books": 2,
  "deleted_books": 1,
  "unchanged_books": 113,
  "errors": []
}
```

## 10. 编码识别

必须支持中文小说常见编码：

- UTF-8
- UTF-8 BOM
- GBK
- GB18030
- Big5

策略：

1. 优先尝试 UTF-8。
2. 失败后尝试 GB18030。
3. 再尝试 Big5。
4. 保存识别结果到 `source_encoding`。
5. 输出精华统一使用 UTF-8。

## 11. 章节解析

支持章节标题：

```text
第1章
第001章
第一章
第一回
卷一
第一卷
楔子
序章
正文
番外
Chapter 1
CHAPTER I
```

解析输出：

- 卷信息。
- 章节序号。
- 标题。
- 起止 offset。
- 字数。
- 置信度。
- 异常点。

低置信度时：

- 标记 `needs_review`。
- 前端显示章节边界审查界面。
- 允许用户合并/拆分章节。

## 12. 吸收流程

完整吸收流程：

```text
扫描
  -> 建立书籍索引
  -> 编码识别
  -> 章节解析
  -> 章节清洗
  -> 章节摘要
  -> 章节结构分析
  -> 场景切分
  -> 场景模板提取
  -> 卷级摘要
  -> 全书摘要
  -> 人物弧光提取
  -> 冲突模型提取
  -> 节奏模型提取
  -> 钩子模型提取
  -> 风格圣经生成
  -> 平台适配分析
  -> 防照抄规则生成
  -> 相似度指纹构建
  -> 写入精华目录
  -> 更新数据库状态
```

## 13. LLM 吸收任务设计

每个分析任务都必须有明确输入和输出。

### 13.1 章节摘要

输入：

- 单章正文。
- 章节标题。
- 上一章摘要。

输出：

- 本章剧情摘要。
- 出场人物。
- 冲突。
- 爽点。
- 情绪变化。
- 伏笔。
- 结尾钩子。

### 13.2 章节结构分析

输出：

- 开篇钩子。
- 冲突引入。
- 中段推进。
- 爽点释放。
- 结尾吊点。
- 节奏评分。

### 13.3 场景模板提取

输出：

- scene_type。
- emotional_curve。
- conflict_pattern。
- pacing_pattern。
- reusable_rules。
- forbidden_copy_points。

### 13.4 全书风格圣经

输入：

- 章节摘要集合。
- 卷级摘要集合。
- 场景模板集合。
- 结构分析集合。

输出：

- `style_bible.md`。

### 13.5 防照抄规则

输出：

- 不可复用的人物名。
- 不可复用的地名。
- 不可复用的势力名。
- 不可复用的核心桥段组合。
- 不可复用的专有能力设定。
- 相似度重写策略。

## 14. 任务队列与进度

吸收整本小说是长任务，必须异步化。

### 14.1 任务状态

```text
queued
running
paused
completed
partial
failed
cancelled
```

### 14.2 任务控制

API 必须支持：

- 启动。
- 暂停。
- 恢复。
- 取消。
- 重试失败章节。
- 只刷新变更文件。
- 从上次断点继续。

### 14.3 进度展示

进度维度：

- 当前步骤。
- 当前章节。
- 已处理章节数。
- 总章节数。
- 成功数。
- 失败数。
- 预计剩余时间。
- 最近错误。

## 15. API 设计

### 15.1 配置

`GET /api/v1/local-library/config`

`PUT /api/v1/local-library/config`

`POST /api/v1/local-library/config/test`

### 15.2 扫描

`POST /api/v1/local-library/scan`

`GET /api/v1/local-library/scan-report`

### 15.3 书库

`GET /api/v1/local-library/books`

`GET /api/v1/local-library/books/{book_id}`

`PATCH /api/v1/local-library/books/{book_id}`

`DELETE /api/v1/local-library/books/{book_id}`

删除只删除索引和精华，默认不删除原文文件。

### 15.4 章节解析

`POST /api/v1/local-library/books/{book_id}/parse`

`GET /api/v1/local-library/books/{book_id}/chapters`

`PATCH /api/v1/local-library/books/{book_id}/chapters/{chapter_id}`

`POST /api/v1/local-library/books/{book_id}/chapters/rebuild`

### 15.5 吸收

`POST /api/v1/local-library/books/{book_id}/absorb`

`POST /api/v1/local-library/books/{book_id}/absorb/pause`

`POST /api/v1/local-library/books/{book_id}/absorb/resume`

`POST /api/v1/local-library/books/{book_id}/absorb/cancel`

`POST /api/v1/local-library/books/{book_id}/absorb/retry-failed`

### 15.6 精华查看

`GET /api/v1/local-library/books/{book_id}/essence`

`GET /api/v1/local-library/books/{book_id}/essence/{file_key}`

`GET /api/v1/local-library/books/{book_id}/scene-patterns`

`GET /api/v1/local-library/books/{book_id}/style-bible`

### 15.7 绑定项目

`GET /api/v1/projects/{project_id}/local-reference-books`

`POST /api/v1/projects/{project_id}/local-reference-books/{book_id}/attach`

`PATCH /api/v1/projects/{project_id}/local-reference-books/{book_id}`

`DELETE /api/v1/projects/{project_id}/local-reference-books/{book_id}`

### 15.8 生成上下文预览

`GET /api/v1/projects/{project_id}/reference-context/preview`

用于查看下一章生成时将注入哪些参考书规则。

## 16. 前端设计

新增页面：

```text
frontend/app/local-library/page.tsx
```

新增项目 Tab：

```text
frontend/components/project/LocalLibraryTab.tsx
```

新增组件：

```text
frontend/components/local-library/LibraryConfigPanel.tsx
frontend/components/local-library/LibraryScanPanel.tsx
frontend/components/local-library/BookListTable.tsx
frontend/components/local-library/BookDetailDrawer.tsx
frontend/components/local-library/ChapterBoundaryReview.tsx
frontend/components/local-library/AbsorptionProgressPanel.tsx
frontend/components/local-library/EssenceViewer.tsx
frontend/components/local-library/StyleBibleViewer.tsx
frontend/components/local-library/ScenePatternBrowser.tsx
frontend/components/local-library/ProjectBindingPanel.tsx
frontend/components/local-library/SimilarityGuardReport.tsx
```

## 17. 前端交互流程

### 17.1 初次配置

用户进入“本地书库”：

1. 显示当前原文目录和精华目录。
2. 如果目录不存在，提供创建按钮。
3. 显示读写权限检测。
4. 显示本地访问开关。

### 17.2 扫描

用户点击“扫描文件夹”：

1. 显示扫描进度。
2. 展示新增/修改/删除书籍。
3. 用户确认更新索引。

### 17.3 解析

用户选择书籍：

1. 点击解析章节。
2. 显示章节列表。
3. 低置信度章节提示人工审查。

### 17.4 吸收

用户点击吸收：

1. 显示步骤进度。
2. 支持暂停/恢复/取消。
3. 失败章节可单独重试。
4. 吸收完成后展示精华文件。

### 17.5 绑定

在项目内：

1. 进入“本地书库/参考书” Tab。
2. 选择已吸收的书。
3. 设置权重和启用项。
4. 预览生成上下文。

## 18. 生成管线接入

生成章节前，系统应执行：

1. 获取项目绑定的参考书。
2. 读取每本书的精华文件。
3. 根据当前章节目标检索场景模板。
4. 根据目标平台选择平台规则。
5. 根据当前章节功能选择：
   - 开篇钩子
   - 爽点爆发
   - 情绪拉扯
   - 战斗升级
   - 反派压迫
   - 结尾追读
6. 拼装成“参考书规则上下文”。
7. 注入 prompt。
8. 生成后执行 Similarity Guard。
9. 如相似度过高，自动重写可疑段落。

## 19. Prompt 注入格式

最终 prompt 应包含：

```text
【参考书吸收规则】
以下内容来自用户授权参考书的结构分析结果。只能学习写法，不得复制原文。

一、全局风格约束
- ...

二、本章适用场景模板
- ...

三、本章节奏建议
- ...

四、本章爽点设计
- ...

五、结尾钩子建议
- ...

六、防照抄要求
- 不得复用参考书人物名、地名、势力名、招式名。
- 不得复用参考书连续桥段组合。
- 不得输出与参考书相似度过高的段落。
```

## 20. 检索策略

检索依据：

- 项目类型。
- 目标平台。
- 当前章节号。
- 当前章节功能。
- 当前章节情绪目标。
- 当前冲突类型。
- 当前人物关系。
- 用户选择的参考书权重。

检索对象：

- `scene_patterns.json`
- `style_bible.md`
- `pacing_rules.md`
- `conflict_models.md`
- `hook_models.md`

排序：

1. 场景匹配度。
2. 平台匹配度。
3. 权重。
4. 质量评分。
5. 最近使用惩罚，避免每章都调用同一种模板。

## 21. 防照抄系统

### 21.1 指纹构建

吸收时构建：

- n-gram 指纹。
- 长句 hash。
- 高频专有名词。
- 场景组合 fingerprint。
- 章节结构 fingerprint。

### 21.2 生成后检测

生成结果按段落切分，检测：

- n-gram 重合率。
- 长句重复。
- 专有名词重合。
- 桥段组合相似。
- embedding 相似度。

### 21.3 处理策略

如果超阈值：

1. 标出可疑段落。
2. 生成重写指令。
3. 要求模型改写：
   - 保留本项目剧情目的。
   - 更换表达方式。
   - 更换场景动作。
   - 更换信息释放顺序。
   - 不使用参考书专有设定。
4. 重新检测。
5. 最多重写 2 次。

### 21.4 报告

生成：

```text
similarity_report.json
```

内容：

- 相似度最高段落编号。
- 来源书籍。
- 来源章节。
- 相似类型。
- 是否自动重写。
- 最终通过状态。

不记录原文。

## 22. 本地 Agent 扩展计划

未来支持云端网站时，需要本地 Agent。

### 22.1 Agent 能力

- 启动本地 HTTP 服务。
- 用户授权文件夹。
- 扫描文件夹。
- 读取白名单文件。
- 写入精华文件。
- 提供本地进度。
- 与云端交换索引和精华。

### 22.2 Agent API

```text
GET  http://127.0.0.1:8765/health
GET  http://127.0.0.1:8765/config
POST http://127.0.0.1:8765/scan
GET  http://127.0.0.1:8765/books
POST http://127.0.0.1:8765/books/{id}/parse
POST http://127.0.0.1:8765/books/{id}/absorb
GET  http://127.0.0.1:8765/books/{id}/essence
```

### 22.3 Agent 安全

- 只监听 `127.0.0.1`。
- 启动时生成本地 token。
- 浏览器连接需 token。
- 用户显式选择目录。
- 不允许远程主机访问。

## 23. 性能设计

### 23.1 大文件处理

- 流式读取。
- offset 索引。
- 不一次性加载整本。
- 章节级处理。
- 长章节自动切块。

### 23.2 缓存

缓存：

- 编码检测结果。
- 章节边界。
- 章节摘要。
- LLM 分析结果。
- 场景模板。
- 相似度指纹。

文件 hash 不变时不重复吸收。

### 23.3 并发

环境变量控制：

```env
REFERENCE_ABSORB_CONCURRENCY=2
```

避免同时处理太多章节导致 API 费用爆炸或本地卡死。

## 24. 失败恢复

必须支持：

- 单章失败不影响整本任务。
- 失败章节记录错误。
- 任务可暂停。
- 任务可恢复。
- 文件变化后只刷新变化部分。
- 精华文件写入使用临时文件 + 原子替换。

## 25. 日志与可观测性

日志文件：

```text
REFERENCE_LOG_DIR/local_library.log
REFERENCE_LOG_DIR/absorption_tasks.log
REFERENCE_LOG_DIR/similarity_guard.log
```

日志不得包含：

- 原文大段内容。
- API Key。
- 用户敏感路径外的文件内容。

后台管理页展示：

- 最近扫描时间。
- 最近吸收时间。
- 总书籍数。
- 已吸收书籍数。
- 失败任务数。
- 精华目录大小。
- 最近错误。

## 26. 权限与多用户

本地单用户模式下：

- 可允许 `user_id nullable`。
- 仍然保留 user_id 字段，方便未来多用户。

多用户模式下：

- 每个用户有自己的本地目录配置。
- 项目只能绑定当前用户可见的参考书。
- 云端模式不暴露本地路径给其他用户。

## 27. 前端视觉和交互要求

保持当前项目风格，避免做成营销页。

界面应偏工具型：

- 信息密度高。
- 表格清晰。
- 进度明确。
- 错误可恢复。
- 按钮状态可靠。

关键状态：

- 未配置。
- 目录不可读。
- 目录不可写。
- 扫描中。
- 解析中。
- 需要审查。
- 吸收中。
- 部分失败。
- 已完成。
- 已绑定项目。

## 28. 测试计划

### 28.1 后端单元测试

新增：

```text
backend/tests/test_local_file_guard.py
backend/tests/test_local_library_scanner.py
backend/tests/test_local_book_parser.py
backend/tests/test_local_absorption_service.py
backend/tests/test_local_essence_writer.py
backend/tests/test_local_reference_context.py
backend/tests/test_similarity_guard.py
```

覆盖：

- 路径白名单。
- 路径穿越拦截。
- 敏感文件拦截。
- txt/md 扫描。
- hash 变更检测。
- GBK/UTF-8 编码识别。
- 中文章节解析。
- 低置信度标记。
- 精华文件写入。
- 项目绑定。
- 生成上下文注入。
- 不把原文注入 prompt。
- 相似度检测触发重写。

### 28.2 前端测试

新增：

```text
frontend/components/local-library/*.test.tsx
```

覆盖：

- 配置面板。
- 扫描报告。
- 书籍列表。
- 章节审查。
- 吸收进度。
- 精华查看。
- 项目绑定。

### 28.3 集成测试

使用测试小说 fixture：

```text
backend/tests/fixtures/reference_books/sample_utf8.txt
backend/tests/fixtures/reference_books/sample_gbk.txt
backend/tests/fixtures/reference_books/sample_markdown.md
```

流程：

1. 创建临时 books 目录。
2. 创建临时 essence 目录。
3. 扫描。
4. 解析。
5. 吸收。
6. 检查精华文件存在。
7. 绑定项目。
8. 预览生成上下文。
9. 检查 prompt 不包含原文大段内容。

## 29. 验收命令

后端：

```powershell
pytest backend/tests/test_local_file_guard.py -q
pytest backend/tests/test_local_library_scanner.py -q
pytest backend/tests/test_local_book_parser.py -q
pytest backend/tests/test_local_absorption_service.py -q
pytest backend/tests/test_local_reference_context.py -q
pytest backend/tests/test_similarity_guard.py -q
pytest backend/tests/test_generation_pipeline.py -q
```

前端：

```powershell
cd frontend
npm run typecheck
npm run test
npm run build
```

全量：

```powershell
pytest backend/tests -q
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

## 30. 人工验收流程

1. 创建：

```text
D:\NovelLibrary\books
D:\NovelLibrary\essence
```

2. 放入三本测试小说：

```text
UTF-8 txt
GBK txt
Markdown
```

3. 在网页配置本地目录。
4. 点击测试目录权限。
5. 点击扫描。
6. 确认发现书籍。
7. 点击解析章节。
8. 检查章节列表。
9. 对低置信度章节做人工修正。
10. 点击完整吸收。
11. 暂停任务。
12. 恢复任务。
13. 模拟单章失败并重试。
14. 查看精华文件。
15. 绑定到项目。
16. 预览生成上下文。
17. 生成章节。
18. 查看相似度报告。
19. 确认生成结果没有复刻参考书。

## 31. 文档交付

新增或更新：

```text
docs/LOCAL_LIBRARY_GUIDE.md
docs/WHOLE_BOOK_ABSORPTION_GUIDE.md
docs/REFERENCE_ESSENCE_FORMAT.md
docs/SIMILARITY_GUARD_GUIDE.md
docs/LOCAL_AGENT_DESIGN.md
README.md
README_zh-CN.md
.env.example
```

文档必须说明：

- 如何配置本地文件夹。
- 如何扫描。
- 如何解析。
- 如何吸收。
- 如何绑定项目。
- 如何处理失败。
- 如何保护版权。
- 如何避免照抄。
- 云端部署为什么不能直接读本地文件夹。

## 32. 实施阶段

这是完整实施阶段，不是简化版本。

### 阶段一：基础设施

- 环境变量。
- 本地目录配置。
- 路径白名单。
- 数据库表。
- API 骨架。
- 前端配置页。

### 阶段二：书库扫描

- 递归扫描。
- hash 计算。
- 文件变更检测。
- 编码识别。
- 扫描报告。
- 书籍列表 UI。

### 阶段三：章节解析

- 中文章节识别。
- 卷识别。
- offset 索引。
- 低置信度审查。
- 前端章节修正。

### 阶段四：精华文件系统

- 精华目录生成。
- manifest。
- 章节摘要文件。
- 卷级摘要文件。
- 原子写入。
- 精华查看 API。

### 阶段五：完整吸收管线

- 章节摘要。
- 章节结构分析。
- 场景模板提取。
- 卷级摘要。
- 全书摘要。
- 风格圣经。
- 节奏规则。
- 冲突模型。
- 人物弧光。
- 钩子模型。
- 平台适配。
- 防照抄规则。

### 阶段六：任务系统

- 后台任务。
- 暂停/恢复/取消。
- 断点续跑。
- 失败重试。
- 进度展示。

### 阶段七：项目绑定与生成接入

- 绑定参考书。
- 权重设置。
- 精华检索。
- 生成上下文预览。
- prompt_builder 接入。
- generation_context_service 接入。

### 阶段八：防照抄检测

- 指纹构建。
- 相似度检测。
- 自动重写。
- 报告输出。
- 前端报告查看。

### 阶段九：本地 Agent 预留与设计

- Agent API 设计文档。
- 后端抽象接口。
- 前端连接状态。
- 云端模式兼容设计。

### 阶段十：测试、文档、发布

- 后端测试。
- 前端测试。
- 集成测试。
- 人工验收。
- 文档。
- 发布检查。

## 33. 交付标准

完成后必须满足：

1. 可以配置本地小说原文文件夹。
2. 可以配置本地精华输出文件夹。
3. 可以扫描多层目录。
4. 可以识别新增、修改、删除书籍。
5. 可以解析章节和卷。
6. 可以人工修正章节边界。
7. 可以完整吸收一本长篇小说。
8. 可以在精华目录生成完整文件结构。
9. 可以在网页查看风格圣经、场景模板、章节摘要。
10. 可以把参考书绑定到具体项目。
11. 可以设置多本参考书权重。
12. 生成章节时能自动调用参考书精华。
13. prompt 不包含大段原文。
14. 生成后能做相似度检测。
15. 相似度过高时能自动重写。
16. 任务可以暂停、恢复、取消、失败重试。
17. 数据库不保存整本小说原文。
18. 后端不能访问白名单外文件。
19. 原有测试全部通过。
20. 文档完整可用。

## 34. 给 Antigravity 的执行要求

执行时必须遵守：

1. 先读现有 `backend/app/database.py`、`generation_context_service.py`、`task_orchestrator.py`、`frontend/lib/api-client.ts` 的模式。
2. 复用现有项目风格，不引入大型新框架。
3. 所有新增功能必须有测试。
4. 不修改 `.env` 真实密钥。
5. 不删除用户数据库和项目文件。
6. 不把原文写进日志。
7. 每个阶段完成后运行对应测试。
8. 每个阶段输出变更摘要。

## 35. 最终一句话设计

原文永远留在用户电脑的“小说原文文件夹”；系统只保存索引和分析结果；吸收后的精华写入“精华输出文件夹”；生成小说时只读取精华规则，不读取和复刻整本原文。
