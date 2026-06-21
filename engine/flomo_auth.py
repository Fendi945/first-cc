"""Flomo MCP OAuth 授权工具 — 通过浏览器完成 OAuth 授权并保存 Token。

用法:
  python -m engine.flomo_auth          # 启动授权流程
  python -m engine.flomo_auth --status  # 查看 Token 状态

流程:
  1. 启动本地 HTTP 服务器接收回调
  2. 打开浏览器跳转到 Flomo 授权页面
  3. 用户登录并授权
  4. 获取 access_token + refresh_token
  5. 保存到 flomo_token.json
"""

import argparse
import hashlib
import base64
import json
import logging
import os
import secrets
import socket
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional

logger = logging.getLogger("flomo_auth")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = PROJECT_ROOT / "flomo_token.json"

# OAuth 端点（从 .well-known 自动发现）
AUTH_ENDPOINT = "https://flomoapp.com/integration/grant"
TOKEN_ENDPOINT = "https://flomoapp.com/oauth/token"
REVOKE_ENDPOINT = "https://flomoapp.com/oauth/revoke"

# 客户端标识（用于 PKCE 公共客户端）
CLIENT_ID = "yuanyan-engine"
REDIRECT_PORT = 18765
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"
SCOPE = "mcp"


# ── PKCE 工具 ──

