# 本地文件夹整本小说吸收系统：工程级项目计划

## 0. 文档定位

本文档是 `LOCAL_FOLDER_ABSORPTION_PLAN.md` 的工程实施版，用于指导 Antigravity、Gemini 或其他代码代理按阶段完成完整项目交付。

本计划不是功能愿望清单，而是工程执行计划，包含：

- 阶段准备
- 阶段实施
- 阶段自测
- 阶段复查
- 阶段审查
- 阶段兼容性要求
- 阶段可扩展性要求
- 阶段完成后的小总结模板
- 最终验收标准

执行要求：

1. 不允许一次性实现全部内容。
2. 每个阶段必须通过阶段门禁后才能进入下一阶段。
3. 每个阶段必须保留对前序阶段的兼容性。
4. 每个阶段必须为后续阶段预留接口、数据结构或扩展点。
5. 不得修改 `.env` 中真实密钥。
6. 不得删除用户数据库、小说文件、项目文件。
7. 不得把参考小说原文写入数据库、日志或最终 prompt。

## 1. 项目目标

在现有 `AI_NovelGenerator` 中新增一个完整的“本地文件夹整本小说吸收系统”。

用户在电脑上维护两个文件夹：

```text
小说原文文件夹：存放整本小说 txt/md/epub/docx
精华输出文件夹：存放吸收后的摘要、风格圣经、场景模板、节奏规则、防照抄规则
```

系统能力：

1. 网页配置本地文件夹。
2. 后端安全扫描本地文件。
3. 自动识别小说、章节、卷。
4. 异步吸收整本小说。
5. 输出结构化精华文件。
6. 项目绑定参考书精华。
7. 章节生成时自动调用精华规则。
8. 生成后执行相似度检查和自动重写。
9. 为未来云端网页 + 本地 Agent 模式预留接口。

## 2. 工程原则

### 2.1 交付原则

- 每个阶段必须能独立运行、独立测试、独立回滚。
- 每个阶段只实现本阶段范围内的功能。
- 不做无关重构。
- 不破坏现有生成、项目、状态、记忆、备份系统。
- 后端先于前端，接口契约先于交互美化。
- 安全边界先于功能便利。

### 2.2 数据原则

- 数据库只保存索引、状态、路径、hash、统计信息。
- 原文只保留在用户本地原文文件夹。
- 精华写入用户指定精华文件夹。
- prompt 只读取精华规则，不读取整本原文。
- 日志不记录原文内容。

### 2.3 测试原则

每阶段至少包含：

- 单元测试
- 关键 API 测试
- 回归测试
- 阶段验收命令

涉及前端时，还必须包含：

- `npm run typecheck`
- `npm run build`

## 3. 总体阶段图

```text
阶段 0：基线审计与准备
阶段 1：架构契约冻结
阶段 2：本地目录配置与安全文件守卫
阶段 3：数据库迁移与索引模型
阶段 4：本地书库扫描
阶段 5：章节/卷解析
阶段 6：精华文件系统
阶段 7：异步任务系统
阶段 8：整本吸收分析管线
阶段 9：前端本地书库管理页
阶段 10：项目绑定与生成上下文接入
阶段 11：防照抄与自动重写
阶段 12：本地 Agent 兼容抽象
阶段 13：全量回归、文档和发布验收
```

## 4. 阶段通用门禁

每个阶段结束前必须输出阶段小结。

### 4.1 阶段小结模板

```markdown
## 阶段 X 小结

### 已完成
- ...

### 修改文件
- ...

### 新增测试
- ...

### 验收命令
- 命令：
- 结果：

### 兼容性检查
- 对前序阶段：
- 对现有项目：

### 为后续阶段预留
- ...

### 风险与遗留
- ...

### 是否允许进入下一阶段
- 是/否
```

### 4.2 阶段复查清单

每个阶段结束后，执行者必须自查：

- 是否超出本阶段范围。
- 是否改动无关文件。
- 是否引入未使用的大型依赖。
- 是否破坏现有测试。
- 是否泄露原文、路径或密钥。
- 是否有足够测试覆盖。
- 是否有清晰错误处理。
- 是否保留向后兼容。

### 4.3 阶段审查清单

审查者必须检查：

- 接口是否稳定。
- 数据结构是否能支持后续阶段。
- 安全边界是否足够。
- 失败场景是否可恢复。
- 日志是否安全。
- UI 是否暴露不可用功能。
- 文档是否跟代码一致。

