#!/usr/bin/env python3
"""
口播视频剪辑 Agent v1.2
=========================
专用子 agent，负责口播视频的全自动剪辑。

功能：
1. 检测并裁剪：沉默(>1s)、语气词(嗯啊呃)、重复内容、废话
2. 背景模糊 + 人物锐化 (OpenCV人脸检测)
3. 智能字幕 (ASS格式，汉仪中黑体加粗 54号，重点词60号黄色高亮，智能换行)

⚠️ 已知陷阱见: video-agent/SKILL.md → 🪤 已知陷阱
   Windows路径转义、ASS Bold=1、禁止\rStyle、DirectWrite字体名等
   每次修改/部署前先读 SKILL.md 的陷阱章节。
"""

import json
import subprocess
import time
import sys
import re
from pathlib import Path

import cv2
import numpy as np

# ============================================================
# 配置
# ============================================================
PROJECT_DIR = Path(__file__).parent
ORIGINAL_VIDEO = Path(r"D:\Documents\Desktop\23b3412458bd8d6a2659e950bf5c9c14.mp4")
TRANSCRIPT_FILE = PROJECT_DIR / "transcript.json"
OUTPUT_DIR = PROJECT_DIR / "output"
TEMP_DIR = PROJECT_DIR / "temp"
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# 字体设置
FONT_NAME = "HYZhongHei 197"     # 汉仪中黑体（Windows注册名，已预装）
FONT_FALLBACK = "SimHei"
FONT_SIZE = 54            # 正文字号
FONT_SIZE_HIGHLIGHT = 60  # 重点词字号
FONT_COLOR = "&H00FFFFFF"      # 白色
FONT_COLOR_HIGHLIGHT = "&H0000FFFF"  # 黄色 (ASS: &HAABBGGRR)

# 模糊参数
BLUR_RADIUS = 6          # boxblur 半径（简单模糊，用户要求不复杂）
BLUR_POWER = 2           # boxblur power
MASK_LOW = 0.02          # 人物遮罩低阈值：<0.02=背景噪声砍掉
MASK_HIGH = 0.25         # 人物遮罩高阈值：>0.25=完全清晰（含胳膊等低置信区域）
FEATHER_RADIUS = 7       # 羽化半径（像素），5-10 柔化人物边缘避免生硬割裂

# 编码质量
VIDEO_BITRATE = "6000k"  # 视频码率（原片高于1080P，设高质量）

# 沉默阈值
SILENCE_THRESHOLD = 1.0  # 超过1秒沉默视为气口

# 语气词列表 (仅确凿无疑的语气词，避免误伤内容词)
FILLER_WORDS = {
    "嗯": 0.3, "啊": 0.3, "呃": 0.3, "哦": 0.3,
    "哎": 0.3, "诶": 0.3, "呀": 0.3, "嘛": 0.3,
    "啦": 0.3, "哈": 0.3, "嚯": 0.3,
}

# Whisper 错字修正词典
CORRECTIONS = {
    "时工钱多": "施工前", "动线每一会儿": "动线没画", "时工对黑": "施工队黑",
    "守五王哪身": "手往哪伸", "红风成一三": "红枫×3", "元宝风成一二": "元宝枫×2",
    "从客厅到水井": "从客厅到水景", "踩一脚衣": "踩一脚泥", "洞个脑子": "动动脑子",
    "叶竹省": "业主审", "怎么省它": "怎么省事", "砸迟毕": "砸池壁",
    "拿枝笔": "拿支笔", "拿着笔": "拿支笔", "循环笵": "循环泵",
    "时工": "施工", "鞋俩字": "写俩字", "绿花袋": "绿化带", "厅步路": "汀步路",
    "红风": "红枫", "元宝风": "元宝枫", "贯笵": "冠幅", "笵坑": "泵坑",
    "迟毕": "池壁", "守五": "手", "数官": "树冠", "数长": "树长", "数种": "树种",
    "掌开": "长开", "兼具": "间距", "石拔": "石板", "水井": "水景",
    "挖两壳": "挖了两棵", "挖两棵": "挖了两棵", "五位书": "五位数",
    "指标了": "只标了", "管先": "管线", "交结": "胶粘", "沾死": "粘死",
    "水准": "水景", "稳资": "文字", "笵": "泵", "堆": "队", "王": "往",
    "蕾": "雷", "流": "留", "巳": "已",
    # ===== 以下修正有顺序依赖，必须 长→短 排序 =====
    "拖写": "拖鞋",
    "是图上埋了三个雷": "是图纸上埋了三个雷",
    "不是时工多了坑了": "不是施工队坑了",
    "时工多最怕你看懂的三个图纸细节": "施工队最怕你看懂的三个图纸细节",
    "重下去三年后": "种下去三年后",
    "时工多": "施工队",
    "重下去": "种下去",
    "是图上": "是图纸上",
}

# 重点词（高亮为黄色60号加粗）
KEY_TERMS = [
    "8万", "八万", "十一万", "五位数", "三个雷", "好几万",
    "汀步路", "绿化带", "循环泵", "冠幅", "树冠",
    "石板", "管线", "池壁", "施工队", "业主",
    "动线", "水景", "检修口", "红枫", "元宝枫",
]

# 数字模式（用于高亮）
NUM_PATTERN = re.compile(r'[零一二三四五六七八九十百千万亿\d]+[万千百]*[万千百]*')

# 新增：用户审定的断句方案文件
SEGMENTED_FILE = PROJECT_DIR / "transcript_segmented.json"


# ============================================================
# 工具函数
# ============================================================
def fix(text):
    """
    修正 Whisper 错字。

    策略：在**原始文本**中找到所有修正匹配的位置，按位置+长度排序，
    重叠冲突时最长 key 获胜，最后从右到左一次性执行。
    这样不会出现「拖写→拖鞋」被后续「鞋→写」覆盖的 bug。
    """
    # 1. 搜集所有匹配
    matches = []  # (pos_in_original, len(w), w, c)
    for w, c in CORRECTIONS.items():
        start = 0
        while True:
            pos = text.find(w, start)
            if pos == -1:
                break
            matches.append((pos, len(w), w, c))
            start = pos + 1

    if not matches:
        return text

    # 2. 按位置 → 按 key 长度降序排序
    matches.sort(key=lambda x: (x[0], -x[1]))

    # 3. 解决重叠冲突：最长 key 获胜
    resolved = []
    for pos, length, w, c in matches:
        if resolved:
            last_pos, last_len, _, _ = resolved[-1]
            if pos < last_pos + last_len:
                continue  # 与上一条已选中的重叠 → 跳过
        resolved.append((pos, length, w, c))

    # 4. 从右到左应用
    result = text
    for pos, length, w, c in reversed(resolved):
        result = result[:pos] + c + result[pos + len(w):]

    return result


