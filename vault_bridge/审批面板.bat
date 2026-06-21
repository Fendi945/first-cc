@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title 元演心智 - 审批中心

:: 获取项目根目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

:: 启动审批服务器（自动打开浏览器）
cd /d "%PROJECT_DIR%"
python -m engine.server

:: 如果服务器退出（Ctrl+C），暂停显示日志
echo.
echo 服务器已关闭
pause
