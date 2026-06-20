"""Video processing pipeline v4 - MediaPipe selfie segmentation + pause cut + word subtitles."""
import json
import subprocess
import time
import sys
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

PROJECT_DIR = Path(__file__).parent
ORIGINAL_VIDEO = PROJECT_DIR / "original.mp4"
TRANSCRIPT_FILE = PROJECT_DIR / "transcript.json"
OUTPUT_DIR = PROJECT_DIR / "output"
TEMP_DIR = PROJECT_DIR / "temp"
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Corrected word mappings for Whisper recognition errors
# Keys are sorted by length descending so longer matches win.
CORRECTIONS = {
    # Full-phrase corrections (longest first)
    "时工钱多": "施工前",
    "动线每一会儿": "动线没画",
    "时工对黑": "施工队黑",
    "守五王哪身": "手往哪伸",
    "红风成一三": "红枫×3",
    "元宝风成一二": "元宝枫×2",
    "从客厅到水井": "从客厅到水景",
    "踩一脚衣": "踩一脚泥",
    "洞个脑子": "动动脑子",
    "叶竹省": "业主审",
    "怎么省它": "怎么省事",
    "砸迟毕": "砸池壁",
    "拿枝笔": "拿支笔",
    "拿着笔": "拿支笔",
    "循环笵": "循环泵",
    "时工": "施工",
    "鞋俩字": "写俩字",
    "绿花袋": "绿化带",
    "厅步路": "汀步路",
    "红风": "红枫",
    "元宝风": "元宝枫",
    "贯笵": "冠幅",
    "笵坑": "泵坑",
    "迟毕": "池壁",
    "守五": "手",
    "数官": "树冠",
    "数长": "树长",
    "数种": "树种",
    "掌开": "长开",
    "兼具": "间距",
    "石拔": "石板",
    "水井": "水景",
    "挖两壳": "挖了两棵",
    "挖两棵": "挖了两棵",
    "五位书": "五位数",
    "指标了": "只标了",
    "管先": "管线",
    "交结": "胶粘",
    "沾死": "粘死",
    "水准": "水景",
    "稳资": "文字",
    "笵": "泵",
    "堆": "队",
    "王": "往",
    "蕾": "雷",
    "流": "留",
    "鞋": "写",
    "巳": "已",
}


def fix(text):
    """Replace Whisper recognition errors in text. Longer keys matched first."""
    for w, c in sorted(CORRECTIONS.items(), key=lambda x: -len(x[0])):
        text = text.replace(w, c)
    return text


def find_first_word(transcript_path):
    with open(transcript_path, encoding="utf-8") as f:
        data = json.load(f)
    for seg in data["segments"]:
        for w in seg.get("words", []):
            return w["start"]
    return 5.16


def find_cuts(transcript_path, after=0, min_gap=2.0):
    with open(transcript_path, encoding="utf-8") as f:
        data = json.load(f)
    cuts = []

    # Check gaps within each segment
    for seg in data["segments"]:
        words = seg.get("words", [])
        for i in range(1, len(words)):
            gap = words[i]["start"] - words[i-1]["end"]
            if gap > min_gap:
                s = words[i-1]["end"] + 0.04
                e = words[i]["start"] - 0.04
                if e > s and s >= after:
                    cuts.append((s, e, gap))

    # Check gaps between segment boundaries
    for i in range(1, len(data["segments"])):
        prev_w = data["segments"][i-1].get("words", [])
        curr_w = data["segments"][i].get("words", [])
        if prev_w and curr_w:
            gap = curr_w[0]["start"] - prev_w[-1]["end"]
            if gap > min_gap:
                s = prev_w[-1]["end"] + 0.04
                e = curr_w[0]["start"] - 0.04
                if e > s and s >= after:
                    cuts.append((s, e, gap))

    return cuts


