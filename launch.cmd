@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE="

if exist "..\.venv\Scripts\python.exe" set "PYTHON_EXE=..\.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"
if not defined PYTHON_EXE set "PYTHON_EXE=python"

if not exist "config.json" if exist "config.example.json" copy /y "config.example.json" "config.json" >nul

call "%PYTHON_EXE%" main.py

if errorlevel 1 (
  echo.
  echo Launch failed.
  echo If dependencies are missing, run setup_and_run.bat once.
  pause
)

endlocal
