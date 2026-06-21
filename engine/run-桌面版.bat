@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title YuanYan AI Engine

set "PROJECT_DIR=C:\Users\Administrator\Documents\trae_projects\first cc"
cd /d "%PROJECT_DIR%"

echo ================================
echo  YuanYan - AI Engine
echo ================================
echo.
echo  Auto:
echo    1) Watch daily inputs  -> classify
echo    2) Watch kanban review -> approve + produce
echo    3) Serve dashboard     -> click to open
echo.
python -m engine.main
echo.
pause
