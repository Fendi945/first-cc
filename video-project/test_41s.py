#!/usr/bin/env python3
"""
快速测试：按手动逐字稿生成 41 秒视频，检验字幕对齐和字体。
使用 HYZhongHei 197 加粗 (汉仪中黑体)。
"""
import subprocess, re
from pathlib import Path

FONT_NAME = "HYZhongHei 197"
FONT_SIZE = 54
FONT_SIZE_HL = 60

TRANSCRIPT = """00:00 前两天我帮业主审了一套图
00:02 图纸报价8万
00:03 一看我就知道这预算不够
00:05 不是施工队黑
00:06 是图纸上埋了三个雷
00:08 今天拆给你看
00:10 设计师动动脑子
00:11 能帮你省下好几万
00:13 外行看图看什么
00:15 看效果图好不好看
00:16 我们看图看什么
00:18 看三年后哪里要改
00:20 第一个雷
00:21 动线没画
00:22 图纸上水景位置画的挺好
00:24 一出客厅正对着
00:25 但你顺着图纸走一遍
00:27 就发现问题了
00:28 人从客厅到水景
00:30 得绕过一片绿化带
00:31 下雨天
00:32 你穿个拖鞋过去踩一脚泥
00:34 这什么意思
00:35 做完了一定会改
00:37 加条汀步路
00:38 拆了草皮铺石板
00:40 管线绕开走
00:41 多花一笔钱"""

def ts(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int((sec - int(sec)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

# Parse transcript
entries = []
for line in TRANSCRIPT.strip().split('\n'):
    m = re.match(r'(\d+):(\d+)\s+(.*)', line)
    if m:
        mm, ss, text = int(m.group(1)), int(m.group(2)), m.group(3).strip()
        text = text.strip("。！？，、；：")
        start = mm * 60 + ss
        entries.append((start, text))

# Compute end times (next start, or +2.5s for last)
subs = []
for i, (start, text) in enumerate(entries):
    if i < len(entries) - 1:
        end = entries[i+1][0]
    else:
        end = start + 2.5
    if end > start + 0.2:
        subs.append((start, end, text))

print(f"Parsed {len(subs)} subtitle entries")

# Generate ASS with INLINE tags (no \rStyle)
PROJECT_DIR = Path(__file__).parent
width, height = 960, 544  # Landscape

ass_lines = [
    "[Script Info]",
    "ScriptType: v4.00+",
    f"PlayResX: {width}",
    f"PlayResY: {height}",
    "ScaledBorderAndShadow: yes",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    f"Style: Default,{FONT_NAME},{FONT_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,1,2,10,10,120,134",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
]

# Key terms to highlight
KEY_TERMS = sorted(["8万", "三个雷", "好几万", "绿化带", "汀步路", "石板", "管线"], key=lambda x: -len(x))
NUM_PATTERN = re.compile(r'[零一二三四五六七八九十百千万亿\d]+')

# Build inline highlight
# Normal: {\fs56\c&H00FFFFFF&\b1}text (SimHei加粗)
# Highlight: {\fs64\c&H0000FFFF&\b1}HL_TEXT{\fs56\c&H00FFFFFF&\b1}
NORMAL_RESET = "{\\fs%d\\c&H00FFFFFF&\\b1}" % FONT_SIZE
HL_OPEN = "{\\fs%d\\c&H0000FFFF&\\b1}" % FONT_SIZE_HL

def build_ass_text(text):
    """Build ASS text with inline highlight tags."""
    result = ""
    i = 0
    while i < len(text):
        matched = False
        for term in KEY_TERMS:
            if text[i:i+len(term)] == term:
                result += HL_OPEN + term + NORMAL_RESET
                i += len(term)
                matched = True
                break
        if matched:
            continue
        m = NUM_PATTERN.match(text, i)
        if m and len(m.group()) >= 1:
            result += HL_OPEN + m.group() + NORMAL_RESET
            i += len(m.group())
            continue
        result += text[i]
        i += 1
    return result

for s, e, text in subs:
    ass_text = build_ass_text(text)
    ass_lines.append(
        f"Dialogue: 0,{ts(s)},{ts(e)},Default,,0,0,0,,{ass_text}"
    )

ass_path = PROJECT_DIR / "temp" / "test_subs.ass"
ass_path.parent.mkdir(exist_ok=True)
ass_path.write_text("\n".join(ass_lines), encoding="utf-8-sig")
print(f"ASS written: {ass_path}")

# Verify inline tags
ass_content = ass_path.read_text(encoding="utf-8-sig")
print(f"  Lines: {len([l for l in ass_content.splitlines() if l.startswith('Dialogue')])}")
if "\\\\r" in ass_content:
    print("  WARNING: Found \\r tags, should use inline \\fs\\c\\b instead!")

# 直接裁剪源视频（仅修剪开头沉默，不做全屏模糊）
src = r"D:\Documents\Desktop\83754c81f0d82514137a517fa44cb3f6.mp4"
trimmed = PROJECT_DIR / "temp" / "test_trimmed.mp4"
subprocess.run([
    "ffmpeg", "-y", "-i", src,
    "-ss", "4.5",  # skip silence
    "-t", "42",
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-an",
    str(trimmed)
], check=True, capture_output=True)
print(f"Trimmed video: {trimmed}")

# Burn subtitles (copy ASS to C:\temp to avoid path escaping issues)
import shutil
shutil.copy2(ass_path, "C:/temp/test_subs.ass")
final = PROJECT_DIR / "output" / "test_41s_v5.mp4"
env = {**__import__('os').environ, "MSYS2_ARG_CONV_EXCL": "*"}
subprocess.run([
    "ffmpeg", "-y", "-i", str(trimmed),
    "-vf", "ass='C\\:/temp/test_subs.ass':original_size=960x544",
    "-c:v", "libx264", "-preset", "medium", "-crf", "23",
    str(final)
], check=True, capture_output=True, env=env)

print(f"\n✅ 完成! 输出: {final}")
print(f"  字体: {FONT_NAME} ({FONT_SIZE}号, 重点词{FONT_SIZE_HL}号黄色)")
