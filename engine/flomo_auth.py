"""Flomo MCP 授权工具 — 一站式 OAuth 授权 + Token 管理。

用法:
  python -m engine.flomo_auth           # 首次：浏览器授权
  python -m engine.flomo_auth --status   # 查看 Token 状态
"""

import argparse
import base64
import hashlib
import json
import logging
import secrets
import socket
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

logger = logging.getLogger("flomo_auth")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = PROJECT_ROOT / "flomo_token.json"
CLIENT_REG_FILE = PROJECT_ROOT / "flomo_client.json"

# OAuth 端点
AUTH_ENDPOINT = "https://flomoapp.com/integration/grant"
TOKEN_ENDPOINT = "https://flomoapp.com/oauth/token"
REG_ENDPOINT = "https://flomoapp.com/oauth/register"
REDIRECT_PORT = 18765
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"


# ── 客户端注册 ──

def get_or_register_client() -> dict:
    """获取已注册的客户端信息，或动态注册一个新客户端。"""
    if CLIENT_REG_FILE.exists():
        try:
            data = json.loads(CLIENT_REG_FILE.read_text(encoding="utf-8"))
            if data.get("client_id"):
                return data
        except (json.JSONDecodeError, OSError):
            pass

    print("  📝 正在注册 OAuth 客户端...")
    reg_data = json.dumps({
        "client_name": "yuanyan-engine",
        "redirect_uris": [REDIRECT_URI],
        "token_endpoint_auth_method": "none",
    }).encode()

    req = urllib.request.Request(
        REG_ENDPOINT,
        data=reg_data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            client = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"注册失败 HTTP {e.code}: {e.read().decode()[:200]}")

    CLIENT_REG_FILE.write_text(json.dumps(client, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ 客户端注册成功: {client['client_id'][:12]}...")
    return client


# ── Token 管理 ──

def save_token(token_data: dict):
    """保存 Token。"""
    TOKEN_FILE.write_text(json.dumps(token_data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_token() -> dict | None:
    """加载 Token。"""
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def is_token_valid(token: dict | None) -> bool:
    if not token:
        return False
    expires_at = token.get("expires_at", 0)
    return expires_at > time.time()


def get_valid_token() -> str | None:
    """获取有效的 access_token，过期则自动刷新。"""
    token = load_token()
    if not token:
        return None
    if is_token_valid(token):
        return token.get("access_token")
    # 尝试刷新
    rt = token.get("refresh_token")
    if not rt:
        return None
    try:
        client = get_or_register_client()
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": client["client_id"],
        }).encode()
        req = urllib.request.Request(
            TOKEN_ENDPOINT, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            new_token = json.loads(resp.read())
        new_token["expires_at"] = time.time() + new_token.get("expires_in", 3600)
        new_token["refresh_token"] = new_token.get("refresh_token", rt)
        save_token(new_token)
        return new_token.get("access_token")
    except Exception as e:
        logger.error("Token 刷新失败: %s", e)
        return None


# ── 本地回调 ──

class Handler(BaseHTTPRequestHandler):
    result = {"code": None, "error": None}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            params = urllib.parse.parse_qs(parsed.query)
            Handler.result["code"] = params.get("code", [None])[0]
            Handler.result["error"] = params.get("error", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "✅ 授权成功！可关闭此页面" if Handler.result["code"] else f"❌ 失败: {Handler.result['error']}"
            self.wfile.write(f"<html><body><h2>{msg}</h2><script>window.close()</script></body></html>".encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a): pass


# ── OAuth 流 ──

def run_auth_flow():
    """执行完整的 OAuth 授权码 + PKCE 流程。"""
    # 注册客户端
    try:
        client = get_or_register_client()
    except RuntimeError as e:
        print(f"\n  ❌ {e}")
        return
    client_id = client["client_id"]

    # PKCE
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)

    # 本地服务器
    Handler.result = {"code": None, "error": None}
    server = HTTPServer(("127.0.0.1", REDIRECT_PORT), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    # 授权 URL
    auth_params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": "mcp",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{AUTH_ENDPOINT}?{auth_params}"

    print()
    print("=" * 58)
    print("  🔑 Flomo MCP 授权")
    print("=" * 58)
    print()
    print("  正在打开浏览器...")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
    print(f"  如果浏览器未自动打开，请手动访问:")
    print(f"  {auth_url}")
    print()
    print("  ⏳ 请在浏览器中登录 Flomo 并完成授权")
    print()

    # 等待
    waited = 0
    while Handler.result["code"] is None and Handler.result["error"] is None:
        time.sleep(0.5)
        waited += 0.5
        if waited > 300:
            print("  ❌ 超时（300秒），请重试")
            server.shutdown()
            return
        if waited > 0 and int(waited) % 10 == 0:
            print(f"  ⏳ 等待授权... ({int(waited)}s)")

    server.shutdown()

    if Handler.result["error"]:
        print(f"\n  ❌ 授权失败: {Handler.result['error']}")
        return
    if not Handler.result["code"]:
        print("\n  ❌ 未获取到授权码")
        return

    print("\n  ✅ 授权成功，正在获取 Token...")

    # 交换授权码
    token_data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": Handler.result["code"],
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }).encode()

    req = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"\n  ❌ Token 获取失败 HTTP {e.code}: {e.read().decode()[:200]}")
        return

    raw["expires_at"] = time.time() + raw.get("expires_in", 3600)
    save_token(raw)

    print(f"\n  ✅ Token 已保存到: {TOKEN_FILE}")
    print(f"  有效期: {raw.get('expires_in', 0)} 秒 ({raw.get('expires_in', 0)/3600:.1f} 小时)")
    print(f"  有 refresh_token: {'是' if raw.get('refresh_token') else '否'}")
    print()


def show_status():
    """查看 Token 状态。"""
    token = load_token()
    if not token:
        print("\n  ❌ 未找到 Token")
        print("  请运行: python -m engine.flomo_auth")
        return

    expires_at = token.get("expires_at", 0)
    remaining = expires_at - time.time()
    if remaining > 0:
        print(f"\n  ✅ Token 有效，剩余 {remaining:.0f} 秒 ({remaining/60:.0f} 分钟)")
        print(f"  有 refresh_token: {'是' if token.get('refresh_token') else '否'}")
    else:
        print(f"\n  ❌ Token 已过期")
        rt = token.get("refresh_token")
        if rt:
            print("  尝试自动刷新...")
            new_token = get_valid_token()
            if new_token:
                print("  ✅ 刷新成功！")
            else:
                print("  ❌ 刷新失败，请重新运行: python -m engine.flomo_auth")
        else:
            print("  请重新运行: python -m engine.flomo_auth")


def main():
    parser = argparse.ArgumentParser(description="Flomo MCP 授权工具")
    parser.add_argument("--status", action="store_true", help="查看 Token 状态")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        run_auth_flow()


if __name__ == "__main__":
    main()
