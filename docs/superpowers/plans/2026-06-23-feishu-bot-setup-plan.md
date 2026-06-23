# 飞书机器人配置 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Claude 配置为飞书机器人，实现 Claude 与飞书之间的基础通信能力，为后续 Obsidian↔飞书文档交互铺路。

**Architecture:** 遵循现有 Flomo 集成模式——在 engine 中新增 `feishu_client.py`（基础 API 封装）和 `feishu_sync.py`（业务逻辑），在 `server.py` 中注册 HTTP API 端点，在 `main.py` 中挂载启动。飞书开放平台应用手动在飞书开发者后台创建。

**Tech Stack:** Python 3.10+, `requests`（飞书 API 调用），`.env` 存储凭证，`schedule`/`threading` 定时同步

## Global Constraints

- 所有飞书相关代码放在 `engine/` 目录下
- API 凭证存储在 `.env` 文件中，通过 `engine/config.py` 加载
- 遵循现有代码风格：类型注解、中文注释、`logger` 日志
- 飞书 API 使用 v2 版本（最新稳定版）

---

## 文件结构

```
engine/
├── feishu_client.py    # 新增：飞书 API 客户端（token 管理、基础API调用）
├── feishu_sync.py      # 新增：飞书文档同步业务逻辑
├── config.py           # 修改：添加飞书相关配置项
├── main.py             # 修改：可选挂载飞书同步
└── server.py           # 修改：添加飞书 API 端点

飞书任务/
└── 01-飞书机器人配置/
    ├── 配置笔记.md       # 已创建：记录配置过程
    ├── API接入记录.md    # 已创建：记录 API 调试
    └── 踩坑记录.md       # 已创建：记录问题
```

### Task 1: 飞书开放平台创建应用（手动步骤）

**这一步需要你在飞书开发者后台手动操作。**

**Files:**
- Modify: `飞书任务/01-飞书机器人配置/配置笔记.md`

**Interfaces:**
- Consumes: 飞书开放平台账号
- Produces: App ID, App Secret（手动记录到 `.env`）

- [ ] **Step 1: 打开飞书开放平台**

访问 https://open.feishu.cn ，用你的飞书账号登录。

- [ ] **Step 2: 创建企业自建应用**

点击「创建应用」→ 选择「企业自建应用」→ 填写：
- 应用名称：`Claude 文档助手`（或你喜欢的名字）
- 应用描述：`Claude 与飞书双向文档交互`
- 分类：随便选一个合适的

- [ ] **Step 3: 获取凭证**

创建成功后进入「凭证与基础信息」页面，记下：
- **App ID**（格式: `cli_xxxxxxxxxxxx`）
- **App Secret**（点击显示后复制）

- [ ] **Step 4: 配置权限**

进入「权限管理」页面，添加以下权限（按需，最小权限原则）：

| 权限 | 权限代码 | 用途 |
|------|----------|------|
| 获取文档内容 | `docx:document:readonly` | 读取飞书文档 |
| 编辑文档 | `docx:document` | 写入飞书文档 |
| 查看多维表格 | `bitable:app` | 读取多维表格 |
| 编辑多维表格 | `bitable:app:write` | 写入多维表格 |
| 获取文件 | `drive:drive:readonly` | 下载文件 |
| 上传文件 | `drive:drive` | 上传文件 |
| 机器人消息 | `im:message` | 发送机器人消息 |

- [ ] **Step 5: 配置应用能力**

进入「应用功能」→「机器人」，开启机器人能力。

- [ ] **Step 6: 发布应用**

进入「版本管理与发布」→ 创建版本 → 填写版本号（如 `1.0.0`）→ 提交发布 → 等待管理员审批
> 如果你是管理员，可以直接审批通过。

- [ ] **Step 7: 将 App ID 和 App Secret 写入 `.env`**

```bash
# 编辑 .env，追加：
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=your-app-secret
```

- [ ] **Step 8: 记录到配置笔记**

打开 `飞书任务/01-飞书机器人配置/配置笔记.md`，记录刚才创建的应用名称、App ID、已申请的权限列表。

---

### Task 2: 添加飞书配置到 engine/config.py

**Files:**
- Modify: `engine/config.py`

**Interfaces:**
- Produces: `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_SYNC_INTERVAL` 全局常量

- [ ] **Step 1: 在 config.py 文件末尾追加飞书配置项**

