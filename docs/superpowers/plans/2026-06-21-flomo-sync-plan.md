# Flomo 笔记同步到反哺弧 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Flomo Pro 笔记定时同步到 Obsidian 捕获目录，用户确认后移入日输入走反哺弧流水线

**Architecture:** Python 引擎侧 `flomo_sync.py` 定时轮询 Flomo API，将新笔记写入 `🌱 原料库/捕获/` 目录；Obsidian 插件检测到新文件后弹出确认对话框，用户点击「移入日输入」后文件移到 `🌱 原料库/日输入/`，触发已有 AI 分类 → 看板审批 → 成品产出流程。

**Tech Stack:** Python 3.11 (engine), TypeScript/Obsidian API (plugin), Flomo Pro API

## Global Constraints

- Python 引擎使用 `http.server` 标准库，不引入新依赖
- Obsidian 插件使用已有 API（`Vault`, `TFile`, `Notice`, `Modal`, `normalizePath`）
- Flomo API 认证使用 Bearer Token（`FLOMO_API_KEY`）
- 同步状态持久化到 `flomo_state.json`，引擎不依赖数据库
- 文件和目录路径必须通过 `normalizePath()` 规范化
- 配置项从 `.env` 文件读取（引擎侧）和 Obsidian 插件设置页（插件侧）

---

### Task 1: 引擎配置 — 添加 Flomo 路径和配置

**Files:**
- Modify: `engine/config.py:10-38`
- Modify: `C:/Users/Administrator/Documents/trae_projects/first cc/.env`

**Interfaces:**
- Consumes: `.env` 文件中的 `FLOMO_API_KEY`
- Produces: `config.CAPTURE_DIR`, `config.FLOMO_API_KEY`, `config.FLOMO_SYNC_INTERVAL` 全局常量

- [ ] **Step 1: 在 config.py 中添加 Flomo 配置**

在 `engine/config.py` 中 `VAULT_PATH` 的目录常量区域添加捕获目录，同时在 API 配置区添加 Flomo 配置：

```python
# ── vault 路径 ─────────────────────────────────────
# 在 DAILY_INPUT_DIR 下面添加：
CAPTURE_DIR = VAULT_PATH / "🌱 原料库" / "捕获"
```

在文件末尾 `DEEPSEEK MODEL` 块之后添加：

```python
# ── Flomo API ──────────────────────────────────────
FLOMO_API_KEY = os.getenv("FLOMO_API_KEY", "")
FLOMO_SYNC_INTERVAL = int(os.getenv("FLOMO_SYNC_INTERVAL", "1800"))  # 秒，默认30分钟
```

- [ ] **Step 2: 在 .env 中添加 Flomo API Key**

```bash
# Flomo Pro API
FLOMO_API_KEY=your-flomo-api-key-here
FLOMO_SYNC_INTERVAL=1800
```

- [ ] **Step 3: 验证**

运行 `python -c "from engine.config import CAPTURE_DIR, FLOMO_API_KEY; print(CAPTURE_DIR, FLOMO_API_KEY[:8] if FLOMO_API_KEY else 'EMPTY')"` 确认导入无报错

- [ ] **Step 4: Commit**

```bash
git add engine/config.py .env
git commit -m "feat(engine): add Flomo API config and capture directory path"
```

---

### Task 2: Flomo 同步模块 — 创建 flomo_sync.py

**Files:**
- Create: `engine/flomo_sync.py`

**Interfaces:**
- Consumes: `config.CAPTURE_DIR`, `config.FLOMO_API_KEY`, `config.FLOMO_SYNC_INTERVAL`
- Produces: `FlomoSync` 类（`sync_once()`、`start_scheduler()`、`get_status()` 方法）

- [ ] **Step 1: 创建 flomo_sync.py**

