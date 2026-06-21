@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title YuanYan ShenPi

set "PROJECT_DIR=C:\Users\Administrator\Documents\trae_projects\first cc"
cd /d "%PROJECT_DIR%"
python -m engine.server
echo.
echo Server closed.
pause
