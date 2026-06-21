@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title 元演心智 - AI 引擎

:: 获取项目根目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."

echo ================================
echo  元演心智 - AI 自动化引擎
echo ================================
echo.
echo  启动 Watchdog 监控日输入目录...
echo  分类结果写入 待审批.json
echo.
python -m engine.main
echo.
pause
