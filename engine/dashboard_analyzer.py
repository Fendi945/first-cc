"""Dashboard 数据分析引擎 — 自动检测视频数据更新，调用 AI 做复盘分析。

工作流程：
  1. 定时 / 手动检查 dashboard-data.json 的 updatedAt 字段
  2. 发现更新则调用 DeepSeek API 分析数据变化
  3. 输出分析结果到 analysis-result.json + 最近数据分析.md
  4. 写入信号文件 _analysis_signal.json 供 AI 消费
"""

import json
import logging
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from engine.retry_utils import retry_with_backoff

from engine.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    PROJECT_ROOT,
    KANBAN_DIR,
    DATA_DIR,
)

logger = logging.getLogger("dashboard_analyzer")

# ── 文件路径 ──
# dashboard-data.json 在 vault 里（人类录入的数据源）
# 分析产物放项目 data 目录（机器的归机器）

DASHBOARD_FILE = KANBAN_DIR / "dashboard-data.json"
ANALYSIS_RESULT_FILE = DATA_DIR / "analysis-result.json"
ANALYSIS_MD_FILE = DATA_DIR / "最近数据分析.md"
SIGNAL_FILE = DATA_DIR / "_analysis_signal.json"
STATE_FILE = PROJECT_ROOT / "dashboard_analysis_state.json"

# ── 分析提示词 ──

ANALYSIS_SYSTEM_PROMPT = """你是元演心智系统的数据分析师，专精视频号内容数据分析。

你的任务：分析视频号视频数据的整体表现和变化。

输出严格 JSON，必须使用以下字段名，不要包含 markdown 包裹或额外文字：

{
  "summary": "整体分析摘要，一句话概括本期数据表现",
  "highlights": ["亮点1", "亮点2", ...],
  "warnings": ["需要注意的问题1", ...],
  "suggestions": ["优化建议1", "优化建议2", ...],
  "topVideo": "表现最好的视频（标题+播放量）",
  "actionableInsight": "一个可立即采取行动的核心洞察"
}"""


def _build_analysis_prompt(old_data: list[dict], new_data: list[dict]) -> str:
    """构建分析 prompt，包含新旧数据对比。"""
    old_count = len(old_data)
    new_count = len(new_data)
    added = [v for v in new_data if v not in old_data]
    removed = [v for v in old_data if v not in new_data]

    def fmt_entry(v: dict) -> str:
        return (
            f"  - {v.get('date', '?')} | {v.get('title', '?')} | "
            f"播放{v.get('plays', 0)} | 完播率{v.get('completionRate', 0)}% | "
            f"均播{v.get('avgWatchTime', 0)}s | 3s留存{v.get('retention3s', 0)}% | "
            f"👍{v.get('likes', 0)} 💬{v.get('comments', 0)} ➕{v.get('follows', 0)} 🔄{v.get('shares', 0)}"
        )

    prompt = f"""## Dashboard 数据变化

数据总量：{old_count} → {new_count} 条
新增 {len(added)} 条，减少 {len(removed)} 条

### 当前完整数据：
{chr(10).join(fmt_entry(v) for v in new_data)}

### 新增数据：
{chr(10).join(fmt_entry(v) for v in added) if added else "无新增"}

### 消失数据：
{chr(10).join(fmt_entry(v) for v in removed) if removed else "无消失"}
"""
    return prompt


@retry_with_backoff()
def _call_deepseek(messages: list) -> dict:
    """调用 DeepSeek API 进行数据分析（带重试）。"""
    resp = requests.post(
        f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    # 解析 JSON（处理可能的 markdown 包裹）
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content.strip())


# ── 核心分析器 ──

