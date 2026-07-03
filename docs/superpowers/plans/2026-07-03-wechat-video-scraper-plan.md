# 微信视频号自动抓取 Implementation Plan

> **For agentic workers:** Inline execution.

**Goal:** Playwright 爬虫自动抓取 channels.weixin.qq.com 最新视频数据，写入 dashboard-data.json，opposition 自动更新。

**Architecture:** 单文件爬虫模块 `wechat_video_scraper.py`，Cookie 持久化扫码登录，集成到 engine server 的后台调度。

**Tech Stack:** Python, Playwright, JSON 文件持久化

## Global Constraints

- 数据写入 `⚙️ 反哺弧/看板/dashboard-data.json`，不涉及飞书
- Cookie 存 `engine/data/wechat_cookies.json`
- 状态存 `engine/data/wechat_scraper_state.json`
- 遵循现有 engine 模块风格（FlomoSync 模式）
- 首次需用户微信扫码

---

### Task 1: 安装 Playwright Chromium

- [ ] **安装浏览器**

```bash
cd "C:\Users\Administrator\Documents\trae_projects\first cc"
python -m playwright install chromium
```

---

### Task 2: 实现 `engine/wechat_video_scraper.py`

**Files:**
- Create: `engine/wechat_video_scraper.py`
- Modify: None yet

**核心类：`WeChatVideoScraper`**

方法：
- `__init__(interval=7200)` — 每2小时检查一次
- `_load_cookies() / _save_cookies(cookies)` — Cookie 持久化
- `_load_state() / _save_state()` — 最后抓取的视频ID
- `_login_flow(page)` — 扫码登录（headed 模式，显示二维码）
- `_ensure_login(page)` — 检查登录态，过期重新扫码
- `_get_latest_video(page)` — 提取最新视频数据
- `_get_top_comment(page, video_url)` — 提取热评
- `_load_dashboard_data() / _save_dashboard_data(data)` — 读写 dashboard-data.json
- `_has_new_video()` — 对比最新视频ID是否已存在
- `fetch_latest()` — 主入口：一次完整抓取流程
- `start_scheduler() / stop_scheduler()` — 后台调度

关键实现细节：
- 首次运行：headed 模式打开 channels.weixin.qq.com → 等待扫码 → 保存 cookie
- 后续运行：headless 模式加载 cookie → 跳转到数据页 → 提取数据
- 数据写入：读取现有 dashboard-data.json → 追加新记录（如果不存在）→ 写回
- 字段完全对齐现有 dashboard-data.json 结构

- [ ] **编写实现代码**（见下方完整源码）

- [ ] **验证模块可导入**

```bash
cd "C:\Users\Administrator\Documents\trae_projects\first cc"
python -c "from engine.wechat_video_scraper import WeChatVideoScraper; print('OK')"
```

---

### Task 3: 集成到 `engine/server.py`

**Files:**
- Modify: `engine/server.py`

在 server.py 中：
1. import `WeChatVideoScraper`
2. 在 `start_server()` 中初始化 scraper 并启动调度器（跟在 FlomoSync 后面）
3. 添加 API 端点：
   - `GET /api/wechat/status` — 爬虫状态
   - `POST /api/wechat/trigger` — 手动触发一次抓取
   - `GET /api/wechat/needs-login` — 是否需要扫码

- [ ] **修改 server.py 集成爬虫**

- [ ] **重启服务器测试**

```bash
# 先停掉旧服务器，再启动
cd "C:\Users\Administrator\Documents\trae_projects\first cc"
PYTHONIOENCODING=utf-8 python -m engine.server --no-browser
```

---

### Task 4: 首次扫码登录

- [ ] **运行首次扫码流程**

```bash
cd "C:\Users\Administrator\Documents\trae_projects\first cc"
PYTHONIOENCODING=utf-8 python -c "
from engine.wechat_video_scraper import WeChatVideoScraper
scraper = WeChatVideoScraper()
scraper.fetch_latest()
"
```

此时 Playwright 会打开浏览器显示二维码 → 用户用微信扫码 → 爬虫自动提取数据。