def get_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def ts(sec):
    """秒 -> ASS 时间格式 H:MM:SS.cc"""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int((sec - int(sec)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ts_srt(sec):
    """秒 -> SRT 时间格式"""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ============================================================
# 分析模块：检测沉默、语气词、重复
# ============================================================
def find_first_word(transcript_path):
    with open(transcript_path, encoding="utf-8") as f:
        data = json.load(f)
    for seg in data["segments"]:
        for w in seg.get("words", []):
            return w["start"]
    return 5.16


def find_silence(transcript_path, after=0, min_gap=SILENCE_THRESHOLD):
    """检测超过阈值(默认1s)的沉默段落，包括段间。"""
    with open(transcript_path, encoding="utf-8") as f:
        data = json.load(f)
    cuts = []

    # 段内
    for seg in data["segments"]:
        words = seg.get("words", [])
        for i in range(1, len(words)):
            gap = words[i]["start"] - words[i-1]["end"]
            if gap > min_gap:
                s = words[i-1]["end"] + 0.04
                e = words[i]["start"] - 0.04
                if e > s and s >= after:
                    cuts.append((s, e, f"沉默({gap:.1f}s)"))

    # 段间
    for i in range(1, len(data["segments"])):
        prev_w = data["segments"][i-1].get("words", [])
        curr_w = data["segments"][i].get("words", [])
        if prev_w and curr_w:
            gap = curr_w[0]["start"] - prev_w[-1]["end"]
            if gap > min_gap:
                s = prev_w[-1]["end"] + 0.04
                e = curr_w[0]["start"] - 0.04
                if e > s and s >= after:
                    cuts.append((s, e, f"段间沉默({gap:.1f}s)"))

    return cuts


def find_fillers(transcript_path, after=0):
    """检测语气词(嗯啊呃)和废话。"""
    with open(transcript_path, encoding="utf-8") as f:
        data = json.load(f)
    cuts = []
    filler_set = set(FILLER_WORDS.keys())
    longer_fillers = sorted([k for k in FILLER_WORDS if len(k) > 1], key=lambda x: -len(x))

    for seg in data["segments"]:
        words = seg.get("words", [])
        for w in words:
            word = w["word"].strip().lower()
            if not word:
                continue
            # 检测多字语气词优先
            hit = None
            for f in longer_fillers:
                if f in word or word in f:
                    hit = f
                    break
            if hit is None and word in filler_set:
                hit = word

            if hit:
                margin = FILLER_WORDS.get(hit, 0.3)
                s = max(w["start"] - margin, 0)
                e = min(w["end"] + margin, seg["end"])
                if s >= after and e > s:
                    cuts.append((s, e, f"语气词:{hit}"))

    return cuts


def find_repeats(transcript_path, after=0):
    """检测重复内容（段间+段内）。"""
    with open(transcript_path, encoding="utf-8") as f:
        data = json.load(f)
    repeats = []

    # 段间重复
    for i in range(1, len(data["segments"])):
        prev_text = fix(data["segments"][i-1]["text"])
        curr_text = fix(data["segments"][i]["text"])
        prev_w = data["segments"][i-1].get("words", [])
        curr_w = data["segments"][i].get("words", [])

        if not prev_w or not curr_w:
            continue

        # 寻找前段尾部与后段头部的重复
        for n in range(min(40, len(prev_text), len(curr_text)), 3, -1):
            tail = prev_text[-n:].strip("，。！？、； ")
            head = curr_text[:n].strip("，。！？、； ")
            if tail and len(tail) >= 5 and tail[:max(1, len(tail)//2)] in head:
                # 在 prev_words 中定位重复开始位置
                overlap = tail
                start_chars = len(prev_text) - len(overlap)
                char_ratio = start_chars / max(len(prev_text), 1)
                word_idx = int(char_ratio * len(prev_w))
                word_idx = max(0, min(word_idx, len(prev_w) - 1))
                s = prev_w[word_idx]["start"]
                e = prev_w[-1]["end"]
                if s >= after and e > s + 0.3:
                    repeats.append((s, e, f"重复:{overlap[:15]}..."))
                break

    # 段内重复（相邻短语重复）
    for seg in data["segments"]:
        text = fix(seg["text"])
        words = seg.get("words", [])
        if not words:
            continue

        # 按逗号拆分短语
        phrases = re.split(r'(?<=[，,])', text)
        phrases = [p.strip() for p in phrases if p.strip()]

        seen = {}
        for idx, phrase in enumerate(phrases):
            key = phrase.strip("，。！？、；： ")
            if len(key) < 4:
                continue
            if key in seen and idx - seen[key] <= 2:
                # 找到重复
                cum_chars = sum(len(p) for p in phrases[:idx])
                char_ratio = cum_chars / max(len(text), 1)
                word_pos = int(char_ratio * len(words))
                word_pos = max(0, min(word_pos, len(words) - 1))
                end_ratio = (cum_chars + len(phrase)) / max(len(text), 1)
                end_pos = int(end_ratio * len(words))
                end_pos = max(0, min(end_pos, len(words) - 1))
                s = words[word_pos]["start"]
                e = words[end_pos]["end"]
                if s >= after and e > s + 0.3:
                    repeats.append((s, e, f"重复:{key[:15]}..."))
            seen[key] = idx

    # 3. 段内连续短语重复检测（放开阈值，捕获"觉得有用吗,收藏这期,觉得有用吗,收藏这期"模式）
    for seg in data["segments"]:
        text = fix(seg["text"])
        words = seg.get("words", [])
        if not words:
            continue

        # 按逗号/句号拆分
        phrases = re.split(r'(?<=[，,。.!?！？])', text)
        phrases = [p.strip() for p in phrases if p.strip()]

        seen2 = {}
        for idx, phrase in enumerate(phrases):
            key = phrase.strip("，。！？、；： ")
            if len(key) < 3:
                continue
            if key in seen2 and idx - seen2[key] <= 5:
                # 找到重复段 — 标记重复部分
                first_cum = sum(len(phrases[j]) for j in range(seen2[key]))
                end_cum = first_cum + len(phrase) * 2  # approximate
                char_ratio = first_cum / max(len(text), 1)
                word_pos = int(char_ratio * len(words))
                word_pos = max(0, min(word_pos, len(words) - 1))
                end_ratio = min(1.0, end_cum / max(len(text), 1))
                end_pos = int(end_ratio * len(words))
                end_pos = max(0, min(end_pos, len(words) - 1))
                s = words[word_pos]["start"]
                e = words[end_pos]["end"]
                if s >= after and e > s + 0.3:
                    repeats.append((s, e, f"重复:{key[:12]}..."))
            seen2[key] = idx

    return repeats


# ============================================================
# 模糊模块：人物-背景分离
# ============================================================
SEGMENTER_MODEL = Path(__file__).parent / "temp" / "selfie_segmenter.tflite"
_SEGMENTER_CACHE = [None]  # module-level lazy singleton


def _get_segmenter():
    """Lazy init MediaPipe ImageSegmenter (model loaded once)."""
    if _SEGMENTER_CACHE[0] is None and SEGMENTER_MODEL.exists():
        from mediapipe.tasks.python.vision import (
            ImageSegmenter, ImageSegmenterOptions, RunningMode,
        )
        from mediapipe.tasks.python.core.base_options import BaseOptions
        opts = ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=str(SEGMENTER_MODEL)),
            running_mode=RunningMode.IMAGE,
            output_confidence_masks=True,
        )
        _SEGMENTER_CACHE[0] = ImageSegmenter.create_from_options(opts)
    return _SEGMENTER_CACHE[0]


def blur_video(input_path, output_path, trim_seconds, max_duration=0):
    """
    人物-背景分离 + 背景模糊。

    Phase 1 — FFmpeg boxblur 预模糊全帧（GPU 加速）
    Phase 2 — MediaPipe 全人分割 → 合成（sharp person + blurred bg）
    """
    print(f"  [模糊] 处理中 (trim={trim_seconds:.1f}s)...")
    t0 = time.time()

    # === Phase 1: FFmpeg 全帧 boxblur ===
    temp_blur = TEMP_DIR / "blur_base.mp4"
    subprocess.run([
        "ffmpeg", "-i", str(input_path),
        "-ss", str(trim_seconds),
        "-vf", f"boxblur={BLUR_RADIUS}:{BLUR_POWER}",
        "-c:v", "h264_mf", "-b:v", VIDEO_BITRATE,
        "-an", "-y", str(temp_blur)
    ] + (["-t", str(max_duration)] if max_duration > 0 else []), check=True, capture_output=True)
    print(f"  [模糊] 预模糊 ({time.time()-t0:.0f}s)")

    # === Phase 2: 全人分割 + 合成 ===
    cap_orig = cv2.VideoCapture(str(input_path))
    cap_blur = cv2.VideoCapture(str(temp_blur))
    fps = cap_orig.get(cv2.CAP_PROP_FPS)
    width = int(cap_orig.get(3))
    height = int(cap_orig.get(4))
    total = int(cap_orig.get(cv2.CAP_PROP_FRAME_COUNT))

    skip = int(trim_seconds * fps)
    cap_orig.set(cv2.CAP_PROP_POS_MSEC, trim_seconds * 1000)
    remaining = total - skip
    if max_duration > 0:
        max_frames = int(max_duration * fps)
        if remaining > max_frames:
            remaining = max_frames

    # Pipe to FFmpeg
    ffmpeg_proc = subprocess.Popen([
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{width}x{height}", "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "h264_mf", "-b:v", VIDEO_BITRATE,
        "-an", "-y", str(output_path)
    ], stdin=subprocess.PIPE)

    # MediaPipe person segmenter
    segmenter = _get_segmenter()
    from mediapipe import Image as MpImage, ImageFormat

    current_mask = None
    detect_every = 8       # 每 8 帧跑一次分割，中间帧复用
    frame_idx = 0
    interval = max(1, remaining // 10)
    processed = 0

    while True:
        ret_o, frame_o = cap_orig.read()
        ret_b, frame_b = cap_blur.read()
        if not ret_o or not ret_b:
            break
        if processed >= remaining:
            break

        frame_idx += 1

        # 每 detect_every 帧跑一次分割
        if (frame_idx % detect_every == 1) or current_mask is None:
            if segmenter is not None:
                rgb = cv2.cvtColor(frame_o, cv2.COLOR_BGR2RGB)
                mp_img = MpImage(image_format=ImageFormat.SRGB, data=rgb)
                seg_result = segmenter.segment(mp_img)
                # confidence_masks[0] = person confidence (H, W, 1) float32
                current_mask = seg_result.confidence_masks[0].numpy_view().squeeze()

        # 合成：sharp person + blurred background
        # 对比度拉伸 → 保证人物中心完全清晰，高斯模糊边缘做羽化
        if current_mask is not None:
            mask_boosted = np.clip(
                (current_mask - MASK_LOW) / (MASK_HIGH - MASK_LOW), 0, 1
            )
            # 羽化：高斯模糊 mask 柔化边缘，避免人物与背景生硬割裂
            if FEATHER_RADIUS > 0:
                mask_boosted = cv2.GaussianBlur(
                    mask_boosted, (0, 0), FEATHER_RADIUS
                )
            m3 = np.stack([mask_boosted] * 3, axis=-1)
            comp = (frame_o * m3 + frame_b * (1 - m3)).astype(np.uint8)
        else:
            comp = frame_b  # fallback: 全帧模糊

        ffmpeg_proc.stdin.write(comp.tobytes())

        processed += 1
        if processed % interval == 0:
            el = time.time() - t0
            speed = processed / el
            eta = (remaining - processed) / speed
            print(f"    {processed/remaining*100:.0f}% ({speed:.0f}fps, ETA {eta:.0f}s)")

    cap_orig.release()
    cap_blur.release()
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()
    print(f"  [模糊] 完成 ({time.time()-t0:.0f}s)")


# ============================================================
# 裁剪模块
# ============================================================
def cut_main(blurred_path, audio_path, all_cuts, trim_start):
    """执行裁剪：用 filter_complex select 一次性完成（NVENC 编码）。"""
    adj_cuts = [(s - trim_start, e - trim_start) for s, e, _ in all_cuts]
    segments = []
    prev = 0.0
    for s, e in adj_cuts:
        if s > prev + 0.05:
            segments.append((prev, s))
        prev = e
    bdur = get_dur(blurred_path)
    if bdur > prev + 0.05:
        segments.append((prev, bdur))

    print(f"  [裁剪] 保留 {len(segments)} 段, 裁剪 {len(all_cuts)} 处")
    tv = TEMP_DIR / "tv.mp4"
    ta = TEMP_DIR / "ta.aac"

    if not segments:
        subprocess.run(["ffmpeg", "-i", str(blurred_path), "-c", "copy",
                       "-y", str(tv)], check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-i", str(audio_path), "-c", "copy",
                       "-y", str(ta)], check=True, capture_output=True)
        return tv, ta

    # select 表达式: select='between(t,0,30)+between(t,35,69)+...'
    select_expr = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in segments)

    # 视频: select 保留段 → setpts 压缩时间线 → MF 编码
    subprocess.run([
        "ffmpeg", "-i", str(blurred_path),
        "-filter_complex",
        f"select='{select_expr}',setpts=N/FRAME_RATE/TB",
        "-c:v", "h264_mf", "-b:v", VIDEO_BITRATE,
        "-an", "-y", str(tv)
    ], check=True, capture_output=True)

    # 音频: aselect → asetpts → AAC
    subprocess.run([
        "ffmpeg", "-i", str(audio_path),
        "-filter_complex",
        f"aselect='{select_expr}',asetpts=N/SR/TB",
        "-c:a", "aac", "-b:a", "128k",
        "-y", str(ta)
    ], check=True, capture_output=True)

    return tv, ta


# ============================================================
# 字幕模块：ASS格式，风尚黑体，混合样式，智能换行
# ============================================================
def build_subtitles(transcript_path, cuts, trim_start):
    """构建字幕条目，基于 Whisper 词级时间戳。"""
    with open(transcript_path, encoding="utf-8") as f:
        data = json.load(f)

    all_words = []
    for seg in data["segments"]:
        for w in seg.get("words", []):
            t = w["word"].strip()
            # 剔除字词中的全部标点（Whisper 经常把逗号贴在字上）
            t = re.sub(r'[，,。．！？、；：!?.\'\"()（）【】《》「」『』﹁﹂—…·]', '', t)
            if t:
                all_words.append((w["start"], w["end"], t))

    # 分组：2~8 字为一个字幕条，在气口处断开
    PUNCT_RE = re.compile(r"[　、。，『』「」！？．《》；：!?.,;'()（）【】「」『』╱╲—…·]")
    subs = []
    group = []

    for w_start, w_end, text in all_words:
        group.append((w_start, w_end, text))
        should_break = False
        # 词间停顿 >0.35s
        if len(group) > 1 and (group[-1][0] - group[-2][1]) > 0.35:
            should_break = True
        # 单句最多 8 个字
        if len(group) >= 8:
            should_break = True

        if should_break:
            combined = "".join(w[2] for w in group).strip()
            combined = PUNCT_RE.sub('', combined)
            combined = fix(combined)
            if len(combined) >= 2:
                subs.append((group[0][0], group[-1][1], combined))
            elif combined and subs:
                prev_s, prev_e, prev_text = subs[-1]
                subs[-1] = (prev_s, max(prev_e, w_end), prev_text + combined)
            group = []

    if group:
        combined = "".join(w[2] for w in group).strip()
        combined = PUNCT_RE.sub('', combined)
        combined = fix(combined)
        if len(combined) >= 2:
            subs.append((group[0][0], group[-1][1], combined))
        elif combined and subs:
            prev_s, prev_e, prev_text = subs[-1]
            subs[-1] = (prev_s, max(prev_e, group[-1][1]), prev_text + combined)


    # 调整时间轴（考虑裁剪）
    def cut_before(t):
        c = 0.0
        for s, e, _ in cuts:
            if e <= t:
                c += (e - s)
            elif s < t < e:
                c += (t - s)
        return c + trim_start

    adjusted = []
    for s, e, text in subs:
        ns = s - cut_before(s)
        ne = e - cut_before(e)
        if ne > ns + 0.15 and text:
            adjusted.append((ns, ne, text))

    return adjusted


def build_subtitles_from_segmented(transcript_path, segmented_path, cuts, trim_start):
    """
    Match user lines to timing by finding each line in the CORRECTED
    Whisper text (which matches the user's edited text), then mapping
    the character position back to Raw word timestamps.

    Strategy:
    1. Build corrected full text (fix() applied to concatenated raw)
    2. For each user line, find exact match in corrected text
    3. Use character position to look up the nearest Raw word timestamp
    4. End of line N = start of line N+1
    """
    import json, re
    with open(transcript_path, encoding="utf-8") as f:
        whisper_data = json.load(f)
    with open(segmented_path, encoding="utf-8") as f:
        seg_data = json.load(f)

    user_lines = [s["text"] for s in seg_data["segments"]]

    # Collect raw words (no punctuation)
    PUNCT_RE = re.compile(r"[　、。，『』「」！？．《》；：!?.,;'()（）【】「」『』╱╲—…·]")
    raw_words = []  # [(start, end, text)]
    for seg in whisper_data["segments"]:
        for w in seg.get("words", []):
            t = w["word"].strip()
            t = PUNCT_RE.sub('', t)
            if t:
                raw_words.append((w["start"], w["end"], t))

    if not raw_words:
        return []

    # Build raw concatenated text + char-to-word mapping
    full_raw = "".join(w[2] for w in raw_words)
    char_to_word = []
    for wi, (_, _, txt) in enumerate(raw_words):
        for _ in txt:
            char_to_word.append(wi)

    # Build corrected full text (fix() on concatenated text, catches all corrections)
    full_corrected = fix(full_raw)

    # Match each user line in corrected text; use position to get raw word timestamp
    subs = []
    search_pos = 0
    unmatched = []

    for text in user_lines:
        if not text:
            continue
        p = full_corrected.find(text, search_pos)
        if p >= 0:
            # Position in corrected ≈ position in raw (same-length corrections)
            wi = char_to_word[min(p, len(char_to_word) - 1)]
            subs.append((raw_words[wi][0], text))
            search_pos = p + 1  # advance past first char
        else:
            unmatched.append(text)

    if unmatched:
        print(f"  [WARN] {len(unmatched)} lines unmatched in corrected text:")
        for t in unmatched[:5]:
            print(f"    {t}")
        # Fill unmatched with proportional estimate
        for text in unmatched:
            total_chars = sum(len(t[1]) for t in subs) + sum(len(t) for t in unmatched)
            if total_chars < 1:
                continue
            cum_before = 0
            user_order = list(dict.fromkeys([s[1] for s in subs] + unmatched))
            for t in user_order:
                if t == text:
                    break
                cum_before += len(t)
            total_dur = raw_words[-1][1] - raw_words[0][0]
            estimate = raw_words[0][0] + (cum_before / total_chars) * total_dur
            if subs:
                estimate = max(estimate, subs[-1][0] + 0.3)
            subs.append((estimate, text))

    subs.sort(key=lambda x: x[0])

    # Convert start times to (start, end) pairs
    # Duration = max(reading speed, natural gap) — no overlap
    subs_out = []
    for i in range(len(subs)):
        start, text = subs[i]
        read_time = max(0.8, len(text) * 0.18 + 0.3)
        if i + 1 < len(subs):
            next_start = subs[i + 1][0]
            gap = next_start - start
            duration = max(read_time, gap)
            end = start + duration
            # Never overlap next subtitle
            if end > next_start - 0.05:
                end = next_start - 0.05
        else:
            end = start + max(1.0, read_time)
        if end - start > 6.0:
            end = start + 6.0
        subs_out.append((start, end, text))

    # Adjust for cuts
    def cut_before(t):
        c = 0.0
        for s, e, _ in cuts:
            if e <= t:
                c += (e - s)
            elif s < t < e:
                c += (t - s)
        return c + trim_start

    # Adjust for cuts + enforce minimum readable durations
    raw_adjusted = []
    for s, e, text in subs_out:
        ns = s - cut_before(s)
        ne = e - cut_before(e)
        if text:
            raw_adjusted.append((ns, ne, text))

    # Post-process: enforce minimum 0.7s per subtitle, no overlaps
    adjusted = []
    for i in range(len(raw_adjusted)):
        s, e, text = raw_adjusted[i]
        # Calculate minimum readable duration
        read_time = max(0.7, len(text) * 0.18 + 0.3)
        # Enforce minimum
        if e - s < read_time:
            e = s + read_time
        # No overlap with next subtitle
        if i + 1 < len(raw_adjusted):
            next_s = raw_adjusted[i + 1][0]
            if e > next_s - 0.05:
                e = next_s - 0.05
        # Max cap
        if e - s > 6.0:
            e = s + 6.0
        # Only skip if truly zero-length after all adjustments
        if e - s >= 0.1:
            adjusted.append((s, e, text))

    # Self-check
    too_short = sum(1 for s,e,t in adjusted if e-s < 0.7)

    # 右向左借时间：短字幕 < 0.7s 的从前一条字幕借时间
    # 策略：从右往左遍历，短字幕向后伸长到 0.7s，不够的部分从前一条的 end 处扣
    for i in range(len(adjusted) - 1, -1, -1):
        s, e, text = adjusted[i]
        dur = e - s
        if dur >= 0.7:
            continue
        need = 0.7 - dur  # 还差多少秒
        if i == 0:
            # 第一条字幕，只能自己扛
            adjusted[i] = (s, s + 0.7, text)
        else:
            prev_s, prev_e, prev_text = adjusted[i - 1]
            # 前一条至少保留 0.7s（或它的阅读时间，取较大值）
            prev_min = prev_s + max(0.7, len(prev_text) * 0.18 + 0.3)
            borrow = min(need, prev_e - prev_min)
            if borrow > 0.01:
                adjusted[i - 1] = (prev_s, prev_e - borrow, prev_text)
                adjusted[i] = (s, e + borrow, text)
            # 借不够也尽力了，不强行拉长以免重叠

    # Re-check after fix
    still_short = sum(1 for s,e,t in adjusted if e-s < 0.7)
    if too_short:
        print(f"  [WARN] {too_short}/{len(adjusted)} subs < 0.7s (fast speech)")
        for s,e,t in adjusted:
            if e-s < 0.7:
                print(f"    {s:.1f}s-{e:.1f}s ({e-s:.2f}s) {t}")
    if still_short and still_short < too_short:
        print(f"  [FIX] 右向左借时间修复了 {too_short-still_short}/{too_short} 条短字幕")

    print(f"  [Subs] {len(adjusted)}/{len(user_lines)} subs, {too_short} short")
    return adjusted
def format_subtitle_line(text):
    """
    智能换行规则：
    - 逗号/句号后如果只剩1-2个字符 → 换行到下一行
    - 不允许 "一句话说完，又" 同行的格式
    """
    for punct in "，,。.!?？；;、":
        # 从右往左找标点
        idx = text.rfind(punct)
        if idx >= 0 and idx < len(text) - 1:
            after = text[idx+1:].strip()
            if len(after) <= 2:
                text = text[:idx+1] + "\\N" + after
                break
    return text


def auto_wrap_text(text, max_chars=22):
    """
    自动折行：每行最多 max_chars 字符，在标点处断开。
    """
    if len(text) <= max_chars:
        return text

    result = ""
    while len(text) > max_chars:
        # 在 max_chars 范围内找最后一个标点断行
        break_pos = -1
        for i in range(max_chars, max_chars // 2, -1):
            if i < len(text) and text[i] in "，,。.!?？；;、：: ":
                break_pos = i + 1
                break
        if break_pos == -1:
            break_pos = max_chars

        result += text[:break_pos].strip() + "\\N"
        text = text[break_pos:].strip()

    result += text
    return result


def is_keyword(word):
    """判断是否为需要高亮的重点词。"""
    if word in KEY_TERMS:
        return True
    if NUM_PATTERN.fullmatch(word):
        return True
    # 包含数字的词
    if any(ch.isdigit() or ch in "零一二三四五六七八九十百千万亿" for ch in word):
        return True
    return False


def build_ass_text(text):
    """
    将普通文本转为带 ASS 格式标记的文本。
    重点词加大黄色加粗，普通词白色。
    """
    if not text:
        return text

    # 使用配置的字体大小
    tags_close = f"{{\\fs{FONT_SIZE}\\c&H00FFFFFF&\\b1}}"
    tags_hl = f"{{\\fs{FONT_SIZE_HIGHLIGHT}\\c&H0000FFFF&\\b1}}"

    result = ""
    i = 0
    while i < len(text):
        matched = False
        # 先匹配 KEY_TERMS（长词优先）
        for term in sorted(KEY_TERMS, key=lambda x: -len(x)):
            if text[i:i+len(term)] == term:
                result += tags_hl + term + tags_close
                i += len(term)
                matched = True
                break
        if matched:
            continue
        # 再匹配数字模式
        m = NUM_PATTERN.match(text, i)
        if m and len(m.group()) >= 1:
            word = m.group()
            result += tags_hl + word + tags_close
            i += len(word)
            continue
        # 普通字符
        result += text[i]
        i += 1

    return result


def write_ass(subtitles, path, width, height):
    """生成 ASS 字幕文件（支持混合样式、智能换行）。"""
    lines = [
        "[Script Info]",
        f"Title: 口播字幕",
        "ScriptType: v4.00+",
        "Collisions: Normal",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "Timer: 100.0000",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{FONT_NAME},{FONT_SIZE},{FONT_COLOR},&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,1,2,10,10,120,134",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for s, e, text in subtitles:
        # 按原始标点换行
        display_text = format_subtitle_line(text)
        # 手动再加一层：超长文本自动在标点处折行
        # 每行最多25个字
        display_text = auto_wrap_text(display_text, max_chars=22)
        # ASS 标记（重点词高亮）
        marked_text = build_ass_text(display_text)
        if marked_text == display_text:
            marked_text = display_text

        lines.append(
            f"Dialogue: 0,{ts(s)},{ts(e)},Default,,0,0,0,,{marked_text}"
        )

    path.write_text("\n".join(lines), encoding="utf-8-sig")
    print(f"  [字幕] ASS: {len(subtitles)} 条 ({FONT_NAME} {FONT_SIZE}号)")


# ============================================================
# 渲染模块：合成最终视频
# ============================================================
def mux_av(video_path, audio_path, output_path):
    """合成视频+音频。"""
    subprocess.run([
        "ffmpeg", "-i", str(video_path), "-i", str(audio_path),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0", "-shortest",
        "-y", str(output_path)
    ], check=True, capture_output=True)


def burn_ass(video_path, ass_path, output_path):
    """烧录 ASS 字幕到视频。"""
    print(f"  [渲染] 烧录字幕...")
    ass_esc = str(ass_path).replace("\\", "/").replace(":", "\\:")
    subprocess.run([
        "ffmpeg", "-i", str(video_path),
        "-vf", f"ass='{ass_esc}'",
        "-c:v", "h264_mf", "-b:v", VIDEO_BITRATE,
        "-c:a", "copy",
        "-y", str(output_path)
    ], check=True, capture_output=True)


# ============================================================
# 快速验证：CORRECTIONS 匹配率（不跑完整 pipeline）
# ============================================================
def test_corrections():
    """
    仅运行字幕匹配逻辑，验证 CORRECTIONS 的匹配效果。
    不依赖视频文件，5秒内输出报告。

    用法: python sub_agent.py --test-corrections
    """
    import json, re

    if not SEGMENTED_FILE.exists():
        print(f"  ❌ 未找到审定断句文件: {SEGMENTED_FILE}")
        return

    with open(TRANSCRIPT_FILE, encoding="utf-8") as f:
        whisper_data = json.load(f)
    with open(SEGMENTED_FILE, encoding="utf-8") as f:
        seg_data = json.load(f)

    user_lines = [s["text"] for s in seg_data["segments"]]

    # Collect raw words (no punctuation)
    PUNCT_RE = re.compile(r"[　、。，『』「」！？．《》；：!?.,;'()（）【】「」『』╱╲—…·]")
    raw_words = []
    for seg in whisper_data["segments"]:
        for w in seg.get("words", []):
            t = PUNCT_RE.sub('', w["word"].strip())
            if t:
                raw_words.append((w["start"], w["end"], t))

    if not raw_words:
        print("  ❌ 无词级时间戳，无法验证")
        return

    # Build raw concatenated text + char-to-word mapping
    full_raw = "".join(w[2] for w in raw_words)
    char_to_word = []
    for wi, (_, _, txt) in enumerate(raw_words):
        for _ in txt:
            char_to_word.append(wi)

    full_corrected = fix(full_raw)

    # Show corrections effect
    print(f"\n{'='*60}")
    print(f"  CORRECTIONS 验证")
    print(f"{'='*60}")
    print(f"  原始文本({len(full_raw)}字) → 修正文本({len(full_corrected)}字)")
    print(f"  修正条目: {len(CORRECTIONS)} 条")

    # Show corrected vs raw diff
    diffs = []
    for w, c in sorted(CORRECTIONS.items(), key=lambda x: -len(x[0])):
        if w in full_raw:
            diffs.append((full_raw.find(w), f"  ✓ {w} → {c}"))
    diffs.sort()
    if diffs:
        print(f"  原始中触发修正:")
        for _, d in diffs[:15]:
            print(d)
        if len(diffs) > 15:
            print(f"  ... 还有 {len(diffs) - 15} 处")

    # Match each user line
    subs = []
    unmatched = []
    matched_at = []
    search_pos = 0

    for text in user_lines:
        if not text:
            continue
        p = full_corrected.find(text, search_pos)
        if p >= 0:
            wi = char_to_word[min(p, len(char_to_word) - 1)]
            subs.append((raw_words[wi][0], text))
            matched_at.append((p, text))
            search_pos = p + 1
        else:
            unmatched.append(text)

    subs.sort(key=lambda x: x[0])

    total = len(user_lines)
    matched = len(subs)
    rate = matched / total * 100

    print(f"\n{'─'*50}")
    print(f"  匹配率: {matched}/{total} ({rate:.1f}%)")
    print(f"{'─'*50}")

    if unmatched:
        print(f"\n  ❌ {len(unmatched)} 条未匹配:")
        for i, t in enumerate(unmatched):
            print(f"  {i+1:2d}. 「{t}」")
            # Suggest possible fix
            if len(t) >= 2:
                for w in raw_words:
                    word = w[2]
                    if len(word) >= 2 and (word[:3] in t or t[:3] in word):
                        if fix(word) != word:
                            print(f"     相关修正: {word} → {fix(word)}")

    # Timing preview
    print(f"\n  时间轴预览 (前 20 条 + 末 5 条):")
    preview_indices = list(range(min(20, len(subs))))
    if len(subs) > 25:
        preview_indices += list(range(len(subs) - 5, len(subs)))

    short_count = 0
    overlap_count = 0
    for idx in preview_indices:
        start, text = subs[idx]
        if idx + 1 < len(subs):
            next_start = subs[idx + 1][0]
            gap = next_start - start
            read_time = max(0.8, len(text) * 0.18 + 0.3)
            if gap > read_time:
                dur = gap
            else:
                dur = read_time
            if dur > next_start - start - 0.05:
                dur = next_start - start - 0.05
            dur = max(0.7, dur)
        else:
            dur = max(1.0, len(text) * 0.18 + 0.3)

        tag = "✓"
        if dur < 0.7:
            tag = "⚠短"
            short_count += 1
        elif dur > 5.0:
            tag = "⚠长"

        if len(subs) > 25 and idx == 20:
            print(f"  ... ({len(subs) - 25} 条中间省略)")

        print(f"  {start:6.1f}s → {start+dur:6.1f}s ({dur:4.1f}s) {tag} {text}")

    # Full overlap check
    overlaps = []
    for i in range(len(subs) - 1):
        s1 = subs[i][0]
        s2 = subs[i + 1][0]
        _, t1 = subs[i]
        read1 = max(0.8, len(t1) * 0.18 + 0.3)
        e1 = s1 + read1
        if e1 > s2 - 0.05:
            overlaps.append((t1, subs[i+1][1], e1 - (s2 - 0.05)))

    if overlaps:
        overlap_count = len(overlaps)
        print(f"\n  ⚠️  {overlap_count} 处潜在重叠:")
        for t1, t2, ov in overlaps[:5]:
            print(f"     「{t1}」→「{t2}」 重叠 {ov:.1f}s")

    # Summary line
    print(f"\n{'─'*50}")
    issues = []
    if unmatched:
        issues.append(f"{len(unmatched)} 未匹配")
    if short_count:
        issues.append(f"{short_count} 短字幕")
    if overlap_count:
        issues.append(f"{overlap_count} 重叠")
    if issues:
        print(f"  ⚠️  {', '.join(issues)}")
    else:
        print(f"  ✅ 全部通过")
    print(f"{'='*60}\n")


# ============================================================
# 主流程
# ============================================================
def main(args=None):
    if args is None:
        # 兼容无参数调用
        class FakeArgs:
            preview = 0; skip_blur = False; skip_cut = False; skip_burn = False; input = None; output_dir = None
        args = FakeArgs()

    preview_seconds = args.preview
    skip_blur = args.skip_blur
    skip_cut = args.skip_cut
    skip_burn = args.skip_burn

    # 支持 --input 动态指定视频
    source_video = Path(args.input) if args.input else ORIGINAL_VIDEO

    # 支持 --output-dir 动态指定输出目录
    if args.output_dir:
        OUTPUT_DIR_OVERRIDE = Path(args.output_dir)
        OUTPUT_DIR_OVERRIDE.mkdir(exist_ok=True)
    else:
        OUTPUT_DIR_OVERRIDE = None

    print()
    print("=" * 60)
    print("  口播视频剪辑 Agent v1.2")
    print("  Sub-Agent for 口播 editing")
    print("=" * 60)
    if preview_seconds:
        print(f"  🔍 预览模式: 前 {preview_seconds}s")

    # 预览模式输出路径
    out_dir = OUTPUT_DIR_OVERRIDE or OUTPUT_DIR
    out_dir.mkdir(exist_ok=True)
    output_path = out_dir / ("preview.mp4" if preview_seconds else "final.mp4")

    # ========================================
    # 第零步：清理（skip 模式下保留 temp 文件）
    # ========================================
    clean_list = [TEMP_DIR / "blur_base.mp4"]
    if not skip_cut:
        clean_list += [TEMP_DIR / "tv.mp4", TEMP_DIR / "ta.aac"]
    if not skip_burn:
        clean_list += [TEMP_DIR / "muxed.mp4", output_path]
    for p in clean_list:
        if p.exists():
            if p.is_dir():
                import shutil
                shutil.rmtree(p)
            else:
                p.unlink()

    # ========================================
    # 第一步：分析
    # ========================================
    print("\n" + "─" * 50)
    print("  Step 1: 分析")
    print("─" * 50)

    trim_start = find_first_word(TRANSCRIPT_FILE)
    print(f"  📍 片头空档: 0-{trim_start:.1f}s")

    # 找沉默
    silence_cuts = find_silence(TRANSCRIPT_FILE, after=trim_start)
    total_silence = sum(e - s for s, e, _ in silence_cuts)
    print(f"  🔇 沉默(>{SILENCE_THRESHOLD}s): {len(silence_cuts)} 处, 共 {total_silence:.1f}s")

    # 找语气词
    filler_cuts = find_fillers(TRANSCRIPT_FILE, after=trim_start)
    total_filler = sum(e - s for s, e, _ in filler_cuts)
    print(f"  🗣️ 语气词: {len(filler_cuts)} 处, 共 {total_filler:.1f}s")
    if filler_cuts:
        for s, e, reason in filler_cuts[:10]:
            print(f"    {s:.1f}s-{e:.1f}s  {reason}")

    # 找重复
    repeat_cuts = find_repeats(TRANSCRIPT_FILE, after=trim_start)
    total_repeat = sum(e - s for s, e, _ in repeat_cuts)
    print(f"  🔄 重复: {len(repeat_cuts)} 处, 共 {total_repeat:.1f}s")

    # 合并所有裁剪段
    all_cuts_raw = silence_cuts + filler_cuts + repeat_cuts
    # 合并重叠段
    all_cuts = []
    for s, e, reason in sorted(all_cuts_raw, key=lambda x: x[0]):
        if not all_cuts:
            all_cuts.append((s, e, reason))
        else:
            last_s, last_e, last_reason = all_cuts[-1]
            if s <= last_e + 0.1:
                # 重叠或相邻，合并
                all_cuts[-1] = (last_s, max(last_e, e), f"{last_reason} + {reason}")
            else:
                all_cuts.append((s, e, reason))

    total_cut = sum(e - s for s, e, _ in all_cuts)
    print(f"  ✂️ 总计: {len(all_cuts)} 处裁剪段, 共 {total_cut:.1f}s")

    if all_cuts:
        print("  ── 裁剪列表 ──")
        for s, e, reason in all_cuts:
            dur = e - s
            print(f"    {s:.1f}s-{e:.1f}s ({dur:.1f}s)  {reason}")

    # 预览模式：裁剪段限制在 preview_seconds 内
    if preview_seconds > 0:
        all_cuts = [(s, e, r) for s, e, r in all_cuts if s < preview_seconds]
        if trim_start >= preview_seconds:
            trim_start = 0

    # ========================================
    # 第二步：提取音频
    # ========================================
    print("\n" + "─" * 50)
    print("  Step 2: 提取音频")
    print("─" * 50)

    raw_audio = TEMP_DIR / "raw.aac"
    subprocess.run([
        "ffmpeg", "-i", str(source_video), "-vn",
        "-c:a", "copy", "-y", str(raw_audio)
    ], check=True, capture_output=True)
    audio_t = TEMP_DIR / "audio_t.aac"
    audio_cmd = ["ffmpeg", "-i", str(raw_audio), "-ss", str(trim_start)]
    if preview_seconds > 0:
        audio_cmd += ["-t", str(preview_seconds - trim_start)]
    audio_cmd += ["-c", "copy", "-y", str(audio_t)]
    subprocess.run(audio_cmd, check=True, capture_output=True)
    print(f"  OK ({get_dur(audio_t):.1f}s)")

    # ========================================
    # 第三步：背景模糊
    # ========================================
    print("\n" + "─" * 50)
    print("  Step 3: 背景模糊 + 人物锐化")
    print("─" * 50)

    blurred = TEMP_DIR / "blurred.mp4"
    if skip_blur and blurred.exists():
        print(f"  [跳过] 使用已有 {blurred.name}")
    else:
        blur_video(source_video, blurred, trim_start, preview_seconds)

    # ========================================
    # 第四步：裁剪
    # ========================================
    print("\n" + "─" * 50)
    print("  Step 4: 裁剪沉默/语气词/重复")
    print("─" * 50)

    tv = TEMP_DIR / "tv.mp4"
    ta = TEMP_DIR / "ta.aac"
    if skip_cut and tv.exists() and ta.exists():
        print(f"  [跳过] 使用已有 {tv.name} + {ta.name}")
    else:
        tv, ta = cut_main(blurred, audio_t, all_cuts, trim_start)

    # ========================================
    # 第五步：字幕
    # ========================================
    print("\n" + "─" * 50)
    print("  Step 5: 生成字幕 (ASS)")
    print("─" * 50)

    # 获取视频宽高
    cap = cv2.VideoCapture(str(tv))
    vw = int(cap.get(3))
    vh = int(cap.get(4))
    cap.release()

    # 优先使用用户审定的断句方案
    if SEGMENTED_FILE.exists():
        print(f"  [字幕] 使用审定断句方案 ({SEGMENTED_FILE.name})")
        subs = build_subtitles_from_segmented(TRANSCRIPT_FILE, SEGMENTED_FILE, all_cuts, trim_start)
    else:
        subs = build_subtitles(TRANSCRIPT_FILE, all_cuts, trim_start)
    ass_path = TEMP_DIR / "subtitles.ass"
    write_ass(subs, ass_path, vw, vh)

    # ========================================
    # 第六步：合成
    # ========================================
    print("\n" + "─" * 50)
    print("  Step 6: 合成视频")
    print("─" * 50)

    muxed = TEMP_DIR / "muxed.mp4"
    mux_av(tv, ta, muxed)

    # ========================================
    # 第七步：烧录字幕
    # ========================================
    print("\n" + "─" * 50)
    print("  Step 7: 烧录字幕")
    print("─" * 50)

    if skip_burn:
        print(f"  [跳过] --skip-burn 已设，输出 muxed.mp4")
        output_path = muxed
    else:
        burn_ass(muxed, ass_path, output_path)

    # ========================================
    # 输出自检
    # ========================================
    od = get_dur(source_video)
    fd = get_dur(output_path)

    issues = []
    # 检查是否还有字幕重叠
    overlap_count = 0
    for i in range(len(subs) - 1):
        if subs[i][1] > subs[i+1][0] - 0.05:
            overlap_count += 1
    if overlap_count:
        issues.append(f"{overlap_count} 处字幕重叠")

    # 检查短字幕（< 0.5s 才算问题，因为 0.7s 已经修过）
    very_short = sum(1 for s,e,t in subs if e - s < 0.5)
    if very_short:
        issues.append(f"{very_short} 条字幕 < 0.5s")

    # 检查输出文件异常
    if not output_path.exists() or output_path.stat().st_size < 1024:
        issues.append("输出文件异常")

    print()
    print("=" * 60)
    print("  ✅ 完成!" if not issues else f"  ⚠️  完成（{', '.join(issues)}）")
    print(f"  ⏱  {od:.1f}s → {fd:.1f}s (剪 {od-fd:.1f}s)")
    print(f"  📝 字幕: {len(subs)} 条 (ASS格式)")
    print(f"  🎨 字体: {FONT_NAME} {FONT_SIZE}号 / 重点词 {FONT_SIZE_HIGHLIGHT}号黄色")
    print(f"  🔇 沉默: {len(silence_cuts)} 处 | 🗣️ 语气词: {len(filler_cuts)} 处 | 🔄 重复: {len(repeat_cuts)} 处")
    print(f"  📂 输出: {output_path}")
    if issues:
        print(f"  ⚠️  自检发现: {'; '.join(issues)}")
        print(f"  💡 建议重新运行或检查参数")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="口播视频剪辑流水线")
    parser.add_argument("--test-corrections", action="store_true",
                        help="快速验证 CORRECTIONS 匹配率（5秒）")
    parser.add_argument("--input", type=str, default=None,
                        help="输入视频路径（覆盖 ORIGINAL_VIDEO）")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="输出目录（默认 output/）")
    parser.add_argument("--preview", type=float, default=0,
                        help="预览模式：只处理前 N 秒，输出 output/preview.mp4")
    parser.add_argument("--skip-blur", action="store_true",
                        help="跳过模糊（重用 temp/blurred.mp4）")
    parser.add_argument("--skip-cut", action="store_true",
                        help="跳过裁剪（重用 temp/tv.mp4 + ta.aac）")
    parser.add_argument("--skip-burn", action="store_true",
                        help="跳过烧录字幕（输出 muxed.mp4）")
    args = parser.parse_args()

    if args.test_corrections:
        test_corrections()
    else:
        main(args)
