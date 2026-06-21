@echo off
chcp 65001 >nul
title 🧠 元演心智 · 审批中心

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "DASHBOARD_DIR=%PROJECT_DIR%\dashboard"

:: 打开审批面板
start "" "%DASHBOARD_DIR%\index.html"
echo ✅ 审批面板已打开
echo.
pause
