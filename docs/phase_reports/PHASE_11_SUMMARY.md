# 阶段 11 小结：防照抄与自动重写 (Similarity Guard)

## 1. 阶段目标与完成情况
- **目标**：降低生成内容与参考书高度相似的风险。实现防照抄与自动重写的最后防线机制。
- **完成情况**：**已完成**。新增了相似度检测核心服务 `local_similarity_guard_service.py`，支持基于 n-gram、大段连续字数、专有名词、以及长句重叠的指纹检测。并已经将检测机制内置于章节生成的收尾流程 `novel_generator/chapter.py` 中。如果触发拦截，会自动调用 LLM 使用专门的防照抄提示词将文字打碎重写（最多2次）。前端 `SimilarityGuardReport.tsx` 也已升级为真实实现，并动态展示每章检测数据。

## 2. 修改与新增文件
- `backend/app/routes/local_reference_books.py` (顺手修复): 修复了 Pydantic V2 弃用的 `data.dict()` 警告，改为 `data.model_dump()`。
- `backend/app/services/local_similarity_guard_service.py` (新增): 包含 n-gram, 长句 hash，专有名词检测。
- `backend/app/routes/chapters.py` (修改): 增加 `get_chapter_similarity_report` API 提供 JSON 报告下载读取。
- `frontend/lib/api-client.ts` (修改): 新增了 `getSimilarityReport`。
- `frontend/components/local-library/SimilarityGuardReport.tsx` (修改): 实现真正的组件与 API 数据对接，动态渲染检测详情或引导提示。
- `novel_generator/chapter.py` (修改): 在生成步骤末尾接入了 `Similarity Guard` 后置卡点，拦截高相似度并启动重抽（带专属 instruction）
- `backend/tests/test_similarity_guard.py` (新增): 新增测试用例。

## 3. 测试与验收情况
- 测试 `pytest backend/tests/test_similarity_guard.py` 0 失败，覆盖率完整，包含超阈值检测和不超过最大重试限制逻辑。
- 回归测试 `pytest backend/tests/test_generation_pipeline.py -q` 0 失败，原本的生成流程依然工作。
- 兼容性检查：若未绑定或未在项目中开启 `use_anti_copy_guard`，则自动跳过防照抄流程，不影响原本业务。
- 前端 TypeScript typecheck & Build 通过。

## 4. 关键安全与工程纪律确认
- **安全隔离**：报告（`similarity_report.json`）仅保存相似度数值、重叠特征词数量、拦截原因，**不包含原文字符串片段**，防信息泄漏成功。
- **生成后检查**：防照抄是纯后置拦截重抽逻辑，绝对没有破坏任何书籍原参考精华文件。
- **阈值配置**：各个维度的重合阈值都在 `local_similarity_guard_service.py` 内部声明为宏变量/常数（如 `DEFAULT_NGRAM_OVERLAP_THRESHOLD`），可后续扩展配置化。

## 5. 为后续阶段预留与风险
- **预留 Embedding 检测**：已在检测报告体系内部留好了 `embedding_similarity` 字段坑位，如果需要更深度的语义排重可在下一阶段补充向量逻辑。
- **风险**：对某些极其生僻的词，若参考书包含特定的短句且恰好非常普遍，可能面临误杀；但在设置合理的 `n=4` 且比率 `< 5%` 或长句字数大于15个的情况下，误伤概率已基本消减到最低。

## 6. 是否允许进入下一阶段
**允许进入阶段 12（本地 Agent 兼容抽象）。**
