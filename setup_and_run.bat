@echo off
chcp 65001 >nul
echo ============================================
echo    AI_NovelGenerator 一键安装与启动脚本
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [1/3] 检测到 Python 环境
python --version
echo.

:: 安装依赖
echo [2/3] 正在安装依赖，请耐心等待...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [警告] 清华源安装失败，尝试默认源...
    pip install -r requirements.txt
)
echo.

:: 检查 config.json
if not exist "config.json" (
    echo [提示] 未找到 config.json，正在从示例复制...
    copy config.example.json config.json
    echo [提示] 请编辑 config.json 填入你的 API Key 后再运行！
    echo         记事本打开: notepad config.json
    pause
    exit /b 0
)

:: 启动
echo [3/3] 启动 AI_NovelGenerator...
echo.
python main.py

pause
