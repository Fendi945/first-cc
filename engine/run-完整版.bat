@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title 元演心智 - AI 引擎 (含 Flomo 同步)

:: 项目根目录
cd /d "C:\Users\Administrator\Documents\trae_projects\first cc"

echo ================================
echo  元演心智 - AI 自动化引擎
echo ================================
echo.
echo  ✓ Flomo 笔记自动同步（每30分钟）
echo  ✓ 捕获目录监控
echo  ✓ 日输入 AI 分类
echo  ✓ 看板审批面板
echo.
echo  启动中...
echo.
python -m engine.main
echo.
pause
