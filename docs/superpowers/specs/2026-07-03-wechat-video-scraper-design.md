# 微信视频号数据自动抓取 — 设计文档

## 背景

用户（Fendi）手动通过桌面看板程序（看板v2_修改版.exe）录入微信视频号数据到
`dashboard-data.json`，opposition 审批面板读取该文件展示数据。

升级 Windows 11 后手动录入中断（最后一条数据：2026-06-26），需要自动化。

## 目标

自动抓取 channels.weixin.qq.com（视频号助手）上最新视频的数据，写入
`dashboard-data.json`，使 opposition 面板自动更新。

## 数据流

```
channels.weixin.qq.com
    │  Playwright 自动抓取
    ▼
engine/wechat_video_scraper.py
    │  写入 JSON
    ▼
⚙️ 反哺弧/看板/dashboard-data.json
    │  opposition 读取
    ▼
审批面板 (http://127.0.0.1:8765/dashboard/)
```

## 组件设计

### `engine/wechat_video_scraper.py`

Playwright 爬虫，单文件模块。

**能力：**
- Cookie 持久化管理（首次扫码 → 保存 → 复用）
- 登录态检测（过期自动提醒重新扫码）
- 视频列表数据提取
- 热评提取（最新视频下点赞最高的评论）
- 写入 dashboard-data.json（追加新记录，不覆盖旧数据）

**状态文件：**
- `engine/data/wechat_cookies.json` — Playwright cookie 存储
- `engine/data/wechat_scraper_state.json` — 最后抓取的视频 ID/时间

### 数据映射

| 视频号助手字段 | dashboard-data.json 字段 | 来源 |
|---|---|---|
| 作品标题 | `title` | 作品列表页 |
| 播放量 | `plays` | 作品列表页 |
| 完播率 | `completionRate` | 作品列表页 |
| 平均观看时长(秒) | `avgWatchTime` | 作品列表页 |
| 3秒留存率 | `retention3s` | 作品列表页 |
| 点赞 | `likes` | 作品列表页 |
| 评论数 | `comments` | 作品列表页 |
| 新增关注 | `follows` | 作品列表页 |
| 分享 | `shares` | 作品列表页 |
| 视频时长(秒) | `duration` | 作品列表页 |
| 视频ID | `id` | 作品列表页（视频URL） |
| 发布日期 | `date` | 作品列表页 |
| 创建时间 | `createdAt` | ISO 格式时间戳 |
| 热评第一 | `topComment` | 点击视频进入详情获取 |

### 调度策略

- **检查间隔：** 每 2 小时
- **触发条件：** 检测到新视频（ID 不在已有记录中）→ 抓取
- **无新视频：** 跳过，更新轮询时间
- **运行方式：** 集成到引擎服务器的后台线程（类似 FlomoSync）

### Cookie 生命周期

1. 首次运行 → Playwright 打开 channels.weixin.qq.com → 显示二维码
2. 用户扫码 → Playwright 捕获完整 cookie context → 保存到文件
3. 后续运行 → 加载 cookie → 登录态有效 → 正常抓取
4. 登录态过期 → Playwright 检测到跳转到登录页 → 重新弹二维码

## 文件清单

新增文件：
- `engine/wechat_video_scraper.py` — 爬虫主模块

修改文件：
- `engine/server.py` — 启动时初始化爬虫调度器

状态/数据文件：
- `engine/data/wechat_cookies.json` — 浏览器 cookie
- `engine/data/wechat_scraper_state.json` — 抓取状态
- `⚙️ 反哺弧/看板/dashboard-data.json` — 已存在，追加数据

## 风险与约束

- 微信 cookie 有效期不定（数天~数周），过期需用户重新扫码
- 视频号助手页面 DOM 结构可能随微信更新变化，需要维护
- 爬虫使用 headed 模式（首次扫码）和 headless 模式（后续运行）
- Playwright 需要系统安装 Chromium
