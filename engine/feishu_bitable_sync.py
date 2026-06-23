"""飞书多维表格同步模块 —— 管理 Obsidian → 飞书 的数据同步。

负责三个表格的维护：
1. 成品区发布物 — 同步 成品区/发布物/ 的文档
2. 口播文档 — 同步 加工间/常驻/、视频脚本/ 的口播稿
3. 公众号&视频号数据 — 记录各平台数据变化
"""

import calendar
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from engine.config import PROJECT_ROOT, VAULT_PATH
from engine.feishu_client import FeishuClient

logger = logging.getLogger("feishu_bitable_sync")

# ── 状态文件 ──
STATE_FILE = PROJECT_ROOT / "feishu_bitable_state.json"

# ── 表格定义 ──

def _to_ts(dt_str: str) -> int:
    """将 ISO 时间字符串转为飞书 API 所需的 Unix 时间戳（秒）。"""
    try:
        dt = datetime.fromisoformat(dt_str)
        return int(dt.timestamp())
    except (ValueError, TypeError):
        return int(time.time())

def _now_ts() -> int:
    """当前时间的 Unix 时间戳。"""
    return int(time.time())

# 字段类型常量
FT_TEXT = 1
FT_NUMBER = 2
FT_SELECT = 3
FT_MULTISELECT = 5
FT_DATETIME = 5
FT_URL = 15

BITABLE_DEFS = {
    "成品区发布物": {
        "description": "Obsidian 成品区已发布的文档",
        "tables": [
            {
                "name": "发布物清单",
                "fields": [
                    {"field_name": "标题", "type": FT_TEXT},
                    {"field_name": "分类", "type": FT_SELECT, "property": {"options": [{"name": "口播"}, {"name": "渔樵问对"}, {"name": "其他"}]}},
                    {"field_name": "状态", "type": FT_SELECT, "property": {"options": [{"name": "已发布"}, {"name": "待发布"}]}},
                    {"field_name": "最后修改时间", "type": FT_DATETIME},
                    {"field_name": "内容摘要", "type": FT_TEXT},
                    {"field_name": "文件路径", "type": FT_TEXT},
                    {"field_name": "同步时间", "type": FT_DATETIME},
                ],
            }
        ],
        "source_dirs": ["🍎 成品区/发布物"],
    },
    "口播文档": {
        "description": "口播稿与视频脚本",
        "tables": [
            {
                "name": "口播清单",
                "fields": [
                    {"field_name": "标题", "type": FT_TEXT},
                    {"field_name": "状态", "type": FT_SELECT, "property": {"options": [{"name": "草稿"}, {"name": "常驻"}, {"name": "已发布"}]}},
                    {"field_name": "创建时间", "type": FT_DATETIME},
                    {"field_name": "最后修改时间", "type": FT_DATETIME},
                    {"field_name": "内容摘要", "type": FT_TEXT},
                    {"field_name": "文件路径", "type": FT_TEXT},
                    {"field_name": "来源目录", "type": FT_SELECT, "property": {"options": [{"name": "常驻"}, {"name": "视频脚本"}, {"name": "文章草稿"}]}},
                    {"field_name": "同步时间", "type": FT_DATETIME},
                ],
            }
        ],
        "source_dirs": ["🌿 加工间/常驻", "🌿 加工间/视频脚本"],
    },
    "公众号&视频号数据": {
        "description": "各平台数据变化记录",
        "tables": [
            {
                "name": "数据记录",
                "fields": [
                    {"field_name": "日期", "type": FT_DATETIME},
                    {"field_name": "平台", "type": FT_SELECT, "property": {"options": [{"name": "公众号"}, {"name": "视频号"}]}},
                    {"field_name": "作品标题", "type": FT_TEXT},
                    {"field_name": "阅读量/播放量", "type": FT_NUMBER},
                    {"field_name": "点赞", "type": FT_NUMBER},
                    {"field_name": "评论", "type": FT_NUMBER},
                    {"field_name": "转发/分享", "type": FT_NUMBER},
                    {"field_name": "新增关注", "type": FT_NUMBER},
                    {"field_name": "备注", "type": FT_TEXT},
                    {"field_name": "记录时间", "type": FT_DATETIME},
                ],
            }
        ],
        "source_dirs": [],  # 手动录入，无本地源
    },
}