class DashboardAnalyzer:
    """Dashboard 数据分析器，支持自动检测更新并触发分析。"""

    def __init__(self, check_interval: int = 1800):
        self.check_interval = check_interval
        self._state: dict = self._load_state()
        self._last_data: list[dict] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_check_result: Optional[str] = None

    # ── 状态持久化 ──

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("读取分析状态失败: %s", e)
        return {
            "last_known_updated_at": "",
            "last_analysis_at": "",
            "last_analyzed_count": 0,
        }

    def _save_state(self):
        try:
            STATE_FILE.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("保存分析状态失败: %s", e)

    # ── 数据读取 ──

    def _read_dashboard(self) -> Optional[dict]:
        """读取 dashboard-data.json，返回完整对象或 None。"""
        if not DASHBOARD_FILE.exists():
            logger.warning("dashboard-data.json 不存在")
            return None
        try:
            return json.loads(DASHBOARD_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("读取 dashboard-data.json 失败: %s", e)
            return None

    def _read_old_result(self) -> dict:
        """读取上次的分析结果（用于对比）。"""
        if ANALYSIS_RESULT_FILE.exists():
            try:
                return json.loads(ANALYSIS_RESULT_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    # ── 更新检测 ──

    def has_update(self) -> bool:
        """检查 dashboard-data.json 是否有更新。"""
        dashboard = self._read_dashboard()
        if not dashboard:
            return False

        updated_at = dashboard.get("updatedAt", "")
        data_entries = dashboard.get("data", [])

        if not updated_at:
            return False

        last_known = self._state.get("last_known_updated_at", "")
        if updated_at == last_known:
            return False

        # 数据量没变且 updatedAt 没变 → 无更新
        last_count = self._state.get("last_analyzed_count", 0)
        if len(data_entries) == last_count and updated_at == last_known:
            return False

        return True

    # ── 执行分析 ──

    def analyze(self) -> dict:
        """执行一次完整分析，返回分析结果。"""
        dashboard = self._read_dashboard()
        if not dashboard:
            return {"error": "无法读取 dashboard-data.json"}

        new_data = dashboard.get("data", [])
        updated_at = dashboard.get("updatedAt", "")

        # 读取旧数据（上次 state 中保存的快照）
        old_data = self._last_data

        # 保存当前数据快照
        self._last_data = new_data

        # 构建 prompt
        prompt = _build_analysis_prompt(old_data, new_data)

        # 调用 DeepSeek
        messages = [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        logger.info("正在调用 DeepSeek 分析 %d 条视频数据...", len(new_data))
        result = _call_deepseek(messages)

        if "error" in result and not any(k in result for k in ("summary", "comparison", "highlights", "trends")):
            logger.error("分析失败: %s", result["error"])
            self.last_check_result = "error"
            return result

        # 补充元信息
        result["_meta"] = {
            "analyzedAt": datetime.now().isoformat(),
            "dataUpdatedAt": updated_at,
            "dataCount": len(new_data),
        }

        # 写入 structured result
        ANALYSIS_RESULT_FILE.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 写入 markdown 文件（人类可读）
        self._write_markdown(result, new_data, old_data)

        # 写入信号文件（供 AI 消费）
        self._write_signal(result, updated_at)

        # 更新状态
        self._state["last_known_updated_at"] = updated_at
        self._state["last_analysis_at"] = datetime.now().isoformat()
        self._state["last_analyzed_count"] = len(new_data)
        self._save_state()

        self.last_check_result = "ok"
        logger.info("分析完成: 共 %d 条数据", len(new_data))
        return result

    # ── 输出写入 ──

    def _write_markdown(self, result: dict, new_data: list[dict], old_data: list[dict]):
        """生成人类可读的分析报告 Markdown。"""
        # 兼容两种 schema：最新指定格式 + DeepSeek 原始返回
        summary = (result.get("summary")
                   or result.get("comparison", "无摘要"))
        highlights = (result.get("highlights")
                      or ([result.get("trends")] if result.get("trends") else []))
        warnings = (result.get("warnings")
                    or ([result.get("anomalies")] if result.get("anomalies") else []))
        suggestions = (result.get("suggestions")
                       or result.get("recommendations", []))
        top_video = result.get("topVideo", "")
        insight = result.get("actionableInsight", "")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        updated_str = self._state.get("last_known_updated_at", "未知")[:19]

        lines = [
            "---",
            f"created: {now_str}",
            "tags: [dashboard, analysis, auto-review]",
            "updated: auto",
            "---",
            "",
            f"# 📊 视频数据分析报告",
            "",
            f"> 自动生成于 {now_str} · 数据更新于 {updated_str}",
            "",
            "---",
            "",
            "## 分析摘要",
            "",
            summary,
            "",
        ]

        if top_video:
            lines += ["", f"**🏆 最佳视频：** {top_video}", ""]

        if highlights:
            lines += ["", "## ✨ 亮点发现", ""]
            for h in highlights:
                lines.append(f"- ✅ {h}")

        if warnings:
            lines += ["", "## ⚠️ 需要注意", ""]
            for w in warnings:
                lines.append(f"- 🔴 {w}")

        if suggestions:
            lines += ["", "## 💡 优化建议", ""]
            for s in suggestions:
                lines.append(f"- {s}")

        if insight:
            lines += ["", "---", "", "## 🎯 核心洞察", "", insight, ""]

        lines += [
            "",
            "---",
            "",
            "### 当前数据概览",
            "",
            "| 日期 | 标题 | 播放 | 完播率 | 均播(s) | 3s留存 | 👍 | 💬 | ➕ | 🔄 |",
            "|:----|:-----|:----|:-------|:--------|:-------|:--|:--|:--|:--|",
        ]

        for v in sorted(new_data, key=lambda x: x.get("date", ""), reverse=True):
            lines.append(
                f"| {v.get('date', '')} "
                f"| {v.get('title', '')[:20]} "
                f"| {v.get('plays', 0)} "
                f"| {v.get('completionRate', 0)}% "
                f"| {v.get('avgWatchTime', 0)} "
                f"| {v.get('retention3s', 0)}% "
                f"| {v.get('likes', 0)} "
                f"| {v.get('comments', 0)} "
                f"| {v.get('follows', 0)} "
                f"| {v.get('shares', 0)} |"
            )

        lines.append("")
        ANALYSIS_MD_FILE.write_text("\n".join(lines), encoding="utf-8")
        logger.info("已写入分析报告: %s", ANALYSIS_MD_FILE)

    def _write_signal(self, result: dict, data_updated_at: str):
        """写入信号文件，供 AI 在下一轮对话中读取。"""
        signal = {
            "hasNewAnalysis": True,
            "analyzedAt": datetime.now().isoformat(),
            "dataUpdatedAt": data_updated_at,
            "summary": (result.get("summary")
                        or result.get("comparison", "")),
            "highlights": (result.get("highlights")
                           or ([result.get("trends")] if result.get("trends") else [])),
            "warnings": (result.get("warnings")
                         or ([result.get("anomalies")] if result.get("anomalies") else [])),
            "actionableInsight": (result.get("actionableInsight")
                                  or (result.get("recommendations", [])[0] if result.get("recommendations") else "")),
        }
        SIGNAL_FILE.write_text(
            json.dumps(signal, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("已写入分析信号: %s", SIGNAL_FILE)

    # ── 手动触发 ──

    def check_and_analyze(self) -> dict:
        """检测是否有更新，有则执行分析。返回分析结果或空 dict。"""
        if not self.has_update():
            return {"updated": False, "message": "数据无变化"}

        result = self.analyze()
        if "error" in result:
            return {"updated": False, "error": result["error"]}

        return {
            "updated": True,
            "dataCount": len(self._last_data),
            "summary": result.get("summary", ""),
            "highlights": result.get("highlights", []),
            "warnings": result.get("warnings", []),
        }

    # ── 定时调度 ──

    def start_scheduler(self):
        """启动后台定时检查。"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="dashboard-analysis"
        )
        self._thread.start()
        logger.info("Dashboard 分析调度已启动，间隔 %d 秒", self.check_interval)

    def stop_scheduler(self):
        self._running = False

    def _run_loop(self):
        # 启动后立即检查一次
        try:
            self.check_and_analyze()
        except Exception as e:
            logger.error("启动分析失败: %s", e)

        while self._running:
            time.sleep(self.check_interval)
            if self._running:
                try:
                    self.check_and_analyze()
                except Exception as e:
                    logger.error("定时分析失败: %s", e)

    # ── 状态查询 ──

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "interval": self.check_interval,
            "last_known_updated_at": self._state.get("last_known_updated_at", ""),
            "last_analysis_at": self._state.get("last_analysis_at", ""),
            "last_analyzed_count": self._state.get("last_analyzed_count", 0),
            "last_check_result": self.last_check_result,
            "dashboard_file_exists": DASHBOARD_FILE.exists(),
        }