```python
# ── 飞书 API ─────────────────────────────────────
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_SYNC_INTERVAL = int(os.getenv("FEISHU_SYNC_INTERVAL", "1800"))  # 秒，默认30分钟
```

---

### Task 3: 创建飞书 API 客户端 engine/feishu_client.py

**Files:**
- Create: `engine/feishu_client.py`

**Interfaces:**
- Consumes: `engine.config.FEISHU_APP_ID`, `FEISHU_APP_SECRET`
- Produces: `FeishuClient` 类
  - `get_tenant_access_token() -> str`
  - `get_document(document_token: str) -> dict`
  - `list_bitable_records(app_token: str, table_id: str) -> list`
  - `create_bitable_record(app_token: str, table_id: str, fields: dict) -> dict`

- [ ] **Step 1: 创建 feishu_client.py**

```python
"""飞书 API 客户端 —— 基础认证与 API 调用封装。

用法:
    from engine.feishu_client import FeishuClient
    client = FeishuClient()
    token = client.get_tenant_access_token()
"""

import logging
import time
from typing import Optional

import requests

from engine.config import FEISHU_APP_ID, FEISHU_APP_SECRET

logger = logging.getLogger("feishu_client")

BASE_URL = "https://open.feishu.cn/open-apis"


class FeishuClient:
    """飞书 API 客户端（自动管理 tenant_access_token）。"""

    def __init__(self):
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    # ── Token 管理 ──

    def get_tenant_access_token(self) -> str:
        """获取（或刷新）tenant_access_token。

        返回:
            有效的 token 字符串。

        抛出:
            RuntimeError: 凭证未配置或认证失败
        """
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
            raise RuntimeError(
                "飞书凭证未配置。请先在 .env 中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET"
            )

        url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET,
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                raise RuntimeError(
                    f"飞书认证失败: {data.get('msg', '未知错误')} "
                    f"(code={data.get('code')})"
                )

            self._token = data["tenant_access_token"]
            self._token_expires_at = time.time() + data.get("expire", 7200)
            logger.info("飞书 tenant_access_token 已刷新")
            return self._token

        except requests.RequestException as e:
            raise RuntimeError(f"飞书认证请求失败: {e}")

    # ── 通用请求封装 ──

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """带 token 自动刷新的 API 请求。"""
        token = self.get_tenant_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json; charset=utf-8"

        url = f"{BASE_URL}{path}"
        try:
            resp = requests.request(method, url, headers=headers, timeout=kwargs.pop("timeout", 30), **kwargs)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                raise RuntimeError(
                    f"飞书 API 错误 [{path}]: {data.get('msg', '未知错误')} "
                    f"(code={data.get('code')})"
                )

            return data

        except requests.RequestException as e:
            raise RuntimeError(f"飞书 API 请求失败 [{path}]: {e}")

    def _get(self, path: str, **kwargs) -> dict:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs) -> dict:
        return self._request("POST", path, **kwargs)

    # ── 文档 API（docx） ──

    def get_document(self, document_token: str) -> dict:
        """获取飞书文档内容。

        参数:
            document_token: 文档 token（从 URL 中获取）

        返回:
            文档数据字典
        """
        path = f"/docx/v1/documents/{document_token}/raw_content"
        return self._get(path)

    # ── 多维表格 API（bitable） ──

    def list_bitable_records(self, app_token: str, table_id: str, page_size: int = 500) -> list:
        """列出多维表格的所有记录。

        参数:
            app_token: 多维表格 app token
            table_id: 数据表 ID
            page_size: 每页数量（最大 500）

        返回:
            记录列表
        """
        records = []
        page_token = None

        while True:
            path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            data = self._get(path, params=params)
            items = data.get("data", {}).get("items", [])
            records.extend(items)

            if not data.get("data", {}).get("has_more"):
                break
            page_token = data.get("data", {}).get("page_token")

        return records

    def create_bitable_record(self, app_token: str, table_id: str, fields: dict) -> dict:
        """在多维表格中创建一条记录。

        参数:
            app_token: 多维表格 app token
            table_id: 数据表 ID
            fields: 字段键值对

        返回:
            创建的记录数据
        """
        path = f"/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        payload = {"fields": fields}
        data = self._post(path, json=payload)
        return data.get("data", {}).get("record", {})

    # ── 云空间 API（drive） ──

    def upload_file(self, file_path: str, parent_node: str, parent_type: str = "explorer") -> dict:
        """上传文件到飞书云空间。

        参数:
            file_path: 本地文件路径
            parent_node: 父节点 token（文件夹）
            parent_type: 父节点类型（explorer / docx / bitable）

        返回:
            上传结果
        """
        import os as _os
        from pathlib import Path as _Path

        path = _Path(file_path)
        file_name = path.name
        file_size = path.stat().st_size

        upload_path = "/drive/v1/files/upload_all"
        payload = {
            "file_name": file_name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": file_size,
        }

        # 飞书上传需要 multipart/form-data
        token = self.get_tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f)}
                resp = requests.post(
                    f"{BASE_URL}{upload_path}",
                    headers=headers,
                    data=payload,
                    files=files,
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != 0:
                    raise RuntimeError(
                        f"上传失败: {data.get('msg', '未知错误')}"
                    )
                return data
        except requests.RequestException as e:
            raise RuntimeError(f"飞书上传请求失败: {e}")
```

