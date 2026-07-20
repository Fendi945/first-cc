# 元演系统 · Batch B 架构加固 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 加固服务端架构 — ThreadingHTTPServer 并发处理 + 统一日志系统 + 优雅关闭

**Architecture:** 三项独立加固：
1. 替换 `http.server.HTTPServer` 为 `ThreadingHTTPServer`（Python 3.7+ 内置），单行导入变更
2. 新增 `engine/log_utils.py` 提供统一日志配置，逐步替换 `print()` → `logger.*()` 调用
3. 在 `server.py` 注册 SIGINT/SIGTERM 信号处理，按序停止所有 scheduler 后关闭 server

**Tech Stack:** Python 3.7+, `socketserver.ThreadingMixIn`, `logging`, `signal`

**设计约束：** 不改动审批面板任何前端逻辑和数据统计 API 路由。所有改造仅为后端架构加固。

---

## File Structure

```
engine/
├── log_utils.py          # [NEW] 统一日志配置工具
├── server.py             # [MODIFY] HTTPServer → ThreadingHTTPServer + 优雅关闭 + 日志
├── watchdog.py           # [MODIFY] print → logger (ConsoleHandler 保留, 只改 API)
├── approval_sync.py      # [MODIFY] print → logger
├── producer.py           # [MODIFY] print → logger
├── classifier.py         # [NOT TOUCHED] 无 print 语句
```

**Task 1:** `server.py` — ThreadingHTTPServer 替换（1 行 import 变更）
**Task 2:** `engine/log_utils.py` — 统一日志工具创建 + `server.py` 日志改造
**Task 3:** `watchdog.py` — print 替换为 logger
**Task 4:** `producer.py` + `approval_sync.py` — print 替换为 logger
**Task 5:** `server.py` — 优雅关闭（信号处理 + scheduler shutdown）

---

### Task 1: ThreadingHTTPServer

**Files:**
- Modify: `engine/server.py:339`

**Interfaces:**
- Produces: `server` 对象从 `HTTPServer` 实例变为 `ThreadingHTTPServer` 实例，APIHandler 无变化

- [ ] **Step 1: 修改 import 和 server 创建**

将 server.py 第 13 行附近：
```python
import http.server
```
改为：
```python
import http.server
from socketserver import ThreadingMixIn


class ThreadingHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    """支持并发请求的 HTTP Server（每个请求独立线程）。"""
    daemon_threads = True
```

将第 339 行：
```python
    server = http.server.HTTPServer((HOST, port), APIHandler)
```
改为：
```python
    server = ThreadingHTTPServer((HOST, port), APIHandler)
```

- [ ] **Step 2: 验证 server 启动和 API 响应**

Run:
```bash
cd "C:\Users\Administrator\Documents\trae_projects\first cc" && timeout 5 python -c "
from engine.server import start_server
import threading
t = threading.Thread(target=lambda: start_server(no_browser=True), daemon=True)
t.start()
import time; time.sleep(2)

import urllib.request
resp = urllib.request.urlopen('http://127.0.0.1:8765/api/health')
import json
data = json.loads(resp.read())
assert data['ok'] == True
print('✅ ThreadingHTTPServer 启动正常')
print('✅ API /api/health 响应正常')
"
```

Expected: 服务启动成功，health API 返回 `{"ok": true}`

- [ ] **Step 3: Commit**

```bash
git add engine/server.py
git commit -m "fix: ThreadingHTTPServer — 支持并发请求，长API不阻塞其他调用"
```

---

### Task 2: 统一日志工具 + server.py 日志改造

**Files:**
- Create: `engine/log_utils.py`
- Modify: `engine/server.py`

**Interfaces:**
- Produces:
  - `log_utils.setup_logging(level=logging.INFO, log_file=None)` — 全局调用一次，配置根 logger
  - `log_utils.get_logger(name: str)` — 获取带 `[name]` 前缀的 logger
- Consumes: 无（独立工具，不依赖其他任务）

- [ ] **Step 1: 创建 engine/log_utils.py**

