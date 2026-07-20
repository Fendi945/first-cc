---
title: 元演心智 · Bug 修复与稳定性加固
created: 2026-06-24
status: approved
tags: [元演心智, bugfix, 稳定性, 设计文档]
---

# 元演心智 · Bug 修复与稳定性加固

> **一句话：修复当前系统中最高优先级的 3 个稳定性问题——JSON 并发写竞争、API 错误被吞、API 调用无重试。**

---

## 一、修复范围

本次仅覆盖 **批次 A（紧急修复）**，不改变现有功能逻辑：

| # | 问题 | 严重度 | 涉及模块数 |
|---|------|--------|-----------|
| 1 | JSON 文件多线程并发写竞争 | 🔴 数据损坏风险 | 5 个模块 |
| 2 | API 错误返回被静默吞掉 | 🔴 用户不知情 | 2 个模块 |
| 3 | API 调用没有重试逻辑 | 🟡 瞬断即永久失败 | 4 个模块 + 新增工具 |

---

## 二、修复 1：JSON 文件锁

### 根因

`watchdog.py` / `server.py` / `approval_sync.py` / `producer.py` 四个模块都可能并发读写同一个 `待审批.json`。

典型竞态场景：
1. Watchdog 检测到日输入 → `read_json` 读取
2. 与此同时 Server API 处理审批 → `write_json` 写入
3. Watchdog 基于旧数据做修改 → 覆盖了 Server 的写入 → 审批记录丢失
4. 更糟：两个同时 `write_json` → 文件内容截断/损坏

### 方案：线程级文件锁

在 `vault_bridge/vault_utils.py` 中新增：

```python
import threading

# 全局文件锁注册表
_file_locks: dict[str, threading.Lock] = {}
_file_locks_lock = threading.Lock()

def _get_file_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _file_locks_lock:
        if key not in _file_locks:
            _file_locks[key] = threading.Lock()
        return _file_locks[key]

def safe_read_json(path: Path) -> Any:
    """线程安全读取 JSON（加锁）。"""
    with _get_file_lock(path):
        return read_json(path)

def safe_write_json(path: Path, data: Any) -> None:
    """线程安全写入 JSON（加锁）。"""
    with _get_file_lock(path):
        write_json(path, data)
```

### 改动

所有对 `待审批.json` 的读写操作，从 `read_json(PENDING_FILE)` / `write_json(PENDING_FILE, data)` 统一换为 `safe_read_json(PENDING_FILE)` / `safe_write_json(PENDING_FILE, data)`。

涉及位置：

| 文件 | 函数 | 改动点 |
|------|------|--------|
| `watchdog.py` | `process_file()` | `read_json` → `safe_read_json`, `write_json` → `safe_write_json` |
| `server.py` | `_read_pending()`, `_write_pending()` | 同上 |
| `approval_sync.py` | `sync_approvals()` | 同上 |
| `producer.py` | `run_production()` | 同上 |

对 `分类日志.json` 和 `审批日志.json` 的读取不加锁（只有单一模块写入），但为保持一致性也换用 `safe_read_json`。

---

## 三、修复 2：分类引擎错误传播

### 根因

`classifier.py` 的两层函数错误被中间层静默消化：

```
_call_deepseek()
  ├── 请求失败 → 捕获异常 → 返回 {segments:[], error:"..."}
  └── JSON 解析失败 → 捕获异常 → 返回 {segments:[], error:"..."}

classify_text()
  ├── 调用 _call_deepseek()
  └── result.get("segments", [])  ← 丢弃 error 字段！
```

结果：API 挂了 → `process_file()` 看到空列表 → 打印"无分类结果，跳过" → 用户毫不知情。

### 方案：结构化返回值

```python
classify_result = {
    "ok": bool,            # True=成功, False=失败
    "segments": [...],     # ok=True 时有效
    "error": str | None,   # ok=False 时给出错误信息
    "error_type": str | None,  # "api" | "auth" | "parse" | None
}
```

`classify_text()` 内部逻辑：
- API 请求成功 + 返回有效 JSON → `{ok: True, segments: [...]}`
- API 返回 HTTP 401 → `{ok: False, error: "API Key 认证失败", error_type: "auth"}`
- API 超时/网络错误 → `{ok: False, error: "请求超时，请检查网络", error_type: "api"}`
- 返回非 JSON → `{ok: False, error: "API 返回格式异常", error_type: "parse"}`

调用方 `watchdog.py` 改动：
```python
result = classify_text(content)
if not result.get("ok"):
    print(f"  ❌ 分类失败: {result.get('error', '未知错误')}")
    return
segments = result.get("segments", [])
# ... 继续正常流程
```

### 优点

- 不改变 `segments` 格式，下游代码无需修改
- 错误信息可读，用户知道是 API 挂了还是 Key 过期了
- 为后续 UI 通知铺路（可在审批面板显示 API 状态）

---

## 四、修复 3：API 指数退避重试

### 根因

DeepSeek API、微信 API、Flomo MCP 三处调用都没有重试：

| 调用位置 | 无重试后果 |
|----------|-----------|
| `classifier._call_deepseek()` | 网络闪断 → 整条日输入不被处理 |
| `wechat_publisher._get_access_token()` | Token 刷新时网络波动 → 文章无法推送 |
| `flomo_sync._mcp_fetch_notes()` | MCP 连接闪断 → 整轮同步失败 |
| `dashboard_analyzer._call_api()` | 分析失败 → 复盘报告缺失 |

### 方案：通用重试工具

在 `engine/` 下新增 `retry_utils.py`：

```python
import random
import time
from functools import wraps

# 不重试的 HTTP 状态码
NO_RETRY_STATUSES = {400, 401, 403, 422}


def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
    retryable_exceptions=None,
):
    """带指数退避+抖动的重试包装器。

    规则：
    - 重试最多 max_retries 次
    - 等待时间：base_delay, 2*base_delay, 4*base_delay...（每次 ×2）
    - 每次加 0~20% 随机抖动
    - retryable_exceptions: 哪些异常可重试（默认 ConnectionError, TimeoutError）
    - HTTP 响应中有状态码的，4xx 不重试（401/403 直接失败）
    """
```

函数签名设计为同时支持 `@retry_with_backoff()` 装饰器和 `retry_with_backoff(func, ...)` 显式调用。

### 应用位置

| 模块 | 函数 | 参数 |
|------|------|------|
| `classifier.py` | `_call_deepseek()` | 3 次, 1s 起步, 只重试网络错误+429 |
| `wechat_publisher.py` | `_get_access_token()`, `push_draft()` | 3 次, 1s 起步 |
| `flomo_sync.py` | `_mcp_fetch_notes()` | 2 次, 2s 起步（MCP 超时已较长） |
| `dashboard_analyzer.py` | `_call_api()` | 3 次, 1s 起步 |

---

## 五、不受影响的部分

- **审批面板 HTML/CSS/JS** — 无改动
- **看板生成器** — `kanban_generator.py` 只读 `PENDING_FILE` 且无并发写场景
- **Feishu 同步模块** — 独立 API 调用，不涉及本地文件竞争
- **配置加载** — `config.py` 不做架构修改

---

## 六、自检清单

- [x] 每个修复描述清楚根因和方案
- [x] 无"TBD"/"TODO"占位
- [x] 前后端接口一致（返回值格式未变）
- [x] 不改变现有业务流程
- [x] 改动范围可控（9 个文件，每处改几行到几十行）
- [x] 降级策略：重试失败后仍回到现有行为（不加重试导致的新问题）
