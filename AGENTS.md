# 元演心智 — Fendi 的 AI 学习系统

> 个人知识管理 + AI 自动化系统。站长 Fendi945，Windows 10 / Git Bash / Trae 编辑器。

---

## 🌐 网站 (12页纯前端)

**设计风格：** Esther 不二 · 暖米底 `#fefcf6` · 强调色 暖黄 `#F4D758` 蓝 `#2B7FD8` 橙 `#F7A946`
**字体：** Huiwen Mincho（标题） · Noto Sans SC（正文） · Caveat（装饰）
**技术：** 纯 HTML+CSS+JS，无框架，CSS 变量控制全站颜色

| 文件 | 说明 |
|------|------|
| `index.html` | 首页（终端打字机Hero + 所有模块聚合） |
| `iching.html` | 易经六十四卦二进制推演（~98KB） |
| `yuanyan.html` | 元演系统架构 |
| `four-quadrants.html` | 要事第一四象限 |
| `habits.html` | 习惯追踪 |
| `diary.html` | 工作日志 |
| `daily.html` | AI 每日资讯 |
| `ai.html` | AI 学习笔记 |
| `log.html` | 每日复盘 |
| `garden.html` | 项目案例 |
| `videos.html` | 视频素材 |
| `images.html` | 图片素材 |

---

## 🖥️ 桌面应用

**要事第一四象限** — Electron 程序，暖橙大地色+磨砂玻璃。启动：`four-quadrants/启动要事第一.bat`
**番茄钟** — Electron 计时器。启动：`pomodoro-timer/启动番茄钟.bat`
⚠️ **禁止 `npx`** 启动 Electron，需直接指定 electron.exe 路径

---

## ⚙️ 后端引擎 (engine/)

Python 飞书集成自动化。主要模块：`feishu_client.py` · `feishu_bitable_sync.py` · `dashboard_gen.py` · `classifier.py` · `flomo_sync.py` · `wechat_publisher.py` · `watchdog.py`

---

## 🎨 小黑插图 Skill (ian-xiaohei-illustrations)

**已安装于** `.claude/skills/ian-xiaohei-illustrations/`
**调用方式：** 用 Skill 工具调用 `ian-xiaohei-illustrations`
**生图API：** Agnes `agnes-image-2.1-flash`（用 project 根目录 `.env` 的 `AGNES_API_KEY`）

### 小黑形象规范

**通用特征：**
- 黑色实心水滴/圆豆形身体，略高>宽，无脖子
- 两个白色正圆大眼，各有极小黑色瞳孔
- 无嘴、无眉毛、无其他五官
- 胳膊腿极细——跟画里的线条/电线一样细（stick figure level）
- 表情空洞、呆、认真
- 纯黑白手绘线稿风格，不用灰色、阴影、渐变

**两种风格按内容切换：**

| 内容类型 | 小黑风格 | 说明 |
|---------|---------|------|
| 易经、古文、历史文化 | **古装小黑** | 白色轮廓线画古装袍子在黑身体上（不填色块），头顶发髻+白绳 |
| 电子设备、技术、现代场景 | **现代极简小黑** | 纯黑豆子裸身，无古装，无发髻，仅白点眼+细杆四肢 |

### 文字禁忌（重要）
- AI 图像模型写中文必出乱码/幻觉/重复
- **优先零文字方案**——纯图形表达
- 如果必须加文字：仅限极短英文（L1/L2/L3）或事后编辑

### 工作流
1. 先出 shot list（配图策略），每张写清楚主题/核心意思/结构类型/小黑动作
2. 每张图单独用 `agnes-image-2.1-flash` 生成
3. 检查 QA checklist 后交付

### 参考文件
`SKILL.md` · `references/style-dna.md` · `references/xiaohei-ip.md` · `references/prompt-template.md` · `references/qa-checklist.md`

### 错题库
参见 `memory/image-gen-errors.md` — 中文文字出错记录和回避策略。

---

## 🎥 视频流水线 (video-project/)

口播视频：Whisper 识别 → 字幕（汉仪中黑体 54号白/60号黄加粗）→ 模糊背景。横版 960×544 · 竖版 544×960。文案直接写入 Obsidian vault，不展示全文。

---

## 📌 关键约定

- 网页一律 `lang="zh-CN"`
- 样式全走 CSS 变量，无框架
- VBScript/PowerShell 对中文支持有限，避免使用
- 图标归档 `D:\要事第一\图标\` 或 `D:\icons\`
- 视频输出到桌面 D 盘目录

---

## 🎯 输出硬规则

基调: Top expert. Accuracy beats approval. Blunt, argumentative. No disclaimers/praise. Lead with counterarguments.

**标签体系** — 每条主张必打：`[KNOWN]` `[COMPUTED]` `[INFERRED]` `[COMMON]` `[FRAME]` `[GUESS]`

**帧实分离** — 符号框架不翻译成真实世界主张（医学/法律/金融）

**置信度** — HIGH ≥80% · MED 50–80% · LOW 20–50% · VERY LOW <20%

**不知道** → 第一行 "I don't know." 不编造

**反奉承** → 红旗下加 `[GUESS]` 或说不知道

**后见之明** → 不能预测则标记 `[INFERRED, post-hoc]`

**违规报告** → 末尾追加 `[RULES I BROKE]: 哪条、在哪、为什么。`
