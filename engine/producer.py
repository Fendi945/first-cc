"""生产执行器 —— 根据审批结果执行具体生产动作。

当用户在 Obsidian 看板完成审批后，本模块负责：
- video → 生成口播脚本
- article → 生成公众号文章
- tool → 格式化工具 → 写入 成品区/工具
- explore → 写入 问题库
- none → 归档（无操作）
"""

import time
import json
from pathlib import Path
from engine.config import PENDING_FILE, APPROVED_FILE, SEED_DIR, TOOL_DIR, ISSUE_DIR, KANBAN_DIR


def run_production():
    """扫描已审批尚未生产的项目，执行生产。"""
    from vault_bridge.vault_utils import read_json, write_json

    pending = read_json(PENDING_FILE)
    if not isinstance(pending, list):
        print("  [producer] ⚠️ 待审批数据格式错误")
        return

    produced = 0
    for item in pending:
        if item.get("status") == "approved" and not item.get("produced"):
            tag = item.get("output_tag", "none")
            print(f"  [producer] 🏭 生产: {item.get('summary','')[:20]}... ({tag})")

            result = _produce(item, tag)
            if result:
                item["produced"] = True
                item["produced_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                item["produced_path"] = str(result)
                produced += 1
                print(f"    → 产出: {result}")

    if produced:
        write_json(PENDING_FILE, pending)
        print(f"  [producer] ✅ {produced} 项已生产")
        # 更新看板
        try:
            from engine.kanban_generator import write_kanban_file
            write_kanban_file()
        except Exception:
            pass
    else:
        print("  [producer] 📭 无待生产的项")


def _produce(item: dict, tag: str) -> Path | None:
    """根据产出标签执行生产，返回产出文件路径。"""
    title = item.get("suggested_title") or item.get("summary") or "未命名"
    summary = item.get("summary", "")
    original = item.get("original_text", "")
    source_date = item.get("source_date", "")

    if tag == "tool":
        return _produce_tool(item, title, summary, original, source_date)
    elif tag == "explore":
        return _produce_explore(item, title, original, source_date)
    elif tag == "video":
        return _produce_script(item, title, summary, original, source_date)
    elif tag == "article":
        return _produce_article(item, title, summary, original, source_date)
    else:
        return None


def _produce_tool(item, title, summary, original, date) -> Path | None:
    """将内容格式化为认知工具，写入 成品区/工具。"""
    TOOL_DIR.mkdir(parents=True, exist_ok=True)

    # 生成工具文件名
    safe_name = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:30]
    if not safe_name:
        safe_name = f"tool-{int(time.time())}"

    tool_file = TOOL_DIR / f"{safe_name}.md"
    content = f"""---
created: {date}
type: tool
source: 元演AI自动分类
status: published
---

# {title}

**摘要：** {summary}

## 来源

{original}

## 核心要点

（待补充——可根据 AI 提炼自动生成）

## 使用场景

（待补充）

## 相关链接

- 来源: 日输入 {date}
"""
    try:
        # 避免覆盖已有文件
        if tool_file.exists():
            tool_file = TOOL_DIR / f"{safe_name}-{int(time.time())}.md"
        tool_file.write_text(content, encoding="utf-8")
        return tool_file
    except Exception as e:
        print(f"    ❌ 写入工具失败: {e}")
        return None


def _produce_explore(item, title, original, date) -> Path | None:
    """将待深入内容放入问题库。"""
    ISSUE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:30]
    if not safe_name:
        safe_name = f"explore-{int(time.time())}"

    issue_file = ISSUE_DIR / f"{safe_name}.md"
    content = f"""---
created: {date}
type: explore
status: open
---

# {title}

**来源：** 日输入 {date}

## 原始内容

{original}

## 探究方向

（待定义）

## 状态

⏳ 待深入探究
"""
    try:
        if issue_file.exists():
            issue_file = ISSUE_DIR / f"{safe_name}-{int(time.time())}.md"
        issue_file.write_text(content, encoding="utf-8")
        return issue_file
    except Exception as e:
        print(f"    ❌ 写入问题库失败: {e}")
        return None


def _produce_script(item, title, summary, original, date) -> Path | None:
    """生成口播视频脚本草稿。"""
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:30]
    if not safe_name:
        safe_name = f"script-{int(time.time())}"

    script_file = SEED_DIR / f"{safe_name}-脚本.md"
    content = f"""---
created: {date}
type: video-script
status: draft
duration: ~3min
---

# {title}

**摘要：** {summary}

## 口播脚本

（待 AI 生成完整脚本——基于原文: {original}）

### 开头 Hook

### 主体内容

### 结尾 Call to Action

## 拍摄提示

- 时长: ~3分钟
- 格式: 竖屏 9:16
- 风格: 口播

## 相关

- 来源: {date}
"""
    try:
        if script_file.exists():
            script_file = SEED_DIR / f"{safe_name}-{int(time.time())}.md"
        script_file.write_text(content, encoding="utf-8")
        return script_file
    except Exception as e:
        print(f"    ❌ 生成脚本失败: {e}")
        return None


def _produce_article(item, title, summary, original, date) -> Path | None:
    """生成公众号文章草稿。"""
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:30]
    if not safe_name:
        safe_name = f"article-{int(time.time())}"

    article_file = SEED_DIR / f"{safe_name}-文章.md"
    content = f"""---
created: {date}
type: article-draft
status: draft
platform: 公众号
---

# {title}

**摘要：** {summary}

## 正文

（待 AI 生成完整文章——基于原文: {original}）

---

*本文由元演心智AI自动生成草稿，经人工审核后发布。*
"""
    try:
        if article_file.exists():
            article_file = SEED_DIR / f"{safe_name}-{int(time.time())}.md"
        article_file.write_text(content, encoding="utf-8")
        return article_file
    except Exception as e:
        print(f"    ❌ 生成文章失败: {e}")
        return None
