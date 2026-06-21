"""看板生成器 —— 将 待审批.json 渲染为 Obsidian 可读的 看板.md"""

import time
from pathlib import Path
from engine.config import PENDING_FILE, APPROVED_FILE, KANBAN_DIR

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
    """安全读取 JSON，文件不存在或损坏则返回空列表。"""
    try:
        from vault_bridge.vault_utils import read_json
        data = read_json(path)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def generate_kanban() -> str:
    """从 待审批.json 生成 Markdown 看板内容。"""
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
    lines.append(f"> 共 {len(pending)} 项待审批 · 上次更新: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # ── 按产出标签分组 ──
    pending_items = [i for i in pending if i.get("status") == "pending"]
    done_items = [i for i in pending if i.get("status") != "pending"]

    if not pending_items:
        lines.append("## 待审批")
        lines.append("")
        lines.append("🎉 暂无待审批项")
        lines.append("")
    else:
        lines.append("## ✅ 待审批 — 勾选后告诉我「批完了」")
        lines.append("")
        lines.append("> 💡 在 Obsidian 里把 `[ ]` 改成 `[x]` 表示通过，改成 `[-]` 表示跳过")
        lines.append("> 改完后告诉我 **「批完了」**，我自动执行。")
        lines.append("")

        # 按标签分组
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

                lines.append(f"- [ ] `{item_id}` **{title}**")
                if summary:
                    lines.append(f"  - {summary}")
                lines.append(f"  - {layer_icon} {layer} · 📅 {date} · 🎯 {platform}")
                if original:
                    short = original[:80] + ("..." if len(original) > 80 else "")
                    lines.append(f"  - > {short}")
                lines.append("")

    # ── 已处理区 ──
    if done_items:
        lines.append("---")
        lines.append("")
        lines.append("## 📋 已处理")
        lines.append("")
        approved_count = sum(1 for i in done_items if i.get("status") == "approved")
        skipped_count = sum(1 for i in done_items if i.get("status") == "skipped")
        lines.append(f"✅ 已通过 {approved_count} · ⏭️ 已跳过 {skipped_count}")
        lines.append("")
        for item in done_items:
            status_icon = "✅" if item.get("status") == "approved" else "⏭️"
            title = item.get("suggested_title") or item.get("summary") or "(无标题)"
            tag = item.get("output_tag", "")
            tag_icon = TAG_ICON.get(tag, "📄")
            lines.append(f"- {status_icon} {tag_icon} {title}")
        lines.append("")

    # ── 审批日志摘要 ──
    if logs:
        lines.append("---")
        lines.append("")
        lines.append("## 审批日志")
        lines.append("")
        # 只显示最近 10 条
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
    """生成看板.md 并写入 vault。"""
    content = generate_kanban()
    kanban_file = KANBAN_DIR / "看板.md"
    kanban_file.parent.mkdir(parents=True, exist_ok=True)
    kanban_file.write_text(content, encoding="utf-8")
    print(f"  [kanban] ✅ 看板已更新: {kanban_file}")
    return kanban_file


if __name__ == "__main__":
    write_kanban_file()
    print("看板生成完成")
