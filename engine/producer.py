"""生产执行器 —— 根据审批结果在 🌿 加工间 执行生产。

审批通过后，不同标签进入不同加工流程：

  video   → 写入加工间/视频脚本/ + 调用现有 FFmpeg 管线
  article → 写入加工间/文章草稿/ + 推送到公众号草稿箱
  tool    → 写入加工间/工具雏形/
  explore → 写入加工间/攻坚/
  none    → 归档（无操作）
"""

import time
from pathlib import Path
from engine.config import PENDING_FILE, PROCESSING_DIR
from engine.log_utils import get_logger

logger = get_logger("producer")


def run_production():
    """扫描已审批尚未生产的项目，执行生产。"""
    from vault_bridge.vault_utils import read_json, write_json, safe_read_json, safe_write_json

    pending = safe_read_json(PENDING_FILE)
    if not isinstance(pending, list):
        logger.warning("待审批数据格式错误")
        return

    produced = 0
    for item in pending:
        if item.get("status") == "approved" and not item.get("produced"):
            tag = item.get("output_tag", "none")
            summary = item.get("summary", "")[:20]
            logger.info("生产: %s (%s)", summary, tag)

            result = _produce(item, tag)
            if result:
                item["produced"] = True
                item["produced_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                item["produced_path"] = str(result)
                produced += 1
                logger.info("产出: %s", result.name)

    if produced:
        safe_write_json(PENDING_FILE, pending)
        logger.info("%d 项已生产", produced)
        try:
            from engine.kanban_generator import write_kanban_file
            write_kanban_file()
        except Exception:
            pass
    else:
        logger.info("无待生产的项")


def _produce(item: dict, tag: str) -> Path | None:
    title = item.get("suggested_title") or item.get("summary") or "未命名"
    summary = item.get("summary", "")
    original = item.get("original_text", "")
    source_date = item.get("source_date", "")

    if tag == "tool":
        return _produce_tool(item, title, summary, original, source_date)
    elif tag == "explore":
        return _produce_explore(item, title, original, source_date)
    elif tag == "video":
        return _produce_video(item, title, summary, original, source_date)
    elif tag == "article":
        return _produce_article(item, title, summary, original, source_date)
    else:
        return None


def _produce_tool(item, title, summary, original, date) -> Path | None:
    """工具雏形 -> 写入 🌿 加工间/工具雏形/"""
    target_dir = PROCESSING_DIR / "工具雏形"
    target_dir.mkdir(parents=True, exist_ok=True)
    return _write_md(target_dir, title, f"""---
created: {date}
type: tool-draft
status: draft
source: 元演AI自动分类
---

# {title}

**摘要：** {summary}

## 来源

{original}

## 核心要点

（待补充 - AI 可进一步提炼）

## 使用场景

（待补充）

## 待完善

- [ ] 补充核心要点
- [ ] 验证实用性
- [ ] 定稿后移入 成品区/工具
""")


def _produce_explore(item, title, original, date) -> Path | None:
    """待深入 -> 写入 🌿 加工间/攻坚/"""
    target_dir = PROCESSING_DIR / "攻坚"
    target_dir.mkdir(parents=True, exist_ok=True)
    return _write_md(target_dir, title, f"""---
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
""")


def _produce_video(item, title, summary, original, date) -> Path | None:
    """视频脚本草稿 -> 写入 🌿 加工间/视频脚本/

    注意：视频的实际生产走现有 FFmpeg 管线（cut_video），
    这里只生成脚本草稿供审核。
    """
    target_dir = PROCESSING_DIR / "视频脚本"
    target_dir.mkdir(parents=True, exist_ok=True)
    return _write_md(target_dir, title, f"""---
created: {date}
type: video-script-draft
status: draft
duration: ~3min
---

# {title}

**摘要：** {summary}

## 口播脚本框架

### 开头 Hook（前5秒）
（待生成 - 基于原文: {original[:100]}）

### 主体逻辑
（待生成）

### 结尾 CTA
（待生成）

## 生产提示

- 后期制作走现有 FFmpeg 管线
- 参考: cut_video --input 口播视频.mp4
- 时长控制在 3 分钟左右

## 待办

- [ ] AI 生成完整脚本
- [ ] 用户审核脚本
- [ ] 进入视频制作管线
""")


def _produce_article(item, title, summary, original, date) -> Path | None:
    """文章草稿 -> 写入 🌿 加工间/文章草稿/ -> 推送到公众号草稿箱"""
    target_dir = PROCESSING_DIR / "文章草稿"
    target_dir.mkdir(parents=True, exist_ok=True)

    filepath = _write_md(target_dir, title, f"""---
created: {date}
type: article-draft
status: draft
platform: 公众号
---

# {title}

**摘要：** {summary}

## 正文

（待 AI 生成完整文章）

---

*本文由元演心智AI自动生成草稿，经人工审核后发布。*
""")

    # 异步推送公众号草稿箱
    if filepath:
        try:
            _push_to_wechat_draft(item, title, summary)
        except Exception as e:
            logger.warning("公众号推送失败: %s", e)

    return filepath


def _push_to_wechat_draft(item, title, summary):
    """将文章推送到微信公众号草稿箱。"""
    try:
        from engine.wechat_publisher import push_draft
        result = push_draft(title, summary)
        if result:
            logger.info("已推送至公众号草稿箱")
            item["wechat_draft_id"] = result
    except ImportError:
        logger.warning("wechat_publisher 模块未就绪")
    except Exception as e:
        logger.warning("公众号推送异常: %s", e)


def _write_md(target_dir: Path, title: str, content: str) -> Path | None:
    """写入 .md 文件，避免覆盖已有文件。"""
    safe_name = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:40]
    if not safe_name:
        safe_name = f"draft-{int(time.time())}"
    filepath = target_dir / f"{safe_name}.md"
    if filepath.exists():
        filepath = target_dir / f"{safe_name}-{int(time.time())}.md"
    try:
        filepath.write_text(content, encoding="utf-8")
        return filepath
    except Exception as e:
        logger.error("写入失败: %s", e)
        return None
