# 元演心智 — Fendi 的 AI 学习系统

## 📋 项目概览

个人知识管理+AI自动化系统，包含个人网站、桌面工具、飞书集成、视频流水线。

**站长：** Fendi945
**系统：** Windows 10 / Git Bash
**编辑器：** Trae
**GitHub：** Fendi945

---

## 🌐 网站 (website/)

纯前端个人网站，**Esther 不二设计风格**。

### 设计系统

| 属性 | 值 |
|------|-----|
| 底色 | `#fefcf6` 暖米色 |
| 强调色 | 暖黄 `#F4D758` · 蓝 `#2B7FD8` · 橙 `#F7A946` |
| 标题字体 | Huiwen Mincho（明朝体） |
| 正文字体 | Noto Sans SC |
| 装饰字体 | Caveat（手写体） |
| 圆角 | 卡片 20px · 小组件 12px |
| 风格词 | 暖色、留白、磨砂玻璃、终端Hero、鼠标辉光 |

### 页面结构（12页）

| 文件 | 内容 |
|------|------|
| `index.html` | 首页 — 终端打字机Hero + 引用幻灯片 + 所有模块聚合 |
| `iching.html` | 易经专栏 — 六十四卦二进制推演（约98KB） |
| `yuanyan.html` | 元演系统架构说明 |
| `four-quadrants.html` | 要事第一四象限（可嵌入桌面版） |
| `habits.html` | 习惯追踪 |
| `diary.html` | 工作日志 |
| `daily.html` | AI 每日资讯 |
| `ai.html` | AI 学习笔记 |
| `log.html` | 每日复盘 |
| `garden.html` | 项目案例 |
| `videos.html` | 视频素材 |
| `images.html` | 图片素材 |

### 关键技术

- 纯前端 HTML + CSS + JS，无框架
- CSS 自定义属性控制所有颜色（`--accent`, `--primary`, `--surface` 等）
- 原生 JS 动画：终端打字机、鼠标辉光、卡片倾斜、滚动浮现

---

## 🖥️ 桌面应用

### 要事第一四象限 (four-quadrants/)
- Electron 桌面程序
- 暖橙大地色系 + 磨砂玻璃质感
- 启动：`four-quadrants/启动要事第一.bat`
- 图标：`D:\要事第一\图标\` 或 `D:\icons\`

### 番茄钟 (pomodoro-timer/)
- Electron 桌面计时程序
- 启动：`pomodoro-timer/启动番茄钟.bat`
- **禁止使用 `npx`** 启动 Electron，需直接指定 electron.exe 路径

---

## ⚙️ 引擎 (engine/)

Python 后端，飞书集成与自动化。

| 模块 | 功能 |
|------|------|
| `feishu_client.py` | 飞书 API 客户端（App Token + User Auth） |
| `feishu_bitable_sync.py` | 飞书多维表格同步 |
| `feishu_kanban_sync.py` | 飞书看板同步 |
| `dashboard_gen.py` | Dashboard 自动生成 |
| `classifier.py` | 内容分类器 |
| `flomo_sync.py` | flomo 笔记同步 |
| `wechat_publisher.py` | 公众号发布 |
| `wechat_video_scraper.py` | 微信视频号数据自动抓取（Playwright） |
| `dashboard_analyzer.py` | Dashboard 数据分析引擎（调用 DeepSeek） |
| `feedback_writer.py` | 分析结果→Obsidian 笔记自动写入 |
| `watchdog.py` | 文件监控自动触发 |

---

## 🎥 视频流水线 (video-project/)

**已归档（2026-07-07）。** 视频制作完全使用剪映：
- 贴文字稿自动对齐字幕
- E/Q 快捷键裁气口
- 剪映自带背景模糊/特效/封面

AI 能力集中在 **口播稿生产**（capture → classify → produce），不涉及视频剪辑自动化。

---

## 🏛️ Vault Bridge (vault_bridge/)

Obsidian vault 与飞书审批面板的桥接工具。
- `审批入口.md` / `审批面板.bat` — 打开审批面板
- `vault_utils.py` — vault 工具函数

---

## 📌 项目规范

### 写作
- 口播稿：口气平视、讲痛点、≤600字、金句结尾、标题带数字
- 公众号封面图：必须精准匹配文章主题
- 封面图规范：三层分层合成（参考图风格）

### 编码
- 网页统一 lang="zh-CN"
- 所有样式通过 CSS 变量控制
- 无框架，原生 JS

### 路径
- 桌面：`D:\Documents\Desktop`
- 图标：`D:\要事第一\图标\` / `D:\icons\`
- 视频输出：桌面 D 盘目录

### 注意
- **禁止 `npx`** 启动 Electron（需直接指定 electron.exe）
- VBScript/PowerShell 对中文/emoji 支持有限，避免用

### 驱动与软件安装
- 安装任何驱动/软件前，先做四步检查：
  1. 系统架构（32-bit vs 64-bit）
  2. 查询现有版本：`Get-WmiObject Win32_PnPSignedDriver`
  3. 检查本地是否已有安装包（D:\、Downloads\ 等）
  4. 确认计划后再执行，不擅自下载或覆盖
- GUI 安装器不能在 Git Bash 中运行，需要用户交互或提权时先说明
- 卸载旧驱动后再装新驱动，不要覆盖安装

### 协作规则
- 多步骤任务必须先列计划、确认后再动手，不跳步
- 涉及文件/数据库/配置变更的，先列出「创建/移动/删除」清单
- **不擅自删除任何文件或数据**，必须经用户确认
- 跨 session 的关键状态（已下载的文件、已安装的软件、已解决的问题）先查 memory 记录，不重复下载或操作

---

## 🎯 输出硬规则（我对所有 Agent 通用）

### 基调
Top expert. Accuracy beats approval. Blunt, argumentative. No disclaimers or praise. Lead with counterarguments. Don't capitulate without new evidence.

### 标签体系
每条主张必须打标：
- `[KNOWN]` 训练事实 · `[COMPUTED]` 计算推导 · `[INFERRED]` 逻辑推论
- `[COMMON]` 领域常识 · `[FRAME]` 符号系统 · `[GUESS]` 无依据猜测

无标签的疾病、法条、引用、命名实体一律禁止。

### 帧实分离
不把符号框架（占星、分类学）翻译成真实世界主张（医学、法律、金融）。跨框架翻译必须标注。

### 置信度
- HIGH ≥80% · MED 50–80% · LOW 20–50% · VERY LOW <20%
- `[FRAME]` 真实世界 + `[GUESS]` 上限 LOW

### 不知道
第一行 "I don't know." 不掩埋，不编造。

### 反奉承
红旗：异常优雅 / 一个模式解释一切 / 无证据妥协 / 为未获得权威的具体化。应对 → 删具体化，加 `[GUESS]`，或说不知道。

### 后见之明检测
"不知道结果时能预测吗？" → 不能则标记 `[INFERRED, post-hoc]`

### 引用
绝不伪造。维护一致性而改立场必须公开说明。

### 违规报告
输出末尾追加：`[RULES I BROKE]: 哪条、在哪、为什么。`