```python
"""Flomo 笔记同步模块 — 定时轮询 Flomo Pro API，写入捕获目录。"""

import json
import logging
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from engine.config import CAPTURE_DIR, FLOMO_API_KEY, FLOMO_SYNC_INTERVAL, PROJECT_ROOT

logger = logging.getLogger("flomo_sync")

STATE_FILE = PROJECT_ROOT / "flomo_state.json"


class FlomoSync:
    """Flomo API 同步器。"""

    def __init__(self, api_key: str = FLOMO_API_KEY, interval: int = FLOMO_SYNC_INTERVAL):
        self.api_key = api_key
        self.interval = interval
        self._state: dict = self._load_state()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_sync_time: Optional[str] = self._state.get("last_sync_time")
        self.last_error: Optional[str] = None
        self.sync_count: int = 0

    # ── 状态持久化 ──

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("读取状态文件失败: %s", e)
        return {"last_sync_time": "", "imported_ids": []}

    def _save_state(self):
        self._state["last_sync_time"] = self.last_sync_time or ""
        try:
            STATE_FILE.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error("保存状态文件失败: %s", e)

    # ── Flomo API ──

    def fetch_notes(self, since: Optional[str] = None) -> list[dict]:
        """调用 Flomo API 获取笔记列表。

        返回按 created_at 升序排列的笔记列表。
        API 文档参考: https://flomoapp.com/api/docs (Pro)
        GET /api/v1/notes?since={timestamp}&limit=50
        """
        import urllib.request
        import urllib.error

        if not self.api_key:
            raise ValueError("FLOMO_API_KEY 未配置")

        params = "?limit=50"
        if since:
            params += f"&since={since}"

        url = f"https://flomoapp.com/api/v1/notes{params}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Flomo API HTTP {e.code}: {body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Flomo API 网络错误: {e.reason}")

        notes = data.get("notes", [])
        # 按时间升序排列
        notes.sort(key=lambda n: n.get("created_at", ""))
        return notes

    # ── 笔记写入 ──

    def save_note_to_vault(self, note: dict) -> Optional[Path]:
        """将单条 Flomo 笔记写入捕获目录。

        返回文件路径，若已去重则返回 None。
        """
        note_id = str(note.get("id", ""))
        if not note_id:
            logger.warning("笔记缺少 id，跳过")
            return None

        # 去重检查
        if note_id in self._state.get("imported_ids", []):
            return None

        content = note.get("content", "").strip()
        if not content:
            logger.warning("笔记 id=%s 内容为空，跳过", note_id)
            return None

        created_at = note.get("created_at", datetime.now(timezone.utc).isoformat())
        tags = note.get("tags", [])

        # 标题：取第一行
        first_line = content.split("\n")[0]
        title = first_line[:40] if first_line else f"flomo-{note_id[:8]}"
        # 清理文件名非法字符
        safe_title = "".join(c if c.isalnum() or c in " _-一-龥" else "_" for c in title).strip()
        if not safe_title:
            safe_title = f"flomo-{note_id[:8]}"

        date_prefix = created_at[:10]  # YYYY-MM-DD
        filename = f"{date_prefix} {safe_title}.md"
        filepath = CAPTURE_DIR / filename

        # 文件名冲突：加后缀
        counter = 1
        while filepath.exists():
            filename = f"{date_prefix} {safe_title}_{counter}.md"
            filepath = CAPTURE_DIR / filename
            counter += 1

        # 构建 frontmatter + 正文
        tag_lines = "\n".join(f"  - {t}" for t in tags) if tags else ""
        frontmatter = f"""---
created: {created_at}
source: flomo
flomo_id: {note_id}
tags:
{tag_lines}
---

"""
        md_content = frontmatter + content

        # 写入文件
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        filepath.write_text(md_content, encoding="utf-8")

        # 更新状态
        self._state.setdefault("imported_ids", []).append(note_id)
        self._save_state()

        logger.info("写入捕获目录: %s", filename)
        return filepath

    # ── 同步流程 ──

    def sync_once(self) -> int:
        """执行一次同步，返回新导入的笔记数量。"""
        logger.info("开始同步 Flomo 笔记...")
        try:
            notes = self.fetch_notes(since=self.last_sync_time)
        except (ValueError, RuntimeError, OSError) as e:
            self.last_error = str(e)
            logger.error("同步失败: %s", e)
            return 0

        count = 0
        for note in notes:
            if self.save_note_to_vault(note):
                count += 1

        # 更新最后同步时间
        if notes:
            self.last_sync_time = notes[-1].get("created_at", "")
            self._save_state()

        self.sync_count += count
        self.last_error = None
        logger.info("同步完成: 新导入 %d 条笔记", count)
        return count

    # ── 定时调度 ──

    def start_scheduler(self):
        """在后台线程启动定时同步。"""
        if self._running:
            return
        if not self.api_key:
            logger.warning("FLOMO_API_KEY 未配置，不启动 Flomo 同步")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="flomo-sync")
        self._thread.start()
        logger.info("Flomo 同步调度已启动，间隔 %d 秒", self.interval)

    def stop_scheduler(self):
        self._running = False

    def _run_loop(self):
        # 启动后立即执行一次
        self.sync_once()
        while self._running:
            time.sleep(self.interval)
            if self._running:
                self.sync_once()

    # ── 状态查询 ──

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "api_key_configured": bool(self.api_key),
            "interval": self.interval,
            "last_sync_time": self.last_sync_time,
            "last_error": self.last_error,
            "sync_count": self.sync_count,
            "imported_count": len(self._state.get("imported_ids", [])),
        }
```