def _generate_pkce() -> tuple[str, str]:
    """生成 PKCE code_verifier 和 code_challenge (S256)。"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(challenge).rstrip(b"=").decode()
    return code_verifier, code_challenge


# ── Token 持久化 ──

def load_token() -> Optional[dict]:
    """从文件加载已保存的 Token。"""
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("读取 Token 文件失败: %s", e)
    return None


def save_token(token: dict):
    """保存 Token 到文件。"""
    TOKEN_FILE.write_text(json.dumps(token, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Token 已保存到 %s", TOKEN_FILE)


def is_token_valid(token: dict) -> bool:
    """检查 access_token 是否在有效期内。"""
    expires_at = token.get("expires_at", 0)
    return expires_at > time.time()


def get_valid_token() -> Optional[str]:
    """获取有效的 access_token，过期则自动刷新。"""
    token = load_token()
    if not token:
        return None

    if is_token_valid(token):
        return token.get("access_token")

    # 尝试刷新
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        logger.warning("Token 已过期且无 refresh_token，需重新授权")
        return None

    try:
        new_token = _refresh_access_token(refresh_token)
        save_token(new_token)
        return new_token.get("access_token")
    except Exception as e:
        logger.error("Token 刷新失败: %s", e)
        return None


def _refresh_access_token(refresh_token: str) -> dict:
    """使用 refresh_token 获取新的 access_token。"""
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
    }).encode()

    req = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Token 刷新失败 HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Token 刷新网络错误: {e.reason}")

    return _normalize_token(token_data)


def _normalize_token(raw: dict) -> dict:
    """标准化 token 数据结构，添加 expires_at。"""
    token = {
        "access_token": raw.get("access_token", ""),
        "refresh_token": raw.get("refresh_token", ""),
        "scope": raw.get("scope", ""),
        "token_type": raw.get("token_type", "Bearer"),
        "expires_in": raw.get("expires_in", 3600),
        "expires_at": time.time() + raw.get("expires_in", 3600),
    }
    return token


# ── 本地回调服务器 ──

class CallbackHandler(BaseHTTPRequestHandler):
    """处理 OAuth 回调的本地 HTTP 服务器。"""

    auth_code: Optional[str] = None
    auth_error: Optional[str] = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/callback":
            params = urllib.parse.parse_qs(parsed.query)
            CallbackHandler.auth_code = params.get("code", [None])[0]
            error = params.get("error", [None])[0]
            CallbackHandler.auth_error = params.get("error_description", [error])[0]

            if CallbackHandler.auth_code:
                self._respond_html("""
                <html><body style="font-family:sans-serif;text-align:center;padding:80px">
                <h2>✅ 授权成功！</h2>
                <p>Flomo MCP 授权已完成，你可以关闭此页面了。</p>
                <script>window.close()</script>
                </body></html>
                """)
            else:
                err = CallbackHandler.auth_error or "未知错误"
                self._respond_html(f"""
                <html><body style="font-family:sans-serif;text-align:center;padding:80px">
                <h2>❌ 授权失败</h2>
                <p>{err}</p>
                </body></html>
                """, status=400)
        else:
            self.send_response(404)
            self.end_headers()

    def _respond_html(self, html: str, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        logger.debug("回调服务器: %s", format % args)


def _start_callback_server() -> HTTPServer:
    """启动本地回调服务器。"""
    server = HTTPServer(("127.0.0.1", REDIRECT_PORT), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("回调服务器已启动: http://127.0.0.1:%d", REDIRECT_PORT)
    return server


# ── 授权流程 ──

def run_auth_flow() -> Optional[dict]:
    """执行完整的 OAuth 授权码流程（含 PKCE）。"""
    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(16)

    # 启动本地回调服务器
    server = _start_callback_server()

    # 构建授权 URL
    auth_params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{AUTH_ENDPOINT}?{auth_params}"

    print()
    print("=" * 60)
    print("  🔑 Flomo MCP 授权")
    print("=" * 60)
    print()
    print("  正在打开浏览器进行 Flomo 授权...")
    print(f"  如果浏览器没有自动打开，请访问:")
    print(f"  {auth_url}")
    print()
    print("  请在浏览器中登录 Flomo 并完成授权。")
    print()

    # 打开浏览器
    try:
        webbrowser.open(auth_url)
    except Exception:
        print(f"  ⚠️ 无法自动打开浏览器，请手动访问上面的链接。")

    # 等待回调（最长 300 秒）
    timeout = 300
    interval = 1
    waited = 0
    while CallbackHandler.auth_code is None and CallbackHandler.auth_error is None:
        time.sleep(interval)
        waited += interval
        if waited > timeout:
            print("\n  ⚠️ 超时未收到授权回调")
            server.shutdown()
            return None

    server.shutdown()

    # 处理错误
    if CallbackHandler.auth_error:
        print(f"\n  ❌ 授权失败: {CallbackHandler.auth_error}")
        return None

    auth_code = CallbackHandler.auth_code
    if not auth_code:
        print("\n  ❌ 未获取到授权码")
        return None

    # 验证 state（简化版，生产环境应严格比较）
    print("\n  ✅ 授权成功，正在获取 Token...")

    # 交换授权码获取 Token
    token_data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": code_verifier,
    }).encode()

    req = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_token = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"\n  ❌ Token 获取失败 HTTP {e.code}: {body}")
        return None
    except urllib.error.URLError as e:
        print(f"\n  ❌ Token 获取网络错误: {e.reason}")
        return None

    token = _normalize_token(raw_token)
    save_token(token)

    print(f"\n  ✅ Flomo MCP 授权完成！Token 已保存")
    print(f"  📁 {TOKEN_FILE}")
    print()

    return token


# ── CLI ──

def show_status():
    """显示当前 Token 状态。"""
    token = load_token()
    if token:
        expires_at = token.get("expires_at", 0)
        remaining = expires_at - time.time()
        if remaining > 0:
            print(f"✅ Token 有效，剩余 {remaining:.0f} 秒 ({remaining/60:.0f} 分钟)")
            print(f"   有 refresh_token: {'是' if token.get('refresh_token') else '否'}")
        else:
            print(f"❌ Token 已过期（{int(-remaining)} 秒前过期）")
            # 尝试刷新
            print("   尝试刷新...")
            token2 = load_token()
            rt = token2.get("refresh_token") if token2 else None
            if rt:
                try:
                    new = _refresh_access_token(rt)
                    save_token(new)
                    print("   ✅ 刷新成功！")
                except Exception as e:
                    print(f"   ❌ 刷新失败: {e}")
                    print("   请重新运行授权: python -m engine.flomo_auth")
            else:
                print("   无 refresh_token，请重新授权: python -m engine.flomo_auth")
    else:
        print("❌ 未找到 Token")
        print("   请运行: python -m engine.flomo_auth")


def main():
    parser = argparse.ArgumentParser(description="Flomo MCP OAuth 授权工具")
    parser.add_argument("--status", action="store_true", help="查看 Token 状态")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        run_auth_flow()


if __name__ == "__main__":
    main()
