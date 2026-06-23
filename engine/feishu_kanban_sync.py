"""飞书审批看板同步 —— 连接本地 待审批.json 与飞书多维表格。

双向同步：
  - 本地新增待审批项 → 写入飞书
  - 飞书修改状态（通过/拒绝）→ 写回本地
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from engine.config import PENDING_FILE, APPROVED_FILE, PROJECT_ROOT
from engine.feishu_client import FeishuClient

logger = logging.getLogger("feishu_kanban_sync")

STATE_FILE = PROJECT_ROOT / "feishu_kanban_state.json"

# 字段类型
FT_TEXT = 1
FT_SELECT = 3
FT_DATETIME = 5

KANBAN_DEF = {
    "name": "审批看板",
    "table": "审批清单",
    "fields": [
        {"field_name": "标题", "type": FT_TEXT},
        {"field_name": "摘要", "type": FT_TEXT},
        {"field_name": "来源文件", "type": FT_TEXT},
        {"field_name": "建议输出", "type": FT_SELECT, "property": {
            "options": [{"name": "none"}, {"name": "video"}, {"name": "article"}, {"name": "tool"}]}},
        {"field_name": "最终输出", "type": FT_SELECT, "property": {
            "options": [{"name": "none"}, {"name": "video"}, {"name": "article"}, {"name": "tool"}]}},
        {"field_name": "状态", "type": FT_SELECT, "property": {
            "options": [{"name": "pending"}, {"name": "approved"}, {"name": "rejected"}]}},
        {"field_name": "创建时间", "type": FT_DATETIME},
        {"field_name": "审批时间", "type": FT_DATETIME},
        {"field_name": "认知层", "type": FT_TEXT},
        {"field_name": "操作层", "type": FT_TEXT},
        {"field_name": "规范层", "type": FT_TEXT},
        {"field_name": "事件层", "type": FT_TEXT},
    ],
}


class FeishuKanbanSync:
    """审批看板双向同步器。"""

    def __init__(self):
        self._client = FeishuClient()
        self._state: dict = self._load_state()

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("读取飞书看板状态失败: %s", e)
        return {"bitable": {}, "record_map": {}}

    def _save_state(self):
        try:
            STATE_FILE.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("保存飞书看板状态失败: %s", e)

    # ── 表格创建 ──

    def ensure_bitable(self) -> tuple[str, str]:
        """确保审批看板表格存在。"""
        existing = self._state.get("bitable", {})
        if existing:
            return existing["app_token"], existing["table_id"]

        data = self._client.create_bitable(KANBAN_DEF["name"])
        app_token = data.get("app_token")
        if not app_token:
            raise RuntimeError("创建审批看板失败")

        default_table_id = data.get("default_table_id", "")
        tables = self._client.list_tables(app_token)
        table_id = default_table_id

        for t in tables:
            if t.get("table_id") == default_table_id:
                table_id = default_table_id
                break
        else:
            for t in tables:
                table_id = t["table_id"]
                break

        # 创建字段
        for field_def in KANBAN_DEF["fields"]:
            try:
                path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
                payload = {"field_name": field_def["field_name"], "type": field_def["type"]}
                if "property" in field_def:
                    payload["property"] = field_def["property"]
                self._client._post(path, json=payload)
            except RuntimeError as e:
                logger.warning("创建字段失败 %s: %s", field_def["field_name"], e)

        self._state["bitable"] = {"app_token": app_token, "table_id": table_id}
        self._save_state()
        return app_token, table_id

    # ── 从本地同步到飞书 ──

    def sync_local_to_feishu(self) -> dict:
        """将本地待审批数据推送到飞书。"""
        if not PENDING_FILE.exists():
            return {"synced": 0, "total": 0}

        local_data = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        if not isinstance(local_data, list):
            return {"synced": 0, "total": 0}

        app_token, table_id = self.ensure_bitable()

        # 读取飞书已有记录
        existing_records = self._client.list_bitable_records(app_token, table_id, page_size=500)
        feishu_by_id = {}
        for rec in existing_records:
            rid = rec.get("record_id", "")
            fields = rec.get("fields", {})
            # 从摘要字段读取本地ID（存为标记）
            feishu_by_id[rid] = fields

        # 获取本地已同步的记录映射
        record_map = self._state.get("record_map", {})  # { local_id: feishu_record_id }

        synced = 0
        for item in local_data:
            local_id = item.get("id", "")
            if not local_id:
                continue

            feishu_fields = {
                "标题": item.get("title", ""),
                "摘要": item.get("summary", ""),
                "来源文件": item.get("sourceFile", ""),
                "建议输出": item.get("suggestedTag", "none"),
                "最终输出": item.get("finalTag", item.get("suggestedTag", "none")),
                "状态": item.get("status", "pending"),
                "认知层": item.get("classification", {}).get("ontology", ""),
                "操作层": item.get("classification", {}).get("ability", ""),
                "规范层": item.get("classification", {}).get("rule", ""),
                "事件层": item.get("classification", {}).get("event", ""),
            }

            # 时间戳处理
            created = item.get("createdAt", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    feishu_fields["创建时间"] = int(dt.timestamp())
                except (ValueError, TypeError):
                    pass

            approved = item.get("approvedAt", "")
            if approved:
                try:
                    dt = datetime.fromisoformat(approved.replace("Z", "+00:00"))
                    feishu_fields["审批时间"] = int(dt.timestamp())
                except (ValueError, TypeError):
                    pass

            # 检查是否已同步
            feishu_id = record_map.get(local_id)
            if feishu_id:
                # 已存在，更新
                try:
                    path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{feishu_id}"
                    self._client._request("PUT", path, json={"fields": feishu_fields})
                    synced += 1
                except RuntimeError as e:
                    logger.warning("更新记录失败 %s: %s", local_id, e)
            else:
                # 新建
                try:
                    result = self._client.create_bitable_record(app_token, table_id, feishu_fields)
                    new_id = result.get("record_id", "")
                    if new_id:
                        record_map[local_id] = new_id
                        synced += 1
                except RuntimeError as e:
                    logger.warning("创建记录失败 %s: %s", local_id, e)

        self._state["record_map"] = record_map
        self._save_state()

        return {"synced": synced, "total": len(local_data)}

    # ── 从飞书同步到本地 ──

    def sync_feishu_to_local(self) -> dict:
        """将飞书中的状态变更写回本地待审批文件。"""
        if not PENDING_FILE.exists():
            return {"updated": 0}

        local_data = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        if not isinstance(local_data, list):
            return {"updated": 0}

        app_token, table_id = self.ensure_bitable()
        record_map = self._state.get("record_map", {})
        if not record_map:
            return {"updated": 0}

        # 读取飞书记录
        feishu_records = self._client.list_bitable_records(app_token, table_id, page_size=500)
        feishu_by_local = {}
        for rec in feishu_records:
            rid = rec.get("record_id", "")
            for lid, fid in record_map.items():
                if fid == rid:
                    feishu_by_local[lid] = rec.get("fields", {})
                    break

        # 反向映射：找本地ID
        local_by_id = {item.get("id", ""): item for item in local_data}

        updated = 0
        for local_id, feishu_fields in feishu_by_local.items():
            if local_id not in local_by_id:
                continue

            item = local_by_id[local_id]
            feishu_status = feishu_fields.get("状态", "")
            local_status = item.get("status", "")

            if feishu_status and feishu_status != local_status:
                item["status"] = feishu_status
                if feishu_status in ("approved", "rejected"):
                    item["approvedAt"] = datetime.now().isoformat() + "Z"

                # 最终输出标记
                feishu_final = feishu_fields.get("最终输出", "")
                if feishu_final:
                    item["finalTag"] = feishu_final

                updated += 1
                logger.info("状态更新 [%s]: %s -> %s", local_id, local_status, feishu_status)

        if updated > 0:
            PENDING_FILE.write_text(
                json.dumps(local_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("本地待审批文件已更新: %d 条", updated)

        return {"updated": updated}

    # ── 全量双向同步 ──

    def sync_all(self) -> dict:
        """先推本地到飞书，再拉飞书变更回本地。"""
        push = self.sync_local_to_feishu()
        pull = self.sync_feishu_to_local()
        return {"push": push, "pull": pull}

    # ── 状态查询 ──

    def get_status(self) -> dict:
        app_token = self._state.get("bitable", {}).get("app_token", "")
        url = f"https://bcn9k7tysatb.feishu.cn/base/{app_token}" if app_token else ""
        return {
            "configured": bool(self._state.get("bitable", {})),
            "url": url,
            "mapped_records": len(self._state.get("record_map", {})),
        }
