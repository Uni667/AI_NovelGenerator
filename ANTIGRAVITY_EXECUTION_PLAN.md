# Antigravity 执行计划：AI Novel Generator

## 0. 给 Antigravity 的总提示词

你正在接手 `D:\Personal\Desktop\plan\AI_NovelGenerator` 项目。这个项目是一个平台化 AI 小说生成与改稿助手，后端为 FastAPI + SQLite，前端为 Next.js 16 + React 19 + TypeScript，核心生成引擎位于 `novel_generator/`。

请按本文件阶段执行。每完成一个阶段都必须运行对应验收命令，并在提交前给出变更摘要、风险说明和测试结果。不要跳过测试，不要修改 `.env` 中的真实密钥，不要破坏既有数据和 `memory/` 状态管理机制。

当前基线已验证：

- 后端测试：`pytest backend/tests -q` 通过，结果为 `133 passed, 1 skipped`。
- 前端类型检查：`cd frontend && npm run typecheck` 通过。
- 前端生产构建：`cd frontend && npm run build` 通过。
- 已知非阻塞警告：`pytest.mark.real_llm` 未在 `pytest.ini` 注册。

## 1. 项目核心边界

### 必须保护

- `memory/` 长期记忆机制不可被绕过。
- AI 提取的 State Patch 必须保持 `pending_review` 人工审核机制，不得自动静默合并。
- 所有写入正式记忆文件的逻辑必须保留备份钩子。
- `pending_review`、`discarded`、`failed` 状态的数据不得进入章节生成上下文。
- 旧版 `Novel_directory.txt` 不得被自动覆盖。
- `.env`、用户真实 API Key、本地数据库与项目文件不得泄露或误删。

### 可以优化

- 文档一致性、乱码显示、开发体验。
- pytest mark 配置、测试分组、CI 可读性。
- 前端交互细节、错误提示中文化、加载状态。
- 长篇生成流程的可观测性、任务状态、失败恢复。
- 部署清单与本地一键启动体验。

## 2. 阶段一：环境与仓库健康收口

目标：让项目对新接手的 AI/开发者更容易正确启动、测试和理解。

任务：

1. 检查 `README.md`、`README_zh-CN.md`、`STATUS.md` 是否存在编码或内容过期问题。
2. 修复 `pytest.mark.real_llm` 未注册警告，在 `pytest.ini` 添加 markers 说明。
3. 检查 `.env.example` 是否使用示例密钥而非看似真实的固定密钥。如需要，替换为明显的占位符，并在文档中说明生成方式。
4. 增加或更新本地启动说明，明确：
   - 后端：`python run_server.py`
   - 前端：`cd frontend && npm run dev`
   - API 文档：`http://localhost:8001/docs`
5. 确认 `.gitignore` 已排除 `.env`、数据库运行文件、日志、构建产物。

验收命令：

```powershell
pytest backend/tests -q
cd frontend
npm run typecheck
npm run build
```

完成标准：

- 后端测试、前端类型检查、前端构建全部通过。
- pytest 不再出现 unknown mark 警告。
- 文档能让新用户在 Windows 环境中按步骤启动。

## 3. 阶段二：真实使用链路回归

目标：确认从注册、登录、创建项目、配置模型、生成架构到章节定稿的主链路可用。

任务：

1. 启动后端与前端。
2. 使用浏览器手工验证：
   - 注册/登录。
   - 新建小说项目。
   - 进入设置页配置模型凭证。
   - 项目页各 Tab 可正常打开。
   - 生成架构、生成目录、生成章节的按钮状态和错误提示合理。
3. 对 SSE 生成链路重点检查：
   - token 获取是否正常。
   - 断线、取消、失败时 UI 是否恢复可操作状态。
   - 后端任务状态是否持久化。
4. 记录任何失败点，按最小改动修复。

验收命令：

```powershell
pytest backend/tests/test_auth_routes.py backend/tests/test_project_routes.py backend/tests/test_generation_pipeline.py -q
cd frontend
npm run typecheck
npm run build
```

完成标准：

- 主流程可在本地完整走通。
- 失败时有中文可理解错误，而不是裸 traceback 或英文技术栈。

## 4. 阶段三：长篇连载安全增强

目标：强化 400 章级别长篇项目的记忆、状态和大纲演化可靠性。

任务：

1. 审查这些文件的调用边界：
   - `backend/app/services/generation_context_service.py`
   - `backend/app/services/state_patch_service.py`
   - `backend/app/services/state_patch_merger.py`
   - `backend/app/services/state_file_service.py`
   - `backend/app/services/outline_evolution_service.py`
   - `novel_generator/chapter_pipeline/`
2. 为关键约束补测试：
   - pending patch 不进入下一章上下文。
   - merge 前后自动备份。
   - 大纲演化只影响未来章节。
   - 删除或损坏核心 JSON 时健康检查能报警。
