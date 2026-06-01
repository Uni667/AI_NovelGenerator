# 部署与测试检查清单 (DEPLOYMENT CHECKLIST)

在将本项目正式投入使用或二次开发部署时，请务必执行以下检查项。

## 1. 基础环境检查

- [ ] **Python 环境**: 推荐使用 Python 3.10+。
- [ ] **Node.js 环境**: 推荐使用 Node 18+ (使用 `npm` 或 `yarn` 或 `pnpm`)。
- [ ] **依赖包安装**:
  - 后端：在 `backend/` 目录下执行 `pip install -r requirements.txt`。
  - 前端：在 `frontend/` 目录下执行 `npm install`。
- [ ] **SQLite**: 确保服务器支持 SQLite 环境。

## 2. 环境变量与配置

- [ ] **前端环境变量**: 确保在 `frontend/.env` 中配置 `NEXT_PUBLIC_API_URL=http://127.0.0.1:8001` 或对应服务器地址。
- [ ] **后端启动端口**: 确保 uvicorn 启动端口与前端配置对应。
- [ ] **API 密钥配置**: 使用浏览器打开前端，进入**设置 -> 模型设置**，填入你的 OpenAI / 智谱 / DeepSeek 等 API_KEY 并通过连通性测试。

## 3. 测试与基准验证 (Testing)

本项目包含大量确保状态不出错的核心测试，强烈建议在修改代码后运行。

### 运行 Mock 自动化测试
运行所有默认拦截了真实 LLM 请求的安全与回归测试（无 token 消耗）：
```bash
cd backend
$env:PYTHONPATH="."  # Windows (PowerShell)
# export PYTHONPATH="."  # Linux/Mac
pytest tests/ -v -W ignore
```
所有关于 `mock_llm` 的 10章连载压力测试、状态演化、回滚测试应当 `PASSED`。

### 运行真实 LLM 冒烟测试
**注意**：真实大模型测试默认跳过，避免意外消耗 Token。如果你需要验证与第三方平台的真实连通性和输出 JSON 格式解析能力：
1. 确保在系统设置中已经配好默认可以使用的模型参数。
2. 配置环境变量 `RUN_REAL_LLM_TESTS=true`。
3. 运行特定标记的测试：
```bash
$env:RUN_REAL_LLM_TESTS="true"
pytest tests/ -m real_llm -v
```

## 4. 启动项目

```bash
# 后端启动
cd backend
$env:PYTHONPATH="."
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 前端启动
cd frontend
npm run dev
```
打开 `http://localhost:3000` 进入系统工作台。

## 5. 项目可用性检查

- [ ] 随意创建一个测试工程。
- [ ] 能否生成大纲并保存？
- [ ] 工作台能否正常调起生成？
- [ ] 手动进入 `状态 -> 状态总览`，页面顶部能否正确获取 `Healthy` 指示标？
- [ ] 点击**导出设定包**能否下载 `story_bible_xxx.md`？

如果以上全部通过，系统具备长篇写作级稳定生产能力！
