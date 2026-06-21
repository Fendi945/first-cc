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
echo  Watching for daily inputs...
echo  Results -> dai shen pi.json
echo.
python -m engine.main
echo.
pause
