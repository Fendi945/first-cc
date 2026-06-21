"""文件系统监控——监听 vault 日输入目录 + 看板审批。

Feature:
  - 防抖处理（避免文件保存中重复触发）
  - 分类结果写入 分类日志.json 用于追溯
  - 启动时自动确保 vault 目录结构
  - 监控 看板.md 变更，自动同步审批 → 执行生产
"""

import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from engine.config import DAILY_INPUT_DIR, KANBAN_DIR, CLASSIFY_LOG
from vault_bridge.vault_utils import get_daily_inputs, read_json, write_json

# ── 防抖配置 ──────────────────────────────────────
FILE_COOLDOWN_SECONDS = 3    # 同一文件两次处理的最小间隔
_last_processed = {}         # {str_path: timestamp}


def _is_cooldown(file_path: Path) -> bool:
    """检查文件是否在冷却期内。"""
    key = str(file_path.resolve())
    now = time.time()
    last = _last_processed.get(key, 0)
    if now - last < FILE_COOLDOWN_SECONDS:
        return True
    _last_processed[key] = now
    return False


def _write_classify_log(file_path: Path, raw_results: list) -> None:
    """将分类原始结果写入 分类日志.json。"""
    log_entry = {
        "source_file": str(file_path),
        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "segments": raw_results,
    }
    try:
        logs = read_json(CLASSIFY_LOG)
        if not isinstance(logs, list):
            logs = []
        logs.append(log_entry)
        # 只保留最近 200 条日志，防止无限膨胀
        if len(logs) > 200:
            logs = logs[-200:]
        write_json(CLASSIFY_LOG, logs)
    except Exception as e:
        print(f"  [watchdog] ⚠️ 写入分类日志失败: {e}")


def _ensure_vault_dirs():
    """确保所有必要的 vault 目录存在。"""
    dirs = [DAILY_INPUT_DIR, KANBAN_DIR]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    if not KANBAN_DIR.exists():
        print(f"  [watchdog] ⚠️ 无法创建看板目录: {KANBAN_DIR}")
    if not DAILY_INPUT_DIR.exists():
        print(f"  [watchdog] ⚠️ 无法创建日输入目录: {DAILY_INPUT_DIR}")


class InputHandler(FileSystemEventHandler):
    """日输入文件事件处理器（带防抖）。"""

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".md"):
            file_path = Path(event.src_path)
            if _is_cooldown(file_path):
                return
            process_file(file_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".md"):
            file_path = Path(event.src_path)
            if _is_cooldown(file_path):
                return
            process_file(file_path)


def process_file(file_path: Path) -> None:
    """处理一个日输入文件。

    流程：读取 → AI 分类 → 记入分类日志 → 生成审批项 → 写入待审批 → 标记已处理。
    """
    from engine.classifier import classify_text
    from vault_bridge.vault_utils import read_markdown_file, mark_processed
    from engine.config import PENDING_FILE

    # 防抖：如果文件刚刚被处理过，跳过
    if _is_cooldown(file_path):
        return

    print(f"  📄 处理: {file_path.name}")

    # 读取内容
    content = read_markdown_file(file_path)
    if not content:
        print(f"  ⏭️  跳过空文件: {file_path.name}")
        return

    # AI 分类
    print(f"  🤖 AI 分类中...")
    try:
        results = classify_text(content)
    except Exception as e:
        print(f"  ❌ 分类失败: {e}")
        return

    if not results:
        print(f"  ⏭️  无分类结果，跳过")
        return

    # 写入分类日志（原始结果，便于追溯）
    _write_classify_log(file_path, results)

    # 生成审批项
    pending_items = []
    for seg in results:
        item = {
            "id": f"{file_path.stem}-{len(pending_items)}",
            "source_file": str(file_path),
            "source_date": file_path.stem,
            "original_text": seg.get("original_text", ""),
            "layer": seg.get("layer", "event"),
            "layer_reason": seg.get("layer_reason", ""),
            "output_tag": seg.get("output_tag", "none"),
            "tag_reason": seg.get("tag_reason", ""),
            "summary": seg.get("summary", ""),
            "suggested_title": seg.get("suggested_title", ""),
            "suitable_platform": seg.get("suitable_platform", ""),
            "status": "pending",  # pending | approved | skipped
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        pending_items.append(item)

    # 写入待审批文件
    existing = read_json(PENDING_FILE)
    existing.extend(pending_items)
    write_json(PENDING_FILE, existing)

    # 标记已处理
    try:
        mark_processed(file_path)
    except FileExistsError:
        pass

    # 输出摘要
    video_count = sum(1 for i in pending_items if i["output_tag"] == "video")
    article_count = sum(1 for i in pending_items if i["output_tag"] == "article")
    tool_count = sum(1 for i in pending_items if i["output_tag"] == "tool")
    print(f"  ✅ 完成: {len(pending_items)} 条内容")
    if video_count:
        print(f"     📹 视频 x{video_count}")
    if article_count:
        print(f"     📝 文章 x{article_count}")
    if tool_count:
        print(f"     🔧 工具 x{tool_count}")

    # 更新 Obsidian 看板
    try:
        from engine.kanban_generator import write_kanban_file
        write_kanban_file()
        print(f"     🗂️  看板已更新")
    except Exception as e:
        print(f"     ⚠️  看板更新失败: {e}")


def scan_existing() -> None:
    """扫描所有未处理的日输入文件。"""
    # 确保目录存在
    _ensure_vault_dirs()

    inputs = get_daily_inputs()
    if not inputs:
        print("  📭 没有待处理的日输入文件")
        return
    print(f"  📂 发现 {len(inputs)} 个待处理文件")
    for inp in inputs:
        process_file(inp["path"])


class KanbanHandler(FileSystemEventHandler):
    """看板文件变更处理器 —— 用户勾选复选框后自动同步审批。"""

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith("看板.md"):
            file_path = Path(event.src_path)
            if _is_cooldown(file_path):
                return
            print(f"  📋 看板已更新，检查审批...")
            try:
                from engine.approval_sync import sync_approvals
                count = sync_approvals()
                if count:
                    print(f"  ✅ 自动审批完成，{count} 项已处理")
                else:
                    print(f"     （未发现新勾选项）")
            except Exception as e:
                print(f"  ⚠️  审批同步失败: {e}")


def start_watchdog() -> None:
    """启动文件系统监控（日输入 + 看板审批）。"""
    # 确保目录存在
    _ensure_vault_dirs()
    if not DAILY_INPUT_DIR.exists():
        print(f"⚠️  日输入目录不存在，创建: {DAILY_INPUT_DIR}")
        DAILY_INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 监控日输入
    input_handler = InputHandler()
    # 监控看板
    kanban_handler = KanbanHandler()

    observer = Observer()
    observer.schedule(input_handler, str(DAILY_INPUT_DIR), recursive=False)
    # 监控整个看板目录（看板.md 在里面）
    if KANBAN_DIR.exists():
        observer.schedule(kanban_handler, str(KANBAN_DIR), recursive=False)
    observer.start()

    print(f"👁️  Watchdog 已启动（防抖 {FILE_COOLDOWN_SECONDS}s）")
    print(f"   监控:")
    print(f"     🌱 日输入 → {DAILY_INPUT_DIR}")
    print(f"     📋 看板   → {KANBAN_DIR / '看板.md'}")
    print(f"   等待新文件或审批... (Ctrl+C 停止)\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
