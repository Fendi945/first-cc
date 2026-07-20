#!/usr/bin/env python3
"""
AI 视频剪辑工具 — 统一入口
===========================
用法:
  cut_video 口播 <视频> [参数]       # 口播视频全自动剪辑（核心流水线）
  cut_video 切片 <视频> <起> <止>    # 从视频截取片段
  cut_video 剪                       # (预留) 通用剪辑

示例:
  cut_video 口播 demo.mp4
  cut_video 口播 demo.mp4 --preview 30
  cut_video 口播 demo.mp4 --skip-blur
  cut_video 切片 demo.mp4 10 30
  cut_video 切片 demo.mp4 10 30 --output clip.mp4
  cut_video --help
"""

import sys
import subprocess
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
SUB_AGENT = PROJECT_DIR / "sub_agent.py"
TRANSCRIPT = PROJECT_DIR / "transcript.json"
SEGMENTED = PROJECT_DIR / "transcript_segmented.json"
DESKTOP_OUTPUT = Path(r"D:\Documents\Desktop\视频成品")


def help():
    print(__doc__)


# ── 子命令：口播 ──────────────────────────────────────────

def cmd_koubo(video, extra_args):
    """全自动口播剪辑流水线"""
    video = Path(video)
    if not video.exists():
        print(f"  ❌ 文件不存在: {video}")
        return

    # Step 1: 转录
    if TRANSCRIPT.exists():
        print(f"  ✅ 已有转录: {TRANSCRIPT.name}")
    else:
        print(f"\n  🎤 转录中... (首次较慢)")
        subprocess.run([
            sys.executable, "-m", "whisper",
            str(video), "--model", "base", "--language", "zh",
            "--output_dir", str(PROJECT_DIR), "--output_format", "json",
        ], check=True)
        whisper_out = video.with_suffix(".json")
        if whisper_out.exists() and whisper_out.resolve() != TRANSCRIPT.resolve():
            whisper_out.replace(TRANSCRIPT)
        print(f"  ✅ 转录完成")

    # Step 2: 默认断句
    if not SEGMENTED.exists():
        print(f"\n  📝 生成默认断句 → {SEGMENTED.name}")
        print(f"  💡 打开文件手动调整断句后重新运行")
        with open(TRANSCRIPT, encoding="utf-8") as f:
            data = json.load(f)
        segments = [{"text": s["text"].strip()}
                     for s in data["segments"] if s["text"].strip()]
        with open(SEGMENTED, "w", encoding="utf-8") as f:
            json.dump({"segments": segments}, f, ensure_ascii=False, indent=2)
        print(f"  ✅ {len(segments)} 条默认断句")

    # Step 3: 调用流水线（默认输出到桌面）
    if "--output-dir" not in " ".join(extra_args):
        extra_args = list(extra_args) + ["--output-dir", str(DESKTOP_OUTPUT)]
    cmd = [sys.executable, str(SUB_AGENT), "--input", str(video)] + extra_args
    print(f"\n{'='*60}")
    print(f"  ✂️  口播剪辑: {video.name} → {DESKTOP_OUTPUT}")
    print(f"{'='*60}")
    subprocess.run(cmd, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})


# ── 子命令：切片 ──────────────────────────────────────────

def cmd_qiepian(video, start, end, output=None):
    """从视频截取片段"""
    video = Path(video)
    if not video.exists():
        print(f"  ❌ 文件不存在: {video}")
        return
    try:
        s = float(start)
        e = float(end)
    except ValueError:
        print(f"  ❌ 起止时间必须是数字（秒）: {start} {end}")
        return
    if e <= s:
        print(f"  ❌ 结束时间必须大于开始时间: {s} → {e}")
        return

    if output:
        out = Path(output)
    else:
        stem = video.stem
        out = video.parent / f"{stem}_{int(s)}_{int(e)}.mp4"

    dur = e - s
    print(f"  ✂️  切片: {video.name}  {s}s → {e}s ({dur:.1f}s)")
    subprocess.run([
        "ffmpeg", "-i", str(video), "-ss", str(s), "-t", str(dur),
        "-c", "copy", "-y", str(out)
    ], check=True)
    print(f"  ✅ 输出: {out}")


# ── 子命令：通用剪辑（预留） ──────────────────────────────

def cmd_cut_video(video, extra_args):
    """(预留) 通用视频剪辑"""
    print("  ⏳ 通用剪辑模式开发中...")


# ── 主入口 ────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        help()
        return

    subcmd = sys.argv[1]

    if subcmd in ("口播", "koubo", "kb"):
        if len(sys.argv) < 3:
            print("用法: cut_video 口播 <视频> [参数]")
            return
        video = sys.argv[2]
        extra = sys.argv[3:]
        cmd_koubo(video, extra)

    elif subcmd in ("切片", "qiepian", "qp", "clip"):
        if len(sys.argv) < 5:
            print("用法: cut_video 切片 <视频> <起(秒)> <止(秒)> [--output 路径]")
            return
        video = sys.argv[2]
        start = sys.argv[3]
        end = sys.argv[4]
        output = None
        if "--output" in sys.argv:
            idx = sys.argv.index("--output")
            if idx + 1 < len(sys.argv):
                output = sys.argv[idx + 1]
        cmd_qiepian(video, start, end, output)

    elif subcmd in ("剪", "cut", "video"):
        if len(sys.argv) < 3:
            print("用法: cut_video 剪 <视频> [参数]")
            return
        video = sys.argv[2]
        extra = sys.argv[3:]
        cmd_cut_video(video, extra)

    else:
        print(f"  ❌ 未知子命令: {subcmd}")
        print(f"  可用: 口播 / 切片 / 剪")
        help()


if __name__ == "__main__":
    main()
