"""飞书同步模块 —— 管理飞书文档的同步任务。

与 FlomoSync 平行的结构，提供定时同步、状态查询等功能。
"""

import logging
import threading
import time
from typing import Optional

from engine.config import FEISHU_SYNC_INTERVAL
from engine.feishu_client import FeishuClient

logger = logging.getLogger("feishu_sync")


class FeishuSync:
    """飞书同步管理器。"""

    def __init__(self, interval: int = FEISHU_SYNC_INTERVAL):
        self.interval = interval
        self._client = FeishuClient()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_sync_time: Optional[str] = None
        self.last_error: Optional[str] = None
        self.sync_count: int = 0
        self._token_ok: Optional[bool] = None

    # ── 连接检查 ──

    def check_connection(self) -> bool:
        """检查飞书 API 连接是否正常。"""
        try:
            self._client.get_tenant_access_token()
            self._token_ok = True
            return True
        except RuntimeError as e:
            self._token_ok = False
            self.last_error = str(e)
            logger.error("飞书连接检查失败: %s", e)
            return False

    # ── 同步（预留，后续阶段扩展） ──

    def sync_once(self) -> int:
        """执行一次同步（预留实现，当前只验证连接）。

        返回:
            同步的文档数量（当前返回 0）

        抛出:
            RuntimeError: 连接失败
        """
        if not self._token_ok:
            ok = self.check_connection()
            if not ok:
                raise RuntimeError(self.last_error or "飞书连接未就绪")

        logger.info("飞书连接正常，同步就绪")
        self.last_sync_time = time.strftime("%Y-%m-%d %H:%M:%S")
        return 0

    # ── 定时调度 ──

    def start_scheduler(self):
        """在后台线程启动定时检查。"""
        if self._running:
            return

        if not self.check_connection():
            logger.warning("飞书连接失败，调度器暂不启动")
            self.last_error = "飞书连接失败"
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="feishu-sync"
        )
        self._thread.start()
        logger.info("飞书同步调度已启动，间隔 %d 秒", self.interval)

    def stop_scheduler(self):
        self._running = False

    def _run_loop(self):
        self.sync_once()
        while self._running:
            time.sleep(self.interval)
            if self._running:
                self.sync_once()

    # ── 状态查询 ──

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "connected": bool(self._token_ok),
            "interval": self.interval,
            "last_sync_time": self.last_sync_time,
            "last_error": self.last_error,
        }
