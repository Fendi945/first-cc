"""AI 分类引擎——调用 DeepSeek API 做四层分类 + 产出标签。"""

import requests
import json

from engine.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from engine.retry_utils import retry_with_backoff

SYSTEM_PROMPT = """你是一个笔记分类助手。分析用户输入的每一段内容，按「元演心智」系统做两层判断：

## 第一层：四层分类

判断这段内容属于哪个认知层：

| 层 | 名称 | 判断标准 | 示例 |
|---|------|---------|------|
| ontology | 本体层 | 价值观、信念、自我认知——"这就是我"的陈述 | "我追求真实，不说假话" |
| ability | 能力层 | 技能、方法、经验技巧——"我能怎么做"的陈述 | "用'你家的院子'开头完播率高" |
| rule | 规则层 | 规则、规范、操作手册——"应该怎么做"的陈述 | "所有水景视频开头必须有避坑钩子" |
| event | 事件层 | 数据、观察、事件记录——"发生了什么"的陈述 | "评论区很多人问过滤系统" |
| action | 行动项 | 待办任务、项目——"要做什么"的陈述 | "待办：剪完锦鲤池视频" |

## 第二层：产出潜力判断

对每个内容判断产出潜力标签：

| 标签 | 含义 | 后续动作 |
|-----|------|---------|
| none | 无产出价值，纯记录归档 | 不触发任何生产 |
| video | 适合做口播视频 | 草拟脚本 |
| article | 适合做公众号图文 | 生成文章 |
| tool | 可提炼为认知工具/规范 | 自动格式化后入库 |
| explore | 值得探究但不明确怎么做 | 放入问题库 |

## 输出格式

你必须以 JSON 格式输出，不要加 markdown 代码块标记：

{
  "segments": [
    {
      "original_text": "原文段落",
      "layer": "ontology|ability|rule|event|action",
      "layer_reason": "判断理由",
      "output_tag": "none|video|article|tool|explore",
      "tag_reason": "标签理由",
      "summary": "一句话摘要（15字内）",
      "suggested_title": "如果产出内容，建议的标题（无产出则为空字符串）",
      "suitable_platform": "建议平台（视频号/公众号/通用/空）"
    }
  ]
}
"""


@retry_with_backoff()
def _call_deepseek(messages: list) -> dict:
    """调用 DeepSeek API 的通用方法（带重试）。"""
    resp = requests.post(
        f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    # 解析 JSON（处理可能的 markdown 包裹）
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content.strip())


def classify_text(text: str) -> dict:
    """对输入文本做分类。

    返回结构化结果:
    {
        "ok": bool,              # True=成功, False=失败
        "segments": [...],       # ok=True 时有效，分类结果列表
        "error": str|None,       # ok=False 时给出可读错误信息
        "error_type": str|None   # "api" | "auth" | "parse" | "empty" | None
    }
    """
    if not text.strip():
        return {
            "ok": False,
            "segments": [],
            "error": "输入文本为空",
            "error_type": "empty",
        }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"请对以下内容做分类：\n\n{text}"},
    ]

    try:
        result = _call_deepseek(messages)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        if status in (401, 403):
            error_type = "auth"
            error_msg = f"API 认证失败 (HTTP {status})"
        else:
            error_type = "api"
            error_msg = f"API 请求失败 (HTTP {status})"
        return {"ok": False, "segments": [], "error": error_msg, "error_type": error_type}
    except (requests.ConnectionError, requests.Timeout) as e:
        return {"ok": False, "segments": [], "error": f"网络请求失败: {e}", "error_type": "api"}
    except json.JSONDecodeError as e:
        return {"ok": False, "segments": [], "error": f"API 返回格式异常: {e}", "error_type": "parse"}
    except KeyError as e:
        return {"ok": False, "segments": [], "error": f"API 响应缺少字段: {e}", "error_type": "parse"}
    except Exception as e:
        return {"ok": False, "segments": [], "error": f"分类失败: {e}", "error_type": "api"}

    # 检查 _call_deepseek 是否返回了错误
    if "error" in result and result["error"]:
        error_msg = result["error"]
        # 判断错误类型
        if "401" in error_msg or "Unauthorized" in error_msg or "认证" in error_msg:
            error_type = "auth"
        elif "JSON" in error_msg or "parse" in error_msg.lower():
            error_type = "parse"
        else:
            error_type = "api"
        return {
            "ok": False,
            "segments": [],
            "error": error_msg,
            "error_type": error_type,
        }

    segments = result.get("segments", [])
    if not segments:
        return {
            "ok": False,
            "segments": [],
            "error": "API 返回了空结果",
            "error_type": "parse",
        }

    return {
        "ok": True,
        "segments": segments,
        "error": None,
        "error_type": None,
    }
