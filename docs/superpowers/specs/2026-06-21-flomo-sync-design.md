# Flomo 笔记自动同步到反哺弧 — 设计文档

## 概述

将 Flomo Pro API 笔记定时同步到 Obsidian 元演心智 vault 的「捕获」目录，经用户确认后移入「日输入」目录，进入已有的反哺弧流水线（AI 分类 → 看板审批 → 成品产出）。

## 背景

用户使用 Flomo（浮墨笔记）记录日常想法和素材，希望这些笔记能自动流入 Obsidian 元演心智系统。目前已有：

- **Python 引擎** (`engine/`) — 后台常驻进程，负责看板生成、审批同步、公众号发布
- **Obsidian 插件** (`obsidian-plugin/`) — 文件监控、AI 分类、审批面板、微信发布
- **Vault 目录结构** — `🌱 原料库/日输入/` → `⚙️ 反哺弧/看板/` → `🌿 加工间/` → `🍎 成品区/`

## 数据流

```
Flomo API (Pro)
    │ 每30分钟轮询增量笔记
    ▼
🌱 原料库/捕获/{日期}-{标题}.md    ← 自动写入
    │
    ▼  Obsidian 插件检测到新文件
📢 弹出确认对话框：
  「检测到 Flomo 笔记『xxx』是否移入日输入？」
    ├── ✅ 是 → 文件移到日输入/ → 触发 AI 分类 → 看板审批 → 产出
    └── ❌ 否 → 留在捕获/ 暂存
```

## 新增文件

### 1. `engine/flomo_sync.py` — Flomo API 同步模块

```
class FlomoSync:
    - api_key: str          # Flomo Pro API Key
    - last_sync_time: str   # 上次同步时间戳（持久化到文件）
    - interval: int         # 轮询间隔，默认1800秒（30分钟）

    方法:
    - fetch_notes(since_time) → list[dict]  # 调用 Flomo API
    - save_note_to_vault(note) → str        # 写入 .md 文件到捕获目录
    - sync_once()                           # 单次同步流程
    - start_scheduler()                     # 启动定时循环

> 注意：引擎只负责将笔记写入捕获目录，不直接操作看板。看板条目由插件在用户确认移入日输入后，通过已有的 AI 分类流程自动创建。
```

### 2. `engine/flomo_state.json` — 同步状态持久化

储存在引擎工作目录，记录：

```json
{
  "last_sync_time": "2026-06-21T10:30:00",
  "imported_ids": ["flomo_note_id_1", "flomo_note_id_2"]
}
```

## 修改文件

### 1. `engine/server.py`

- 启动时初始化 `FlomoSync` 实例
- 检查配置中是否有 `flomo_api_key`，有则调用 `start_scheduler()`
- 添加 `/api/flomo/sync` 路由（手动触发一次同步，调试用）
- 添加 `/api/flomo/status` 路由（查看同步状态）

### 2. `engine/config.py`

新增配置项：

```python
# Flomo 配置
FLOMO_API_KEY: str = ""           # Flomo Pro API Key
FLOMO_SYNC_INTERVAL: int = 1800   # 轮询间隔（秒）
FLOMO_LAST_SYNC: str = ""         # 持久化的最后同步时间
```

### 3. `obsidian-plugin/src/data.ts`

新增：

```typescript
export const CAPTURE_DIR = `${YUANYAN_DIR}/🌱 原料库/捕获`;

// 文件操作
export async function moveFile(vault: Vault, source: string, target: string): Promise<void>;
export function isInCaptureDir(filePath: string): boolean;
```

看板状态无需改动 — 看板条目只在用户确认后通过 AI 分类创建，状态流转不变。

### 4. `obsidian-plugin/src/main.ts`

新增功能：

- 监控 `捕获/` 目录的文件创建事件（`onFileChange` 已处理，但需要区分来源）
- 弹出 Obsidian 确认对话框（使用 `Modal` 或 `Notice` + 自定义确认）
- 「是」→ `moveFile()` 到 `日输入/` 
- 「否」→ 跳过，留在捕获目录
- 捕获目录文件不进入 AI 分类，只有确认后才进入流水线

实现细节：

