"""生成庭院三层产品卡片 PNG (9:16 信笺风)"""
from PIL import Image, ImageDraw, ImageFont
import os

# ── 配置 ─────────────────────────────────────────────
OUT_DIR = r"D:\Documents\Desktop\庭院产品卡片"
W, H = 540, 960                         # 9:16
BG = (250, 245, 235)                    # 信笺米白
TEXT_DARK = (28, 18, 10)                # 深棕文字
TEXT_MED = (80, 65, 50)                 # 中灰棕
TEXT_LIGHT = (140, 125, 110)            # 浅灰棕
ACCENT_ORANGE = (232, 117, 58)          # 暖橙
ACCENT_GREEN = (90, 142, 106)           # 暖灰绿
ACCENT_BLUE = (90, 126, 160)            # 雾霾蓝
LINE_COLOR = (55, 40, 28)               # 线稿颜色

# 字体
FONT_PATH = "C:/Windows/Fonts/simhei.ttf"

def font(size):
    return ImageFont.truetype(FONT_PATH, size)

def draw_lineart_1(draw):  # 避坑券 - 手机+花园+感叹号
    cx, cy = 270, 720
    # 手机
    draw.rounded_rectangle([cx+50, cy-50, cx+76, cy-8], radius=4, outline=LINE_COLOR, width=2)
    draw.rounded_rectangle([cx+53, cy-45, cx+73, cy-15], radius=2, outline=LINE_COLOR, width=1)
    draw.ellipse([cx+61, cy-6, cx+65, cy-2], outline=LINE_COLOR, width=1)
    # 声波
    for i, (y1, y2) in enumerate([(-35,-25), (-30,-20), (-25,-15)]):
        draw.arc([cx+80+i*3, cy+y1, cx+85+i*3, cy+y2], 240, 300, fill=LINE_COLOR, width=1)
    # 花园
    draw.line([cx-130, cy+30, cx-50, cy+30], fill=LINE_COLOR, width=2)
    # 树干
    draw.line([cx-115, cy+30, cx-115, cy], fill=LINE_COLOR, width=2)
    draw.line([cx-110, cy+30, cx-105, cy+5], fill=LINE_COLOR, width=1)
    draw.line([cx-105, cy+30, cx-95, cy-5], fill=LINE_COLOR, width=1)
    # 树冠
    draw.ellipse([cx-133, cy-25, cx-97, cy+5], outline=LINE_COLOR, width=2)
    draw.ellipse([cx-115, cy-20, cx-85, cy+2], outline=LINE_COLOR, width=2)
    # 石头
    draw.ellipse([cx-70, cy+25, cx-58, cy+32], outline=LINE_COLOR, width=1)
    # 感叹号圈
    draw.circle([cx-30, cy-15], 16, outline=LINE_COLOR, width=2)
    draw.line([cx-30, cy-26, cx-30, cy-14], fill=LINE_COLOR, width=3)
    draw.ellipse([cx-32, cy-8, cx-28, cy-4], fill=LINE_COLOR)
    # 箭头
    draw.line([cx+40, cy-20, cx-10, cy-10], fill=LINE_COLOR, width=1)

