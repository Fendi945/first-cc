"""PyInstaller 构建脚本 —— 打包审批面板为单个 EXE。"""
import os
import sys
import PyInstaller.__main__
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = Path(r"D:\Documents\Desktop\元演审批面板")
LAUNCHER = PROJECT_ROOT / "engine" / "exe_launcher.py"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

# 安全防护：确保 DIST_DIR 是桌面下的子目录
DESKTOP = Path(r"D:\Documents\Desktop")
if DESKTOP not in DIST_DIR.parents:
    print("ERROR: DIST_DIR must be under Desktop")
    sys.exit(1)
if DIST_DIR == DESKTOP:
    print("ERROR: DIST_DIR cannot be Desktop itself")
    sys.exit(1)

# 清理旧构建
if DIST_DIR.exists():
    shutil.rmtree(DIST_DIR)

print("=" * 44)
print("  构建元演审批面板 EXE")
print("=" * 44)
print(f"  源码: {LAUNCHER}")
print(f"  输出: {DIST_DIR}")
print()

# Windows 上用 ; 分隔源和目标
add_data_spec = str(DASHBOARD_DIR) + ";" + "dashboard"
print(f"  嵌入数据: {add_data_spec}")

PyInstaller.__main__.run([
    str(LAUNCHER),
    "--name=审批面板",
    "--onedir",
    "--noconfirm",
    "--console",
    "--add-data", add_data_spec,
    f"--distpath={DIST_DIR}",
    "--clean",
    "--workpath", str(PROJECT_ROOT / "build" / "pyinstaller"),
    "--specpath", str(PROJECT_ROOT / "build"),
])

print()
print("=" * 44)
print("  构建完成!")
exe_path = DIST_DIR / "审批面板" / "审批面板.exe"
print(f"  EXE: {exe_path}")
print(f"  Dashboard: {DIST_DIR / '审批面板' / '_internal' / 'dashboard'}")
print("=" * 44)
