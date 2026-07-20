"""推送「一棵古松的三种态度」到公众号草稿箱"""
import requests, json, os, sys

# ── 强制 UTF-8 ────────────────────────────────
sys.stdout.reconfigure(encoding='utf-8')

APP_ID = os.getenv("WECHAT_APP_ID", "wxa965a1f564142049")
APP_SECRET = os.getenv("WECHAT_APP_SECRET", "a8b1e6dce37e3994884722538c6d76b3")
AUTHOR = "大一"

# ── 封面图 ──────────────────────────────────────
COVER = os.path.join(os.path.dirname(__file__), "cover_zhu.png")

# ── 文章正文 ─────────────────────────────────────
with open(os.path.join(os.path.dirname(__file__), "push_wechat_zhu.html"), "r", encoding="utf-8") as f:
    CONTENT = f.read()

# ── 摘要 ─────────────────────────────────────────
DIGEST = "一棵古松，三种态度，三种活法。"

def get_token():
    r = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={"grant_type":"client_credential","appid":APP_ID,"secret":APP_SECRET}
    )
    d = r.json()
    if "access_token" in d:
        return d["access_token"]
    raise Exception(f"获取token失败: {d}")

def upload_image(token, path):
    """上传图片为永久素材，返回 media_id"""
    files = {"media": ("cover.png", open(path,"rb"), "image/png")}
    r = requests.post(
        "https://api.weixin.qq.com/cgi-bin/material/add_material",
        params={"access_token":token,"type":"image"},
        files=files
    )
    d = r.json()
    if "media_id" in d:
        print(f"图片上传成功 → media_id: {d['media_id'][:20]}...")
        return d["media_id"]
    raise Exception(f"上传失败: {d}")

def push_draft(token, title, html, thumb_id):
    payload = {
        "articles": [{
            "title": title,
            "thumb_media_id": thumb_id,
            "author": AUTHOR,
            "digest": DIGEST,
            "content": html,
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
            "show_cover_pic": 1,
        }]
    }
    r = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/add",
        params={"access_token":token},
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    d = r.json()
    if "media_id" in d:
        print(f"[OK] 草稿推送成功 -> media_id: {d['media_id'][:20]}...")
        return d["media_id"]
    raise Exception(f"推送失败: {d}")

if __name__ == "__main__":
    print("=== 推送「一棵古松的三种态度」===")

    token = get_token()
    print("[OK] token 获取成功")

    thumb_id = upload_image(token, COVER)

    media_id = push_draft(token, "一棵古松的三种态度", CONTENT, thumb_id)

    print(f"\n完成！草稿 media_id: {media_id}")
    print("去公众号后台 → 草稿箱 → 可以预览和发布了")
