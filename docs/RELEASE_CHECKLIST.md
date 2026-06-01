# 发布检查清单 (RELEASE CHECKLIST)

在发布新版本前，开发团队需要执行以下验证项，确保更新没有破坏核心的状态管理机制。

## 1. 核心底线 (不能被妥协的设计)

- [ ] `memory/` 核心架构不可更改：不得直接跳过 `State Patch` 机制将 AI 提取的内容静默合并到五大状态 JSON 中。
- [ ] 备份系统不可阻断：任何向 `memory/` 正式文件的写操作，必须强制经过 `state_file_service.py` 里的备份钩子。
- [ ] 大纲兼容机制：新系统的 `outline_state.json` 是主大纲，但不得引入自动覆盖旧 `Novel_directory.txt` 的代码，保护老工程。
- [ ] `pending_review` 数据隔离：任何生成上下文的服务（`generation_context_service.py`）不得读取 `pending_review` 或 `discarded` 或 `failed` 状态的数据，以免幻觉污染生成。

## 2. 自动化测试跑通

- [ ] 必须执行 `pytest tests/ -v`，且通过率必须达到 100%。
- [ ] 包含 10章的压力回归测试 `test_long_novel_stress.py`，必须正常跑通并且上下文字数在可控范围内，无越界污染。
- [ ] 如果修改了 LLM 的 Prompt 或相关调用逻辑，必须执行 `pytest tests/ -m real_llm` 以确认真实 API 可访问并能稳定返回合法的 JSON 格式。

## 3. UI 交互回归检查

- [ ] **高风险警告拦截**：在页面上编辑重要人物关系或修改真名时，必须跳出必须填写 Reason 且勾选 High Risk 的二次确认。
- [ ] **健康状态灯**：当手动伪造一条报错或删除某个核心 json 后，StateTab 顶部的健康指示灯必须变成红色 (Danger/Broken)。
- [ ] **翻译与提示语**：确保所有抛出的常见 `HTTP 400/500` 报错，已经被 `api-client.ts` 或错误边界友好地翻译为了中文业务文案，而不是长篇的 `Traceback`。

## 4. 交付件检查

- [ ] 所有 `docs/` 下的指南必须是最新的，与代码行为一致。
- [ ] 数据库迁移：如果涉及 SQLite 表结构的更改，必须确保旧版 `version 1` 数据能平滑迁移。

当所有勾选完成，可以封版发布！
