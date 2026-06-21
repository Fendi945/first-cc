"""审批同步器 —— 解析用户在看板.md 中修改的状态符号，自动执行。

状态符号对照：
  ⏳ → 待审批（默认，不处理）
  ✅ → 通过（按原标签执行生产）
  ❌ → 拒绝（跳过，不生产）
  📹 → 改视频（覆盖原标签）
  📝 → 改文章（覆盖原标签）
  🔧 → 改工具（覆盖原标签）
"""

import re
import time
from pathlib import Path
from engine.config import KANBAN_DIR, PENDING_FILE

# 状态符号到系统状态的映射
STATUS_MAP = {
    "✅": "approved",
    "❌": "skipped",
}

# 状态符号到产出标签的覆盖映射
TAG_OVERRIDE = {
    "📹": "video",
    "📝": "article",
    "🔧": "tool",
}

# 所有需要处理的符号（⏳ 是待审批，忽略）
ACTIVE_SYMBOLS = set(STATUS_MAP.keys()) | set(TAG_OVERRIDE.keys())


def parse_kanban_actions(kanban_path: Path) -> list[dict]:
    """解析看板.md，找出用户修改了状态符号的项。

    Returns:
        [{"id": str, "action": str, "tag_override": str|None}, ...]
    """
    if not kanban_path.exists():
        print("  [sync] ⚠️ 看板文件不存在")
        return []

    content = kanban_path.read_text(encoding="utf-8")
    actions = []

    # 匹配格式：- {符号} id:{item_id} **标题**
    pattern = re.compile(r"^- ([✅❌📹📝🔧]) `([^`]+)`")

    for line in content.split("\n"):
        m = pattern.match(line.strip())
        if not m:
            continue
        symbol = m.group(1)
        item_id = m.group(2).strip()

        if symbol not in ACTIVE_SYMBOLS:
            continue

        action = {
            "id": item_id,
            "action": STATUS_MAP.get(symbol, "approved"),
            "tag_override": TAG_OVERRIDE.get(symbol, None),
        }
        actions.append(action)

    return actions


def sync_approvals() -> int:
    """从看板同步审批状态到 待审批.json，返回处理的项数。"""
    from vault_bridge.vault_utils import read_json, write_json

    kanban_file = KANBAN_DIR / "看板.md"
    actions = parse_kanban_actions(kanban_file)

    if not actions:
        print("  [sync] 📭 看板中未发现状态变更")
        return 0

    data = read_json(PENDING_FILE)
    if not isinstance(data, list):
        print("  [sync] ❌ 待审批数据格式错误")
        return 0

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    count = 0

    for action in actions:
        item_id = action["id"]
        new_status = action["action"]
        tag_override = action["tag_override"]

        for item in data:
            if item.get("id") == item_id and item.get("status") == "pending":
                item["status"] = new_status
                item["approved_at"] = now

                # 如果用户换了产出标签
                if tag_override:
                    old_tag = item.get("output_tag", "")
                    item["output_tag"] = tag_override
                    item["tag_reason"] = f"用户手动修改: {old_tag} → {tag_override}"

                count += 1
                summary = item.get("summary", "")[:20]
                symbol = "✅" if new_status == "approved" else "❌"
                print(f"  [sync] {symbol} {summary}")
                if tag_override:
                    print(f"        标签改为: {tag_override}")

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
                if item.get("status") in ("approved", "skipped") and item.get("id") in [a["id"] for a in actions]:
                    logs.append({
                        "action": item["status"],
                        "item_id": item["id"],
                        "suggested_title": item.get("suggested_title", ""),
                        "summary": item.get("summary", ""),
                        "output_tag": item.get("output_tag", ""),
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
