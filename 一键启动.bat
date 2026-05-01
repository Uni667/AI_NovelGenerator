@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

set "PYTHON_EXE="

if exist "..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=..\.venv\Scripts\python.exe"
)

if not defined PYTHON_EXE if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
)

if not defined PYTHON_EXE (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_EXE=py -3"
    )
)

if not defined PYTHON_EXE (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_EXE=python"
    )
)

if not defined PYTHON_EXE (
    echo [错误] 没找到 Python。
    echo 请先安装 Python，或者告诉我，我可以继续帮你做成更省事的启动方式。
    pause
    exit /b 1
)

if not exist "config.json" if exist "config.example.json" (
    copy /y "config.example.json" "config.json" >nul
)

echo 正在启动 AI_NovelGenerator...
call %PYTHON_EXE% main.py

if %errorlevel% neq 0 (
    echo.
    echo [提示] 启动失败，常见原因是依赖还没装好。
    echo 这时可以先双击一次 setup_and_run.bat 安装依赖，再回来用这个脚本启动。
    pause
)

endlocal