## 5. 阶段 0：基线审计与准备

### 5.1 阶段目标

确认当前项目健康状态，避免在未知状态上开发。

### 5.2 阶段准备

阅读文件：

```text
README.md
README_zh-CN.md
STATUS.md
backend/app/main.py
backend/app/database.py
backend/app/services/generation_context_service.py
backend/app/services/task_orchestrator.py
frontend/lib/api-client.ts
frontend/lib/types/index.ts
```

运行基线命令：

```powershell
pytest backend/tests -q
cd frontend
npm run typecheck
npm run build
```

### 5.3 实施任务

1. 记录当前测试结果。
2. 记录当前未提交文件。
3. 识别与本功能相关的现有模块。
4. 确认 `.env.example`、`.gitignore`、`pytest.ini` 是否需要准备性修复。
5. 不实现任何新功能。

### 5.4 阶段复查

- 本阶段不能新增业务模块。
- 本阶段不能修改数据库结构。
- 本阶段不能改生成逻辑。

### 5.5 阶段审查

审查输出：

- 当前项目是否可作为开发基线。
- 哪些现有测试必须作为每阶段回归测试。
- 哪些文件存在用户未提交改动，后续不得覆盖。

### 5.6 兼容性要求

本阶段不应改变现有功能行为。

### 5.7 为后续阶段预留

输出一份“基线报告”，供后续阶段对比。

## 6. 阶段 1：架构契约冻结

### 6.1 阶段目标

在写大量代码前，冻结核心接口、数据模型和模块边界。

### 6.2 阶段准备

阅读：

```text
LOCAL_FOLDER_ABSORPTION_PLAN.md
backend/app/routes/
backend/app/services/
frontend/components/project/
```

### 6.3 实施任务

1. 新增工程设计文档或补充本文档中的接口契约。
2. 定义后端模块边界：
   - `local_library_config`
   - `local_file_guard`
   - `local_library_scanner`
   - `local_book_parser_service`
   - `local_essence_writer_service`
   - `local_absorption_service`
   - `local_reference_context_service`
   - `local_similarity_guard_service`
3. 定义 API 路由前缀：
   - `/api/v1/local-library/config`
   - `/api/v1/local-library/scan`
   - `/api/v1/local-library/books`
   - `/api/v1/projects/{project_id}/local-reference-books`
   - `/api/v1/projects/{project_id}/reference-context/preview`
4. 定义前端页面：
   - `frontend/app/local-library/page.tsx`
   - `frontend/components/project/LocalLibraryTab.tsx`
5. 定义 feature flag：
   - `ALLOW_LOCAL_FILE_ACCESS`
   - `REFERENCE_ENABLE_AGENT`
6. 定义精华文件 schema version。

### 6.4 阶段复查

- API 命名是否和现有项目风格一致。
- 数据结构是否支持 txt/md/epub/docx。
- 是否给未来本地 Agent 留出抽象层。

### 6.5 阶段审查

必须确认：

- 原文不会进入数据库。
- 生成上下文接入点清晰。
- 防照抄接入点清晰。
- 前端不会依赖本地绝对路径做安全判断，安全判断必须在后端。

### 6.6 兼容性要求

新增接口不得影响现有 `/api/v1/projects`、`/api/v1/generate`、State Patch 流程。

### 6.7 为后续阶段预留

接口先定义返回结构，即使部分字段暂时为空，也要稳定。

## 7. 阶段 2：本地目录配置与安全文件守卫

### 7.1 阶段目标

实现安全访问本地文件夹的基础能力。

### 7.2 阶段准备

准备测试目录：

```text
tmp/reference_books
tmp/reference_essence
tmp/reference_cache
tmp/reference_logs
```

准备恶意路径用例：

```text
..\..\.env
C:\Windows\System32
白名单目录外文件
软链接跳出目录
敏感扩展名文件
```

### 7.3 实施任务

1. 新增 `local_library_config.py`。
2. 新增 `local_file_guard.py`。
3. 支持环境变量读取：
   - `REFERENCE_BOOKS_DIR`
   - `REFERENCE_ESSENCE_DIR`
   - `REFERENCE_CACHE_DIR`
   - `REFERENCE_LOG_DIR`
   - `REFERENCE_MAX_FILE_MB`
   - `REFERENCE_ALLOWED_EXTENSIONS`