def draw_lineart_2(draw):  # 方向梳理 - 指南针+分支路径
    cx, cy = 250, 720
    # 指南针外圈
    draw.circle([cx, cy], 38, outline=LINE_COLOR, width=2)
    draw.circle([cx, cy], 30, outline=LINE_COLOR, width=1)
    # 十字线
    draw.line([cx, cy-35, cx, cy+35], fill=LINE_COLOR, width=1)
    draw.line([cx-35, cy, cx+35, cy], fill=LINE_COLOR, width=1)
    # 指针 N
    draw.line([cx, cy, cx, cy-32], fill=LINE_COLOR, width=3)
    draw.polygon([(cx, cy-38), (cx-4, cy-30), (cx+4, cy-30)], fill=LINE_COLOR)
    # 指针 S
    draw.line([cx, cy, cx, cy+32], fill=LINE_COLOR, width=2)
    # N/S
    draw.text((cx-5, cy-48), "N", fill=ACCENT_GREEN, font=font(14))
    draw.text((cx-5, cy+38), "S", fill=TEXT_LIGHT, font=font(12))
    # 分支路径
    pts = [(100, cy-20), (160, cy-40), (200, cy-20)]
    draw.line([cx+60, cy-20, *pts[0]], fill=LINE_COLOR, width=1)
    pts = [(100, cy), (160, cy-10), (200, cy)]
    draw.line([cx+60, cy, *pts[0]], fill=LINE_COLOR, width=1)
    pts = [(100, cy+20), (160, cy+30), (200, cy+20)]
    draw.line([cx+60, cy+20, *pts[0]], fill=LINE_COLOR, width=1)
    # 端点
    for x, y in [(200, cy-20), (200, cy), (200, cy+20)]:
        draw.circle([x, y], 5, outline=LINE_COLOR, width=1)
    # 起点箭头
    draw.line([cx+42, cy, cx+56, cy], fill=LINE_COLOR, width=2)
    draw.polygon([(cx+60, cy), (cx+54, cy-4), (cx+54, cy+4)], fill=LINE_COLOR)
    # 对话气泡 (右上)
    bx, by = 400, cy-60
    draw.ellipse([bx-20, by-15, bx+20, by+12], outline=LINE_COLOR, width=2)
    draw.line([bx-5, by+12, bx+5, by+22], fill=LINE_COLOR, width=2)
    draw.line([bx-5, by+12, bx+12, by+12], fill=LINE_COLOR, width=2)
    for yy in [by-5, by+2, by+8]:
        draw.line([bx-12, yy, bx+12, yy], fill=TEXT_LIGHT, width=1)

def draw_lineart_3(draw):  # 带方案草图 - 蓝图+笔+尺
    cx, cy = 250, 720
    # 蓝图
    draw.rounded_rectangle([cx-100, cy-55, cx+20, cy+30], radius=3, outline=LINE_COLOR, width=2)
    # 卷轴左
    draw.ellipse([cx-104, cy-8, cx-96, cy+12], outline=LINE_COLOR, width=2)
    draw.ellipse([cx-104, cy-55, cx-96, cy-50], outline=LINE_COLOR, width=1)
    draw.ellipse([cx-104, cy+25, cx-96, cy+30], outline=LINE_COLOR, width=1)
    # 卷轴右
    draw.ellipse([cx+16, cy-8, cx+24, cy+12], outline=LINE_COLOR, width=2)
    draw.ellipse([cx+16, cy-55, cx+24, cy-50], outline=LINE_COLOR, width=1)
    draw.ellipse([cx+16, cy+25, cx+24, cy+30], outline=LINE_COLOR, width=1)
    # 草图上植物
    draw.circle([cx-60, cy-15], 10, outline=LINE_COLOR, width=1)
    draw.circle([cx-60, cy-15], 5, outline=LINE_COLOR, width=1)
    draw.line([cx-60, cy-5, cx-60, cy+5], fill=LINE_COLOR, width=1)
    draw.circle([cx-30, cy-5], 8, outline=LINE_COLOR, width=1)
    draw.line([cx-30, cy+3, cx-30, cy+10], fill=LINE_COLOR, width=1)
    # 路径
    draw.line([cx-85, cy+12, cx-65, cy+2, cx-45, cy+12, cx-25, cy+2, cx-5, cy+12], fill=LINE_COLOR, width=1)
    # 水景虚线
    draw.ellipse([cx-50, cy-28, cx-20, cy-12], outline=LINE_COLOR, width=1)
    # 铅笔
    draw.polygon([(cx+65, cy-55), (cx+72, cy-55), (cx+68, cy-90)], outline=LINE_COLOR, width=2)
    draw.rectangle([cx+65, cy-48, cx+72, cy-5], outline=LINE_COLOR, width=2)
    draw.line([cx+65, cy-40, cx+72, cy-40], fill=LINE_COLOR, width=1)
    # 尺子
    draw.rectangle([cx+65, cy+5, cx+155, cy+16], outline=LINE_COLOR, width=2)
    for i in range(7):
        xx = cx+72 + i*12
        draw.line([xx, cy+6, xx, cy+15], fill=LINE_COLOR, width=1)
    # 标线
    for i, yy in enumerate([cy-25, cy-18, cy-11]):
        draw.line([cx+75, yy, cx+115, yy], fill=TEXT_LIGHT, width=1)