```typescript
// 在 onFileChange 中
private async onNewCapturedFile(file: TFile): Promise<void> {
    if (!isInCaptureDir(file.path)) return;

    const content = await this.app.vault.read(file);
    const title = file.name.replace(/\.md$/, "");
    
    // 弹出确认对话框
    const confirmed = await this.showConfirmModal(
        `检测到 Flomo 笔记「${title}」是否移入日输入？`,
        content.slice(0, 200)
    );

    if (confirmed) {
        const targetPath = normalizePath(
            `${DAILY_INPUT_DIR}/${file.name}`
        );
        await this.app.vault.rename(file, targetPath);
        new Notice(`已移入日输入: ${title}`);
    }
    // 否 → 不做任何操作
}

// declined 文件持久化
private declinedFiles: Set<string> = new Set();

private async loadDeclinedState(): Promise<void> {
    const data = await this.loadData();
    if (data?.declinedFiles) {
        this.declinedFiles = new Set(data.declinedFiles);
    }
}

// 在 onNewCapturedFile 中先检查 declined
private async onNewCapturedFile(file: TFile): Promise<void> {
    if (!isInCaptureDir(file.path)) return;
    if (this.declinedFiles.has(file.path)) return;  // 已拒绝过
    
    // ...弹出确认框逻辑
    
    if (!confirmed) {
        this.declinedFiles.add(file.path);
        await this.saveDeclinedState();
    }
}
```

### 5. `obsidian-plugin/src/settings.ts`

新增设置项：

```typescript
export interface YuanYanSettings {
    // ... 已有配置
    flomoApiKey: string;
    flomoSyncEnabled: boolean;
}
```

设置面板新增「Flomo 同步」区域：

- Flomo API Key 输入
- 启用/禁用开关
- 「立即同步」按钮（通过引擎 API 触发）

### 6. `obsidian-plugin/src/views/ApprovalView.ts`

无需改动 — Flomo 来源的笔记经过 AI 分类后与其他日输入无异，在看板中统一展示。

## Flomo API 接口

使用 Flomo Pro 提供的 API：

```
GET https://flomoapp.com/api/v1/notes?since={timestamp}&limit=50
Authorization: Bearer {api_key}
```

响应格式：

```json
{
  "notes": [
    {
      "id": "abc123",
      "content": "笔记内容（纯文本或 Markdown）",
      "created_at": "2026-06-21T10:30:00",
      "updated_at": "2026-06-21T10:30:00",
      "tags": ["tag1", "tag2"]
    }
  ]
}
```

> 注意：具体 API 端点需要根据 Flomo 官方 Pro API 文档确认，设计阶段预留适配层接口。

## 笔记转换规则

| Flomo 原始 | 转换为 |
|---|---|
| 纯文本内容 | Markdown 正文 |
| 标签 #tag | Obsidian 标签 `#tag` |
| 时间戳 | frontmatter `created` + `source: flomo` |
| 多行内容 | 保留换行，加粗/列表等 Markdown 语法直通 |

生成的 `.md` 文件格式：

```markdown
---
created: 2026-06-21T10:30:00
source: flomo
flomo_id: abc123
tags:
  - tag1
---
笔记内容...
```

## 状态流转

```
用户操作                        文件状态
──────────                    ──────────
Flomo 笔记同步                 引擎写入 .md → 🌱 捕获/
    │
    ▼ 插件检测到新文件
弹出确认对话框
    ├── ✅ 移入日输入          文件移动到 🌱 日输入/
    │       │                    ↓ (插件自动触发 AI 分类)
    │       ▼
    │    看板待审批 ← pending
    │    → approved/rejected → 产出
    │
    └── ❌ 留在捕获           declined（记录到 declinedFiles Set，不再弹窗提示）
                              用户可手动归档/删除
```

> `declined` 状态持久化：插件保存已拒绝文件列表 `declinedFiles: string[]`，避免 vault 重载后重复弹窗。

## 错误处理

| 场景 | 行为 |
|---|---|
| Flomo API 不可用 | 跳过本轮，下轮重试，记录错误日志 |
| API Key 无效 | 禁用同步，报错通知 |
| 文件写入冲突 | 文件名加时间戳后缀 |
| 网络超时 | 指数退避重试（3次） |
| Obsidian 未运行 | 引擎独立写入文件，下次 Obsidian 打开自动检测 |

## 配置项汇总

| 配置 | 默认值 | 说明 |
|---|---|---|
| Flomo API Key | (空) | Flomo Pro API 凭证 |
| 同步间隔 | 1800秒(30min) | 两次轮询间隔 |
| 自动移入日输入 | false | 未来可选项：彻底自动化 |
| 通知方式 | Dialog | 弹窗 / 静默通知 |

## 界面设计示意

### Obsidian 确认对话框

```
┌──────────────────────────────┐
│  📮 检测到 Flomo 新笔记       │
│                              │
│  「今天想到一个 AI 产品点子」  │
│                              │
│  内容预览: 今天和同事聊到...   │
│                              │
│      [留在捕获]  [移入日输入]  │
└──────────────────────────────┘
```

### 设置面板

```
┌─ Flomo 同步 ─────────────────┐
│  API Key:  [················]│
│  同步间隔: 30 分钟            │
│  [🔄 立即同步]  [上次: 10:30] │
└──────────────────────────────┘
```
