# 本地 Agent 设计文档 (LOCAL_AGENT_DESIGN)

## 1. 架构目标
本系统目前采用 `DirectLocalLibraryBackend`，直接由后端进程读取用户的本地语料文件夹并执行耗时的吸收与生成任务。
为了在未来支持“云端网页控制台 + 本地 Agent”模式，将耗时计算和本地 IO 剥离为独立的本地 Agent 进程，特进行本次服务访问层抽象。

## 2. 接口抽象 (`LocalLibraryBackend`)
通过定义 `LocalLibraryBackend` 接口，系统可在直接本地访问和通过网络访问 Agent 之间无缝切换。

## 3. Agent API 草案
未来本地 Agent 预计提供以下 RESTful/WebSocket 接口，完全复用当前定义的数据结构（如扫描结果结构、书籍索引结构、精华读取结构、任务状态结构）：

* **GET /api/v1/agent/status**
  用于检测本地 Agent 是否在线、心跳正常。

* **POST /api/v1/agent/library/scan**
  触发全量扫描，Agent 异步扫描本地目录并返回或回调 `ScanReport` 结果。

* **GET /api/v1/agent/library/books**
  返回当前已经被 Agent 解析提取的所有书籍索引 `manifest.json` 列表。

* **GET /api/v1/agent/library/books/{book_id}/essence/{file_key}**
  读取具体的精华分析结果文件内容，以便云端读取并构建 Prompt。

* **POST /api/v1/agent/library/books/{book_id}/absorb**
  云端下发指令，命令 Agent 启动书籍的重度吸收分析流程（如提取章节摘要、场景模板、风格圣经等）。

* **GET /api/v1/agent/tasks/{book_id}**
  查询 Agent 执行中的任务状态与进度。

## 4. 兼容性保证
* 现有所有服务不需要更改其返回或接收的数据结构，因为 `AgentLocalLibraryBackend` 只需要负责将本地请求通过 HTTP 代理过去。
* 目前默认使用 `DirectLocalLibraryBackend`，用户感知和体验不会有任何改变，无额外维护成本。
* 前端预留 Agent 在线状态显示字段，但默认隐藏或禁用，防止误导用户。