```python
"""统一日志配置工具 —— 提供一致的日志格式和级别管理。

用法:
    from engine.log_utils import setup_logging, get_logger

    setup_logging()              # 在程序入口调用一次
    logger = get_logger("server")
    logger.info("服务已启动")
"""

import logging
import sys
from typing import Optional


# 日志格式：时间 [级别] [模块名] 消息
CONSOLE_FORMAT = "%(asctime)s [%(levelname)-5s] [%(name)s] %(message)s"
DATE_FORMAT = "%H:%M:%S"

# 日志级别映射（环境变量友好）
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

_root_configured = False


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> None:
    """配置根 logger 的格式和级别（全局调用一次即可）。

    Args:
        level: 日志级别，默认 logging.INFO
        log_file: 可选日志文件路径，指定后同时写入文件
    """
    global _root_configured
    if _root_configured:
        return
    _root_configured = True

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有 handler，防止重复
    root_logger.handlers.clear()

    # 控制台 handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(CONSOLE_FORMAT, datefmt=DATE_FORMAT))
    root_logger.addHandler(console)

    # 可选的日志文件 handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)-5s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """获取带模块名的 logger。

    在模块级别调用:
        logger = get_logger("module_name")
    """
    return logging.getLogger(name)


__all__ = ["setup_logging", "get_logger"]
```

- [ ] **Step 2: 在 server.py 应用日志**

修改 server.py 文件顶部，添加导入：

```python
from engine.log_utils import setup_logging, get_logger
```

在 `start_server()` 函数开头，添加日志初始化（在 os.chdir 之后、KANBAN_DIR 创建之前）：

```python
def start_server(port=DEFAULT_PORT, no_browser=False):
    """启动 HTTP 服务器。"""
    # 切换到项目根目录，使 /dashboard/ 能正确映射
    os.chdir(str(PROJECT_ROOT))

    # 统一日志初始化（全局只需调用一次）
    setup_logging()
```

在文件顶部添加 logger（模块级，所有函数共用）：

在 `from engine.log_utils import setup_logging, get_logger` 之后添加：
```python
logger = get_logger("server")
```

注意：`server.py` 里的 `print()` 要替换为 `logger.*()` 调用。但启动横幅（`=====` 框）保留 `print()` — 那是终端用户体验，不是日志。

找到如下 print 位置并替换：

1. `_read_pending()` 中的 `print(f"  [server] ⚠️ 读取待审批.json 失败: {e}")` → `logger.warning("读取待审批.json 失败: %s", e)`
2. `_write_pending()` 中的 `print(f"  [server] ❌ 写入待审批.json 失败: {e}")` → `logger.error("写入待审批.json 失败: %s", e)`
3. `_append_audit_log()` 中的 `print(f"  [server] ⚠️ 写入审批日志失败: {e}")` → `logger.warning("写入审批日志失败: %s", e)`
4. `APIHandler.log_message()` 保持原样 — 它是 HTTP 访问日志，使用 `print()` 合理
5. `start_server()` 中的 banner `print()` 保持原样 — 终端用户体验
6. `start_server()` 中看板同步初始化的 `print(f"  [server] ⚠️ 看板同步初始化失败: {e}")` → `logger.warning("看板同步初始化失败: %s", e)`
7. `start_server()` 中的 `print("\n  [server] 👋 服务器已关闭")` → `logger.info("服务器已关闭")`

- [ ] **Step 3: 验证 server 模块加载**

Run:
```bash
cd "C:\Users\Administrator\Documents\trae_projects\first cc" && timeout 5 python -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from engine.log_utils import setup_logging, get_logger
setup_logging()
logger = get_logger('test')
logger.info('日志系统正常')
print('✅ log_utils 创建成功')

from engine.server import APIHandler, start_server, _read_pending, _write_pending
print('✅ server.py 日志改造加载正常')
"
```

Expected: 两行输出，无 ImportError

- [ ] **Step 4: Commit**

```bash
git add engine/log_utils.py engine/server.py
git commit -m "feat: 统一日志系统 — log_utils.py + server.py 日志改造"
```

---

### Task 3: watchdog.py 日志替换

**Files:**
- Modify: `engine/watchdog.py`

**Interfaces:**
- Consumes: `engine.log_utils.get_logger`
- Produces: 所有 `print(...)` 替换为 `logger.info/warning/error(...)`

- [ ] **Step 1: 添加 logger 并替换 print**

在 `watchdog.py` 文件顶部，在 `from engine.config import ...` 之后添加：

```python
from engine.log_utils import get_logger

logger = get_logger("watchdog")
```

逐一替换以下 print 语句（不要漏掉任何一处）：

