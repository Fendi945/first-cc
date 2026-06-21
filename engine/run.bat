@echo off
chcp 65001 >nul
title 🧠 元演心智 · AI 引擎

:: 获取项目根目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."

echo ================================
echo  🧠 元演心智 · AI 自动化引擎
echo ================================
echo.
python -m engine.main
echo.
pause
