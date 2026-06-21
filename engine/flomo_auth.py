"""Flomo MCP 授权工具 — 配置个人 Token 或走 OAuth 授权。

用法 1（推荐）：配置个人 Token
  python -m engine.flomo_auth --token "你的Token"

用法 2：查看 Token 状态
  python -m engine.flomo_auth --status

用法 3：OAuth 浏览器授权（备选）
  python -m engine.flomo_auth --oauth
"""

import argparse
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("flomo_auth")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = PROJECT_ROOT / "flomo_token.json"


def save_token(token_data: dict):
    """保存 Token 到文件。"""
    TOKEN_FILE.write_text(json.dumps(token_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  ✅ Token 已保存到: {TOKEN_FILE}")


def load_token() -> dict | None:
    """从文件加载 Token。"""
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
    if expires_at and expires_at > time.time():
        return True
    # 个人 Token 没有过期时间
    if token.get("type") == "personal" and token.get("access_token"):
        return True
    return False


def show_status():
    """查看 Token 状态。"""
    token = load_token()
    if not token:
        print("\n  ❌ 未找到 Token，请运行:")
        print("     python -m engine.flomo_auth --token \"你的Token\"")
        return

    token_type = token.get("type", "unknown")
    if token_type == "personal":
        token_preview = token.get("access_token", "")[:12] + "..." if token.get("access_token") else ""
        print(f"\n  ✅ 个人 Token 已配置: {token_preview}")
        print(f"     类型: 个人 Token（永不过期）")
    else:
        expires_at = token.get("expires_at", 0)
        remaining = expires_at - time.time()
        if remaining > 0:
            print(f"\n  ✅ OAuth Token 有效，剩余 {remaining/60:.0f} 分钟")
            print(f"     有 refresh_token: {'是' if token.get('refresh_token') else '否'}")
        else:
            print(f"\n  ❌ OAuth Token 已过期，请重新运行:")
            print("     python -m engine.flomo_auth --oauth")


def setup_personal_token(token_str: str):
    """保存个人 Token。"""
    if not token_str or len(token_str) < 8:
        print("\n  ❌ Token 似乎无效（太短），请检查是否完整复制")
        return

    save_token({
        "type": "personal",
        "access_token": token_str,
        "token_type": "Bearer",
    })

    # 测试连接
    print("  正在测试连接...")
    import urllib.request
    req = urllib.request.Request(
        "https://flomoapp.com/mcp",
        data=b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"yuanyan-engine","version":"1.0"}}}',
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token_str}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            if resp.status == 200:
                print(f"  ✅ 连接成功！MCP 服务器已响应")
            else:
                print(f"  ⚠️ 服务器返回 {resp.status}: {body[:200]}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"  ❌ Token 无效，请检查是否复制正确")
        else:
            print(f"  ⚠️ HTTP {e.code}: {e.read().decode()[:200]}")
    except urllib.error.URLError as e:
        print(f"  ⚠️ 网络错误: {e.reason}")
    except Exception as e:
        print(f"  ⚠️ 连接测试失败: {e}")


def run_oauth_flow():
    """OAuth 浏览器授权（备选方案）。"""
    import hashlib
    import base64
    import secrets
    import urllib.parse
    import urllib.request
    import webbrowser
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    import socket

    # 找一个可用端口
    port = 18765
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    # PKCE
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(challenge).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)

    # 本地回调服务器
    auth_result = {"code": None, "error": None}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/callback":
                params = urllib.parse.parse_qs(parsed.query)
                auth_result["code"] = params.get("code", [None])[0]
                auth_result["error"] = params.get("error", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                msg = "✅ 授权成功！可关闭此页面" if auth_result["code"] else f"❌ 授权失败: {auth_result['error']}"
                self.wfile.write(f"<html><body><h2>{msg}</h2><script>window.close()</script></body></html>".encode())
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, *a): pass

    server = HTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    # 构建授权 URL
    auth_url = f"https://flomoapp.com/integration/grant?{urllib.parse.urlencode({
        'response_type': 'code',
        'client_id': 'flomo-mcp-client',
        'redirect_uri': redirect_uri,
        'scope': 'mcp',
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    })}"

    print(f"\n  正在打开浏览器...")
    try:
        webbrowser.open(auth_url)
    except:
        pass
    print(f"  如果浏览器未自动打开，请访问:")
    print(f"  {auth_url}")
    print(f"\n  请在浏览器中登录 Flomo 并完成授权")

    # 等待回调
    waited = 0
    while auth_result["code"] is None and auth_result["error"] is None:
        import time as _t
        _t.sleep(0.5)
        waited += 0.5
        if waited > 300:
            print("\n  ⚠️ 超时")
            server.shutdown()
            return
        if waited % 10 == 0:
            print(f"  ⏳ 等待授权... ({int(waited)}s)")

    server.shutdown()

    if auth_result["error"]:
        print(f"\n  ❌ 授权失败: {auth_result['error']}")
        return
    if not auth_result["code"]:
        print("\n  ❌ 未获取到授权码")
        return

    print("\n  ✅ 授权成功，正在获取 Token...")

    # 交换 code
    token_data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": auth_result["code"],
        "redirect_uri": redirect_uri,
        "client_id": "flomo-mcp-client",
        "code_verifier": code_verifier,
    }).encode()

    req = urllib.request.Request(
        "https://flomoapp.com/oauth/token",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode())
            raw["type"] = "oauth"
            raw["expires_at"] = time.time() + raw.get("expires_in", 3600)
            save_token(raw)
            print(f"  ✅ OAuth Token 已保存！")
    except urllib.error.HTTPError as e:
        print(f"  ❌ Token 获取失败: HTTP {e.code}: {e.read().decode()[:200]}")
    except urllib.error.URLError as e:
        print(f"  ❌ 网络错误: {e.reason}")


def main():
    parser = argparse.ArgumentParser(description="Flomo MCP 授权工具")
    parser.add_argument("--token", type=str, help="个人 Token（推荐）")
    parser.add_argument("--oauth", action="store_true", help="OAuth 浏览器授权（备选）")
    parser.add_argument("--status", action="store_true", help="查看 Token 状态")
    args = parser.parse_args()

    if args.token:
        setup_personal_token(args.token)
    elif args.oauth:
        run_oauth_flow()
    else:
        show_status()


if __name__ == "__main__":
    main()
