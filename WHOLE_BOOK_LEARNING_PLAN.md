# 整本小说吸收系统计划：Whole Book Learning

## 0. 给 Antigravity 的总提示词

请在 `D:\Personal\Desktop\plan\AI_NovelGenerator` 中设计并实现“整本小说吸收系统”。目标是让用户可以上传整本小说，系统自动解析章节、提炼结构、学习写法、沉淀风格规则，并在后续生成小说时调用这些规则提升质量。

注意：系统不得以复制原文为目标。上传内容必须限定为用户拥有版权、已获授权或公版作品。生成时只允许注入“分析结果、结构规则、风格标签、场景模板、节奏模式”，不得把大段原文塞进最终 prompt。

## 1. 产品目标

把当前项目升级为一个强大的网页类小说创作平台，新增能力：

1. 整本小说上传。
2. 自动章节识别。
3. 自动拆解剧情结构。
4. 自动提炼写作风格。
5. 自动生成风格圣经。
6. 自动建立场景/爽点/节奏/人物弧光索引。
7. 生成新章节时自动检索可参考的写法规则。
8. 增加防照抄检测，避免输出接近原文。

## 2. 系统分层

### 第一层：原始书库 Book Library

用于保存用户上传的整本小说文件和解析状态。

支持格式优先级：

1. `.txt`
2. `.md`
3. `.epub`
4. `.docx`

建议第一版先做 `.txt` 和 `.md`，第二版再加 `.epub` 和 `.docx`。

### 第二层：章节解析 Chapter Parser

自动识别章节边界：

- `第1章`
- `第一章`
- `Chapter 1`
- `卷一`
- `楔子`
- `序章`
- `番外`

每章保存：

- chapter_index
- title
- raw_text_path
- word_count
- parse_confidence
- detected_volume

如果识别失败，前端允许用户手动修正章节边界。

### 第三层：分层摘要 Hierarchical Summary

不能把整本小说一次性喂给模型。必须分层吸收：

1. 章节级摘要：每章 300-800 字。
2. 卷级摘要：每 20-50 章合并一次。
3. 全书摘要：主题、主线、人物弧光、高潮、结局。
4. 结构图谱：主线、支线、伏笔、反转、爽点、情绪曲线。

### 第四层：写法提炼 Style Mining

对每章或抽样章节提炼：

- 开篇钩子方式。
- 冲突引入方式。
- 爽点铺垫方式。
- 爽点释放方式。
- 反派压迫方式。
- 主角高光方式。
- 对话推进方式。
- 信息释放密度。
- 章节结尾钩子。
- 场景转换方式。
- 叙述节奏。
- 常用句式特征。
- 禁忌：哪些写法不能直接模仿或照抄。

输出不是原文，而是规则。

### 第五层：场景模板 Scene Pattern Index

把整本书拆成可检索的“写法模板”：

- 被羞辱后反击。
- 试炼/比赛/考核。
- 秘境探索。
- 宗门压迫。
- 身份揭露。
- 旧敌重逢。
- 关系破裂。
- 情绪爆发。
- 战斗升级。
- 结尾反转。

每个模板保存：

- scene_type
- emotional_curve
- conflict_pattern
- pacing_pattern
- useful_rules
- source_book_id
- source_chapter_range
- no_copy_warning

### 第六层：风格圣经 Style Bible

为每本上传小说生成一份可读的 `style_bible.md`：

内容包括：

1. 全书定位。
2. 目标读者感受。
3. 节奏模型。
4. 冲突模型。
5. 爽点模型。
6. 人物塑造模型。
7. 章节结构模型。
8. 结尾钩子模型。
9. 可模仿写法。
10. 禁止照抄规则。

## 3. 数据库设计建议

新增表：

### `reference_book`

- id
- user_id
- project_id nullable
- title
- author_label
- source_type
- file_path
- copyright_status
- parse_status
- total_chapters
- total_words
- created_at
- updated_at

### `reference_book_chapter`

- id
- book_id
- chapter_index
- title
- volume_title
- text_path
- word_count
- summary
- analysis_status
- created_at
- updated_at

### `reference_book_analysis`

- id
- book_id
- analysis_type
- content_json
- content_markdown
- model_profile_id nullable
- created_at

analysis_type 可选：

- `book_summary`
- `volume_summary`
- `style_bible`
- `character_arc`
- `plot_structure`
- `scene_patterns`
- `pacing_curve`

### `reference_scene_pattern`

- id
- book_id
- chapter_id nullable
- scene_type
- tags_json
- emotional_curve
- conflict_pattern
- pacing_pattern
- reusable_rules
- source_excerpt_hash
- created_at

注意：`source_excerpt_hash` 只用于相似度和防照抄检测，不在生成 prompt 中展示原文。

## 4. 后端模块建议

新增文件：

- `backend/app/routes/reference_books.py`
- `backend/app/services/reference_book_service.py`
- `backend/app/services/book_parser_service.py`
- `backend/app/services/book_absorption_service.py`
- `backend/app/services/style_mining_service.py`
- `backend/app/services/scene_pattern_service.py`
- `backend/app/services/similarity_guard_service.py`