4. 实现路径解析和白名单校验。
5. 实现敏感文件拦截。
6. 实现目录读写能力检测。
7. 新增配置 API：
   - `GET /api/v1/local-library/config`
   - `PUT /api/v1/local-library/config`
   - `POST /api/v1/local-library/config/test`

### 7.4 新增测试

```text
backend/tests/test_local_file_guard.py
backend/tests/test_local_library_config.py
```

测试覆盖：

- 白名单内路径允许。
- 白名单外路径拒绝。
- `..` 路径拒绝。
- 敏感扩展名拒绝。
- 目录不存在时返回明确错误。
- 可读不可写状态可被检测。

### 7.5 验收命令

```powershell
pytest backend/tests/test_local_file_guard.py backend/tests/test_local_library_config.py -q
pytest backend/tests/test_health_and_export.py -q
```

### 7.6 阶段复查

- 是否所有文件访问都经过 `local_file_guard`。
- 是否没有在路由中直接拼路径。
- 是否错误信息不暴露敏感内容。

### 7.7 阶段审查

重点审查安全边界。

必须确认：

- 后续扫描、解析、写入都能复用该 guard。
- 文件路径判断在 Windows 下可靠。

### 7.8 兼容性要求

如果 `ALLOW_LOCAL_FILE_ACCESS=false`，所有本地书库接口应返回明确禁用状态，不影响主站其他功能。

### 7.9 为后续阶段预留

`local_file_guard` 必须提供统一方法：

```python
resolve_source_path(...)
resolve_essence_path(...)
assert_read_allowed(...)
assert_write_allowed(...)
```

## 8. 阶段 3：数据库迁移与索引模型

### 8.1 阶段目标

增加本地书库索引表，不保存原文。

### 8.2 阶段准备

阅读：

```text
backend/app/database.py
backend/tests/test_migrations.py
```

确认现有 schema_version 机制。

### 8.3 实施任务

新增表：

```text
local_library_config
local_reference_book
local_reference_volume
local_reference_chapter
local_reference_analysis
local_reference_scene_pattern
project_reference_binding
reference_absorption_task
```

实现迁移：

- 从 version 1 到 version 2。
- 幂等执行。
- 旧数据库平滑升级。

### 8.4 新增测试

```text
backend/tests/test_local_library_migrations.py
```

覆盖：

- 新库初始化。
- 旧库迁移。
- 重复 init 不报错。
- 表结构存在。
- 不破坏原有表。

### 8.5 验收命令

```powershell
pytest backend/tests/test_migrations.py backend/tests/test_local_library_migrations.py -q
pytest backend/tests/test_project_routes.py -q
```

### 8.6 阶段复查

- 是否误删旧表。
- 是否在迁移中读取本地文件。
- 是否字段足够支持后续阶段。

### 8.7 阶段审查

必须确认：

- 不保存原文内容字段。
- `project_reference_binding` 能支持多书、多权重、多开关。
- 任务表能支持暂停、恢复、取消、重试。

### 8.8 兼容性要求

旧数据库启动后应自动迁移，不影响现有项目列表、章节、用户登录。

### 8.9 为后续阶段预留

表中保留：

- `source_encoding`
- `parse_confidence`
- `manifest_path`
- `error_message`
- `prompt_version`
- `schema_version`

## 9. 阶段 4：本地书库扫描

### 9.1 阶段目标

扫描小说原文文件夹，建立书籍索引。

### 9.2 阶段准备

准备 fixture：

```text
sample_utf8.txt
sample_gbk.txt
sample_markdown.md
large_sample.txt
ignored.env
ignored.db
```

### 9.3 实施任务

1. 新增 `local_library_scanner.py`。
2. 支持递归扫描。
3. 支持扩展名白名单。
4. 计算文件 sha256、大小、mtime。
5. 识别新增、修改、删除、未变化。
6. 识别编码：
   - UTF-8
   - UTF-8 BOM
   - GB18030
   - Big5
7. 更新 `local_reference_book`。
8. 新增 API：
   - `POST /api/v1/local-library/scan`
   - `GET /api/v1/local-library/books`
   - `GET /api/v1/local-library/books/{book_id}`

### 9.4 新增测试

```text
backend/tests/test_local_library_scanner.py
```

