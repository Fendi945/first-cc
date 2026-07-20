"""反馈写入器 — 自动将视频数据分析结果写入 Obsidian 反哺弧。

工作流：
  1. 监听 _analysis_signal.json 的新信号
  2. 读取分析结果 + 原始数据
  3. 生成结构化 Obsidian 笔记
  4. 写入 ⚙️ 反哺弧/📓 问题库/ 或 /看板/

触发方式：
  - 后台调度（每30分钟检查一次）
  - AI 手动触发（通过 API）
"""

import json
import logging
import os
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from engine.config import PROJECT_ROOT, DATA_DIR, KANBAN_DIR

logger = logging.getLogger("feedback_writer")

# ── 路径 ──
SIGNAL_FILE = DATA_DIR / "_analysis_signal.json"
ANALYSIS_RESULT_FILE = DATA_DIR / "analysis-result.json"
DASHBOARD_FILE = KANBAN_DIR / "dashboard-data.json"
FEEDBACK_DIR = KANBAN_DIR  # ⚙️ 反哺弧/ 目录
LAST_SEEN_SIGNAL = DATA_DIR / "_feedback_last_signal.json"


def _read_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


class FeedbackWriter:
    """将分析结果写成 Obsidian 笔记，放在反哺弧目录。"""

    def __init__(self, check_interval: int = 1800):
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_signal_id = ""  # 去重

    def check_and_write(self) -> dict:
        """检查信号文件，如有新分析结果则写入 Obsidian。"""
        signal = _read_json(SIGNAL_FILE)
        if not signal.get("hasNewAnalysis"):
            return {"written": False, "reason": "no_signal"}

        signal_id = f"{signal.get('analyzedAt', '')}_{signal.get('dataUpdatedAt', '')}"
        if signal_id == self._last_signal_id:
            return {"written": False, "reason": "already_seen"}

        # 读取完整分析结果
        analysis = _read_json(ANALYSIS_RESULT_FILE)
        dashboard = _read_json(DASHBOARD_FILE)

        # 生成 Obsidian 笔记
        note = self._build_note(signal, analysis, dashboard.get("data", []))
        note_path = self._write_note(note)

        self._last_signal_id = signal_id
        # 保存已处理信号ID，即使重启也不重复
        LAST_SEEN_SIGNAL.write_text(
            json.dumps({"last_signal_id": signal_id, "written_at": datetime.now().isoformat()},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info("反馈笔记已写入: %s", note_path)
        return {"written": True, "path": str(note_path)}

    def _build_note(self, signal: dict, analysis: dict, data: list) -> str:
        """构建 Obsidian 笔记内容。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        summary = signal.get("summary", "")
        highlights = signal.get("highlights", [])
        warnings = signal.get("warnings", [])
        insight = signal.get("actionableInsight", "")

        # 最近的5条视频数据
        recent = sorted(data, key=lambda x: x.get("date", ""), reverse=True)[:8]
        recent_lines = []
        for v in recent:
            title = v.get("title", "?")[:30]
            date = str(v.get("date", "?"))[:10]
            plays = v.get("plays", 0)
            likes = v.get("likes", 0)
            comments = v.get("comments", 0)
            follows = v.get("follows", 0)
            shares = v.get("shares", 0)
            recent_lines.append(f"- {date} | {plays}播放 👍{likes} 💬{comments} ➕{follows} 🔄{shares} | {title}")

        lines = [
            "---",
            f"created: {now}",
            "tags: [反哺弧, 自动分析, 视频号数据, AI反馈]",
            "updated: auto",
            "---",
            "",
            f"# 📊 视频号数据自动反馈 — {now[:10]}",
            "",
            "> **AI 自动检测到新数据，以下为分析结果。**",
            "",
            "---",
            "",
            "## 本期摘要",
            "",
            summary or "无分析摘要。",
            "",
        ]

        if highlights:
            lines += ["", "### ✅ 亮点", ""]
            for h in highlights:
                lines.append(f"- {h}")

        if warnings:
            lines += ["", "### ⚠️ 需要注意", ""]
            for w in warnings:
                lines.append(f"- {w}")

        if insight:
            lines += ["", "---", "", "### 🎯 核心建议", "", insight, ""]

        lines += [
            "",
            "---",
            "",
            "### 最新视频数据",
            "",
        ]
        lines += recent_lines
        lines += [
            "",
            "---",
            "",
            f"*AI 自动分析 · {now} · 数据更新于 {signal.get('dataUpdatedAt', '?')}*",
            "",
        ]

        return "\n".join(lines)

    def _write_note(self, content: str) -> Path:
        """写入 Obsidian 笔记到反哺弧目录（如今天已有笔记则覆盖，不追加）。"""
        today = datetime.now().strftime("%Y%m%d")
        note_path = FEEDBACK_DIR / f"AI反馈_{today}.md"

        # 如已存在则覆盖（避免重复累加）
        note_path.write_text(content, encoding="utf-8")
        logger.info("已写入反馈笔记: %s", note_path)
        return note_path

    # ── 后台调度 ──

    def start_scheduler(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="feedback-writer"
        )
        self._thread.start()
        logger.info("反馈写入器调度已启动，间隔 %d 秒", self.check_interval)

    def stop_scheduler(self):
        self._running = False

    def _run_loop(self):
        # 恢复上次的信号ID
        seen = _read_json(LAST_SEEN_SIGNAL)
        self._last_signal_id = seen.get("last_signal_id", "")

        # 启动后立即检查一次
        try:
            self.check_and_write()
        except Exception as e:
            logger.error("启动检查失败: %s", e)

        while self._running:
            time.sleep(self.check_interval)
            if self._running:
                try:
                    self.check_and_write()
                except Exception as e:
                    logger.error("定时检查失败: %s", e)

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "interval": self.check_interval,
            "last_signal_id": self._last_signal_id,
        }


def main():
    """手动触发一次反馈写入。"""
    fw = FeedbackWriter()
    result = fw.check_and_write()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