def find_repeats(transcript_path, after=0, min_gap=0.5):
    """Detect repeated content across segment boundaries and internal stutters."""
    with open(transcript_path, encoding="utf-8") as f:
        data = json.load(f)
    repeats = []

    # 1. Cross-segment repeats: tail of segment i == head of segment i+1
    for i in range(1, len(data["segments"])):
        prev_text = fix(data["segments"][i-1]["text"])
        curr_text = fix(data["segments"][i]["text"])
        prev_words = data["segments"][i-1].get("words", [])
        curr_words = data["segments"][i].get("words", [])

        if not prev_words or not curr_words:
            continue

        # Check overlap: find the longest common suffix of prev = prefix of curr
        overlap = ""
        for n in range(min(40, len(prev_text), len(curr_text)), 3, -1):
            tail = prev_text[-n:].strip("，。！？、； ")
            head = curr_text[:n].strip("，。！？、； ")
            if tail and tail[:len(tail)//2] in curr_text[:n+5]:
                overlap = tail
                break

        if len(overlap) >= 5:
            # The repeated part is in the tail of prev segment → cut it
            # Find the time when the repeat starts (roughly at the overlap's first word)
            ov_start_chars_in_prev = len(prev_text) - len(overlap)
            char_ratio = ov_start_chars_in_prev / max(len(prev_text), 1)
            word_idx = int(char_ratio * len(prev_words))
            word_idx = max(0, min(word_idx, len(prev_words) - 1))
            s = prev_words[word_idx]["start"]
            e = prev_words[-1]["end"]
            if s >= after and e > s + min_gap:
                repeats.append((s, e, "重复"))

    # 2. Internal stutter: same phrase appears twice in a row within a segment
    for seg in data["segments"]:
        text = fix(seg["text"])
        words = seg.get("words", [])
        if not words:
            continue

        # Split into phrases at comma-level
        import re
        phrases = re.split(r'(?<=[，,])', text)
        phrases = [p.strip() for p in phrases if p.strip()]

        seen = {}
        for idx, phrase in enumerate(phrases):
            # Normalize
            key = phrase.strip("，。！？、；： ")
            if len(key) < 4:
                continue
            # Check if this phrase repeats a recent one (within 2 positions)
            if key in seen and idx - seen[key] <= 2:
                # Found repeat — mark from start of this phrase to end
                # Find approx word position
                cum_chars = sum(len(p) for p in phrases[:idx])
                char_ratio = cum_chars / max(len(text), 1)
                word_pos = int(char_ratio * len(words))
                word_pos = max(0, min(word_pos, len(words) - 1))
                # Find the end of the repeated portion
                next_phrase_chars = cum_chars + len(phrase)
                end_ratio = next_phrase_chars / max(len(text), 1)
                end_pos = int(end_ratio * len(words))
                end_pos = max(0, min(end_pos, len(words) - 1))

                s = words[word_pos]["start"]
                e = words[end_pos]["end"]
                if s >= after and e > s + min_gap:
                    repeats.append((s, e, "重复"))
            seen[key] = idx

    return repeats


def build_subtitles(transcript_path, cuts, trim_start):
    """Build word-level subtitles, grouped into phrases."""
    with open(transcript_path, encoding="utf-8") as f:
        data = json.load(f)

    # Collect all words
    all_words = []
    for seg in data["segments"]:
        for w in seg.get("words", []):
            t = w["word"].strip()
            if t and t not in (",", "，", "。", "?", "？", "！", "!", "、"):
                all_words.append((w["start"], w["end"], t))

    # Group into subtitle segments
    subs = []
    group = []
    punct = set("。！？.!?；;")

    for w_start, w_end, text in all_words:
        group.append((w_start, w_end, text))
        should_break = False

        if text in punct or any(text.endswith(p) for p in punct):
            should_break = True
        if len(group) > 1 and (group[-1][0] - group[-2][1]) > 0.3:
            should_break = True
        if len(group) >= 10:
            should_break = True

        if should_break:
            combined = "".join(w[2] for w in group).strip("，,。.！!？?、；;：:")
            combined = fix(combined)
            if combined:
                subs.append((group[0][0], group[-1][1], combined))
            group = []

    if group:
        combined = "".join(w[2] for w in group).strip("，,。.！!？?、；;：:")
        combined = fix(combined)
        if combined:
            subs.append((group[0][0], group[-1][1], combined))

    # Adjust timestamps for trim + cuts
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

    # Merge ≤2-char subtitle entries into the previous one
    merged = []
    for s, e, text in adjusted:
        if len(text) <= 2 and merged:
            prev_s, prev_e, prev_text = merged[-1]
            merged[-1] = (prev_s, max(prev_e, e), prev_text + text)
        elif len(text) > 2:
            merged.append((s, e, text))

    return merged


def write_srt(subtitles, path):
    def ts(sec):
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, (s, e, t) in enumerate(subtitles, 1):
        lines.extend([str(i), f"{ts(s)} --> {ts(e)}", t, ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote {len(subtitles)} subtitle entries")


def blur_video(input_path, output_path, trim_seconds):
    """Trim start + face-aware background blur + person sharpening."""
    print(f"  Blurring (face detection, trim={trim_seconds:.1f}s)...")
    cap = cv2.VideoCapture(str(input_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width, height = int(cap.get(3)), int(cap.get(4))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    skip = int(trim_seconds * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, skip)
    remaining = total - skip

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    # Sharpen kernel for person area
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])

    smooth_cx, smooth_cy = None, None
    smooth_rx, smooth_ry = None, None
    alpha_smooth = 0.3
    interval = max(1, remaining // 10)
    processed = 0
    t0 = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(50, 50))
        mask = np.zeros((height, width), dtype=np.uint8)

        if len(faces) > 0:
            fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])
            cx, cy = fx + fw // 2, fy + fh // 2
            # Larger ellipse to cover face + upper body
            rx, ry = int(fw * 2.5), int(fh * 3.5)

            if smooth_cx is None:
                smooth_cx, smooth_cy = cx, cy
                smooth_rx, smooth_ry = rx, ry
            else:
                a = alpha_smooth
                smooth_cx = int(smooth_cx * (1 - a) + cx * a)
                smooth_cy = int(smooth_cy * (1 - a) + cy * a)
                smooth_rx = int(smooth_rx * (1 - a) + rx * a)
                smooth_ry = int(smooth_ry * (1 - a) + ry * a)

            cv2.ellipse(mask, (smooth_cx, smooth_cy),
                       (smooth_rx, smooth_ry), 0, 0, 360, 255, -1)
        elif smooth_cx is not None:
            cv2.ellipse(mask, (smooth_cx, smooth_cy),
                       (smooth_rx, smooth_ry), 0, 0, 360, 255, -1)

        # Stronger background blur: two passes for heavier effect
        blurred = cv2.GaussianBlur(frame, (99, 99), 0)
        blurred = cv2.GaussianBlur(blurred, (99, 99), 0)

        # Minimal feathering to keep person edge sharp
        mask_f = cv2.GaussianBlur(mask.astype(np.float32), (7, 7), 0) / 255.0
        m3 = np.stack([mask_f] * 3, axis=-1)

        # Composite
        comp = (frame * m3 + blurred * (1 - m3)).astype(np.uint8)

        # Sharpen the person area for extra clarity
        sharpened = cv2.filter2D(comp, -1, sharpen_kernel)
        comp = (sharpened * m3 + comp * (1 - m3)).astype(np.uint8)

        out.write(comp)

        processed += 1
        if processed % interval == 0:
            el = time.time() - t0
            speed = processed / el
            eta = (remaining - processed) / speed
            print(f"    {processed/remaining*100:.0f}% ({speed:.0f}fps, ETA {eta:.0f}s)")

    cap.release()
    out.release()
    print(f"  Done in {time.time()-t0:.0f}s")


def segment_cut(video_path, audio_path, segments, out_video, out_audio):
    """Cut video/audio into kept segments using concat demuxer."""
    n = len(segments)
    if n == 0:
        subprocess.run(["ffmpeg", "-i", str(video_path), "-c", "copy",
                       "-y", str(out_video)], check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-i", str(audio_path), "-c", "copy",
                       "-y", str(out_audio)], check=True, capture_output=True)
        return

    # Extract each segment as separate file
    seg_dir = TEMP_DIR / "segments"
    seg_dir.mkdir(exist_ok=True)

    concat_v = TEMP_DIR / "concat_v.txt"
    concat_a = TEMP_DIR / "concat_a.txt"
    v_lines, a_lines = [], []

    for i, (s, e) in enumerate(segments):
        d = round(e - s, 3)
        v_seg = seg_dir / f"v{i}.mp4"
        a_seg = seg_dir / f"a{i}.aac"

        # Cut video segment
        subprocess.run([
            "ffmpeg", "-ss", str(s), "-i", str(video_path),
            "-t", str(d), "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an", "-y", str(v_seg)
        ], check=True, capture_output=True)

        # Cut audio segment (decode to WAV to avoid format issues)
        a_wav = seg_dir / f"a{i}.wav"
        subprocess.run([
            "ffmpeg", "-ss", str(s), "-i", str(audio_path),
            "-t", str(d), "-c:a", "pcm_s16le",
            "-y", str(a_wav)
        ], check=True, capture_output=True)

        v_lines.append(f"file '{v_seg}'")
        a_lines.append(f"file '{a_wav}'")

    concat_v.write_text("\n".join(v_lines), encoding="utf-8")
    concat_a.write_text("\n".join(a_lines), encoding="utf-8")

    # Concat video
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", str(concat_v),
        "-c", "copy", "-y", str(out_video)
    ], check=True, capture_output=True)

    # Concat audio
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", str(concat_a),
        "-c:a", "aac", "-b:a", "128k", "-y", str(out_audio)
    ], check=True, capture_output=True)


