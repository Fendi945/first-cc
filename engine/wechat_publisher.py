"""微信公众号 · 草稿箱 API

将 AI 生成的文章自动推送到公众号草稿箱，
用户登录公众号后台即可直接发布。

流程：
  1. 获取 access_token（有效期2小时，自动缓存）
  2. 创建草稿 POST /cgi-bin/draft/add
"""

import os
import json
import time
import requests
from pathlib import Path
from engine.retry_utils import retry_with_backoff

# ── 凭证 ──────────────────────────────────────────
APP_ID = os.getenv("WECHAT_APP_ID", "")
APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")
TOKEN_FILE = Path(__file__).resolve().parent.parent / "wechat_token_cache.json"

# Token 缓存
_token_cache = {"access_token": "", "expires_at": 0}


@retry_with_backoff()
def _get_access_token() -> str:
    """获取微信公众号 access_token（带缓存，自动刷新）。"""
    # 检查内存缓存
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    # 检查文件缓存
    if TOKEN_FILE.exists():
        try:
            cached = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            if cached.get("access_token") and now < cached.get("expires_at", 0):
                _token_cache.update(cached)
                return cached["access_token"]
        except Exception:
            pass

    if not APP_ID or not APP_SECRET:
        print("  [wechat] ⚠️ WECHAT_APP_ID 或 WECHAT_APP_SECRET 未配置")
        return ""

    # 请求新 token
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": APP_ID,
        "secret": APP_SECRET,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "access_token" in data:
            token = data["access_token"]
            expires_at = now + data.get("expires_in", 7200) - 300  # 提前5分钟过期
            _token_cache["access_token"] = token
            _token_cache["expires_at"] = expires_at
            # 写入文件缓存
            TOKEN_FILE.write_text(
                json.dumps({"access_token": token, "expires_at": expires_at}, ensure_ascii=False),
                encoding="utf-8"
            )
            return token
        else:
            print(f"  [wechat] ❌ 获取 token 失败: {data}")
            return ""
    except Exception as e:
        print(f"  [wechat] ❌ 网络请求失败: {e}")
        return ""


@retry_with_backoff()
def push_draft(title: str, content: str, author: str = "元演心智") -> str | None:
    """推送文章到公众号草稿箱。

    Args:
        title: 文章标题
        content: 文章正文（HTML 或纯文本）
        author: 作者名

    Returns:
        draft_id: 草稿ID（成功） | None（失败）
    """
    token = _get_access_token()
    if not token:
        print("  [wechat] ⏭️  无 access_token，跳过推送")
        return None

    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"

    # 正文转为 HTML
    body_html = content.replace("\n", "<br>")

    payload = {
        "articles": [
            {
                "title": title,
                "author": author,
                "content": body_html,
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
            }
        ]
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if "media_id" in data:
            print(f"  [wechat] ✅ 草稿创建成功，media_id: {data['media_id']}")
            return data["media_id"]
        else:
            print(f"  [wechat] ❌ 创建草稿失败: {data}")
            return None
    except Exception as e:
        print(f"  [wechat] ❌ 网络请求失败: {e}")
        return None