- [ ] **Step 2: 手动测试同步模块**

```bash
cd "C:/Users/Administrator/Documents/trae_projects/first cc"
python -c "
from engine.flomo_sync import FlomoSync
sync = FlomoSync(api_key='your-key')
print(sync.get_status())
count = sync.sync_once()
print(f'Imported: {count}')
print(sync.get_status())
"
```

预期：无报错，打印连接状态。由于 API Key 可能无效，应能正常处理错误。

- [ ] **Step 3: Commit**

```bash
git add engine/flomo_sync.py
git commit -m "feat(engine): add Flomo sync module with API polling and capture directory writing"
```

---

### Task 3: 引擎集成 — 接入 server.py 和 main.py

**Files:**
- Modify: `engine/server.py:114-131` (do_GET 添加 Flomo 路由)
- Modify: `engine/server.py:206-207` (do_POST 添加 Flomo 触发)
- Modify: `engine/main.py:26-57` (启动 Flomo 调度器)

**Interfaces:**
- Consumes: `FlomoSync` 类（来自 Task 2）
- Produces: HTTP API 端点 `/api/flomo/sync` 和 `/api/flomo/status`

- [ ] **Step 1: 在 server.py 中添加 Flomo API 端点**

在 `do_GET` 方法的 `elif path == "/api/health":` 后面添加：

```python
        elif path == "/api/flomo/status":
            if hasattr(self.server, "flomo_sync") and self.server.flomo_sync:
                self._send_json(self.server.flomo_sync.get_status())
            else:
                self._send_json({"running": False, "error": "Flomo sync not initialized"})
```

在 `do_POST` 方法的 `elif parsed.path == "/api/approve-all":` 块后面添加：

```python
        elif parsed.path == "/api/flomo/sync":
            try:
                if hasattr(self.server, "flomo_sync") and self.server.flomo_sync:
                    count = self.server.flomo_sync.sync_once()
                    self._send_json({"ok": True, "imported": count})
                else:
                    self._send_json({"ok": False, "error": "Flomo sync not initialized"}, 500)
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
```

在文件顶部 import 添加：

```python
from engine.flomo_sync import FlomoSync
```

在 `start_server` 函数中，创建 `server` 之后添加 Flomo 初始化：

```python
    server = http.server.HTTPServer((HOST, port), APIHandler)

    # ── 初始化 Flomo 同步 ──
    flomo_sync = FlomoSync()
    flomo_sync.start_scheduler()
    server.flomo_sync = flomo_sync
```

- [ ] **Step 2: 在 main.py 中启动 Flomo 同步**

在 `_start_server` 函数后面添加新的后台启动函数：

```python
def _start_flomo_sync():
    """在后台线程启动 Flomo 同步调度。"""
    try:
        from engine.flomo_sync import FlomoSync
        sync = FlomoSync()
        sync.start_scheduler()
    except Exception as e:
        print(f"  ⚠️ Flomo 同步启动失败: {e}")
```

在 `main()` 函数的 `server_thread` 启动之后添加：

```python
        # 启动 Flomo 同步（后台）
        flomo_thread = threading.Thread(target=_start_flomo_sync, daemon=True)
        flomo_thread.start()
```

- [ ] **Step 3: 验证**

```bash
cd "C:/Users/Administrator/Documents/trae_projects/first cc"
python -c "
from engine.flomo_sync import FlomoSync
sync = FlomoSync()
print('FlomoSync init OK')
print(sync.get_status())
"
```

预期：打印 FlomoSync 初始化成功，状态显示 `running: false`（因为没启动调度器）

- [ ] **Step 4: Commit**