- [ ] **Step 2: 验证代码语法**

```bash
cd /d "C:\Users\Administrator\Documents\trae_projects\first cc"
python -c "import ast; ast.parse(open('engine/feishu_client.py', encoding='utf-8').read()); print('✅ 语法正确')"
```

- [ ] **Step 3: 提交**

```bash
git add engine/feishu_client.py
git commit -m "feat: add Feishu API client module"
```

---

### Task 4: 创建飞书同步模块 engine/feishu_sync.py

**Files:**
- Create: `engine/feishu_sync.py`

**Interfaces:**
- Consumes: `FeishuClient`, `engine.config.FEISHU_SYNC_INTERVAL`
- Produces: `FeishuSync` 类（与 FlomoSync 平行）
  - `sync_once() -> int`
  - `start_scheduler()`
  - `stop_scheduler()`
  - `get_status() -> dict`

- [ ] **Step 1: 创建 feishu_sync.py**

```python
"""飞书同步模块 —— 管理飞书文档的同步任务。

与 FlomoSync 平行的结构，提供定时同步、状态查询等功能。
"""

import logging
import threading
import time
from typing import Optional

from engine.config import FEISHU_SYNC_INTERVAL
from engine.feishu_client import FeishuClient

logger = logging.getLogger("feishu_sync")


class FeishuSync:
    """飞书同步管理器。"""

    def __init__(self, interval: int = FEISHU_SYNC_INTERVAL):
        self.interval = interval
        self._client = FeishuClient()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_sync_time: Optional[str] = None
        self.last_error: Optional[str] = None
        self.sync_count: int = 0
        self._token_ok: Optional[bool] = None

    # ── 连接检查 ──

    def check_connection(self) -> bool:
        """检查飞书 API 连接是否正常。"""
        try:
            self._client.get_tenant_access_token()
            self._token_ok = True
            return True
        except RuntimeError as e:
            self._token_ok = False
            self.last_error = str(e)
            logger.error("飞书连接检查失败: %s", e)
            return False

    # ── 同步（预留，后续阶段扩展） ──

    def sync_once(self) -> int:
        """执行一次同步（预留实现，当前只验证连接）。

        返回:
            同步的文档数量（当前返回 0）

        抛出:
            RuntimeError: 连接失败
        """
        if not self._token_ok:
            ok = self.check_connection()
            if not ok:
                raise RuntimeError(self.last_error or "飞书连接未就绪")

        logger.info("飞书连接正常，同步就绪")
        self.last_sync_time = time.strftime("%Y-%m-%d %H:%M:%S")
        return 0

    # ── 定时调度 ──

    def start_scheduler(self):
        """在后台线程启动定时检查。"""
        if self._running:
            return

        if not self.check_connection():
            logger.warning("飞书连接失败，调度器暂不启动")
            self.last_error = "飞书连接失败"
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="feishu-sync"
        )
        self._thread.start()
        logger.info("飞书同步调度已启动，间隔 %d 秒", self.interval)

    def stop_scheduler(self):
        self._running = False

    def _run_loop(self):
        self.sync_once()
        while self._running:
            time.sleep(self.interval)
            if self._running:
                self.sync_once()

    # ── 状态查询 ──

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "connected": bool(self._token_ok),
            "interval": self.interval,
            "last_sync_time": self.last_sync_time,
            "last_error": self.last_error,
        }
```

