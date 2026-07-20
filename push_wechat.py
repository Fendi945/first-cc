"""推送庭院文章到公众号草稿箱"""
import requests, json, os

# 优先从环境变量读取，避免硬编码凭据
APP_ID = os.getenv("WECHAT_APP_ID", "wxa965a1f564142049")
APP_SECRET = os.getenv("WECHAT_APP_SECRET", "a8b1e6dce37e3994884722538c6d76b3")
AUTHOR = "大一"

# ── 封面图 ──────────────────────────────────────
COVER = r"D:\Documents\Desktop\庭院产品卡片\微信图片_20260621215330_52_123.png"

# ── 文章正文 (HTML) ─────────────────────────────
CONTENT = """\
<div class="rich_media_content">
<p style="font-size:16px;line-height:2;color:#3a2a1a">
很多院子不是小，是乱。不是缺东西，是东西太多。
</p>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
<strong>一个院子丑，99%是这三个问题：</strong>
</p>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
<strong>第一个：没有主景。</strong> 进院子扫一眼，视线不知道停在哪。左边种棵桂花，右边放个陶罐，中间铺块草坪——每个都好看，合在一起没有焦点。
</p>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
<strong>第二个：没有停留。</strong> 走一圈全是景，但没一个地方能坐下来。客人来了站门口聊两句就走了——因为你没给他一个"留下来"的理由。
</p>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
<strong>第三个：元素太满。</strong> 恨不得把小红书上好看的全搬进自己家。水景、凉亭、汀步、灯带、假山——最后像个公园，不像院子。
</p>

<hr style="border:0;height:1px;background:#e0d5c8;margin:24px 0">

<p style="font-size:16px;line-height:2;color:#3a2a1a">
<strong>高级院子的底层逻辑就三句话。</strong>
</p>

<p style="font-size:18px;line-height:2;color:#1a1008;font-weight:bold;margin:20px 0 8px">
一、定主景——让视线有归宿
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
一个院子只准有一个主角。可以是一棵树、一面景墙、或者一个水景。其他都是配角。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
选主景的诀窍：从室内最常待的那个位置往外看，视线自然落到的那个点，就是主景位置。
</p>
<p style="font-size:16px;line-height:2;color:#8a6a4a;margin:8px 0">
好院子不是什么都种了，是走进来第一眼知道看哪。
</p>

<p style="font-size:18px;line-height:2;color:#1a1008;font-weight:bold;margin:20px 0 8px">
二、设停留——让人想坐下
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
院子不是展览馆，是生活的地方。你需要在院子里放一两处可以坐下来喝茶、看书、发呆的地方。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
停留点的位置：跟着太阳走。上午有阳光的位置放把椅子，下午有阴凉的地方搭个坐台。秋天坐得住，夏天不晒——这才是好设计。
</p>
<p style="font-size:16px;line-height:2;color:#8a6a4a;margin:8px 0">
好停留不是堆了个亭子，是你不自觉地想在那坐下来。
</p>

<p style="font-size:18px;line-height:2;color:#1a1008;font-weight:bold;margin:20px 0 8px">
三、留白——让空间喘口气
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
留白不是空着不用，是给眼睛休息的地方。一面白墙、一片干净的铺装、一段什么都不种的角落——这些"没用"的地方，恰恰是高级感的来源。
</p>
<p style="font-size:16px;line-height:2;color:#8a6a4a;margin:8px 0">
好设计不是做加法做到极致，是减到不能再减，还能好看。
</p>

<hr style="border:0;height:1px;background:#e0d5c8;margin:24px 0">

<p style="font-size:16px;line-height:2;color:#3a2a1a">
<strong>普通院子变高级的实操步骤：</strong>
</p>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
<strong>第一步：</strong> 清空。把你院子里所有能搬的东西全部搬走——家具、陶罐、小雕塑。看看什么都没有的时候，空间本身好不好看。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
<strong>第二步：</strong> 定主角。在那个最自然的视线落点上，放一个你最想要的东西。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
<strong>第三步：</strong> 添配角。主角定了，其他东西围着它转。配色统一、材质呼应、高度递减。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
<strong>第四步：</strong> 检查每个角度——走进来看、坐在客厅看、站在门口看——都舒服了吗？不舒服就减东西。
</p>

<p style="font-size:16px;line-height:2;color:#8a6a4a;margin:20px 0">
好设计不是做加法做到极致，是减到不能再减，还能好看。
</p>

<hr style="border:0;height:1px;background:#e0d5c8;margin:24px 0">

<p style="font-size:14px;line-height:2;color:#8a7a6a">
下期聊：主景树怎么选？种在前面还是后面？什么树显高级又不疯长？
</p>
<p style="font-size:14px;line-height:2;color:#8a7a6a;margin-top:8px">
评论区告诉我你家院子现在最大的困扰是什么。
</p>
</div>"""

# ══════════════════════════════════════════════════
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
            "digest": "很多院子不是小，是乱。不是缺东西，是东西太多。三招让你的院子变高级。",
            "content": html,
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
            "show_cover_pic": 1,
        }]
    }
    r = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/add",
        params={"access_token":token},
        json=payload
    )
    d = r.json()
    if "media_id" in d:
        print(f"[OK] 草稿推送成功 -> media_id: {d['media_id'][:20]}...")
        return d["media_id"]
    raise Exception(f"推送失败: {d}")

# ══════════════════════════════════════════════════
if __name__ == "__main__":
    print("=== 开始推送公众号草稿 ===")

    token = get_token()
    print("[OK] token 获取成功")

    thumb_id = upload_image(token, COVER)

    media_id = push_draft(token, "院子想高级，先别急着买树", CONTENT, thumb_id)

    print(f"\n完成！草稿 media_id: {media_id}")