```bash
git add engine/server.py engine/main.py
git commit -m "feat(engine): integrate Flomo sync into server and main entry point"
```

---

### Task 4: 插件数据层 — 捕获目录工具函数

**Files:**
- Modify: `obsidian-plugin/src/data.ts:5-16`

**Interfaces:**
- Consumes: `DAILY_INPUT_DIR`（已有）
- Produces: `CAPTURE_DIR` 常量、`moveFile()` 函数、`isInCaptureDir()` 函数

- [ ] **Step 1: 添加捕获目录常量和工具函数**

在 `data.ts` 的文件顶部，`DAILY_INPUT_DIR` 下面添加：

```typescript
export const CAPTURE_DIR = `${YUANYAN_DIR}/🌱 原料库/捕获`;
```

在文件末尾 `isInDailyInputDir` 函数后面添加：

```typescript
/**
 * 检查文件是否在捕获目录内
 */
export function isInCaptureDir(filePath: string): boolean {
	const normalPath = normalizePath(filePath);
	const captureDir = normalizePath(CAPTURE_DIR);
	return normalPath.startsWith(captureDir) && normalPath.endsWith(".md");
}

/**
 * 移动文件到目标目录（使用 vault.adapter 跨平台实现）
 * 如果目标文件已存在则自动加数字后缀
 */
export async function moveFile(
	vault: Vault,
	sourcePath: string,
	targetDir: string
): Promise<string | null> {
	const sourceNormal = normalizePath(sourcePath);
	const fileName = sourceNormal.split("/").pop() || "";
	const baseName = fileName.replace(/\.md$/, "");
	const targetBase = normalizePath(`${targetDir}/${fileName}`);

	// 检查目标是否已存在
	let targetPath = targetBase;
	let counter = 1;
	while (await vault.adapter.exists(normalizePath(targetPath))) {
		targetPath = normalizePath(`${targetDir}/${baseName}_${counter}.md`);
		counter++;
	}

	try {
		await vault.adapter.rename(sourceNormal, targetPath);
		return targetPath;
	} catch (e) {
		console.error("元演引擎: 文件移动失败", sourceNormal, "→", targetPath, e);
		return null;
	}
}
```

同时需要在文件顶部 import 中确认 `Vault` 已被导入（已有 `import { Vault, normalizePath } from "obsidian"`）。

- [ ] **Step 2: 编译验证**

```bash
cd "C:/Users/Administrator/Documents/trae_projects/first cc/obsidian-plugin"
npx esbuild src/data.ts --bundle --platform=node --outfile=/dev/null --log-level=warning 2>&1 || echo "tsc check instead:"
npx tsc --noEmit src/data.ts --skipLibCheck 2>&1 | head -20
```

预期：无类型错误

- [ ] **Step 3: Commit**

```bash
git add obsidian-plugin/src/data.ts
git commit -m "feat(plugin): add capture directory constants and file move utilities"
```

---

### Task 5: 插件设置页 — Flomo 配置 UI

**Files:**
- Modify: `obsidian-plugin/src/settings.ts:6-24`

**Interfaces:**
- Consumes: `YuanYanPlugin` 类（已有）
- Produces: 设置面板新增「Flomo 同步」区域

- [ ] **Step 1: 扩展 YuanYanSettings 接口和默认值**

在 `YuanYanSettings` 接口中添加：

```typescript
export interface YuanYanSettings {
	// ... 已有字段
	flomoApiKey: string;
	flomoSyncEnabled: boolean;
}
```

在 `DEFAULT_SETTINGS` 中添加：

```typescript
export const DEFAULT_SETTINGS: YuanYanSettings = {
	// ... 已有字段
	flomoApiKey: "",
	flomoSyncEnabled: false,
};
```

- [ ] **Step 2: 在设置面板中添加 Flomo 区域**

在 `display()` 方法中，`微信公众号配置` 区域后面添加：