覆盖：

- 扫描新文件。
- 修改文件后状态更新。
- 删除文件后状态更新。
- 敏感文件忽略。
- 编码识别。
- 大文件上限。

### 9.5 验收命令

```powershell
pytest backend/tests/test_local_library_scanner.py -q
pytest backend/tests/test_local_file_guard.py -q
```

### 9.6 阶段复查

- 扫描是否只读。
- 是否没有把正文写入数据库。
- hash 是否用于变更检测。

### 9.7 阶段审查

重点审查：

- 扫描大量文件时是否可控。
- 错误文件是否不会中断整个扫描。

### 9.8 兼容性要求

扫描失败不得影响现有项目页面和生成流程。

### 9.9 为后续阶段预留

扫描结果必须能驱动：

- 解析任务。
- 吸收任务。
- 增量刷新。

## 10. 阶段 5：章节/卷解析

### 10.1 阶段目标

从整本小说文件中识别章节和卷，并记录 offset。

### 10.2 阶段准备

准备多种标题格式：

```text
第1章
第001章
第一章
第一回
卷一
第一卷
楔子
序章
番外
Chapter 1
CHAPTER I
```

### 10.3 实施任务

1. 新增 `local_chapter_boundary_service.py`。
2. 新增 `local_book_parser_service.py`。
3. 按编码流式读取文件。
4. 识别卷和章节。
5. 记录起止 offset。
6. 计算章节字数。
7. 计算解析置信度。
8. 低置信度标记 `needs_review`。
9. 新增 API：
   - `POST /api/v1/local-library/books/{book_id}/parse`
   - `GET /api/v1/local-library/books/{book_id}/chapters`
   - `PATCH /api/v1/local-library/books/{book_id}/chapters/{chapter_id}`
   - `POST /api/v1/local-library/books/{book_id}/chapters/rebuild`

### 10.4 新增测试

```text
backend/tests/test_local_book_parser.py
```

覆盖：

- 中文章节识别。
- 卷识别。
- 序章/番外识别。
- offset 正确。
- 低置信度标记。
- 手动修正章节。
- 重建章节索引。

### 10.5 验收命令

```powershell
pytest backend/tests/test_local_book_parser.py -q
pytest backend/tests/test_local_library_scanner.py -q
```

### 10.6 阶段复查

- 是否处理超长章节。
- 是否避免一次性加载巨大文件。
- 是否支持用户修正结果。

### 10.7 阶段审查

必须确认：

- 后续吸收服务可以按 offset 读取单章。
- 章节解析失败不会破坏书籍索引。

### 10.8 兼容性要求

已扫描但未解析的书仍应能正常展示。

### 10.9 为后续阶段预留

章节记录必须包含：

- summary_path
- analysis_path
- scene_patterns_path

供精华写入阶段使用。

## 11. 阶段 6：精华文件系统

### 11.1 阶段目标

建立精华目录结构和原子写入机制。

### 11.2 阶段准备

准备测试 essence 目录，并模拟：

- 目录不存在。
- 目录不可写。
- 文件已存在。
- 写入中断。

### 11.3 实施任务

1. 新增 `local_essence_writer_service.py`。
2. 为每本书生成 slug 目录。
3. 写入 `manifest.json`。
4. 写入章节摘要目录。
5. 写入分析目录。
6. 支持临时文件 + 原子替换。
7. 支持精华文件读取 API：
   - `GET /api/v1/local-library/books/{book_id}/essence`
   - `GET /api/v1/local-library/books/{book_id}/essence/{file_key}`

### 11.4 新增测试

```text
backend/tests/test_local_essence_writer.py
```

覆盖：

- slug 生成。
- manifest 写入。
- 原子写入。
- 路径白名单。
- 不写入原文目录。
- 读取精华文件。

### 11.5 验收命令

```powershell
pytest backend/tests/test_local_essence_writer.py -q
pytest backend/tests/test_local_file_guard.py -q
```

### 11.6 阶段复查

- 写入是否全部经过 guard。
- manifest 是否带 schema_version。
- 文件是否统一 UTF-8。

### 11.7 阶段审查

必须确认：

- 后续吸收任务可以增量写入。
- 失败写入不会留下半截文件。

### 11.8 兼容性要求

旧 manifest 版本未来可升级，不影响读取。

