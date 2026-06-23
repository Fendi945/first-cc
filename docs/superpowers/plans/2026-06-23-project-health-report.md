# 项目健康检查报告 — 2026-06-23

> 由多 Agent 工作流生成：5 路并行审查 + 1 路报告合成
> 耗时 31 秒，61 项发现

## 🟢 整体健康概览

| 模块 | 状态 | 一句话总结 |
|------|------|-----------|
| 飞书集成模块 | 🔴 有问题 | 5 个 HIGH 问题导致数据一致性严重受损，字段定义缺失和同步竞争条件为最大隐患 |
| video-pipeline | 🟡 需关注 | CORRECTIONS 字典被重复定义导致 Whisper 错字修正完全失效，硬编码路径影响可移植性 |
| Flomo + WeChat Push 模块 | 🔴 有问题 | 微信 APP_SECRET 硬编码在三份推送文件中，Flomo 凭据文件未受 .gitignore 保护 |
| Build & Deployment | 🔴 有问题 | exe_launcher.py 硬编码绝对路径导致打包后无法分发，PS1 脚本全部路径硬编码 |
| 全项目健康审查 | 🟡 需关注 | 嵌套 Git 仓库未配子模块影响可克隆性，缺失 README 和依赖清单，安全合规待加强 |

## 📊 统计

| 指标 | 数量 |
|------|------|
| 总发现数 | **61** |
| HIGH 严重度 | **16** |
| MEDIUM 严重度 | **23** |
| LOW 严重度 | **22** |
| 🔴 有问题的模块 | 3 |
| 🟡 需关注的模块 | 2 |
| 🟢 健康的模块 | 0 |

---

## 各模块详情

### 飞书集成模块 🔴

**总结**：模块架构清晰但健壮性不足，多个数据一致性问题需优先修复。

**HIGH 严重度发现：**

1. **BITABLE_DEFS 缺少「标题」字段定义** — `engine/feishu_bitable_sync.py`
   - `BITABLE_DEFS` 中「成品区发布物」和「口播文档」的 fields 均未定义「标题」。第 318 行对所有 bitable 硬编码写入「标题」，而「公众号&视频号数据」表实际字段名为「作品标题」。
   - **修复**：在 BITABLE_DEFS 显式声明标题字段名，写入时根据 bitable_name 动态选择。

2. **双向同步存在数据竞争，飞书端变更被静默覆盖** — `engine/feishu_kanban_sync.py`
   - `sync_all()` 先 push 再 pull。push 无条件覆盖飞书端同期变更，后续 pull 发现 status 一致则跳过。
   - **修复**：实现基于时间戳的冲突检测，或改为先 pull 再 push。

3. **重复上传文件到飞书云空间** — `engine/feishu_bitable_sync.py`
   - `sync_bitable()` 无条件执行 `upload_file`，每次同步产生新文件副本。
   - **修复**：在状态文件中记录已上传的 file_token，同步前检查。

4. **缺少请求重试和 API 限流处理** — `engine/feishu_client.py`
   - `FeishuClient._request()` 未处理 429 或 5xx 错误。飞书 API 通常限制 100 QPS。
   - **修复**：添加指数退避重试（1s/2s/4s/8s，最多 3-4 次）。

5. **401 响应后未清除缓存的 token** — `engine/feishu_client.py`
   - `_request()` 收到 401 时不清理 `self._token`，后续请求持续失败。
   - **修复**：检测 401 时将 token 置为 None 并自动重试一次。

6. **状态文件读写存在 TOCTOU 竞争条件** — `engine/feishu_kanban_sync.py`
   - `sync_feishu_to_local()` 读 PENDING_FILE → API 调用 → 写回文件，期间 server.py 可能并发修改。
   - **修复**：使用文件锁（portalocker 或 threading.Lock）保护。

---

### video-pipeline 🟡

**总结**：核心功能完整，但存在一个致命 bug 导致字幕错字无法修正。

**HIGH 严重度发现：**

1. **CORRECTIONS 字典被重复定义覆盖** — `video-project/sub_agent.py`
   - 第 74-113 行定义了完整字典（含「裁老」→「拆了」等），但第 140-163 行第二个赋值完全覆盖它。FONT_COLOR、BLUR_RADIUS 等常量同样被重复定义。
   - **修复**：删除第 116-163 行的重复定义块。

2. **硬编码绝对路径** — `video-project/sub_agent.py`、`gen_covers.sh`、`gen_cards.py`
   - `ORIGINAL_VIDEO` 和 `OUTPUT_DIR` 硬编码 `D:\Documents\Desktop\...`，包含用户名。
   - **修复**：使用命令行参数或环境变量提供路径。

---

### Flomo + WeChat Push 模块 🔴

**总结**：硬编码凭证泄露风险，架构上存在重复实现。

**HIGH 严重度发现：**

1. **微信 APP_SECRET 硬编码在三份推送文件中** — `push_wechat.py`、`push_wechat_yuyan.py`、`push_wx.mjs`
   - 硬编码值（`a8b1e6dce37e3994884722538c6d76b3`）与 .env 中的值不同，两套不一致。
   - **修复**：删除硬编码凭据，改为环境变量读取；统一走 `engine/wechat_publisher.py`。