def get_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                       "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                      capture_output=True, text=True)
    return float(r.stdout.strip())


def burn_subs(video_path, srt_path, output_path):
    print(f"  Burning subtitles...")
    srt_esc = str(srt_path).replace("\\", "/").replace(":", "\\:")
    subprocess.run([
        "ffmpeg", "-i", str(video_path),
        "-vf", f"subtitles='{srt_esc}':force_style="
               f"'FontName=Microsoft YaHei,FontSize=13,"
               f"PrimaryColour=&H00FFFFFF,"
               f"BorderStyle=1,Outline=2,Shadow=1,"
               f"MarginV=45,Alignment=2'",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "copy",
        "-y", str(output_path)
    ], check=True, capture_output=True)


def main():
    print("=" * 55)
    print("  口播视频处理 v5")
    print("=" * 55)

    # Analyze
    print("\n[0] 分析...")
    trim_start = find_first_word(TRANSCRIPT_FILE)
    print(f"  片头空档: 0-{trim_start:.1f}s")
    cuts = find_cuts(TRANSCRIPT_FILE, after=trim_start)
    total_pause = sum(e - s for s, e, _ in cuts)
    print(f"  气口(>2s): {len(cuts)} 处, 共 {total_pause:.1f}s")

    # Detect repeated content
    repeats = find_repeats(TRANSCRIPT_FILE, after=trim_start)
    if repeats:
        total_rep = sum(e - s for s, e, _ in repeats)
        print(f"  重复/口误: {len(repeats)} 处, 共 {total_rep:.1f}s")
        for s, e, _ in repeats:
            print(f"    {s:.1f}s-{e:.1f}s")

    # Merge cuts (pauses + repeats)
    all_cuts = sorted(cuts + repeats, key=lambda x: x[0])

    # Step 1: Extract audio + trim
    print("\n[1] 提取音频...")
    raw_audio = TEMP_DIR / "raw.aac"
    subprocess.run([
        "ffmpeg", "-i", str(ORIGINAL_VIDEO), "-vn",
        "-c:a", "copy", "-y", str(raw_audio)
    ], check=True, capture_output=True)
    audio_t = TEMP_DIR / "audio_t.aac"
    subprocess.run([
        "ffmpeg", "-i", str(raw_audio), "-ss", str(trim_start),
        "-c", "copy", "-y", str(audio_t)
    ], check=True, capture_output=True)

    # Step 2: Blur video
    blurred = TEMP_DIR / "blurred.mp4"
    blur_video(ORIGINAL_VIDEO, blurred, trim_start)

    # Step 3: Cut pauses + repeats
    print("\n[2] 裁剪气口与重复...")
    adj_cuts = [(s - trim_start, e - trim_start) for s, e, _ in all_cuts]
    segments = []
    prev = 0.0
    for s, e in adj_cuts:
        if s > prev + 0.05:
            segments.append((prev, s))
        prev = e
    bdur = get_dur(blurred)
    if bdur > prev + 0.05:
        segments.append((prev, bdur))

    print(f"  保留 {len(segments)} 段, 裁剪 {len(all_cuts)} 处")
    tv = TEMP_DIR / "tv.mp4"
    ta = TEMP_DIR / "ta.aac"
    segment_cut(blurred, audio_t, segments, tv, ta)

    # Step 4: Subtitles
    print("\n[3] 生成逐句字幕...")
    subs = build_subtitles(TRANSCRIPT_FILE, all_cuts, trim_start)
    srt_path = TEMP_DIR / "subtitles.srt"
    write_srt(subs, srt_path)

    # Step 5: Mux
    print("\n[4] 合成...")
    muxed = TEMP_DIR / "muxed.mp4"
    subprocess.run([
        "ffmpeg", "-i", str(tv), "-i", str(ta),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0", "-map", "1:a:0", "-shortest",
        "-y", str(muxed)
    ], check=True, capture_output=True)

    # Step 6: Burn subtitles
    print("\n[5] 叠加字幕...")
    final = OUTPUT_DIR / "final.mp4"
    burn_subs(muxed, srt_path, final)

    # Summary
    od = get_dur(ORIGINAL_VIDEO)
    fd = get_dur(final)
    print()
    print("=" * 55)
    print(f"  [OK] 完成")
    print(f"  {od:.1f}s -> {fd:.1f}s (剪 {od-fd:.1f}s)")
    print(f"  字幕: {len(subs)} 条")
    print(f"  输出: {final}")
    print("=" * 55)


if __name__ == "__main__":
    main()