### 11.9 为后续阶段预留

manifest 必须保留：

- `files`
- `generated_at`
- `source_hash`
- `schema_version`
- `absorb_status`

## 12. 阶段 7：异步任务系统

### 12.1 阶段目标

支持长时间吸收任务的启动、暂停、恢复、取消、失败重试和进度展示。

### 12.2 阶段准备

阅读现有：

```text
backend/app/services/task_orchestrator.py
novel_generator/task_manager.py
novel_generator/cancel_token.py
backend/app/routes/generation.py
```

### 12.3 实施任务

1. 新增或复用任务调度机制。
2. 任务类型：
   - scan
   - parse
   - summarize_chapters
   - build_style_bible
   - extract_scene_patterns
   - build_similarity_index
   - full_absorb
3. 支持状态：
   - queued
   - running
   - paused
   - completed
   - partial
   - failed
   - cancelled
4. 新增 API：
   - `POST /api/v1/local-library/books/{book_id}/absorb`
   - `POST /api/v1/local-library/books/{book_id}/absorb/pause`
   - `POST /api/v1/local-library/books/{book_id}/absorb/resume`
   - `POST /api/v1/local-library/books/{book_id}/absorb/cancel`
   - `POST /api/v1/local-library/books/{book_id}/absorb/retry-failed`
5. 支持断点续跑。
6. 记录任务进度。

### 12.4 新增测试

```text
backend/tests/test_local_absorption_tasks.py
```

覆盖：

- 创建任务。
- 更新进度。
- 暂停。
- 恢复。
- 取消。
- 失败重试。
- 断点续跑。

### 12.5 验收命令

```powershell
pytest backend/tests/test_local_absorption_tasks.py -q
pytest backend/tests/test_task_manager.py -q
```

### 12.6 阶段复查

- 任务状态是否持久化。
- 重启后是否可恢复。
- 取消是否及时生效。

### 12.7 阶段审查

必须确认：

- 不会阻塞 FastAPI 主线程。
- 任务失败不会污染已完成精华文件。

### 12.8 兼容性要求

不得破坏现有章节生成任务。

### 12.9 为后续阶段预留

任务系统必须能挂载后续 LLM 分析步骤。

## 13. 阶段 8：整本吸收分析管线

### 13.1 阶段目标

实现从整本小说到精华文件的完整分析流程。

### 13.2 阶段准备

准备 mock LLM，避免测试消耗真实 API。

阅读：

```text
llm_adapters.py
backend/tests/mock_llm.py
novel_generator/prompts/
```

### 13.3 实施任务

新增：

```text
local_absorption_service.py
local_style_mining_service.py
local_scene_pattern_service.py
```

实现分析步骤：

1. 章节摘要。
2. 章节结构分析。
3. 场景切分。
4. 场景模板提取。
5. 卷级摘要。
6. 全书摘要。
7. 人物弧光。
8. 冲突模型。
9. 节奏模型。
10. 钩子模型。
11. 风格圣经。
12. 平台适配。
13. 防照抄规则。

### 13.4 输出文件

必须输出：

```text
book_summary.md
style_bible.md
plot_structure.md
pacing_rules.md
conflict_models.md
character_arcs.md
hook_models.md
scene_patterns.json
platform_adaptation.md
anti_copy_rules.md
quality_report.md
chapter_summaries/
chapter_analysis/
volume_summaries/
```

### 13.5 新增测试

```text
backend/tests/test_local_absorption_service.py
backend/tests/test_local_style_mining_service.py
backend/tests/test_local_scene_pattern_service.py
```

覆盖：

- mock LLM 分析成功。
- 单章失败不中断全书。
- 输出文件齐全。
- 不输出原文大段内容。
- JSON 结构合法。
- 可断点续跑。

### 13.6 验收命令

```powershell
pytest backend/tests/test_local_absorption_service.py backend/tests/test_local_style_mining_service.py backend/tests/test_local_scene_pattern_service.py -q
pytest backend/tests/test_llm_adapters.py -q
```

### 13.7 阶段复查

- prompt 是否要求“只提炼写法，不复刻原文”。
- 输出是否含大段原文。
- 长书是否按章节分块处理。

### 13.8 阶段审查

必须确认：

- 结果能被后续生成上下文读取。
- mock 测试不依赖真实 API。
- 真实 LLM 冒烟测试可选且默认跳过。