1. `print(f"  ⏭️  跳过 _done 文件（防重复）: {file_path.name}")` → `logger.info("跳过 _done 文件（防重复）: %s", file_path.name)`
2. `print(f"  📄 处理: {file_path.name}")` → `logger.info("处理: %s", file_path.name)`
3. `print(f"  ⏭️  跳过空文件: {file_path.name}")` → `logger.info("跳过空文件: %s", file_path.name)`
4. `print(f"  🤖 AI 分类中...")` → `logger.info("AI 分类中...")`
5. `print(f"  ❌ 分类失败（异常）: {e}")` → `logger.error("分类失败（异常）: %s", e)`
6. 

```python
    error_tag = {"auth": "🔑", "api": "🌐", "parse": "📄", "empty": "📭"}.get(error_type, "❌")
    print(f"  {error_tag} 分类失败 [{error_type}]: {error}")
```
→ `logger.error("分类失败 [%s]: %s", error_type, error)`

7. `print(f"  ✅ 完成: {len(pending_items)} 条内容")` → `logger.info("完成: %d 条内容", len(pending_items))`
8. `print(f"     📹 视频 x{video_count}")` → `logger.info("  视频 x%d", video_count)`（保留缩进）
9. `print(f"     📝 文章 x{article_count}")` → `logger.info("  文章 x%d", article_count)`
10. `print(f"     🔧 工具 x{tool_count}")` → `logger.info("  工具 x%d", tool_count)`
11. `print(f"     🗂️  看板已更新")` → `logger.info("看板已更新")`
12. `print(f"     ⚠️  看板更新失败: {e}")` → `logger.warning("看板更新失败: %s", e)`
13. `print("  📭 没有待处理的日输入文件")` → `logger.info("没有待处理的日输入文件")`
14. `print(f"  📂 发现 {len(inputs)} 个待处理文件")` → `logger.info("发现 %d 个待处理文件", len(inputs))`

15. 看板变更部分：
```python
print(f"  📋 看板已更新，检查审批...")
```
→ `logger.info("看板已更新，检查审批...")`

```python
count = sync_approvals()
if count:
    print(f"  ✅ 自动审批完成，{count} 项已处理")
else:
    print(f"     （未发现新勾选项）")
```
→
```python
count = sync_approvals()
if count:
    logger.info("自动审批完成，%d 项已处理", count)
else:
    logger.info("未发现新勾选项")
```

16. `print(f"  ⚠️  审批同步失败: {e}")` → `logger.warning("审批同步失败: %s", e)`

17. start_watchdog 部分：
```python
print(f"⚠️  日输入目录不存在，创建: {DAILY_INPUT_DIR}")
```
→ `logger.warning("日输入目录不存在，创建: %s", DAILY_INPUT_DIR)`

```python
print(f"👁️  Watchdog 已启动（防抖 {FILE_COOLDOWN_SECONDS}s）")
print(f"   监控:")
print(f"     🌱 日输入 → {DAILY_INPUT_DIR}")
print(f"     📋 看板   → {KANBAN_DIR / '看板.md'}")
print(f"   等待新文件或审批... (Ctrl+C 停止)\n")
```
→
```python
logger.info("Watchdog 已启动（防抖 %ds）", FILE_COOLDOWN_SECONDS)
logger.info("  监控:")
logger.info("    日输入 → %s", DAILY_INPUT_DIR)
logger.info("    看板   → %s", KANBAN_DIR / "看板.md")
logger.info("  等待新文件或审批... (Ctrl+C 停止)")
```

18. `_write_classify_log()` 中的 `print(f"  [watchdog] ⚠️ 写入分类日志失败: {e}")` → `logger.warning("写入分类日志失败: %s", e)`
19. `_ensure_vault_dirs()` 中的 `print(f"  [watchdog] ⚠️ 无法创建看板目录: {KANBAN_DIR}")` → `logger.warning("无法创建看板目录: %s", KANBAN_DIR)`
20. `_ensure_vault_dirs()` 中的 `print(f"  [watchdog] ⚠️ 无法创建日输入目录: {DAILY_INPUT_DIR}")` → `logger.warning("无法创建日输入目录: %s", DAILY_INPUT_DIR)`

- [ ] **Step 2: 验证 watchdog 模块加载**