3. 检查 `test_long_novel_stress.py` 是否覆盖章节数量、上下文字数上限和隔离区污染。
4. 若当前 UI 没有清楚展示记忆接入状态，增强 `WorkbenchStatusPane` 或 `StateTab` 的状态展示。

验收命令：

```powershell
pytest backend/tests/test_state_patch_merge.py backend/tests/test_state_editing_flow.py backend/tests/test_outline_evolution_flow.py backend/tests/test_long_novel_stress.py -q
cd frontend
npm run typecheck
```

完成标准：

- 状态系统的关键底线均有测试保护。
- UI 能让作者知道“哪些事实已生效，哪些仍待审核”。

## 5. 阶段四：创作工作台体验优化

目标：让作者生成、编辑、定稿、回滚章节时更顺手。

任务：

1. 审查并优化：
   - `frontend/components/project/WorkbenchTab.tsx`
   - `frontend/components/project/workbench/WorkbenchEditor.tsx`
   - `frontend/components/project/workbench/WorkbenchControls.tsx`
   - `frontend/components/project/workbench/WorkbenchStatusPane.tsx`
2. 补齐常见状态：
   - 空章节。
   - 正在生成。
   - 已取消。
   - 生成失败可重试。
   - 已定稿不可误覆盖。
3. 检查按钮文案、禁用状态、加载状态、Toast 提示是否一致。
4. 保证移动端或窄屏下主要控件不重叠。

验收命令：

```powershell
cd frontend
npm run typecheck
npm run build
npm run test
```

完成标准：

- 用户能清楚知道当前章节处于草稿、生成中、待定稿或已定稿状态。
- 不出现按钮可点但请求必失败的状态。

## 6. 阶段五：模型配置与调用观测

目标：减少用户配置 API Key 和模型时的挫败感，方便排查调用失败。

任务：

1. 审查：
   - `backend/app/routes/user_api_config.py`
   - `backend/app/services/api_credential_service.py`
   - `backend/app/services/model_runtime.py`
   - `backend/app/services/invocation_logger.py`
   - `frontend/app/settings/page.tsx`
   - `frontend/components/home/ModelConfigDialog.tsx`
2. 增加“测试连接/试调用”能力，确保不会泄露 Key。
3. 错误分类：
   - Key 缺失。
   - 余额/权限不足。
   - 超时。
   - JSON 解析失败。
   - 模型不支持当前能力。
4. 在 Analytics 或设置页展示最近调用状态，但必须隐藏敏感信息。

验收命令：

```powershell
pytest backend/tests/test_llm_adapters.py backend/tests/test_analytics_routes.py -q
cd frontend
npm run typecheck
```

完成标准：

- 用户能在生成前验证模型配置。
- 调用失败时能看到可行动的中文提示。

## 7. 阶段六：部署与备份实战化

目标：让本地、Railway、Vercel 的部署路径一致且可恢复。

任务：

1. 校对：
   - `Dockerfile`
   - `railway.toml`
   - `render.yaml`
   - `frontend/vercel.json`
   - `docs/DEPLOYMENT_CHECKLIST.md`
   - `docs/BACKUP_AND_RESTORE_GUIDE.md`
2. 验证 Railway 使用的依赖文件是否为 `backend/requirements-cloud.txt`，且不会缺少运行时必要包。
3. 执行一次备份脚本干跑或真实备份：
   - `python utils/backup.py backup`
   - `python utils/backup.py list`
4. 检查备份包是否包含数据库和项目文件，且不包含 `.env`。
5. 更新发布检查清单，把当前验证命令固化进去。

验收命令：

```powershell
pytest backend/tests/test_health_and_export.py backend/tests/test_migrations.py -q
cd frontend
npm run build
```

完成标准：

- 新环境可按文档部署。
- 出问题能按文档备份和恢复。

## 8. 阶段七：最终验收与交付

目标：形成一个可交付、可回滚、可继续迭代的版本。

最终验收命令：

```powershell
pytest backend/tests -q
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

人工验收：

1. 注册/登录。
2. 创建项目。
3. 配置模型。
4. 生成架构。
5. 生成章节目录。
6. 生成章节草稿。
7. 定稿章节。
8. 查看 State Patch。
9. 合并或废弃 Patch。
10. 导出 Story Bible。
11. 执行备份列表查看。

交付说明必须包含：

- 修改了哪些文件。
- 修复了哪些问题。
- 新增了哪些测试。
- 哪些测试已通过。
- 是否涉及数据迁移。
- 是否需要用户重新配置环境变量。
- 回滚方式。

## 9. 建议执行顺序

优先级从高到低：

1. 阶段一：环境与仓库健康收口。
2. 阶段二：真实使用链路回归。
3. 阶段三：长篇连载安全增强。
4. 阶段五：模型配置与调用观测。
5. 阶段四：创作工作台体验优化。
6. 阶段六：部署与备份实战化。
7. 阶段七：最终验收与交付。

如果时间有限，至少完成阶段一到阶段三。这三步能最大化降低“后续章节越写越乱、状态被污染、用户不知道哪里坏了”的风险。