接入现有模块：

- 在 `backend/app/main.py` 注册 `reference_books.router`。
- 在 `backend/app/database.py` 增加 schema/migration。
- 在 `backend/app/services/generation_context_service.py` 增加“参考书规则上下文”。
- 在 `novel_generator/chapter_pipeline/prompt_builder.py` 中加入风格规则区域。

## 5. API 设计

### 上传整本小说

`POST /api/v1/reference-books/upload`

FormData:

- file
- title
- copyright_status
- project_id optional

### 获取书库

`GET /api/v1/reference-books`

### 获取书籍详情

`GET /api/v1/reference-books/{book_id}`

### 启动解析

`POST /api/v1/reference-books/{book_id}/parse`

### 启动吸收分析

`POST /api/v1/reference-books/{book_id}/absorb`

### 查看风格圣经

`GET /api/v1/reference-books/{book_id}/style-bible`

### 查看场景模板

`GET /api/v1/reference-books/{book_id}/scene-patterns`

### 绑定到项目

`POST /api/v1/projects/{project_id}/reference-books/{book_id}/attach`

### 解绑

`DELETE /api/v1/projects/{project_id}/reference-books/{book_id}`

## 6. 前端页面设计

新增页面或 Tab：

- `frontend/components/project/ReferenceBooksTab.tsx`
- 或全局页面：`frontend/app/reference-books/page.tsx`

核心界面：

1. 上传区。
2. 版权确认选择。
3. 解析进度。
4. 章节列表。
5. 吸收进度。
6. 风格圣经预览。
7. 场景模板列表。
8. 绑定到当前项目。
9. 生成时是否启用参考书规则。

## 7. 生成时如何使用

生成某章前，系统根据当前章节目标检索：

- 当前章节类型。
- 当前情绪目标。
- 目标平台。
- 需要的爽点。
- 需要的冲突类型。
- 角色关系状态。

然后从参考书库中取出：

1. 3-5 条场景模板。
2. 1 份相关节奏规则。
3. 1 份风格圣经摘要。
4. 1 份禁止事项。

最终 prompt 中应该类似：

```text
以下是参考书分析后提炼的写法规则，不得复制原文：

风格规则：
- ...

场景模板：
- ...

节奏要求：
- ...

禁止事项：
- 不得复用参考书中的具体人物、地名、法宝名、句子和桥段组合。
- 不得连续输出与参考书高度相似的段落。
```

## 8. 防照抄机制

必须加入 Similarity Guard：

1. 生成后按段落切分。
2. 与参考书章节片段做相似度检测。
3. 如果某段过于接近，自动要求模型重写。
4. 日志只记录相似度和来源章节，不输出原文。

第一版可以做简单策略：

- n-gram 重合率。
- 长句重复检测。
- 专有名词重复检测。

第二版再接入 embedding 相似度。

## 9. 异步任务

整本吸收会很慢，必须异步化：

- 上传后立即返回 book_id。
- 解析、摘要、风格提炼都作为后台任务。
- 前端轮询或 SSE 展示进度。

任务状态：

- uploaded
- parsing
- parsed
- absorbing
- absorbed
- failed

## 10. 第一版 MVP

第一版不要一次做太大，建议只实现：

1. 上传 `.txt` / `.md`。
2. 自动章节识别。
3. 章节摘要。
4. 全书风格圣经。
5. 场景模板提取。
6. 项目绑定参考书。
7. 生成章节时注入风格规则。
8. 简单防照抄检测。

暂不做：

- epub/docx。
- 可视化情绪曲线。
- 高级向量数据库。
- 多书混合权重。

## 11. 验收测试

后端测试：

```powershell
pytest backend/tests/test_reference_books.py -q
pytest backend/tests/test_generation_pipeline.py -q
```

前端测试：

```powershell
cd frontend
npm run typecheck
npm run build
```

全量回归：

```powershell
pytest backend/tests -q
cd frontend
npm run typecheck
npm run build
```

## 12. 关键验收标准

- 能上传一本 `.txt` 小说。
- 能识别章节并展示章节列表。
- 能生成整本风格圣经。
- 能生成场景模板列表。
- 能把参考书绑定到小说项目。
- 生成新章节时能看到参考书规则被注入。
- 最终 prompt 不包含大段参考书原文。
- 生成内容不会大段复刻参考书。
- 原有后端测试和前端构建不被破坏。

## 13. 版权与安全提示

界面必须提示：

用户只能上传自己拥有版权、获得授权或属于公版领域的作品。系统仅用于提炼写作结构、风格规则和创作技巧，不应生成与原书高度相似的内容。

必须避免：

- 复刻整本书。
- 复刻具体桥段组合。
- 复刻人物名、地名、势力名、专有设定。
- 输出大段相似句子。

## 14. 推荐实施顺序

1. 数据库表和后端路由。
2. txt/md 上传与章节解析。
3. 章节摘要与全书摘要。
4. 风格圣经生成。
5. 场景模板生成。
6. 前端书库页面。
7. 绑定项目并注入生成上下文。
8. 防照抄检测。
9. 测试和文档。
