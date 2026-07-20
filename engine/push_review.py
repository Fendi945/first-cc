#!/usr/bin/env python3
"""推送「一个月复盘」到公众号草稿箱"""
import requests, json, os, sys, base64

sys.stdout.reconfigure(encoding='utf-8')

APP_ID = os.getenv("WECHAT_APP_ID", "wxa965a1f564142049")
APP_SECRET = os.getenv("WECHAT_APP_SECRET", "a8b1e6dce37e3994884722538c6d76b3")
AUTHOR = "付工"

def get_token():
    r = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={"grant_type":"client_credential","appid":APP_ID,"secret":APP_SECRET}
    )
    d = r.json()
    if "access_token" in d:
        return d["access_token"]
    raise Exception(f"获取token失败: {d}")

def upload_image(token, image_path):
    """上传图片到微信公众号素材库，返回 media_id。"""
    if not os.path.exists(image_path):
        raise Exception(f"图片不存在: {image_path}")
    with open(image_path, "rb") as f:
        r = requests.post(
            "https://api.weixin.qq.com/cgi-bin/material/add_material",
            params={"access_token": token, "type": "image"},
            files={"media": (os.path.basename(image_path), f, "image/png")}
        )
    d = r.json()
    if "media_id" in d:
        print(f"  图片上传成功 media_id={d['media_id'][:20]}...")
        return d["media_id"]
    raise Exception(f"图片上传失败: {d}")

def create_draft(token, content, media_id, title, digest):
    """创建草稿箱文章。"""
    # 替换图片 src 中的占位符
    content_with_img = content.replace(
        'src="" alt=""',
        f'src="https://mmbiz.qpic.cn/mmbiz_png/0/0?wx_fmt=png" data-media_id="{media_id}"'
    )

    body = {
        "articles": [{
            "title": title,
            "author": AUTHOR,
            "digest": digest,
            "content": content_with_img,
            "thumb_media_id": media_id,
        }]
    }
    r = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/add",
        params={"access_token": token},
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    d = r.json()
    if "media_id" in d:
        print(f"\n✅ 草稿创建成功！media_id={d['media_id'][:20]}...")
        return d["media_id"]
    raise Exception(f"创建草稿失败: {d}")

def main():
    token = get_token()
    print(f"✅ Token 获取成功")

    # 上传封面/配图
    cover = os.path.join(os.path.dirname(__file__), "..", "engine", "data", "xiaohei-books-floor-v4.png")
    media_id = upload_image(token, cover)

    # 读取文章内容
    html_path = os.path.join(os.path.dirname(__file__), "push_wechat_review.html")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 创建草稿
    create_draft(
        token,
        content,
        media_id,
        title="一个月搭系统",
        digest="一个月，从零搭起自己的系统。"
    )

if __name__ == "__main__":
    main()
