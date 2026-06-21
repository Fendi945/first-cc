"""元演审批面板 · EXE 启动入口
被 PyInstaller 打包为单个 EXE 文件。双击运行，自动打开浏览器审批面板。
"""
import os
import sys
import shutil
import webbrowser
import threading
import time
from pathlib import Path


# ── 路径 ──────────────────────────────────────────
if getattr(sys, 'frozen', False):
    EXE_DIR = Path(sys.executable).parent          # EXE 所在目录
    BUNDLE_DIR = Path(sys._MEIPASS)                # 打包资源目录
else:
    EXE_DIR = Path(__file__).resolve().parent.parent
    BUNDLE_DIR = EXE_DIR

BUNDLED_DASHBOARD = BUNDLE_DIR / "dashboard"
PROJECT_ROOT = Path(r"C:\Users\Administrator\Documents\trae_projects\first cc")
TARGET_DASHBOARD = PROJECT_ROOT / "dashboard"

PORT = 8765
HOST = "127.0.0.1"


def setup_dashboard():
    """确保 dashboard 文件在项目目录中可用。"""
    if getattr(sys, 'frozen', False) and BUNDLED_DASHBOARD.exists():
        TARGET_DASHBOARD.mkdir(parents=True, exist_ok=True)
        for f in BUNDLED_DASHBOARD.iterdir():
            if f.is_file() and f.suffix in ('.html', '.js', '.css'):
                shutil.copy2(f, TARGET_DASHBOARD / f.name)
        print("  [OK] Dashboard files ready")


def load_env():
    """加载 .env 配置。"""
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print("  [OK] Config loaded")
    else:
        print(f"  [WARN] .env not found: {env_file}")


def ensure_vault_dirs():
    """确保 vault 看板目录存在。"""
    from engine.config import KANBAN_DIR
    KANBAN_DIR.mkdir(parents=True, exist_ok=True)


def run_server():
    """启动 HTTP 服务器。"""
    os.chdir(str(PROJECT_ROOT))
    from engine.server import start_server as _start
    _start(port=PORT, no_browser=True)


def open_browser_later():
    """延迟以 Edge App 模式打开（无浏览器工具栏）。"""
    time.sleep(1.5)
    url = f"http://{HOST}:{PORT}/dashboard/"
    print(f"  [Browser] Opening: {url}")
    # Edge App 模式 → 无地址栏，像桌面程序
    import subprocess
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    opened = False
    for edge in edge_paths:
        if Path(edge).exists():
            try:
                subprocess.Popen([edge, "--app=" + url], shell=False)
                opened = True
                break
            except Exception:
                continue
    if not opened:
        webbrowser.open(url)


def main():
    print()
    print("=" * 44)
    print("  YuanYan - Approval Panel")
    print("=" * 44)

    setup_dashboard()
    load_env()

    try:
        ensure_vault_dirs()
    except Exception as e:
        print(f"  [WARN] Dir setup: {e}")

    print()
    print(f"  URL: http://{HOST}:{PORT}/dashboard/")
    print(f"  Close window to exit")
    print("=" * 44)
    print()

    threading.Thread(target=open_browser_later, daemon=True).start()
    run_server()


if __name__ == "__main__":
    main()
