"""看板生成器 —— 将 待审批.json 渲染为 Obsidian 可读的 看板.md"""

import time
from pathlib import Path
from engine.config import PENDING_FILE, APPROVED_FILE, KANBAN_DIR

STATUS_SYMBOL = {
    "pending": "⏳",
    "approved": "✅",
    "skipped": "❌",
}

LAYER_ICON = {
    "ontology": "🧬",
    "ability": "🛠️",
    "rule": "📏",
    "event": "📡",
    "action": "✅",
}

TAG_ICON = {
    "video": "📹",
    "article": "📝",
    "tool": "🔧",
    "none": "⛔",
    "explore": "❓",
}

TAG_LABEL = {
    "video": "适合做视频",
    "article": "适合写文章",
    "tool": "可提炼工具",
    "none": "归档记录",
    "explore": "待深入探究",
}


def _read_json_safe(path: Path) -> list:
    try:
        from vault_bridge.vault_utils import read_json
        data = read_json(path)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def generate_kanban() -> str:
    pending = _read_json_safe(PENDING_FILE)
    logs = _read_json_safe(APPROVED_FILE)

    lines = []
    lines.append("---")
    lines.append("created: " + time.strftime("%Y-%m-%d %H:%M"))
    lines.append("updated: auto")
    lines.append("tags: [kanban, review]")
    lines.append("---")
    lines.append("")
    lines.append("# 元演心智 · 待审批看板")
    lines.append("")

    pending_items = [i for i in pending if i.get("status") == "pending"]
    done_items = [i for i in pending if i.get("status") != "pending"]

    total = len(pending_items)
    lines.append(f"> 共 {total} 项待审批 · 上次更新: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 操作说明")
    lines.append("")
    lines.append("每个待审批项前面有个符号，**替换它**来控制我的下一步：")
    lines.append("")
    lines.append("| 替换为 | 含义 | 我会做什么 |")
    lines.append("|-------|------|-----------|")
    lines.append("| ✅ | **通过** | 按原标签执行生产 |")
    lines.append("| ❌ | **拒绝** | 跳过此项，不生产 |")
    lines.append("| 📹 | **改视频** | 按视频脚本走管线 |")
    lines.append("| 📝 | **改文章** | 按公众号文章生成 |")
    lines.append("| 🔧 | **改工具** | 提炼为认知工具入库 |")
    lines.append("")
    lines.append("> ⏳ 保留不动 = 待审批，我不处理")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── 待审批区 ──
    if not pending_items:
        lines.append("## 待审批")
        lines.append("")
        lines.append("🎉 暂无待审批项")
        lines.append("")
    else:
        lines.append("## 待审批")
        lines.append("")

        groups = {"video": [], "article": [], "tool": [], "explore": [], "none": []}
        for item in pending_items:
            tag = item.get("output_tag", "none")
            if tag in groups:
                groups[tag].append(item)
            else:
                groups["none"].append(item)

        for tag, items in groups.items():
            if not items:
                continue
            icon = TAG_ICON.get(tag, "📄")
            label = TAG_LABEL.get(tag, "")
            lines.append(f"### {icon} {label}（{len(items)}项）")
            lines.append("")
            for item in items:
                item_id = item.get("id", "")
                title = item.get("suggested_title") or item.get("summary") or "(无标题)"
                summary = item.get("summary", "")
                original = item.get("original_text", "")
                layer = item.get("layer", "")
                layer_icon = LAYER_ICON.get(layer, "📄")
                date = item.get("source_date", "")
                platform = item.get("suitable_platform") or "待定"

                summary_text = f" — {summary}" if summary else ""
                lines.append(f"- ⏳ `{item_id}` **{title}**{summary_text}")
                lines.append(f"  - {layer_icon} {layer} · 📅 {date} · 🎯 {platform}")
                if original:
                    short = original[:80] + ("..." if len(original) > 80 else "")
                    lines.append(f"  - > {short}")
                lines.append("")

    # ── 已处理区 ──
    if done_items:
        lines.append("---")
        lines.append("")
        lines.append("## 已处理")
        lines.append("")
        approved_count = sum(1 for i in done_items if i.get("status") == "approved")
        skipped_count = sum(1 for i in done_items if i.get("status") == "skipped")
        lines.append(f"✅ 已通过 {approved_count} · ❌ 已拒绝 {skipped_count}")
        lines.append("")
        for item in done_items:
            status_icon = "✅" if item.get("status") == "approved" else "❌"
            title = item.get("suggested_title") or item.get("summary") or "(无标题)"
            tag = item.get("output_tag", "")
            tag_icon = TAG_ICON.get(tag, "📄")
            lines.append(f"- {status_icon} {tag_icon} {title}")
        lines.append("")

    # ── 审批日志 ──
    if logs:
        lines.append("---")
        lines.append("")
        lines.append("## 审批日志")
        lines.append("")
        recent = logs[-10:]
        for entry in recent:
            ts = entry.get("timestamp", "")
            action = entry.get("action", "")
            action_icon = "✅" if action == "approved" else "⏭️"
            title = entry.get("suggested_title", "") or entry.get("summary", "")[:20]
            lines.append(f"- {action_icon} {title} · {ts}")
        lines.append("")

    return "\n".join(lines)


def write_kanban_file():
    content = generate_kanban()
    kanban_file = KANBAN_DIR / "看板.md"
    kanban_file.parent.mkdir(parents=True, exist_ok=True)
    kanban_file.write_text(content, encoding="utf-8")
    print(f"  [kanban] ✅ 看板已更新: {kanban_file}")
    return kanban_file


if __name__ == "__main__":
    write_kanban_file()
    print("看板生成完成")
