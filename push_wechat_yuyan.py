"""推送渔樵问对文章到公众号草稿箱"""
import requests, json, os, sys

# 优先从环境变量读取，避免硬编码凭据
APP_ID = os.getenv("WECHAT_APP_ID", "wxa965a1f564142049")
APP_SECRET = os.getenv("WECHAT_APP_SECRET", "a8b1e6dce37e3994884722538c6d76b3")
AUTHOR = "大一"

# ── 封面图 ──────────────────────────────────────
COVER = r"D:\Documents\Desktop\公众号封面\微信图片_20260622053212_74_123.jpg"

# ── 文章正文 (HTML · WeChat 仅支持 inline style) ─
CONTENT = """\
<div class="rich_media_content">
<p style="font-size:15px;line-height:1.8;color:#8a7a6a;text-align:center;margin-bottom:24px">
渔樵问对 · 对话认知系列
</p>

<hr style="border:0;height:1px;background:#e0d5c8;margin:0 0 20px">

<h2 style="font-size:22px;font-weight:700;color:#1a1008;line-height:1.6;margin-bottom:8px">
渔樵问对：<br>一个造园师的自我追问
</h2>

<p style="font-size:14px;color:#8a7a6a;margin-bottom:28px;line-height:1.6">
方向不是选出来的，是走着走着，自己显现的。
</p>

<h3 style="font-size:18px;font-weight:700;color:#1a1008;margin:28px 0 12px;line-height:1.6">一、起于日常之问</h3>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
最近在做一件事：把我和 AI 的日常协作过程记录下来。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
这件事让我很兴奋——兴奋到睡不着觉。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
但兴奋之余，心里冒出一个问题：<strong>我到底在做什么？</strong>
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
我是一个造园师。帮别人设计庭院园林十几年，从无到有，从沟通到落地。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
现在我不在院子里干活了，跑到互联网上，敲键盘、搭网站、和 AI 对话。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
这算什么事？
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
于是我用渔樵问对的方法——就是这段时间一直在学的那套邵雍的思维框架——对自己做了一场推演。
</p>

<h3 style="font-size:18px;font-weight:700;color:#1a1008;margin:28px 0 12px;line-height:1.6">二、锚定具体</h3>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
先说自己做了什么：
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
公众号上发了一些内容，有 AI 拆书的读书笔记，有专业知识摘录，有工作感悟。视频号上更杂——日常记录、山海经、历史、园林手作、真人口播。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
方向看起来很乱。但乱不是问题，问题是——<strong>我在找一条主线的感觉。</strong>
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a;background:#f7f4ef;padding:16px;border-radius:4px;margin:16px 0">
渔者问我：「这里面哪一类让你在做的时候最来劲？不是看数据，是做的时候的感觉。」
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
我想了想：<strong>都没有。</strong>
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
反而是和 AI 一问一答推演系统、解决问题、建网站这件事，让我兴奋得睡不着觉。
</p>

<h3 style="font-size:18px;font-weight:700;color:#1a1008;margin:28px 0 12px;line-height:1.6">三、逐层追问</h3>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
渔者问我：「你觉得自己更像哪种人——造物者、布道者、建造者、对话者？」
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
我选了三个：造物者、建造者、对话者。没有选布道者。
</p>
<p style="font-size:16px;line-height:2;color:#8a6a4a;margin:8px 0">
这个排除很重要——我不是想教别人什么，我是享受从无到有造东西的过程。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a;margin-top:12px">
渔者又问：「那你怕什么？」
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
我说了三怕：
</p>
<div style="background:#f7f4ef;padding:16px 20px;border-radius:4px;margin:12px 0">
<p style="font-size:16px;line-height:2;color:#3a2a1a;margin:0">
第一，怕别人看我天天不做专业工作，手艺生疏了。<br>
第二，怕别人不相信我，觉得我夸夸其谈。<br>
第三，怕赚不到安身立命的钱。
</p>
</div>
<p style="font-size:16px;line-height:2;color:#3a2a1a;margin-top:12px">
渔者让我一个一个拆。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
第一个拆出来：「手艺长在身上了，驾轻就熟。」
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
第二个拆下去，挖出一句实话：<strong>不是怕别人不信任——是怕再次被辜负。</strong>
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
第三个接着挖：不是怕赚不到钱——是怕新的这条路，也是先付出、没有回报的老路。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a;background:#f7f4ef;padding:16px;border-radius:4px;margin:16px 0">
渔者说了一句让我沉默很久的话：<br><br>
「你不是在怕能不能做好——你是在怕会不会重蹈覆辙。」
</p>

<h3 style="font-size:18px;font-weight:700;color:#1a1008;margin:28px 0 12px;line-height:1.6">四、揭示范畴关系</h3>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
渔者让我用体用分析来拆：
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
帮别人造园的十几年——<strong>体（本质）</strong>是通过对话理解需求，从无到有营造一个系统；<strong>用（工具）</strong>是庭院设计这个行业。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
现在做的事——<strong>体</strong>是通过对话从无到有营造自己的认知系统；<strong>用</strong>是网站、AI、内容。
</p>
<p style="font-size:16px;line-height:2;color:#8a6a4a;margin:8px 0">
体完全没变。变的只是「用的对象」——从帮别人造园，变成造自己的体系。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a;margin-top:12px">
那为什么忐忑？
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
因为过去那个行业里的生意模式是：先干活，后拿钱，层层分包，被拖着不给。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
我不是做不下去了，是我自己选择不干的——「我自己断了一条腿」。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a;background:#f7f4ef;padding:16px;border-radius:4px;margin:16px 0">
而现在做的事，走的是一条完全不同的路：<br><br>
<strong>互联网不会拖欠你的「内容款」。你做一分，就有一分在。</strong>
</p>

<h3 style="font-size:18px;font-weight:700;color:#1a1008;margin:28px 0 12px;line-height:1.6">五、回归于道</h3>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
渔者问我：「土壤更肥沃还是更贫瘠了？」
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
我说：<strong>「我的根是我的认知，我的诚实。互联网缺的就是这个。」</strong>
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
渔者说：这句话就够了。
</p>
<div style="background:#f7f4ef;padding:16px 20px;border-radius:4px;margin:16px 0">
<p style="font-size:16px;line-height:2;color:#3a2a1a;margin:0">
土壤没有肥沃贫瘠之分，只有适合种什么之分。<br><br>
物理土壤适合种需要慢生长、高信任、高单价的东西。<br>
互联网土壤适合种可以长长久久、不怕被辜负、每一寸根都属于自己的东西。
</p>
</div>
<p style="font-size:16px;line-height:2;color:#3a2a1a;margin-top:12px">
一个造园师不在院子里干活了——但他还是在造园子。只是园子从物理空间，扩展到了认知空间。
</p>

<hr style="border:0;height:1px;background:#e0d5c8;margin:28px 0">

<h3 style="font-size:18px;font-weight:700;color:#1a1008;margin:28px 0 12px;line-height:1.6">收尾</h3>

<p style="font-size:16px;line-height:2;color:#3a2a1a">
这篇文章不是什么教程，也不是什么课程。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a">
它就是一段对话的记录——一个造园师用渔樵问对的方法，对自己做了一次诚实的追问。
</p>
<p style="font-size:16px;line-height:2;color:#3a2a1a;background:#f7f4ef;padding:16px;border-radius:4px;margin:16px 0">
最后渔者收竿的时候说：<br><br>
互联网不缺信息、不缺工具、不缺课——<br>
缺的就是一个诚实的人，老老实实说「我是这么问自己的」。
</p>
<p style="font-size:16px;line-height:2;color:#8a6a4a;text-align:center;margin:32px 0">
那就从这里开始。
</p>
<p style="font-size:14px;line-height:2;color:#8a7a6a;text-align:center;margin-top:20px">
慢慢走，欣赏啊 · 朱光潜
</p>
</div>"""

