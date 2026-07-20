@echo off
REM 元演引擎启动脚本（解决 Windows GBK 编码问题）
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo 正在启动元演引擎...
start "元演引擎" python -m engine.main
echo 引擎已启动，请稍候...
echo 审批面板: http://127.0.0.1:8765/dashboard/
