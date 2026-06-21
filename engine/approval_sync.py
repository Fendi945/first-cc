"""审批同步器 —— 读取用户在看板.md 中勾选的复选框，自动审批。

工作流：
  1. 用户在 Obsidian 打开 看板.md
  2. 点击方框打勾 [x] （Obsidian 默认行为）
  3. Watchdog 自动检测 → 同步审批 → 执行生产
"""

import re
import time
from pathlib import Path
from engine.config import KANBAN_DIR, PENDING_FILE


def parse_kanban_approvals(kanban_path: Path) -> list:
    """解析看板.md，找出用户勾选 [x] 的项。

    Returns:
        [item_id1, item_id2, ...]  # 已勾选的 ID 列表
    """
    if not kanban_path.exists():
        print("  [sync] ⚠️ 看板文件不存在")
        return []

    content = kanban_path.read_text(encoding="utf-8")
    approved = []

    # 匹配复选框行: [x] 表示通过，忽略 [ ]
    pattern = re.compile(r"^- \[([x])\] `([^`]+)`")
    for line in content.split("\n"):
        m = pattern.match(line.strip())
        if m:
            item_id = m.group(2).strip()
            approved.append(item_id)

    return approved


def sync_approvals() -> int:
    """从看板同步审批状态到 待审批.json，返回处理的项数。"""
    from vault_bridge.vault_utils import read_json, write_json

    kanban_file = KANBAN_DIR / "看板.md"
    approved = parse_kanban_approvals(kanban_file)

    if not approved:
        print("  [sync] 📭 看板中未发现新勾选的项")
        print("  [sync] 💡 在 Obsidian 里点击方框打勾即可")
        return 0

    data = read_json(PENDING_FILE)
    if not isinstance(data, list):
        print("  [sync] ❌ 待审批数据格式错误")
        return 0

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    count = 0

    for item in data:
        item_id = item.get("id", "")
        if item_id in approved and item.get("status") == "pending":
            item["status"] = "approved"
            item["approved_at"] = now
            count += 1
            print(f"  [sync] ✅ 通过: {item.get('summary','')[:20]}")

    if count:
        write_json(PENDING_FILE, data)
        print(f"  [sync] ✅ {count} 项已同步")

        # 写入审批日志
        try:
            from vault_bridge.vault_utils import read_json as rj, write_json as wj
            from engine.config import APPROVED_FILE
            logs = rj(APPROVED_FILE)
            if not isinstance(logs, list):
                logs = []
            for item in data:
                if item.get("status") == "approved" and item.get("id") in approved:
                    logs.append({
                        "action": "approved",
                        "item_id": item["id"],
                        "suggested_title": item.get("suggested_title", ""),
                        "summary": item.get("summary", ""),
                        "timestamp": now,
                    })
            if len(logs) > 500:
                logs = logs[-500:]
            wj(APPROVED_FILE, logs)
        except Exception as e:
            print(f"  [sync] ⚠️ 日志写入失败: {e}")

        # 更新看板
        try:
            from engine.kanban_generator import write_kanban_file
            write_kanban_file()
        except Exception:
            pass

        # 自动执行生产
        try:
            from engine.producer import run_production
            run_production()
        except Exception as e:
            print(f"  [sync] ⚠️ 生产执行失败: {e}")
    else:
        print("  [sync] 📭 勾选的项已处理过或无变更")

    return count
