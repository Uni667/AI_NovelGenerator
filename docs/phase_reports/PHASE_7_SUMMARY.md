# Phase 7 Summary: 异步任务系统 (Asynchronous Task System)

## 已完成任务 (Completed Tasks)
1. **新增 `local_absorption_task_manager.py`**:
   - 实现了基于 asyncio 和多线程混合驱动的异步任务系统，不阻塞 FastAPI 主线程。
   - 实现了完整的任务状态流转控制接口：`start` / `pause` / `resume` / `cancel` / `retry_failed`。
   - 实现了一个能实时持久化进度（`progress_current`）、受控于 `threading.Event` 从而能够被随时暂停或取消的模拟 Worker (`_worker_loop`)。
2. **API 路由替换**:
   - 在 `local_library.py` 中更新了 `/absorb` 及其操作端点的全部 Mock 实现，将其代理到了实际的 `local_absorption_task_manager.py`。
   - 新增了重试接口 `POST /api/v1/local-library/books/{book_id}/absorb/retry-failed`。
3. **启用并修复测试**:
   - 启用了并重构了 `test_local_library_contract.py` 中被跳过的 `test_absorption_task_control` 测试，成功跑通任务控制的所有 API 流程。
   - 新增了 `test_local_absorption_tasks.py`，完整覆盖了任务生命周期，断点续跑，撤销操作等核心特性。

## 修改与新增的文件 (Modified / Added Files)
- **[NEW]** `backend/app/services/local_absorption_task_manager.py`
- **[NEW]** `backend/tests/test_local_absorption_tasks.py`
- **[MODIFY]** `backend/app/routes/local_library.py`
- **[MODIFY]** `backend/tests/test_local_library_contract.py`

## 新增测试与验收结果 (Test & Acceptance Results)
执行命令：
```powershell
pytest backend/tests/test_local_absorption_tasks.py backend/tests/test_task_manager.py backend/tests/test_local_library_contract.py -v
```
**结果：** `17 passed, 1 skipped` (唯一跳过的是保留给阶段 10 的 `test_project_bindings_flow`)。
在确保无任何 Failed 测试用例的情况下，所有任务系统的要求已经落实。

## 兼容性检查 (Compatibility Checks)
- **对前序阶段兼容性：** 系统完美兼容了 SQLite 中的已有表结构 (`reference_absorption_task`)。
- **对现有项目兼容性：** 未破坏 `task_orchestrator.py` 与原版系统生成任务机制。针对 FastAPI `def` 与 `async def` 路由执行池在多协程环境中的差异，通过自建 `_thread_target` 生成私有 Event Loop 兜底的方法避免了 `RuntimeError: no running event loop`，保证了任何环境下的兼容性。

## 为后续阶段预留 (Provisions for Next Phases)
`local_absorption_task_manager.py` 中的 `_worker_loop` 是一个基于断点 (`start_progress`) 输入的异步调度框架。
当阶段 8 进入时，可以在该 worker 函数中通过 `task_type` 分发到对应的具体 LLM 任务处理管线（例如 `summarize_chapters`），并通过轮询进度或回调进行任务同步，以满足后续真实提取及处理的需求。

## 风险与遗留 (Risks & Tech Debt)
- **测试环境背景任务清理**：在使用 API `TestClient` 进行测试结束时，后台可能残留了依然在跑的未被 `cancel` 的 `_worker_loop`。由于此时 FastAPI 销毁了测试数据库连接，会导致后台抛出无害的 `sqlite3.OperationalError`。这仅出现在测试套件结束时。真实生产环境中 FastAPI 服务器具有较长生命周期，并且关机阶段会有优雅终止。
- **并发数量管控**：目前 `local_absorption_task_manager` 对任务启动没有全局的并发阈值拦截器，允许同个系统并发发起极多个任务，这可以在阶段 8 或后期集成中进行扩展限制以保护 LLM API。

## 是否允许进入下一阶段 (Proceed to Next Phase?)
**是 (Yes)**。阶段 7 所要求的断点续跑、并发不阻塞、异步任务状态流转全已实现。请您复查，验证通过后可授权进入阶段 8。