```typescript
		// ── Flomo 同步配置 ──
		containerEl.createEl("h3", { text: "Flomo 同步配置" });

		new Setting(containerEl)
			.setName("启用 Flomo 同步")
			.setDesc("定时从 Flomo 拉取笔记到捕获目录")
			.addToggle(toggle =>
				toggle
					.setValue(this.plugin.settings.flomoSyncEnabled)
					.onChange(async value => {
						this.plugin.settings.flomoSyncEnabled = value;
						await this.plugin.saveSettings();
						if (value) {
							this.plugin.startFlomoSync();
						} else {
							this.plugin.stopFlomoSync();
						}
					})
			);

		new Setting(containerEl)
			.setName("Flomo API Key")
			.setDesc("Flomo Pro 用户的 API 密钥（设置 → API → 复制）")
			.addText(text =>
				text
					.setPlaceholder("输入 Flomo API Key")
					.setValue(this.plugin.settings.flomoApiKey)
					.onChange(async value => {
						this.plugin.settings.flomoApiKey = value.trim();
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("立即同步")
			.setDesc("手动触发一次 Flomo 笔记同步")
			.addButton(button =>
				button
					.setButtonText("🔄 同步")
					.setCta()
					.onClick(async () => {
						button.setDisabled(true);
						button.setButtonText("同步中...");
						await this.plugin.triggerFlomoSync();
						button.setButtonText("✅ 完成");
						setTimeout(() => {
							button.setButtonText("🔄 同步");
							button.setDisabled(false);
						}, 2000);
					})
			);
```

- [ ] **Step 3: 编译验证**

```bash
cd "C:/Users/Administrator/Documents/trae_projects/first cc/obsidian-plugin"
npx tsc --noEmit src/settings.ts --skipLibCheck 2>&1 | head -20
```

预期：可能报错因为 `startFlomoSync` / `stopFlomoSync` / `triggerFlomoSync` 还没实现（Task 6）。这是预期行为，先确认接口定义没有语法错误即可。

- [ ] **Step 4: Commit**

```bash
git add obsidian-plugin/src/settings.ts
git commit -m "feat(plugin): add Flomo sync settings in configuration panel"
```

---

### Task 6: 插件主逻辑 — 捕获目录监控 + 确认弹窗 + 文件移动

**Files:**
- Modify: `obsidian-plugin/src/main.ts:1-404`

**Interfaces:**
- Consumes: `CAPTURE_DIR`, `DAILY_INPUT_DIR`, `isInCaptureDir()`, `moveFile()`（来自 Task 4）、`flomoApiKey`/`flomoSyncEnabled`（来自 Task 5）
- Produces: 捕获目录文件监控、确认弹窗、文件移动逻辑、引擎 API 通信

- [ ] **Step 1: 添加 import 和类型**

在 `main.ts` 顶部 import 区域添加：

```typescript
import { CAPTURE_DIR, DAILY_INPUT_DIR, isInCaptureDir, moveFile } from "./data";
import { Modal, Setting } from "obsidian";
```

- [ ] **Step 2: 创建确认弹窗组件**

在 `main.ts` 中 `YuanYanPlugin` 类前面添加：

```typescript
// ========== Flomo 确认弹窗 ==========

class FlomoConfirmModal extends Modal {
	private title: string;
	private preview: string;
	private filePath: string;
	private plugin: YuanYanPlugin;
	private onConfirm: () => void;
	private onDecline: () => void;

	constructor(
		app: App,
		plugin: YuanYanPlugin,
		filePath: string,
		title: string,
		preview: string,
		onConfirm: () => void,
		onDecline: () => void
	) {
		super(app);
		this.plugin = plugin;
		this.filePath = filePath;
		this.title = title;
		this.preview = preview;
		this.onConfirm = onConfirm;
		this.onDecline = onDecline;
	}

	onOpen(): void {
		const { contentEl } = this;

		contentEl.empty();
		contentEl.addClass("flomo-confirm-modal");

		contentEl.createEl("h2", { text: "📮 检测到 Flomo 新笔记" });

		contentEl.createEl("h3", { text: this.title, cls: "flomo-note-title" });

		const previewEl = contentEl.createEl("div", { cls: "flomo-preview" });
		previewEl.createEl("p", { text: this.preview.slice(0, 200) });
		if (this.preview.length > 200) {
			previewEl.createEl("p", { text: "......", cls: "flomo-preview-more" });
		}

		new Setting(contentEl)
			.addButton(button =>
				button
					.setButtonText("❌ 留在捕获")
					.setWarning()
					.onClick(() => {
						this.close();
						this.onDecline();
					})
			)
			.addButton(button =>
				button
					.setButtonText("✅ 移入日输入")
					.setCta()
					.onClick(() => {
						this.close();
						this.onConfirm();
					})
			);
	}

	onClose(): void {
		const { contentEl } = this;
		contentEl.empty();
	}
}
```