TITLE = "渔樵问对：造园师的自我追问"
DIGEST = "方向不是选出来的，是走着走着，自己显现的。一个造园师的自我追问。"

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
    if not os.path.exists(path):
        raise Exception(f"封面图不存在: {path}")
    files = {"media": ("cover.jpg", open(path,"rb"), "image/jpeg")}
    r = requests.post(
        "https://api.weixin.qq.com/cgi-bin/material/add_material",
        params={"access_token":token,"type":"image"},
        files=files
    )
    d = r.json()
    if "media_id" in d:
        print(f"[OK] 图片上传成功 -> media_id: {d['media_id'][:20]}...")
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
        json=payload
    )
    d = r.json()
    if "media_id" in d:
        print(f"[OK] 草稿推送成功 -> media_id: {d['media_id'][:20]}...")
        return d["media_id"]
    raise Exception(f"推送失败: {d}")

# ══════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 40)
    print("=== 推送渔樵问对文章到公众号草稿箱 ===")
    print("=" * 40)

    token = get_token()
    print("[OK] token 获取成功")

    thumb_id = upload_image(token, COVER)

    media_id = push_draft(token, TITLE, CONTENT, thumb_id)

    print(f"\n[OK] 完成！草稿已存入微信公众号后台")
    print(f"   标题：{TITLE}")
    print(f"   封面：{COVER.split(chr(92))[-1]}")
