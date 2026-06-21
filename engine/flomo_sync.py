"""Flomo 笔记同步模块 — 定时轮询 Flomo Pro API，写入捕获目录。"""

import json
import logging
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from engine.config import CAPTURE_DIR, FLOMO_API_KEY, FLOMO_SYNC_INTERVAL, PROJECT_ROOT

logger = logging.getLogger("flomo_sync")

STATE_FILE = PROJECT_ROOT / "flomo_state.json"


class FlomoSync:
    """Flomo API 同步器。"""

    def __init__(self, api_key: str = FLOMO_API_KEY, interval: int = FLOMO_SYNC_INTERVAL):
        self.api_key = api_key
        self.interval = interval
        self._state: dict = self._load_state()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_sync_time: Optional[str] = self._state.get("last_sync_time")
        self.last_error: Optional[str] = None
        self.sync_count: int = 0

    # ── 状态持久化 ──

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("读取状态文件失败: %s", e)
        return {"last_sync_time": "", "imported_ids": []}

    def _save_state(self):
        self._state["last_sync_time"] = self.last_sync_time or ""
        try:
            STATE_FILE.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("保存状态文件失败: %s", e)

    # ── Flomo API ──

    def fetch_notes(self, since: Optional[str] = None) -> list[dict]:
        """调用 Flomo API 获取笔记列表。

        返回按 created_at 升序排列的笔记列表。
        API 文档参考: https://flomoapp.com/api/docs (Pro)
        GET /api/v1/notes?since={timestamp}&limit=50
        """
        import urllib.request
        import urllib.error

        if not self.api_key:
            raise ValueError("FLOMO_API_KEY 未配置")

        params = "?limit=50"
        if since:
            params += f"&since={since}"

        url = f"https://flomoapp.com/api/v1/notes{params}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Flomo API HTTP {e.code}: {body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Flomo API 网络错误: {e.reason}")

        notes = data.get("notes", [])
        # 按时间升序排列
        notes.sort(key=lambda n: n.get("created_at", ""))
        return notes

    # ── 笔记写入 ──

    def save_note_to_vault(self, note: dict) -> Optional[Path]:
        """将单条 Flomo 笔记写入捕获目录。

        返回文件路径，若已去重则返回 None。
        """
        note_id = str(note.get("id", ""))
        if not note_id:
            logger.warning("笔记缺少 id，跳过")
            return None

        # 去重检查
        if note_id in self._state.get("imported_ids", []):
            return None

        content = note.get("content", "").strip()
        if not content:
            logger.warning("笔记 id=%s 内容为空，跳过", note_id)
            return None

        created_at = note.get("created_at", datetime.now(timezone.utc).isoformat())
        tags = note.get("tags", [])

        # 标题：取第一行
        first_line = content.split("\n")[0]
        title = first_line[:40] if first_line else f"flomo-{note_id[:8]}"
        # 清理文件名非法字符
        safe_title = "".join(c if c.isalnum() or c in " _-一-龥" else "_" for c in title).strip()
        if not safe_title:
            safe_title = f"flomo-{note_id[:8]}"

        date_prefix = created_at[:10]  # YYYY-MM-DD
        filename = f"{date_prefix} {safe_title}.md"
        filepath = CAPTURE_DIR / filename

        # 文件名冲突：加后缀
        counter = 1
        while filepath.exists():
            filename = f"{date_prefix} {safe_title}_{counter}.md"
            filepath = CAPTURE_DIR / filename
            counter += 1

        # 构建 frontmatter + 正文
        tag_lines = "\n".join(f"  - {t}" for t in tags) if tags else ""
        frontmatter = f"""---
created: {created_at}
source: flomo
flomo_id: {note_id}
tags:
{tag_lines}
---

"""
        md_content = frontmatter + content

        # 写入文件
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        filepath.write_text(md_content, encoding="utf-8")

        # 更新状态
        self._state.setdefault("imported_ids", []).append(note_id)
        self._save_state()

        logger.info("写入捕获目录: %s", filename)
        return filepath

    # ── 同步流程 ──

    def sync_once(self) -> int:
        """执行一次同步，返回新导入的笔记数量。"""
        logger.info("开始同步 Flomo 笔记...")
        try:
            notes = self.fetch_notes(since=self.last_sync_time)
        except (ValueError, RuntimeError, OSError) as e:
            self.last_error = str(e)
            logger.error("同步失败: %s", e)
            return 0

        count = 0
        for note in notes:
            if self.save_note_to_vault(note):
                count += 1

        # 更新最后同步时间
        if notes:
            self.last_sync_time = notes[-1].get("created_at", "")
            self._save_state()

        self.sync_count += count
        self.last_error = None
        logger.info("同步完成: 新导入 %d 条笔记", count)
        return count

    # ── 定时调度 ──

    def start_scheduler(self):
        """在后台线程启动定时同步。"""
        if self._running:
            return
        if not self.api_key:
            logger.warning("FLOMO_API_KEY 未配置，不启动 Flomo 同步")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="flomo-sync")
        self._thread.start()
        logger.info("Flomo 同步调度已启动，间隔 %d 秒", self.interval)

    def stop_scheduler(self):
        self._running = False

    def _run_loop(self):
        # 启动后立即执行一次
        self.sync_once()
        while self._running:
            time.sleep(self.interval)
            if self._running:
                self.sync_once()

    # ── 状态查询 ──

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "api_key_configured": bool(self.api_key),
            "interval": self.interval,
            "last_sync_time": self.last_sync_time,
            "last_error": self.last_error,
            "sync_count": self.sync_count,
            "imported_count": len(self._state.get("imported_ids", [])),
        }