Run:
```bash
cd "C:\Users\Administrator\Documents\trae_projects\first cc" && timeout 5 python -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from engine.log_utils import setup_logging
setup_logging()

from engine.watchdog import (
    process_file, start_watchdog, scan_existing,
    _has_duplicate, _is_cooldown, _write_classify_log,
)
print('✅ watchdog 日志改造加载正常')
"
```

Expected: 无 ImportError，输出 "✅ watchdog 日志改造加载正常"

- [ ] **Step 3: Commit**

```bash
git add engine/watchdog.py
git commit -m "refactor: watchdog.py 日志替换 — print → logger"
```

---

### Task 4: producer.py + approval_sync.py 日志替换

**Files:**
- Modify: `engine/producer.py`
- Modify: `engine/approval_sync.py`

**Interfaces:**
- Consumes: `engine.log_utils.get_logger`

- [ ] **Step 1: producer.py 日志替换**

在 `producer.py` 文件顶部 `from engine.config import ...` 之后添加：

```python
from engine.log_utils import get_logger

logger = get_logger("producer")
```

替换所有 print 语句：

1. `print("  [producer] ⚠️ 待审批数据格式错误")` → `logger.warning("待审批数据格式错误")`
2. `print(f"  [producer] 🏭 生产: {summary} ({tag})")` → `logger.info("生产: %s (%s)", summary, tag)`
3. `print(f"    -> 产出: {result.name}")` → `logger.info("产出: %s", result.name)`
4. `print(f"  [producer] ✅ {produced} 项已生产")` → `logger.info("%d 项已生产", produced)`
5. `print("  [producer] 📭 无待生产的项")` → `logger.info("无待生产的项")`
6. `print(f"    ⚠️ 公众号推送失败: {e}")` → `logger.warning("公众号推送失败: %s", e)`
7. `print(f"    📤 已推送至公众号草稿箱")` → `logger.info("已推送至公众号草稿箱")`
8. `print(f"    ⚠️ wechat_publisher 模块未就绪")` → `logger.warning("wechat_publisher 模块未就绪")`
9. `print(f"    ⚠️ 公众号推送异常: {e}")` → `logger.warning("公众号推送异常: %s", e)`
10. `print(f"    ❌ 写入失败: {e}")` → `logger.error("写入失败: %s", e)`

- [ ] **Step 2: approval_sync.py 日志替换**

在 `approval_sync.py` 文件顶部 `from engine.config import ...` 之后添加：

```python
from engine.log_utils import get_logger

logger = get_logger("approval_sync")
```

替换所有 print 语句：

1. `print("  [sync] ⚠️ 看板文件不存在")` → `logger.warning("看板文件不存在")`
2. `print("  [sync] 📭 看板中未发现状态变更")` → `logger.info("看板中未发现状态变更")`
3. `print("  [sync] ❌ 待审批数据格式错误")` → `logger.error("待审批数据格式错误")`
4. 
```python
print(f"  [sync] {symbol} {summary}")
if tag_override:
    print(f"        标签改为: {tag_override}")
```
→
```python
logger.info("%s %s", symbol, summary)
if tag_override:
    logger.info("  标签改为: %s", tag_override)
```

5. `print(f"  [sync] ✅ {count} 项已同步")` → `logger.info("%d 项已同步", count)`
6. `print(f"  [sync] ⚠️ 日志写入失败: {e}")` → `logger.warning("日志写入失败: %s", e)`
7. `print(f"  [sync] ⚠️ 生产执行失败: {e}")` → `logger.warning("生产执行失败: %s", e)`
8. `print("  [sync] 📭 勾选的项已处理过或无变更")` → `logger.info("勾选的项已处理过或无变更")`

- [ ] **Step 3: 验证两个模块加载**

Run:
```bash
cd "C:\Users\Administrator\Documents\trae_projects\first cc" && timeout 5 python -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from engine.log_utils import setup_logging
setup_logging()

from engine.producer import run_production, _produce
print('✅ producer 日志加载正常')

from engine.approval_sync import sync_approvals, parse_kanban_actions
print('✅ approval_sync 日志加载正常')
"
```

Expected: 两行输出，无 ImportError

- [ ] **Step 4: Commit**

```bash
git add engine/producer.py engine/approval_sync.py
git commit -m "refactor: producer + approval_sync 日志替换 — print → logger"
```

---

### Task 5: 优雅关闭（信号处理 + Scheduler Shutdown）

