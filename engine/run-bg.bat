@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

:: 项目目录
set "PROJECT_DIR=C:\Users\Administrator\Documents\trae_projects\first cc"

:: 启动 AI 引擎（隐藏窗口）
start /min "" cmd /c "cd /d "%PROJECT_DIR%" && python -m engine.main"

:: 等一秒让引擎就绪
timeout /t 2 /nobreak >nul

:: 打开 Obsidian
start "" "C:\Users\Administrator\AppData\Local\Programs\Obsidian\Obsidian.exe"

:: 退出本窗口
exit