2. **Flomo OAuth 凭据文件未加入 .gitignore** — `flomo_client.json`、`flomo_token.json`
   - 包含 `registration_access_token`、JWT `access_token`、`refresh_token`。
   - **修复**：立即加入 .gitignore。

---

### Build & Deployment 🔴

**总结**：exe_launcher.py 硬编码绝对路径导致构建产物无法分发。

**HIGH 严重度发现：**

1. **exe_launcher.py 硬编码项目根路径** — `engine/exe_launcher.py`
   - `PROJECT_ROOT = r"C:\Users\Administrator\Documents\trae_projects\first cc"`
   - **修复**：改用 `sys.executable`（frozen 模式）或 `__file__` 推导。

2. **build_exe.py 缺少 hidden-imports** — `scripts/build_exe.py`
   - PyInstaller 可能遗漏 `engine.config`、`engine.server`、`dotenv` 等动态导入。
   - **修复**：添加 `--hidden-import=engine.config --hidden-import=engine.server --hidden-import=dotenv`。

3. **PowerShell 脚本路径全部硬编码** — `scripts/create_shortcut.ps1`
   - 所有路径硬编码 `D:\Documents\Desktop\`、`C:\Users\Administrator\`。
   - **修复**：使用 `$PSScriptRoot` 推导项目根目录。

4. **exe_launcher.py 硬编码 Edge 浏览器路径** — `engine/exe_launcher.py`
   - 硬编码 `msedge.exe` 的两个可能安装路径。
   - **修复**：使用 `shutil.which('msedge')` 或 Windows 注册表查询。

---

### 全项目健康审查 🟡

**总结**：项目架构模块清晰，但嵌套 Git 和凭据管理存在隐患。

**HIGH 严重度发现：**

1. **嵌套 Git 仓库未配置为子模块** — `four-quadrants/` 和 `pomodoro-timer/`
   - 以 gitlink 形式存在于索引中，无 `.gitmodules` 文件，他人克隆无法获得代码。
   - **修复**：方案 A — 注册为正式子模块；方案 B — 迁入主仓库。

2. **Flomo OAuth 凭据文件未加入 .gitignore** — `flomo_client.json`、`flomo_token.json`、`flomo_state.json`
   - **修复**：立即加入 .gitignore。

3. **二进制测试文件未加入 .gitignore** — `test_out.mp4`（687KB）、`test_chinese.png`（22KB）
   - **修复**：根 .gitignore 添加 `*.mp4`、`*.png` 等媒体文件模式。

---

## 📋 紧急修复清单（16 个 HIGH）

| 优先级 | 模块 | 标题 | 文件 |
|--------|------|------|------|
| 🔴 P0 | Flomo+微信 | 微信 APP_SECRET 硬编码 | `push_wechat.py` 等 3 文件 |
| 🔴 P0 | 全项目 | Flomo 凭据文件未 .gitignore | `flomo_client.json` 等 |
| 🔴 P0 | 全项目 | 二进制测试文件未 .gitignore | `test_out.mp4` 等 |
| 🔴 P0 | 全项目 | 嵌套 Git 仓库未配子模块 | `four-quadrants/`, `pomodoro-timer/` |
| 🟠 P1 | 飞书 | BITABLE_DEFS 缺少标题字段 | `feishu_bitable_sync.py` |
| 🟠 P1 | 飞书 | 双向同步数据竞争 | `feishu_kanban_sync.py` |
| 🟠 P1 | 飞书 | 重复上传文件 | `feishu_bitable_sync.py` |
| 🟠 P1 | 飞书 | 缺少限流重试 | `feishu_client.py` |
| 🟠 P1 | 飞书 | 401 不清理 token | `feishu_client.py` |
| 🟠 P1 | 飞书 | TOCTOU 竞争条件 | `feishu_kanban_sync.py` |
| 🟠 P1 | 视频 | CORRECTIONS 字典被覆盖 | `sub_agent.py` |
| 🟠 P1 | 视频 | 硬编码绝对路径 | `sub_agent.py` 等 |
| 🟡 P2 | 构建 | exe_launcher 硬编码根路径 | `exe_launcher.py` |
| 🟡 P2 | 构建 | build_exe 缺少 hidden-imports | `build_exe.py` |
| 🟡 P2 | 构建 | PS1 脚本路径硬编码 | `create_shortcut.ps1` |
| 🟡 P2 | 构建 | exe_launcher 硬编码 Edge 路径 | `exe_launcher.py` |

## ✅ 做得好的地方

- 飞书模块架构清晰，**FeishuClient** 实现了 token 缓存和自动续期
- 视频流水线裁剪+字幕烧录一次编码完成，性能优化到位
- 利用 MediaPipe 实现人物分割+背景模糊，方案成熟
- .gitignore 已包含 .env、wechat_token_cache.json 等常见敏感文件
- 凭据尚未被提交到 git 历史（均为 untracked 状态）
- build_exe.py 已实现安全检测（验证 DIST_DIR 在桌面下）
- website 视觉风格统一，审美在线
- 项目迭代活跃，自动化能力丰富（Flomo/飞书/微信/Dashboard）