**Files:**
- Modify: `engine/server.py`

**Interfaces:**
- Consumes: `server.flomo_sync`, `server.feishu_sync`, `server.dashboard_analyzer` 的 `stop_scheduler()` 方法

- [ ] **Step 1: 添加信号处理和 shutdown 函数**

在 `server.py` 文件顶部 import 区域添加：

```python
import signal
```

在 `start_server()` 函数 `server.serve_forever()` 调用之前（即 start_server 函数的末尾部分），注入 shutdown 逻辑。

具体修改如下（约第 406 行，当前的 `try: server.serve_forever()` 块）：

原代码：
```python
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  [server] 👋 服务器已关闭")
        server.server_close()
```

改为：
```python
    # ── 优雅关闭 ──
    shutdown_requested = False

    def _shutdown(signum=None, frame=None):
        """按序停止所有服务并关闭 server。"""
        nonlocal shutdown_requested
        if shutdown_requested:
            return
        shutdown_requested = True
        logger.info("正在关闭所有服务...")

        # 1. 停止 scheduler 线程（不再接收新任务）
        for name, sync_obj in [
            ("Flomo", getattr(server, "flomo_sync", None)),
            ("Feishu", getattr(server, "feishu_sync", None)),
            ("Dashboard", getattr(server, "dashboard_analyzer", None)),
        ]:
            if sync_obj and hasattr(sync_obj, "stop_scheduler"):
                sync_obj.stop_scheduler()
                logger.info("  %s 调度已停止", name)

        # 2. 关闭 HTTP 服务器（不再接受新连接）
        server.server_close()

        # 3. 等待线程自然退出
        import threading
        for t in threading.enumerate():
            if t is not threading.main_thread() and t.daemon is False:
                t.join(timeout=2.0)

        logger.info("服务器已关闭")

    # 注册信号处理器（SIGTERM 用于系统关闭，SIGINT 用于 Ctrl+C）
    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    logger.info("服务已就绪，按 Ctrl+C 停止")

    try:
        server.serve_forever()
    finally:
        _shutdown()
```

注意：`_shutdown` 函数需要放在 `start_server()` 函数体内部（在 `serve_forever()` 之前），作为闭包访问 `server` 和 `logger` 变量。

- [ ] **Step 2: 验证模块加载**

Run:
```bash
cd "C:\Users\Administrator\Documents\trae_projects\first cc" && timeout 8 python -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from engine.log_utils import setup_logging
setup_logging()

# 验证 server 模块包含新的 shutdown 逻辑
import signal
print(f'✅ signal 模块可用: SIGINT={signal.SIGINT}')

from engine.server import start_server, APIHandler, _read_pending, _write_pending
print('✅ server 优雅关闭加载正常')

# 快速启动验证
import threading, time, urllib.request

def run_server():
    start_server(no_browser=True)

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(2)

resp = urllib.request.urlopen('http://127.0.0.1:8765/api/health')
import json
data = json.loads(resp.read())
assert data['ok'] == True
print('✅ 启动正常，health API 正常')
print('🎉 全部 Batch B 任务完成 + 验证通过')
"
```

Expected: 所有模块加载正常，Health API 响应正常

- [ ] **Step 3: Commit**

```bash
git add engine/server.py
git commit -m "feat: 优雅关闭 — 信号处理 + 按序停止 scheduler + server_close"
```

---

## 自检清单

**Spec 覆盖检查：**
1. ✅ ThreadingHTTPServer — Task 1（单行 import 变更）
2. ✅ 统一日志系统 — Task 2（log_utils.py）+ Task 3/4（watchdog/producer/approval_sync 替换）
3. ✅ 优雅关闭 — Task 5（信号处理 + scheduler shutdown 顺序）

**约束检查：**
- ✅ 不修改审批面板前端逻辑（HTML/CSS/JS 无改动）
- ✅ 不修改数据统计 API 路由（API 路径和处理逻辑无改动）
- ✅ 不改动 classifier.py（无 print 语句，不需日志替换）

**占位符检查：** 无 TBD/TODO/占位代码。

**类型一致性：**
- `setup_logging()` 和 `get_logger()` 接口跨 Task 2/3/4 一致
- `stop_scheduler()` 方法签名在所有 scheduler 类中一致
- `ThreadingHTTPServer` 与 `HTTPServer` 接口完全兼容，APIHandler 无变化
