"""审批同步器 —— 读取用户在看板.md 中勾选的复选框，同步到 待审批.json。

工作流：
  1. 用户在 Obsidian 打开 看板.md
  2. 把 [ ] 改成 [x]（通过）或 [-]（跳过）
  3. 用户告诉我「批完了」
  4. 我运行此脚本 → 读取看板 → 更新 JSON → 执行生产
"""

import re
import time
from pathlib import Path
from engine.config import KANBAN_DIR, PENDING_FILE


def parse_kanban_approvals(kanban_path: Path) -> dict:
    """解析看板.md，找出用户勾选的项。

    Returns:
        {"approved": [id1, id2], "skipped": [id3]}
    """
    if not kanban_path.exists():
        print("  [sync] ⚠️ 看板文件不存在")
        return {"approved": [], "skipped": []}

    content = kanban_path.read_text(encoding="utf-8")
    approved = []
    skipped = []

    # 匹配复选框行: - [x] `item-id` Title 或 - [-] `item-id` Title
    pattern = re.compile(r"^- \[([ x-])\] `([^`]+)`")
    for line in content.split("\n"):
        m = pattern.match(line.strip())
        if m:
            status = m.group(1)
            item_id = m.group(2).strip()
            if status == "x":
                approved.append(item_id)
            elif status == "-":
                skipped.append(item_id)

    return {"approved": approved, "skipped": skipped}


def sync_approvals() -> int:
    """从看板同步审批状态到 待审批.json，返回处理的项数。"""
    from vault_bridge.vault_utils import read_json, write_json

    kanban_file = KANBAN_DIR / "看板.md"
    result = parse_kanban_approvals(kanban_file)
    approved = result["approved"]
    skipped = result["skipped"]

    if not approved and not skipped:
        print("  [sync] 📭 看板中未发现勾选的项")
        print("  [sync] 💡 在 Obsidian 里把 [ ] 改成 [x]（通过）或 [-]（跳过）")
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
        elif item_id in skipped and item.get("status") == "pending":
            item["status"] = "skipped"
            item["skipped_at"] = now
            count += 1
            print(f"  [sync] ⏭️ 跳过: {item.get('summary','')[:20]}")

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
                if item.get("status") in ("approved", "skipped") and item.get("id") in approved + skipped:
                    logs.append({
                        "action": item["status"],
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