### 13.9 兼容性要求

LLM 失败不应影响已有项目生成。

### 13.10 为后续阶段预留

分析结果必须支持多书合并检索和权重排序。

## 14. 阶段 9：前端本地书库管理页

### 14.1 阶段目标

提供完整网页操作体验。

### 14.2 阶段准备

阅读当前 UI 风格：

```text
frontend/app/page.tsx
frontend/components/project/
frontend/components/ui/
frontend/lib/api-client.ts
```

### 14.3 实施任务

新增页面：

```text
frontend/app/local-library/page.tsx
```

新增组件：

```text
LibraryConfigPanel.tsx
LibraryScanPanel.tsx
BookListTable.tsx
BookDetailDrawer.tsx
ChapterBoundaryReview.tsx
AbsorptionProgressPanel.tsx
EssenceViewer.tsx
StyleBibleViewer.tsx
ScenePatternBrowser.tsx
ProjectBindingPanel.tsx
SimilarityGuardReport.tsx
```

实现功能：

1. 配置目录。
2. 测试权限。
3. 扫描。
4. 查看书籍。
5. 解析章节。
6. 修正章节。
7. 启动吸收。
8. 暂停/恢复/取消。
9. 查看精华。
10. 查看失败信息。

### 14.4 新增测试

```text
frontend/components/local-library/*.test.tsx
```

### 14.5 验收命令

```powershell
cd frontend
npm run typecheck
npm run test
npm run build
```

### 14.6 阶段复查

- UI 是否暴露未实现功能。
- 按钮禁用状态是否正确。
- 错误是否中文可读。
- 窄屏是否不重叠。

### 14.7 阶段审查

必须确认：

- 前端不绕过后端安全校验。
- 所有危险操作都有确认。

### 14.8 兼容性要求

新增页面不影响现有项目页、登录页、设置页。

### 14.9 为后续阶段预留

组件应支持后续加入本地 Agent 状态。

## 15. 阶段 10：项目绑定与生成上下文接入

### 15.1 阶段目标

让已吸收精华真正参与章节生成。

### 15.2 阶段准备

阅读：

```text
backend/app/services/generation_context_service.py
novel_generator/chapter_pipeline/prompt_builder.py
backend/app/routes/generation.py
frontend/components/project/GenerationTab.tsx
frontend/components/project/workbench/
```

### 15.3 实施任务

1. 新增 `local_reference_context_service.py`。
2. 实现项目绑定 API：
   - `GET /api/v1/projects/{project_id}/local-reference-books`
   - `POST /api/v1/projects/{project_id}/local-reference-books/{book_id}/attach`
   - `PATCH /api/v1/projects/{project_id}/local-reference-books/{book_id}`
   - `DELETE /api/v1/projects/{project_id}/local-reference-books/{book_id}`
3. 实现生成上下文预览：
   - `GET /api/v1/projects/{project_id}/reference-context/preview`
4. 根据当前章节目标检索：
   - style_bible
   - scene_patterns
   - pacing_rules
   - conflict_models
   - hook_models
   - anti_copy_rules
5. 修改 prompt builder，加入“参考书吸收规则”区块。
6. 前端项目页增加参考书绑定入口。

### 15.4 新增测试

```text
backend/tests/test_local_reference_binding.py
backend/tests/test_local_reference_context.py
```

覆盖：

- 绑定一本书。
- 绑定多本书。
- 权重排序。
- 禁用某本书。
- 预览上下文。
- prompt 不包含原文大段内容。
- 未绑定时生成流程不变。

### 15.5 验收命令

```powershell
pytest backend/tests/test_local_reference_binding.py backend/tests/test_local_reference_context.py -q
pytest backend/tests/test_generation_pipeline.py -q
cd frontend
npm run typecheck
npm run build
```

### 15.6 阶段复查

- 生成上下文是否过长。
- 是否只读取精华文件。
- 是否尊重项目绑定开关。

### 15.7 阶段审查

重点审查：

- 原有生成流程是否兼容。
- State Patch 和 memory 机制是否未被绕过。
- pending_review 是否仍不进入生成上下文。

### 15.8 兼容性要求

没有绑定参考书时，生成行为应与旧版本一致。

### 15.9 为后续阶段预留

上下文服务必须支持：

- 多书权重。
- 最近使用惩罚。
- 场景匹配。
- 平台匹配。

