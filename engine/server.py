"""本地 HTTP 服务器 —— 提供审批面板静态文件 + REST API。

启动后自动打开浏览器到审批面板，所有数据操作通过 API 完成，
避免了 file:// 协议无法写入 JSON 的问题。

用法:
  python -m engine.server             # 默认端口 8765
  python -m engine.server --port 8888 # 自定义端口
  python -m engine.server --no-browser # 不自动打开浏览器
"""

import argparse
import http.server
import json
import os
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import PENDING_FILE, APPROVED_FILE, DAILY_INPUT_DIR
from engine.flomo_sync import FlomoSync
from engine.feishu_sync import FeishuSync
from engine.feishu_bitable_sync import FeishuBitableSync
from engine.feishu_kanban_sync import FeishuKanbanSync
from engine.dashboard_analyzer import DashboardAnalyzer
from vault_bridge.vault_utils import read_json, write_json, safe_read_json, safe_write_json

HOST = "127.0.0.1"
DEFAULT_PORT = 8765


# ── 数据读写工具（带错误处理） ──────────────────────

def _read_pending() -> list:
    """读取待审批 JSON，文件不存在或损坏则返回空列表。"""
    try:
        data = safe_read_json(PENDING_FILE)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  [server] ⚠️ 读取待审批.json 失败: {e}")
        return []


def _write_pending(data: list) -> bool:
    """写入待审批 JSON，返回是否成功。"""
    try:
        safe_write_json(PENDING_FILE, data)
        return True
    except Exception as e:
        print(f"  [server] ❌ 写入待审批.json 失败: {e}")
        return False