- [ ] **Step 3: 添加 Flomo 相关方法到 YuanYanPlugin 类**

在 `YuanYanPlugin` 类中添加属性：

```typescript
export default class YuanYanPlugin extends Plugin {
	settings!: YuanYanSettings;
	engineStatus: "idle" | "running" | "error" = "idle";
	private processedFiles: Set<string> = new Set();
	private debounceTimer: number | null = null;
	private pendingChanges: Map<string, number> = new Map();
	// ── 新增 Flomo 相关 ──
	private declinedFiles: Set<string> = new Set();
	private flomoCheckTimer: number | null = null;
```

在 `onload()` 方法中，`await this.loadProcessedState();` 后面添加：

```typescript
			await this.loadDeclinedState();
```

在 `onload()` 方法末尾，`setTimeout(() => this.processExistingFiles(), 3000);` 后面添加：

```typescript
			// 启动 Flomo 捕获目录监控
			if (this.settings.flomoSyncEnabled) {
				this.startFlomoCaptureWatch();
			}
```

- [ ] **Step 4: 实现 Flomo 方法**

在 `refreshApprovalView()` 方法前面添加所有 Flomo 相关方法：

```typescript
	// ========== Flomo 同步管理 ==========

	async startFlomoSync(): Promise<void> {
		// 通过引擎 API 触发（引擎后台运行）
		try {
			const resp = await fetch("http://127.0.0.1:8765/api/flomo/sync", { method: "POST" });
			if (resp.ok) {
				new Notice("Flomo 同步已启用（引擎后台定时运行）");
			}
		} catch {
			new Notice("Flomo 同步：引擎未运行，仅监控捕获目录");
		}
		this.startFlomoCaptureWatch();
	}

	stopFlomoSync(): void {
		if (this.flomoCheckTimer !== null) {
			window.clearInterval(this.flomoCheckTimer);
			this.flomoCheckTimer = null;
		}
		new Notice("Flomo 同步已停用");
	}

	async triggerFlomoSync(): Promise<void> {
		try {
			const resp = await fetch("http://127.0.0.1:8765/api/flomo/sync", { method: "POST" });
			if (resp.ok) {
				const data = await resp.json();
				new Notice(`Flomo 同步完成: 导入 ${data.imported || 0} 条`);
			} else {
				new Notice("Flomo 同步失败: 引擎未运行？");
			}
		} catch {
			new Notice("Flomo 同步失败: 无法连接引擎");
		}
	}

	// ========== 捕获目录监控 ==========

	private startFlomoCaptureWatch(): void {
		// 每 30 秒检查一次捕获目录的新文件
		if (this.flomoCheckTimer !== null) {
			window.clearInterval(this.flomoCheckTimer);
		}
		this.flomoCheckTimer = window.setInterval(() => {
			this.checkCaptureDir();
		}, 30000);
	}

	private async checkCaptureDir(): Promise<void> {
		const captureDir = normalizePath(CAPTURE_DIR);
		if (!(await this.app.vault.adapter.exists(captureDir))) {
			return;
		}

		const files = this.app.vault.getFiles().filter(f =>
			isInCaptureDir(f.path) &&
			!this.declinedFiles.has(f.path)
		);

		for (const file of files) {
			await this.promptFlomoConfirm(file);
			return; // 每次只处理一个，避免弹窗堆积
		}
	}

	private async promptFlomoConfirm(file: TFile): Promise<void> {
		const content = await this.app.vault.read(file);
		const title = file.name.replace(/\.md$/, "");

		return new Promise((resolve) => {
			const modal = new FlomoConfirmModal(
				this.app,
				this,
				file.path,
				title,
				content.replace(/^---[\s\S]*?---\n/, ""),  // 去掉 frontmatter
				async () => {
					// 确认：移入日输入
					const targetDir = normalizePath(DAILY_INPUT_DIR);
					const result = await moveFile(this.app.vault, file.path, targetDir);
					if (result) {
						new Notice(`已移入日输入: ${title}`);
						// 立即触发分类
						await this.processFile(result);
					} else {
						new Notice(`移动失败: ${title}`, 5000);
					}
					resolve();
				},
				() => {
					// 拒绝：记录 declined
					this.declinedFiles.add(file.path);
					this.saveDeclinedState();
					new Notice(`留在捕获: ${title}`);
					resolve();
				}
			);
			modal.open();
		});
	}

	// ========== Declined 持久化 ==========

	private async loadDeclinedState(): Promise<void> {
		const data = await this.loadData();
		if (data?.declinedFiles) {
			this.declinedFiles = new Set(data.declinedFiles);
		}
	}

	private async saveDeclinedState(): Promise<void> {
		const data = (await this.loadData()) || {};
		data.declinedFiles = Array.from(this.declinedFiles);
		await this.saveData(data);
	}
```