## 16. 阶段 11：防照抄与自动重写

### 16.1 阶段目标

降低生成内容与参考书高度相似的风险。

### 16.2 阶段准备

准备测试文本：

- 与参考书高度相似段落。
- 改写后低相似段落。
- 专有名词重复段落。
- 正常原创段落。

### 16.3 实施任务

1. 新增 `local_similarity_guard_service.py`。
2. 构建指纹：
   - n-gram
   - 长句 hash
   - 专有名词
   - 场景组合 fingerprint
3. 生成后检测：
   - n-gram 重合率
   - 长句重复
   - 专有名词重合
   - embedding 相似度预留
4. 超阈值时自动生成重写指令。
5. 最多重写 2 次。
6. 输出 `similarity_report.json`。
7. 前端展示报告。

### 16.4 新增测试

```text
backend/tests/test_similarity_guard.py
```

覆盖：

- 相似段落命中。
- 正常段落通过。
- 专有名词过多命中。
- 自动重写调用。
- 报告不包含原文。

### 16.5 验收命令

```powershell
pytest backend/tests/test_similarity_guard.py -q
pytest backend/tests/test_generation_pipeline.py -q
```

### 16.6 阶段复查

- 阈值是否可配置。
- 是否误伤过多。
- 是否泄露原文。

### 16.7 阶段审查

必须确认：

- Similarity Guard 是生成后检查，不改变参考书精华。
- 检测失败时有安全默认策略。

### 16.8 兼容性要求

未启用参考书或未启用防照抄时，旧生成流程不受影响。

### 16.9 为后续阶段预留

接口预留 embedding 相似度实现。

## 17. 阶段 12：本地 Agent 兼容抽象

### 17.1 阶段目标

为未来“云端网页 + 本地 Agent”模式预留工程接口。

### 17.2 阶段准备

不要实现完整 Agent，先抽象访问层。

### 17.3 实施任务

1. 抽象 `LocalLibraryBackend` 接口。
2. 当前实现为 `DirectLocalLibraryBackend`。
3. 预留 `AgentLocalLibraryBackend`。
4. 新增 Agent 设计文档：
   - `docs/LOCAL_AGENT_DESIGN.md`
5. 前端增加 Agent 状态字段但默认隐藏或禁用。

### 17.4 新增测试

```text
backend/tests/test_local_library_backend_contract.py
```

### 17.5 验收命令

```powershell
pytest backend/tests/test_local_library_backend_contract.py -q
pytest backend/tests/test_local_library_scanner.py -q
```

### 17.6 阶段复查

- 是否没有引入未完成 Agent 误导用户。
- 是否不破坏本地模式。

### 17.7 阶段审查

确认未来云端模式可以复用：

- 扫描结果结构。
- 书籍索引结构。
- 精华读取结构。
- 任务状态结构。

### 17.8 兼容性要求

默认仍使用本地后端直接访问模式。

### 17.9 为后续阶段预留

Agent API 草案：

```text
GET  /health
GET  /config
POST /scan
GET  /books
POST /books/{id}/parse
POST /books/{id}/absorb
GET  /books/{id}/essence
```

## 18. 阶段 13：全量回归、文档和发布验收

### 18.1 阶段目标

确认完整系统可交付。

### 18.2 阶段准备

准备真实验收目录：

```text
D:\NovelLibrary\books
D:\NovelLibrary\essence
```

准备三类测试小说：

- UTF-8 txt。
- GBK txt。
- Markdown。

### 18.3 实施任务

1. 更新文档：
   - `docs/LOCAL_LIBRARY_GUIDE.md`
   - `docs/WHOLE_BOOK_ABSORPTION_GUIDE.md`
   - `docs/REFERENCE_ESSENCE_FORMAT.md`
   - `docs/SIMILARITY_GUARD_GUIDE.md`
   - `docs/LOCAL_AGENT_DESIGN.md`
   - `README.md`
   - `README_zh-CN.md`
   - `.env.example`
2. 运行全量测试。
3. 手工验收完整流程。
4. 输出发布报告。

### 18.4 全量验收命令