def make_card(title, price, tier_tag, accent, form_text, content_text, essence_text, lineart_fn):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ── 顶部分隔色条 ──
    for i in range(4):
        r = int(accent[0] * (1 - i/5) + 240 * (i/5))
        g = int(accent[1] * (1 - i/5) + 240 * (i/5))
        b = int(accent[2] * (1 - i/5) + 240 * (i/5))
        draw.rectangle([0, i*2, W, i*2+2], fill=(r, g, b))

    # ── 层级标签 ──
    draw.text((W//2, 42), tier_tag, fill=TEXT_LIGHT, font=font(13), anchor="mt")

    # ── 产品名 ──
    draw.text((W//2, 78), title, fill=TEXT_DARK, font=font(32), anchor="mt")

    # ── 价格 ──
    draw.text((W//2, 125), f"¥{price}", fill=accent, font=font(42), anchor="mt")
    draw.text((W//2, 155), "元", fill=TEXT_MED, font=font(16), anchor="mt")

    # ── 分隔线 ──
    for i in range(3):
        alpha = 0.3 + 0.3 * (1 - abs(i-1)/2)
        yy = 180 + i*1
        c = tuple(int(x * alpha + BG[j] * (1-alpha)) for j, x in enumerate(accent))
        draw.line([W//2-30, yy, W//2+30, yy], fill=c, width=1)

    # ── 内容区域 ──
    left = 55
    y0 = 210

    # 形式
    draw.text((left, y0), "形 式", fill=TEXT_LIGHT, font=font(12))
    draw.text((left, y0+22), form_text, fill=TEXT_DARK, font=font(15))

    # 内容
    y1 = y0 + 75
    draw.text((left, y1), "内 容", fill=TEXT_LIGHT, font=font(12))
    draw.multiline_text((left, y1+22), content_text, fill=TEXT_DARK, font=font(14), spacing=6)

    # 本质
    y2 = y1 + 115
    draw.text((left, y2), "本 质", fill=TEXT_LIGHT, font=font(12))
    draw.text((left, y2+22), essence_text, fill=TEXT_MED, font=font(13))

    # ── 线稿 ──
    lineart_fn(draw)

    # ── 底部装饰线 ──
    draw.line([60, H-30, W-60, H-30], fill=TEXT_LIGHT, width=1)

    return img

# ═══════════════════════════════════════════════════════

cards = [
    make_card(
        title="避坑券",
        price="9.9",
        tier_tag="引流款 · 第一层",
        accent=ACCENT_ORANGE,
        form_text="发一张院子照片 + 一个问题\n→ 回一条 30-60 秒语音",
        content_text="一句专业判断 ——\n「这个能不能做」「适合做什么」「哪里有问题」",
        essence_text="卖 16 年经验里的一句话判断，不是卖时间",
        lineart_fn=draw_lineart_1,
    ),
    make_card(
        title="方向梳理",
        price="199",
        tier_tag="利润款 · 第二层",
        accent=ACCENT_GREEN,
        form_text="30 分钟语音通话",
        content_text="· 需求梳理（水景/旱景、预算、风格）\n· 2-3 个可行方向建议\n· 下一步该找谁、该准备什么\n· 避坑提醒（施工队偷工减料点）",
        essence_text="卖判断力和经验——半小时省几个月瞎琢磨",
        lineart_fn=draw_lineart_2,
    ),
    make_card(
        title="带方案草图",
        price="499",
        tier_tag="高端款 · 第三层",
        accent=ACCENT_BLUE,
        form_text="语音通话 + 一张手绘方案草图",
        content_text="· 可执行的布局参考图（拿去跟施工队谈价）\n· 材料清单参考建议\n· 施工队选择避坑指南",
        essence_text="设计方案 + 施工经验打包",
        lineart_fn=draw_lineart_3,
    ),
]

# ── 保存 ───────────────────────────────────────────
names = ["01-避坑券·9.9元", "02-方向梳理·199元", "03-带方案草图·499元"]
for img, name in zip(cards, names):
    path = os.path.join(OUT_DIR, f"产品卡片-{name}.png")
    img.save(path, "PNG")
    print(f"{name} -> {path}")

print(f"\n共 {len(cards)} 张卡片已生成")
