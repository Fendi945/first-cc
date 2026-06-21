"""元演心智 · AI 自动化引擎入口。

启动后同时运行：
  - Watchdog 监控日输入 + 看板审批
  - HTTP 服务器（提供审批面板 + API）

用法：
  python -m engine.main          # 启动 watchdog + 服务器
  python -m engine.main --scan   # 只扫描已有文件，不启动服务
"""

import sys
import threading
from engine.config import DEEPSEEK_API_KEY


def _update_kanban():
    """生成/更新 Obsidian 看板文件。"""
    try:
        from engine.kanban_generator import write_kanban_file
        write_kanban_file()
    except Exception as e:
        print(f"  ⚠️ 看板更新失败: {e}")


def _start_server():
    """在后台线程启动 HTTP 服务器。"""
    try:
        from engine.server import start_server as _start
        _start(no_browser=True)  # 不自动打开浏览器
    except Exception as e:
        print(f"  ⚠️ 服务器启动失败: {e}")


def _start_flomo_sync():
    """在后台线程启动 Flomo 同步调度。"""
    try:
        from engine.flomo_sync import FlomoSync
        sync = FlomoSync()
        sync.start_scheduler()
    except Exception as e:
        print(f"  ⚠️ Flomo 同步启动失败: {e}")


def main():
    # 检查 API Key 是否已配置
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your-api-key-here":
        print("❌ 请先在 .env 中配置 DEEPSEEK_API_KEY")
        sys.exit(1)

    from engine.watchdog import scan_existing, start_watchdog

    if "--scan" in sys.argv:
        print("🔍 扫描已有日输入文件...")
        scan_existing()
        _update_kanban()
        print("\n✅ 扫描完成")
    else:
        # 后台启动服务器（提供审批面板 API）
        server_thread = threading.Thread(target=_start_server, daemon=True)
        server_thread.start()

        # 启动 Flomo 同步（后台）
        flomo_thread = threading.Thread(target=_start_flomo_sync, daemon=True)
        flomo_thread.start()

        # 启动前先扫描已有文件
        print("🔍 启动前扫描已有文件...")
        scan_existing()
        _update_kanban()
        print()
        print("  审批面板: http://127.0.0.1:8765/dashboard/")
        print()
        start_watchdog()


if __name__ == "__main__":
    main()