- [ ] **Step 2: 验证语法**

```bash
cd /d "C:\Users\Administrator\Documents\trae_projects\first cc"
python -c "import ast; ast.parse(open('engine/feishu_sync.py', encoding='utf-8').read()); print('✅ 语法正确')"
```

- [ ] **Step 3: 提交**

```bash
git add engine/feishu_sync.py
git commit -m "feat: add Feishu sync module"
```

---

### Task 5: 集成到服务器（server.py + main.py）

**Files:**
- Modify: `engine/server.py`
- Modify: `engine/main.py`

**Interfaces:**
- Consumes: `FeishuSync`
- Produces: HTTP API `/api/feishu/status`，`/api/feishu/sync`

- [ ] **Step 1: 在 server.py 中集成飞书同步**

找到 `from engine.flomo_sync import FlomoSync` 这一行，在其下方添加：
```python
from engine.feishu_sync import FeishuSync
```

找到 `# -- 初始化 Flomo 同步 --` 区块，在其下方添加飞书初始化代码：
```python
    # -- 初始化飞书同步 --
    feishu_sync = FeishuSync()
    if feishu_sync.check_connection():
        feishu_sync.start_scheduler()
    server.feishu_sync = feishu_sync
```

在 `do_GET` 方法中，在 `/api/flomo/status` 处理之后添加：
```python
        elif path == "/api/feishu/status":
            if hasattr(self.server, "feishu_sync") and self.server.feishu_sync:
                self._send_json(self.server.feishu_sync.get_status())
            else:
                self._send_json({"running": False, "error": "Feishu sync not initialized"})
```

在 `do_POST` 方法中，在 `/api/flomo/sync` 处理之后添加：
```python
        elif parsed.path == "/api/feishu/sync":
            try:
                if hasattr(self.server, "feishu_sync") and self.server.feishu_sync:
                    count = self.server.feishu_sync.sync_once()
                    self._send_json({"ok": True, "synced": count})
                else:
                    self._send_json({"ok": False, "error": "Feishu sync not initialized"}, 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
```

- [ ] **Step 2: 验证代码**

```bash
cd /d "C:\Users\Administrator\Documents\trae_projects\first cc"
python -c "import ast; ast.parse(open('engine/server.py', encoding='utf-8').read()); print('✅ server.py 语法正确')"
```

- [ ] **Step 3: 提交**

```bash
git add engine/server.py
git commit -m "feat: integrate Feishu sync into server"
```

---

### Task 6: 测试飞书连接

**Files:**
- Modify: `飞书任务/01-飞书机器人配置/API接入记录.md`

**Interfaces:**
- Consumes: `.env` 中的 `FEISHU_APP_ID`, `FEISHU_APP_SECRET`

- [ ] **Step 1: 确认 .env 已配置**

检查 `.env` 中存在：
```
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=your-actual-secret
```

- [ ] **Step 2: 运行连接测试**

```bash
cd /d "C:\Users\Administrator\Documents\trae_projects\first cc"
python -c "
from engine.feishu_client import FeishuClient
client = FeishuClient()
token = client.get_tenant_access_token()
print(f'✅ 飞书连接成功，token={token[:20]}...')
"
```

预期输出：
```
✅ 飞书连接成功，token=xxxxxxxxxxxxxxxxxxxx...
```

- [ ] **Step 3: 访问 API 状态端点**

启动引擎后访问：http://127.0.0.1:8765/api/feishu/status

预期返回：
```json
{"running": true, "connected": true, "interval": 1800, "last_sync_time": "...", "last_error": null}
```

- [ ] **Step 4: 记录到 API 接入记录**

打开 `飞书任务/01-飞书机器人配置/API接入记录.md`，记录：
- App ID
- 测试结果（成功/失败）
- 获取到的接口列表

- [ ] **Step 5: 提交最终变更**

```bash
git add .
git commit -m "feat: complete Feishu bot setup and connection test"
```

---

## 自检清单

完成后回顾：

1. ✅ `.env` 已配置 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`
2. ✅ `engine/feishu_client.py` 能获取 token
3. ✅ `engine/feishu_sync.py` 能启动调度器
4. ✅ API 端点 `/api/feishu/status` 返回正确状态
5. ✅ 飞书开放平台应用已发布，机器人能力已开启
6. ✅ 配置笔记已填写关键的 App ID 和权限信息