class FeishuBitableSync:
    """飞书多维表格同步管理器。"""

    def __init__(self):
        self._client = FeishuClient()
        self._state: dict = self._load_state()
        self._vault = VAULT_PATH

    # ── 状态持久化 ──

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("读取飞书表格状态失败: %s", e)
        return {"bitables": {}}  # { bitable_name: { "app_token": "...", "table_map": { "表名": "table_id" } } }

    def _save_state(self):
        try:
            STATE_FILE.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("保存飞书表格状态失败: %s", e)

    # ── 表格创建 ──

    def ensure_bitable(self, name: str) -> tuple[str, dict]:
        """确保多维表格存在，不存在则创建。

        返回:
            (app_token, table_map) — table_map: { table_name: table_id }
        """
        # 检查是否已记录
        existing = self._state.get("bitables", {}).get(name)
        if existing:
            return existing["app_token"], existing["table_map"]

        # 创建多维表格
        logger.info("创建多维表格: %s", name)
        data = self._client.create_bitable(name)
        app_token = data.get("app_token")
        if not app_token:
            raise RuntimeError(f"创建多维表格「{name}」失败: 未返回 app_token")

        # 获取默认表 ID（创建时返回的）
        default_table_id = data.get("default_table_id", "")

        # 获取所有已有表
        tables = self._client.list_tables(app_token)
        table_map = {}
        for t in tables:
            table_map[t.get("name", "")] = t.get("table_id", "")

        # 根据定义创建/更新表结构和字段
        bitable_def = BITABLE_DEFS.get(name)
        if bitable_def:
            for table_def in bitable_def.get("tables", []):
                tname = table_def["name"]

                if default_table_id and tname not in table_map:
                    # 使用刚创建时返回的默认表 ID，映射到目标表名
                    table_map[tname] = default_table_id
                    default_table_id = None
                elif tname not in table_map:
                    logger.warning("表「%s」不存在，请手动在飞书中创建", tname)
                    continue

                # 确保字段存在
                table_id = table_map.get(tname)
                if table_id:
                    self._ensure_fields(app_token, table_id, table_def["fields"])

        # 保存状态
        self._state.setdefault("bitables", {})[name] = {
            "app_token": app_token,
            "table_map": table_map,
        }
        self._save_state()

        return app_token, table_map

    def _ensure_fields(self, app_token: str, table_id: str, required_fields: list[dict]):
        """确保表格包含指定的字段，缺失的自动创建。"""
        path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        existing = self._client._get(path)
        existing_fields = {f.get("field_name", ""): f for f in existing.get("data", {}).get("items", [])}

        for field_def in required_fields:
            fname = field_def["field_name"]
            if fname in existing_fields:
                continue
            try:
                path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
                payload = {
                    "field_name": fname,
                    "type": field_def["type"],
                }
                if "property" in field_def:
                    payload["property"] = field_def["property"]
                self._client._post(path, json=payload)
                logger.info("  创建字段: %s (type=%d)", fname, field_def["type"])
            except RuntimeError as e:
                logger.warning("  创建字段失败 %s: %s", fname, e)

    # ── 文件扫描与同步 ──

    def scan_markdown_files(self, source_dirs: list[str]) -> list[dict]:
        """扫描 Obsidian 目录中的 Markdown 文件，返回文件元数据列表。

        参数:
            source_dirs: 相对 vault 的目录路径列表

        返回:
            [{title, path, content_preview, modified_at, ...}]
        """
        files = []
        for rel_dir in source_dirs:
            full_dir = self._vault / rel_dir
            if not full_dir.exists():
                logger.warning("目录不存在，跳过: %s", full_dir)
                continue
            for md_file in sorted(full_dir.glob("*.md")):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    first_line = content.strip().split("\n")[0].replace("#", "").strip()
                    title = first_line or md_file.stem
                    preview = "\n".join(content.strip().split("\n")[1:6])[:200]

                    mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                    rel_path = str(Path(rel_dir) / md_file.name)

                    files.append({
                        "title": title,
                        "file_path": rel_path,
                        "content_preview": preview,
                        "modified_at": mtime.isoformat(),
                        "full_content": content,
                    })
                except Exception as e:
                    logger.warning("读取文件失败 %s: %s", md_file, e)

        logger.info("扫描到 %d 个文件", len(files))
        return files

    def sync_bitable(self, bitable_name: str) -> int:
        """将源目录中的文件同步到指定的多维表格。

        返回:
            新写入的记录数
        """
        bitable_def = BITABLE_DEFS.get(bitable_name)
        if not bitable_def:
            raise ValueError(f"未定义的表格: {bitable_name}")

        # 确保表格存在
        app_token, table_map = self.ensure_bitable(bitable_name)

        # 获取默认表的 ID
        default_table = bitable_def["tables"][0]
        tname = default_table["name"]
        table_id = table_map.get(tname)
        if not table_id:
            raise RuntimeError(f"多维表格「{bitable_name}」中未找到表「{tname}」")

        # 扫描文件
        files = self.scan_markdown_files(bitable_def.get("source_dirs", []))
        if not files:
            logger.info("没有新文件需要同步")
            return 0

        # 获取已有记录（按标题去重）
        existing = self._client.list_bitable_records(app_token, table_id, page_size=500)
        existing_titles = set()
        for rec in existing:
            fields = rec.get("fields", {})
            title = fields.get("标题", "") or fields.get("作品标题", "")
            if title:
                existing_titles.add(title)

        count = 0

        for f in files:
            if f["title"] in existing_titles:
                logger.debug("跳过已存在的记录: %s", f["title"])
                continue

            # 构建字段
            fields = {
                "标题": f["title"],
                "文件路径": f["file_path"],
                "内容摘要": f["content_preview"],
                "最后修改时间": _to_ts(f["modified_at"]),
                "同步时间": _now_ts(),
            }

            # 自动分类（针对成品区发布物）
            if bitable_name == "成品区发布物":
                if "口播" in f["title"]:
                    fields["分类"] = "口播"
                elif "渔樵" in f["title"]:
                    fields["分类"] = "渔樵问对"
                else:
                    fields["分类"] = "其他"
                fields["状态"] = "已发布"

            # 针对口播文档
            if bitable_name == "口播文档":
                fields["创建时间"] = _to_ts(f["modified_at"])
                # 判断来源目录
                if "常驻" in f["file_path"]:
                    fields["来源目录"] = "常驻"
                    fields["状态"] = "常驻"
                elif "视频脚本" in f["file_path"]:
                    fields["来源目录"] = "视频脚本"
                    fields["状态"] = "草稿"

            try:
                self._client.create_bitable_record(app_token, table_id, fields)
                count += 1
                logger.info("  同步: %s", f["title"])
            except RuntimeError as e:
                logger.error("  写入失败 %s: %s", f["title"], e)

        logger.info("「%s」同步完成: 新增 %d 条", bitable_name, count)
        return count

    # ── 全量同步 ──

    def sync_all(self) -> dict:
        """同步所有有源目录的表格。

        返回:
            { bitable_name: synced_count }
        """
        results = {}
        for name, defn in BITABLE_DEFS.items():
            if defn.get("source_dirs"):
                try:
                    count = self.sync_bitable(name)
                    results[name] = count
                except Exception as e:
                    logger.error("同步「%s」失败: %s", name, e)
                    results[name] = -1
        return results

    # ── 手动记录数据（公众号&视频号数据） ──

    def add_data_record(self, platform: str, title: str, views: int = 0,
                        likes: int = 0, comments: int = 0, shares: int = 0,
                        new_followers: int = 0, notes: str = "",
                        record_date: Optional[str] = None) -> dict:
        """向「公众号&视频号数据」表格添加一条数据记录。

        参数:
            platform: 平台（公众号/视频号）
            title: 作品标题
            views: 阅读量/播放量
            likes: 点赞数
            comments: 评论数
            shares: 转发/分享数
            new_followers: 新增关注
            notes: 备注
            record_date: 日期，默认为当天

        返回:
            创建的记录数据
        """
        bitable_def = BITABLE_DEFS.get("公众号&视频号数据")
        if not bitable_def:
            raise ValueError("公众号&视频号数据表格未定义")

        app_token, table_map = self.ensure_bitable("公众号&视频号数据")
        default_table = bitable_def["tables"][0]
        table_id = table_map.get(default_table["name"])
        if not table_id:
            raise RuntimeError("未找到数据记录表")

        date_str = record_date or datetime.now().strftime("%Y-%m-%d")
        fields = {
            "日期": _to_ts(f"{date_str}T00:00:00"),
            "平台": platform,
            "作品标题": title,
            "阅读量/播放量": views,
            "点赞": likes,
            "评论": comments,
            "转发/分享": shares,
            "新增关注": new_followers,
            "备注": notes,
            "记录时间": _now_ts(),
        }

        return self._client.create_bitable_record(app_token, table_id, fields)

    # ── 状态查询 ──

    def get_status(self) -> dict:
        bitables = {}
        for name, info in self._state.get("bitables", {}).items():
            bitables[name] = {
                "app_token": info["app_token"],
                "tables": info["table_map"],
            }
        return {
            "bitables": bitables,
            "bitable_count": len(bitables),
        }