- [ ] **Step 5: 确保 onFileChange 忽略捕获目录**

在 `onFileChange` 方法中，`if (!isInDailyInputDir(file.path)) return;` 上面添加捕获目录的检查：

```typescript
		// 捕获目录的文件由 checkCaptureDir 处理，不走 AI 分类
		if (isInCaptureDir(file.path)) return;
```

- [ ] **Step 6: 编译验证**

```bash
cd "C:/Users/Administrator/Documents/trae_projects/first cc/obsidian-plugin"
npx esbuild src/main.ts --bundle --external:obsidian --platform=browser --outfile=/dev/null --log-level=warning 2>&1 | head -20
```

预期：无报错（`App` 类型从 `obsidian` 导入需要确认）。如果 `App` 未从 obsidian 导入：

```typescript
import { Plugin, TFile, Notice, normalizePath, WorkspaceLeaf, App, Modal, Setting } from "obsidian";
```

- [ ] **Step 7: Commit**

```bash
git add obsidian-plugin/src/main.ts
git commit -m "feat(plugin): add capture directory monitoring and Flomo confirm modal"
```

---

### Task 7: 构建验证

**Files:**
- Build: `obsidian-plugin/main.js`

- [ ] **Step 1: 构建 Obsidian 插件**

```bash
cd "C:/Users/Administrator/Documents/trae_projects/first cc/obsidian-plugin"
npx esbuild src/main.ts --bundle --external:obsidian --platform=browser --outfile=main.js --log-level=warning
echo "Build exit: $?"
```

预期：无报错，生成 `main.js`

- [ ] **Step 2: 验证引擎模块加载**

```bash
cd "C:/Users/Administrator/Documents/trae_projects/first cc"
python -c "
from engine.flomo_sync import FlomoSync
from engine.config import CAPTURE_DIR, FLOMO_API_KEY, FLOMO_SYNC_INTERVAL
print(f'CAPTURE_DIR: {CAPTURE_DIR}')
print(f'SYNC_INTERVAL: {FLOMO_SYNC_INTERVAL}s')
print(f'API_KEY configured: {bool(FLOMO_API_KEY)}')
sync = FlomoSync()
print(f'Status: {sync.get_status()}')
print('✅ All OK')
"
```

- [ ] **Step 3: 端到端验证（手动）**

1. 在 `.env` 中配置 `FLOMO_API_KEY`
2. 启动引擎：`python -m engine.main`
3. 确认控制台输出包含 "Flomo 同步调度已启动"
4. 在 Obsidian 中加载插件，打开设置页确认 Flomo 配置区域显示
5. 在 Flomo 中写一条笔记，等待下次同步（或通过 `/api/flomo/sync` 触发）
6. 检查 `🌱 原料库/捕获/` 目录是否生成了对应 `.md` 文件
7. 在 Obsidian 中确认弹窗出现
8. 点击「移入日输入」，确认文件出现在 `🌱 原料库/日输入/`
9. 确认 AI 分类流程被自动触发

- [ ] **Step 4: 最终提交**

```bash
cd "C:/Users/Administrator/Documents/trae_projects/first cc"
git add obsidian-plugin/main.js obsidian-plugin/src/ engine/ .env
git commit -m "feat: Flomo 笔记同步到反哺弧 — 引擎定时轮询 + 插件确认移入

- engine/flomo_sync.py: Flomo API 轮询、去重、写入捕获目录
- engine/server.py: 添加 /api/flomo/sync 和 /api/flomo/status 端点
- engine/main.py: 启动 Flomo 后台调度
- obsidian-plugin: 捕获目录监控、确认弹窗、文件移动
- settings.ts: Flomo API Key 和同步开关配置"
```
