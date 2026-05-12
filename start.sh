#!/bin/bash
# AI 小说生成器 — 一键启动脚本
# 同时启动后端 (FastAPI) 和前端 (Next.js)

set -euo pipefail

echo "=========================================="
echo "  AI 小说生成器 — 启动中..."
echo "=========================================="
echo ""

# 后端启动
echo "[1/2] 启动后端 (FastAPI) ..."
python run_server.py &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"

# 等待后端就绪
sleep 2

# 前端启动
echo "[2/2] 启动前端 (Next.js) ..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..
echo "  前端 PID: $FRONTEND_PID"

echo ""
echo "=========================================="
echo "  后端: http://localhost:8001"
echo "  API:  http://localhost:8001/docs"
echo "  前端: http://localhost:3000"
echo "=========================================="
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号，清理子进程
trap "echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# 等待任意子进程退出
wait