```powershell
pytest backend/tests -q
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

### 18.5 人工验收流程

1. 配置本地目录。
2. 测试目录权限。
3. 扫描文件夹。
4. 解析三本书。
5. 修正低置信度章节。
6. 启动完整吸收。
7. 暂停任务。
8. 恢复任务。
9. 重试失败章节。
10. 查看精华文件。
11. 绑定参考书到项目。
12. 预览生成上下文。
13. 生成章节。
14. 查看相似度报告。
15. 确认没有大段复刻。
16. 确认关闭参考书后生成流程仍可用。

### 18.6 阶段复查

- 文档是否与代码一致。
- 所有新增功能是否可关闭。
- 所有测试是否通过。
- 是否存在明显性能问题。

### 18.7 阶段审查

发布前必须确认：

- 不保存原文到数据库。
- 不泄露原文到日志。
- 不越权访问本地文件。
- 不破坏原有项目。
- 有明确回滚方式。

### 18.8 最终交付物

```text
后端模块
前端页面
数据库迁移
测试用例
文档
发布报告
人工验收记录
```

## 19. 横向兼容性矩阵

| 能力 | 对现有系统影响 | 兼容策略 |
|---|---|---|
 本地配置 | 新增 | feature flag 关闭时无影响 |
 书库扫描 | 新增 | 只读本地白名单目录 |
 数据库迁移 | 修改 | 幂等迁移，保留旧表 |
 章节解析 | 新增 | 不影响项目章节 |
 精华写入 | 新增 | 只写 essence 目录 |
 吸收任务 | 新增 | 不复用生成任务状态字段，避免污染 |
 生成上下文 | 修改 | 无绑定参考书时保持旧行为 |
 Prompt Builder | 修改 | 新增可选区块 |
 防照抄 | 新增/可选 | 默认可配置开关 |
 前端页面 | 新增 | 不影响现有路由 |

## 20. 可扩展性矩阵

| 后续能力 | 当前阶段必须预留 |
|---|---|
 epub/docx | 文件类型、解析器接口 |
 本地 Agent | `LocalLibraryBackend` 抽象 |
 多书权重 | `project_reference_binding.weight` |
 多用户 | user_id nullable 但保留 |
 向量检索 | embeddings 目录和 scene vector 字段 |
 云端同步 | manifest schema_version |
 增量吸收 | source_hash、mtime、chapter offset |
 自动整理书库 | 写入权限独立开关 |
 可视化曲线 | emotional_curve_json |
 平台化适配 | platform_adaptation.md |

## 21. 最终验收标准

项目完成时必须满足：

1. 可以配置小说原文文件夹。
2. 可以配置精华输出文件夹。
3. 可以安全扫描多层目录。
4. 可以识别新增、修改、删除小说。
5. 可以识别 UTF-8、GB18030、Big5。
6. 可以解析章节、卷、序章、番外。
7. 可以人工修正章节边界。
8. 可以完整吸收长篇小说。
9. 可以生成完整精华目录。
10. 可以查看风格圣经、场景模板、章节摘要。
11. 可以暂停、恢复、取消、重试吸收任务。
12. 可以把多本参考书绑定到项目。
13. 可以设置参考书权重。
14. 可以预览生成上下文。
15. 生成时只注入精华规则。
16. prompt 不包含大段原文。
17. 生成后可以进行相似度检测。
18. 相似度过高可以自动重写。
19. 数据库不保存整本原文。
20. 日志不保存原文。
21. 后端不能访问白名单外文件。
22. 关闭本地书库功能后旧系统照常运行。
23. 全量后端测试通过。
24. 前端 lint/typecheck/test/build 通过。
25. 文档完整。

## 22. 给执行模型的工作方式

推荐给 Antigravity/Gemini 的执行提示词：

```text
请读取 LOCAL_FOLDER_ABSORPTION_ENGINEERING_PLAN.md。
当前只执行阶段 X。

要求：
1. 只实现阶段 X 范围内任务。
2. 不提前实现后续阶段。
3. 不改无关文件。
4. 不覆盖用户已有修改。
5. 新增必要测试。
6. 运行本阶段验收命令。
7. 输出阶段小结，严格使用文档模板。
8. 明确说明是否允许进入下一阶段。
```

## 23. 关键工程判断

这个项目不能靠一个大 prompt 一口气完成。正确做法是：

```text
小阶段实现
阶段内自测
阶段复查
阶段审查
保留兼容
再进入下一阶段
```

这样即使由 Gemini Flash 类模型执行，也能通过工程门禁降低失控风险。
