#!/usr/bin/env python3
"""
竖屏 10 秒测试：竖屏原素材直接裁剪+字幕（汉仪中黑体加粗 54/60号）。
"""
import subprocess, re, shutil
from pathlib import Path

SRC = r"D:\Documents\Desktop\23b3412458bd8d6a2659e950bf5c9c14.mp4"
PROJECT_DIR = Path(__file__).parent
TEMP = PROJECT_DIR / "temp"
OUTPUT = PROJECT_DIR / "output"
TEMP.mkdir(exist_ok=True); OUTPUT.mkdir(exist_ok=True)

FONT_NAME = "HYZhongHei 197"
FONT_SIZE = 54
FONT_SIZE_HL = 60

# Whisper 错字修正
CORRECTIONS = {"时空对黑": "施工队黑", "时空": "施工", "图上": "图纸上"}

# Whisper 实际转录时间轴（从原视频 0s 开始）
# 裁剪起点 5.0s，字幕时间 = 转录时间 - 5.0
TRIM_START = 5.0
TRANSCRIPT_RAW = [
    (5.1, "前两天我帮业主审了一套图"),
    (7.7, "图纸报价8万"),
    (9.4, "一看我就知道这预算不够"),
    (11.7, "不是施工队黑"),
    (13.2, "是图纸上埋了三个雷"),
    (15.0, "今天拆给你看"),
]

def ts(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int((sec - int(sec)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

# Use Whisper real timestamps, offset by TRIM_START
def fix_text(text):
    """修正 Whisper 错字。"""
    for wrong, correct in sorted(CORRECTIONS.items(), key=lambda x: -len(x[0])):
        text = text.replace(wrong, correct)
    return text

subs = []
for i, (raw_start, text) in enumerate(TRANSCRIPT_RAW):
    # Relative to trimmed video start
    start = round(raw_start - TRIM_START, 1)
    if i < len(TRANSCRIPT_RAW) - 1:
        end = round(TRANSCRIPT_RAW[i+1][0] - TRIM_START, 1)
    else:
        end = start + 1.8
    text = fix_text(text.strip("。！？，、；："))
    if end > start + 0.2:
        subs.append((start, end, text))

print(f"Entries: {len(subs)}")

# Portrait dimensions
pw, ph = 544, 960  # portrait 竖屏（与原素材一致）

# --- Step 1: Trim 10s from portrait source ---
trimmed = TEMP / "portrait_trimmed.mp4"
subprocess.run([
    "ffmpeg", "-y", "-ss", f"{TRIM_START}", "-i", SRC,
    "-t", "11",
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-c:a", "aac", "-b:a", "128k", str(trimmed)
], check=True, capture_output=True)
print(f"Trimmed: {trimmed}")

# --- Step 4: Generate ASS subtitles (portrait) ---
KEY_TERMS = sorted(["8万", "三个雷", "好几万", "施工队"], key=lambda x: -len(x))
NUM_PATTERN = re.compile(r'[零一二三四五六七八九十百千万亿\d]+')

NORMAL_RESET = "{\\fs%d\\c&H00FFFFFF&\\b1}" % FONT_SIZE
HL_OPEN = "{\\fs%d\\c&H0000FFFF&\\b1}" % FONT_SIZE_HL

def build_ass_text(text):
    result = ""
    i = 0
    while i < len(text):
        matched = False
        for term in KEY_TERMS:
            if text[i:i+len(term)] == term:
                result += HL_OPEN + term + NORMAL_RESET
                i += len(term); matched = True; break
        if matched: continue
        m = NUM_PATTERN.match(text, i)
        if m and len(m.group()) >= 1:
            result += HL_OPEN + m.group() + NORMAL_RESET
            i += len(m.group()); continue
        result += text[i]; i += 1
    return result

ass_lines = [
    "[Script Info]", "ScriptType: v4.00+",
    f"PlayResX: {pw}", f"PlayResY: {ph}", "ScaledBorderAndShadow: yes",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    f"Style: Default,{FONT_NAME},{FONT_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,1,2,10,10,120,134",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
]

for s, e, text in subs:
    ass_text = build_ass_text(text)
    ass_lines.append(f"Dialogue: 0,{ts(s)},{ts(e)},Default,,0,0,0,,{ass_text}")

ass_path = TEMP / "portrait_subs.ass"
ass_path.write_text("\n".join(ass_lines), encoding="utf-8-sig")
print(f"ASS: {ass_path} ({len(subs)} entries)")

# --- Step 5: Burn subtitles ---
shutil.copy2(ass_path, "C:/temp/portrait_subs.ass")
final = OUTPUT / "test_portrait_10s.mp4"
env = {**__import__('os').environ, "MSYS2_ARG_CONV_EXCL": "*"}
subprocess.run([
    "ffmpeg", "-y", "-i", str(trimmed),
    "-vf", "ass='C\\:/temp/portrait_subs.ass':original_size=544x960",
    "-c:v", "libx264", "-preset", "medium", "-crf", "23",
    "-c:a", "copy", str(final)
], check=True, capture_output=True, env=env)

print(f"\n✅ 完成! 输出: {final}")
print(f"   分辨率: {pw}x{ph} 竖屏")
print(f"   字体: {FONT_NAME} 加粗 {FONT_SIZE}号 / 重点词 {FONT_SIZE_HL}号黄色")
