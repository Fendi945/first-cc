"""Vault 文件读写工具函数。"""
import json
import re
import threading
from pathlib import Path
from typing import Any, Optional
from engine.config import DAILY_INPUT_DIR


def read_markdown_file(path: Path) -> str:
    """读取 .md 文件，去除 YAML frontmatter，返回正文。"""
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8")
    # 去除 ---...--- frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            content = content[end + 3:]
    return content.strip()


def read_json(path: Path) -> Any:
    """读取 JSON 文件，文件不存在返回空列表/空字典。"""
    if not path.exists():
        return [] if path.suffix == ".json" else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def write_json(path: Path, data: Any) -> None:
    """写入 JSON 文件（UTF-8，缩进2）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_daily_inputs() -> list[dict]:
    """获取日输入目录中所有未处理的 .md 文件。

    返回: [{"path": Path, "filename": str, "date": str}, ...]
    按修改时间排序，最新的在前。
    """
    if not DAILY_INPUT_DIR.exists():
        return []
    files = []
    for f in sorted(DAILY_INPUT_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        # 跳过已处理文件（文件名以 _done 结尾）
        if f.stem.endswith("_done"):
            continue
        files.append({
            "path": f,
            "filename": f.name,
            "date": f.stem,  # YYYY-MM-DD
        })
    return files


def mark_processed(file_path: Path) -> None:
    """标记文件已处理：重命名为 原名_done.md。"""
    new_path = file_path.with_stem(file_path.stem + "_done")
    file_path.rename(new_path)


# ── 线程安全 JSON 读写 ──────────────────────────────
_file_locks: dict[str, threading.Lock] = {}
_file_locks_lock = threading.Lock()


def _get_file_lock(path: Path) -> threading.Lock:
    """获取或创建文件级线程锁（按路径互斥）。"""
    key = str(path.resolve())
    with _file_locks_lock:
        if key not in _file_locks:
            _file_locks[key] = threading.Lock()
        return _file_locks[key]


def safe_read_json(path: Path) -> Any:
    """线程安全地读取 JSON 文件。

    与 read_json() 行为完全一致，但加锁防止并发写导致的数据损坏。
    """
    lock = _get_file_lock(path)
    with lock:
        return read_json(path)


def safe_write_json(path: Path, data: Any) -> None:
    """线程安全地写入 JSON 文件。

    与 write_json() 行为完全一致，但加锁防止并发写导致的数据损坏。
    """
    lock = _get_file_lock(path)
    with lock:
        write_json(path, data)
