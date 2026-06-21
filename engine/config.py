"""配置加载——从 .env 文件读取并暴露为全局常量。"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录（engine/ 的父目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ── vault 路径 ─────────────────────────────────────
VAULT_PATH = Path(os.getenv("VAULT_PATH", ""))
if not VAULT_PATH.exists():
    raise FileNotFoundError(f"VAULT_PATH 不存在: {VAULT_PATH}")

# 目录常量（基于 vault 路径的相对路径）
DAILY_INPUT_DIR = VAULT_PATH / "🌱 原料库" / "日输入"
KANBAN_DIR = VAULT_PATH / "⚙️ 反哺弧" / "看板"
SEED_DIR = VAULT_PATH / "🍎 成品区" / "种子"
TOOL_DIR = VAULT_PATH / "🍎 成品区" / "工具"
RULE_DIR = VAULT_PATH / "🍎 成品区" / "规范"
PROCESSING_DIR = VAULT_PATH / "🌿 加工间"
ISSUE_DIR = VAULT_PATH / "⚙️ 反哺弧" / "📓 问题库"

# 关键 JSON 文件
PENDING_FILE = KANBAN_DIR / "待审批.json"
APPROVED_FILE = KANBAN_DIR / "审批日志.json"
CLASSIFY_LOG = KANBAN_DIR / "分类日志.json"

# ── DeepSeek API ──────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

if not DEEPSEEK_API_KEY:
    raise ValueError(
        "DEEPSEEK_API_KEY 未在 .env 中配置。"
        "请确保 .env 文件中包含 DEEPSEEK_API_KEY=your-key"
    )
