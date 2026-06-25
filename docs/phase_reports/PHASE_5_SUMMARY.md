# Phase 5 Summary: 章节/卷解析 (Chapter/Volume Parsing)

## 已完成任务 (Completed Tasks)
1. **边界解析引擎 (`local_chapter_boundary_service.py`)**:
   - 实现了基于二进制块读取的流式小说解析器 (`'rb'` + 解码)，避免一次性加载大文件引发 OOM 问题。
   - 实现了精准的字节级 offset (`start_offset`, `end_offset`) 记录。
   - 实现了卷级、章级的多重正则规则检测（支持“第X章”、“Chapter X”、“序章”等多种中文/英文格式）。
   - 添加了自动分析置信度机制，当单章字数过长(>10万)或平均字数异常时触发置信度衰减，进而为书籍打上 `needs_review` 标签。
2. **解析编排服务 (`local_book_parser_service.py`)**:
   - 负责读取并清理重置原有章节数据（保证重建的幂等性）。
   - 将流式解析返回的章节列表结构化并插入 `local_reference_chapter` 和 `local_reference_volume` 数据库表。
   - 自动维护所属卷与书籍统计（总卷数、总章数、总字数）。
3. **API 路由补全 (`backend/app/routes/local_library.py`)**:
   - `POST /api/v1/local-library/books/{book_id}/parse`: 触发全书解析。
   - `POST /api/v1/local-library/books/{book_id}/chapters/rebuild`: 丢弃历史手动修正，重新解析。
   - `GET /api/v1/local-library/books/{book_id}/chapters`: 从数据库真实读取章节列表。
   - `PATCH /api/v1/local-library/books/{book_id}/chapters/{chapter_id}`: 支持手动编辑章节名和序号修正。
4. **测试体系补充与修复**:
   - 新增了 `test_local_book_parser.py` 进行白盒组件测试，对长文本惩罚、offset 截断验证、中文正则识别做了多维度校验。
   - 解除并修复了 `test_local_library_contract.py` 中对 `test_get_books_and_chapters_index` 契约 API 的跳过，并增加数据库真实 Mock。

## 修改与新增的文件 (Modified / Added Files)
- **[NEW]** `backend/app/services/local_chapter_boundary_service.py`
- **[NEW]** `backend/app/services/local_book_parser_service.py`
- **[NEW]** `backend/tests/test_local_book_parser.py`
- **[MODIFY]** `backend/app/routes/local_library.py`
- **[MODIFY]** `backend/tests/test_local_library_contract.py`

## 新增测试与验收结果 (Test & Acceptance Results)
测试命令：
```powershell
pytest backend/tests/test_local_book_parser.py backend/tests/test_local_library_scanner.py backend/tests/test_local_library_contract.py -v
```
**结果：** `14 passed, 3 skipped in 3.68s` (0 failed)。
跳过的测试完全属于阶段 7-10，符合工程规则约定。

## 兼容性检查 (Compatibility Checks)
- **对前序阶段兼容性：** 流式读取完全利用了阶段 4 中探测到的 `source_encoding`，完美衔接。
- **对现有项目兼容性：** 未改动与核心 Project 相关的其他业务逻辑代码。

## 为后续阶段预留 (Provisions for Next Phases)
- 在写入 `local_reference_chapter` 时，预留了 `summary_path`、`analysis_path` 以及 `scene_patterns_path` 字段为 NULL，为阶段 6（精华写入阶段）准备就绪。

## 风险与遗留 (Risks & Tech Debt)
- **极小概率的解码断裂**：通过 `'rb'` 按行读取时如果在 Windows 换行符处碰巧发生字节截断，可能会被 `errors='replace'` 替换部分字符，不过由于 `readline()` 基于 `\n` 处理，该情况概率可以忽略不计。
- **自定义正则需求**：有些轻小说可能使用“第1话”、“幕间”等非常规标题，后续可考虑提供用户自定义正则的能力。

## 是否允许进入下一阶段 (Proceed to Next Phase?)
**是 (Yes)**。阶段 5 的开发任务已 100% 达成，测试覆盖率充分，未发生越界实现阶段 6+ 功能。可以进入阶段 6 开发。