def _append_audit_log(action: str, item: dict) -> None:
    """向审批日志.json 追加一条审计记录。"""
    log_entry = {
        "action": action,
        "item_id": item.get("id", ""),
        "suggested_title": item.get("suggested_title", ""),
        "summary": item.get("summary", ""),
        "layer": item.get("layer", ""),
        "output_tag": item.get("output_tag", ""),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        logs = read_json(APPROVED_FILE)
        if not isinstance(logs, list):
            logs = []
        logs.append(log_entry)
        write_json(APPROVED_FILE, logs)
    except Exception as e:
        print(f"  [server] ⚠️ 写入审批日志失败: {e}")


# ── HTTP API 处理 ──────────────────────────────────

class APIHandler(http.server.SimpleHTTPRequestHandler):
    """自定义 HTTP 请求处理器 —— 同时提供静态文件和 REST API。"""

    # 禁用默认的日志消息（我们自己控制）
    def log_message(self, format, *args):
        print(f"  [server] {self.client_address[0]} - {format % args}")

    def _send_json(self, data, status=200):
        """发送 JSON 响应。"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def _read_body(self) -> bytes:
        """读取请求体。"""
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    # ── 路由 ────────────────────────────────────────

    def do_OPTIONS(self):
        """CORS 预检请求。"""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/pending":
            self._send_json(_read_pending())

        elif path == "/api/stats":
            data = _read_pending()
            stats = {
                "total": len(data),
                "pending": sum(1 for i in data if i.get("status") == "pending"),
                "approved": sum(1 for i in data if i.get("status") == "approved"),
                "skipped": sum(1 for i in data if i.get("status") == "skipped"),
                "video": sum(1 for i in data if i.get("output_tag") == "video" and i.get("status") == "pending"),
                "article": sum(1 for i in data if i.get("output_tag") == "article" and i.get("status") == "pending"),
                "tool": sum(1 for i in data if i.get("output_tag") == "tool" and i.get("status") == "pending"),
            }
            self._send_json(stats)

        elif path == "/api/health":
            self._send_json({"ok": True, "time": time.strftime("%Y-%m-%d %H:%M:%S")})

        elif path == "/api/flomo/status":
            if hasattr(self.server, "flomo_sync") and self.server.flomo_sync:
                self._send_json(self.server.flomo_sync.get_status())
            else:
                self._send_json({"running": False, "error": "Flomo sync not initialized"})

        elif path == "/api/feishu/status":
            if hasattr(self.server, "feishu_sync") and self.server.feishu_sync:
                self._send_json(self.server.feishu_sync.get_status())
            else:
                self._send_json({"running": False, "error": "Feishu sync not initialized"})

        elif path == "/api/feishu/bitable/status":
            if hasattr(self.server, "feishu_bitable"):
                self._send_json(self.server.feishu_bitable.get_status())
            else:
                self._send_json({"error": "Feishu bitable not initialized"})

        elif path == "/api/feishu/kanban/status":
            if hasattr(self.server, "feishu_kanban"):
                self._send_json(self.server.feishu_kanban.get_status())
            else:
                self._send_json({"error": "Feishu kanban not initialized"})

        elif path == "/api/dashboard/status":
            if hasattr(self.server, "dashboard_analyzer"):
                self._send_json(self.server.dashboard_analyzer.get_status())
            else:
                self._send_json({"running": False, "error": "Dashboard analyzer not initialized"})

        else:
            # 非 API 请求：当作静态文件处理
            super().do_GET()

    def do_PUT(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/pending":
            try:
                body = self._read_body()
                data = json.loads(body)
                if not isinstance(data, list):
                    self._send_json({"ok": False, "error": "数据格式错误，需要数组"}, 400)
                    return
                ok = _write_pending(data)
                self._send_json({"ok": ok, "count": len(data)})
            except json.JSONDecodeError as e:
                self._send_json({"ok": False, "error": f"JSON 解析错误: {e}"}, 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
        else:
            self._send_json({"ok": False, "error": "Not Found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/api/approve", "/api/skip"):
            try:
                body = self._read_body()
                payload = json.loads(body) if body else {}
                item_id = payload.get("id", "")

                data = _read_pending()
                found = None
                for item in data:
                    if item.get("id") == item_id:
                        found = item
                        break

                if not found:
                    self._send_json({"ok": False, "error": f"未找到 id={item_id}"}, 404)
                    return

                action = "approved" if parsed.path == "/api/approve" else "skipped"
                found["status"] = action
                found[f"{action}_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                _write_pending(data)
                _append_audit_log(action, found)

                self._send_json({"ok": True, "id": item_id, "status": action})

            except json.JSONDecodeError as e:
                self._send_json({"ok": False, "error": f"JSON 解析错误: {e}"}, 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)

        elif parsed.path == "/api/approve-all":
            try:
                data = _read_pending()
                now = time.strftime("%Y-%m-%d %H:%M:%S")
                count = 0
                for item in data:
                    if item.get("status") == "pending":
                        item["status"] = "approved"
                        item["approved_at"] = now
                        _append_audit_log("approved", item)
                        count += 1
                _write_pending(data)
                self._send_json({"ok": True, "count": count})

            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)

        elif parsed.path == "/api/flomo/sync":
            try:
                if hasattr(self.server, "flomo_sync") and self.server.flomo_sync:
                    count = self.server.flomo_sync.sync_once()
                    self._send_json({"ok": True, "imported": count})
                else:
                    self._send_json({"ok": False, "error": "Flomo sync not initialized"}, 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)

        elif parsed.path == "/api/feishu/sync":
            try:
                if hasattr(self.server, "feishu_sync") and self.server.feishu_sync:
                    count = self.server.feishu_sync.sync_once()
                    self._send_json({"ok": True, "synced": count})
                else:
                    self._send_json({"ok": False, "error": "Feishu sync not initialized"}, 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)

        elif parsed.path == "/api/feishu/bitable/sync":
            try:
                if hasattr(self.server, "feishu_bitable"):
                    results = self.server.feishu_bitable.sync_all()
                    self._send_json({"ok": True, "results": results})
                else:
                    self._send_json({"ok": False, "error": "Feishu bitable not initialized"}, 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)

        elif parsed.path == "/api/feishu/kanban/sync":
            try:
                if hasattr(self.server, "feishu_kanban"):
                    result = self.server.feishu_kanban.sync_all()
                    self._send_json({"ok": True, "result": result})
                else:
                    self._send_json({"ok": False, "error": "Feishu kanban not initialized"}, 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)

        elif parsed.path == "/api/dashboard/analyze":
            try:
                if hasattr(self.server, "dashboard_analyzer"):
                    result = self.server.dashboard_analyzer.check_and_analyze()
                    self._send_json({"ok": True, "result": result})
                else:
                    self._send_json({"ok": False, "error": "Dashboard analyzer not initialized"}, 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)

        elif parsed.path == "/api/feishu/bitable/record":
            try:
                body = self._read_body()
                payload = json.loads(body) if body else {}
                required = ["platform", "title"]
                for r in required:
                    if r not in payload:
                        self._send_json({"ok": False, "error": f"缺少必填字段: {r}"}, 400)
                        return
                if hasattr(self.server, "feishu_bitable"):
                    record = self.server.feishu_bitable.add_data_record(
                        platform=payload["platform"],
                        title=payload["title"],
                        views=payload.get("views", 0),
                        likes=payload.get("likes", 0),
                        comments=payload.get("comments", 0),
                        shares=payload.get("shares", 0),
                        new_followers=payload.get("new_followers", 0),
                        notes=payload.get("notes", ""),
                        record_date=payload.get("record_date"),
                    )
                    self._send_json({"ok": True, "record": record})
                else:
                    self._send_json({"ok": False, "error": "Feishu bitable not initialized"}, 500)
            except json.JSONDecodeError as e:
                self._send_json({"ok": False, "error": f"JSON 解析错误: {e}"}, 400)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)

        else:
            self._send_json({"ok": False, "error": "Not Found"}, 404)

    # ── 全局 404 ────────────────────────────────────
    def do_DELETE(self):
        self._send_json({"ok": False, "error": "Not Found"}, 404)


# ── 启动器 ─────────────────────────────────────────

def start_server(port=DEFAULT_PORT, no_browser=False):
    """启动 HTTP 服务器。"""
    # 切换到项目根目录，使 /dashboard/ 能正确映射
    os.chdir(str(PROJECT_ROOT))

    # 确保看板目录存在
    from engine.config import KANBAN_DIR
    KANBAN_DIR.mkdir(parents=True, exist_ok=True)

    server = http.server.HTTPServer((HOST, port), APIHandler)

    # -- 初始化 Flomo 同步 --
    flomo_sync = FlomoSync()
    flomo_sync.start_scheduler()
    server.flomo_sync = flomo_sync

    # -- 初始化飞书同步 --
    feishu_sync = FeishuSync()
    if feishu_sync.check_connection():
        feishu_sync.start_scheduler()
    server.feishu_sync = feishu_sync

    # -- 初始化飞书多维表格同步 --
    server.feishu_bitable = FeishuBitableSync()

    # -- 初始化飞书审批看板同步 --
    server.feishu_kanban = FeishuKanbanSync()
    try:
        server.feishu_kanban.sync_local_to_feishu()
    except Exception as e:
        print(f"  [server] ⚠️ 看板同步初始化失败: {e}")

    # -- 初始化 Dashboard 数据分析 --
    dashboard = DashboardAnalyzer()
    dashboard.start_scheduler()
    server.dashboard_analyzer = dashboard

    url = f"http://{HOST}:{port}/dashboard/"

    # 控制台可能不支持 emoji，用 ASCII 安全版本
    print()
    print("=" * 44)
    print("  元演心智 · 审批服务器")
    print("=" * 44)
    print(f"  地址: {url}")
    print(f"  端口: {port}")
    print(f"  关闭: Ctrl+C")
    print("=" * 44)
    print()

    if not no_browser:
        # 延迟打开浏览器，确保服务器已就绪
        import threading
        import subprocess

        def _open_browser():
            import time as t
            t.sleep(0.8)
            # Edge App 模式：无地址栏/标签页，像桌面程序
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

        threading.Thread(target=_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  [server] 👋 服务器已关闭")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="元演心智 · 审批服务器")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"监听端口（默认 {DEFAULT_PORT}）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    start_server(port=args.port, no_browser=args.no_browser)


if __name__ == "__main__":
    main()
