"""微信视频号数据自动抓取 — Playwright 爬虫。

用法:
    # 首次运行（弹出浏览器扫码）
    python -m engine.wechat_video_scraper

    # 查看状态
    python -m engine.wechat_video_scraper --status

    # 强制重新扫码
    python -m engine.wechat_video_scraper --force-login

架构:
    - Cookie 持久化: engine/data/wechat_cookies.json
    - 状态文件: engine/data/wechat_scraper_state.json
    - 写入目标: ⚙️ 反哺弧/看板/dashboard-data.json
"""

import json
import logging
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from engine.config import PROJECT_ROOT

logger = logging.getLogger("wechat_scraper")

# ── 路径 ──
DATA_DIR = PROJECT_ROOT / "engine" / "data"
COOKIE_FILE = DATA_DIR / "wechat_cookies.json"
STATE_FILE = DATA_DIR / "wechat_scraper_state.json"
DEBUG_HTML = DATA_DIR / "_wechat_debug.html"

# ── 视频号助手 ──
CHANNELS_URL = "https://channels.weixin.qq.com/"


def _find_dashboard_json() -> Path:
    """定位 vault 中的 dashboard-data.json。"""
    try:
        from engine.config import KANBAN_DIR
        path = KANBAN_DIR / "dashboard-data.json"
        if path.exists():
            return path
    except Exception:
        pass

    env_vault = os.getenv("VAULT_PATH", "")
    if env_vault:
        p = Path(env_vault) / "⚙️ 反哺弧" / "看板" / "dashboard-data.json"
        if p.exists():
            return p

    return Path(
        r"D:\Documents\Documents\Obsidian Vault\🧠 元演心智"
        r"\⚙️ 反哺弧\看板\dashboard-data.json"
    )


class WeChatVideoScraper:
    """微信视频号数据爬虫。

    1. 首次运行 → headed 浏览器 → 扫码 → 保存 cookie
    2. 后续运行 → 加载 cookie → 导航到视频列表 → 提取最新视频 → 写 dashboard-data.json
    3. 每 interval 秒后台检查一轮
    """

    def __init__(self, interval: int = 7200):
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_check_time: Optional[str] = None
        self.last_error: Optional[str] = None
        self.sync_count: int = 0
        self._needs_login: bool = False
        self._dashboard_json: Path = _find_dashboard_json()

    # ── Cookie ──

    def _cookies_exist(self) -> bool:
        return COOKIE_FILE.exists() and COOKIE_FILE.stat().st_size > 10

    def _save_cookies(self, context) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        cookies = context.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Cookie 已保存 (%d 条)", len(cookies))

    def _load_cookies_to(self, context) -> int:
        if not self._cookies_exist():
            return 0
        cookies = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
        if cookies:
            context.add_cookies(cookies)
        logger.info("已加载 %d 条 cookie", len(cookies))
        return len(cookies)

    # ── 状态 ──

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"last_video_id": "", "last_check_time": ""}

    def _save_state(self, **kw):
        state = self._load_state()
        state.update(kw)
        try:
            STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            logger.error("保存状态失败: %s", e)

    # ── 扫码登录 ──

    def _login_flow(self, page, timeout_sec: int = 180) -> bool:
        """带头模式让用户扫码。返回是否登录成功。"""
        logger.info("===== 请在打开的浏览器中用微信扫描二维码 =====")
        page.goto(CHANNELS_URL, timeout=30000)
        time.sleep(4)

        # 已经登录？
        if "login" not in page.url.lower() and page.url.strip("/") != CHANNELS_URL.strip("/"):
            logger.info("检测到已登录（%s）", page.url)
            return True

        # 等用户扫码
        try:
            page.wait_for_url(
                lambda u: "login" not in u.lower() and u.strip("/") != CHANNELS_URL.strip("/"),
                timeout=timeout_sec * 1000,
            )
            logger.info("扫码成功 → %s", page.url)
            return True
        except Exception as e:
            logger.error("扫码超时: %s", e)
            return False

    def _ensure_login(self, page, force_login: bool = False) -> bool:
        """保证登录态有效。"""
        if force_login or not self._cookies_exist():
            self._needs_login = True
            return self._login_flow(page)

        self._load_cookies_to(page.context)
        try:
            page.goto(CHANNELS_URL, timeout=30000, wait_until="domcontentloaded")
            time.sleep(4)
            if "login" in page.url.lower():
                logger.warning("Cookie 过期，需要重新扫码")
                self._needs_login = True
                return self._login_flow(page)
            self._needs_login = False
            logger.info("Cookie 有效，当前页面: %s", page.url)
            return True
        except Exception as e:
            logger.warning("登录检测异常: %s", e)
            self._needs_login = True
            return self._login_flow(page)

    # ── SPA 导航 ──

    def _click_menu_by_text(self, page, text: str, timeout_sec: int = 10) -> bool:
        """点击包含特定文本的菜单项（支持主菜单和子菜单）。"""
        try:
            # 使用 get_by_text 找到元素并点击
            locator = page.get_by_text(text, exact=False).first
            if locator.count() > 0:
                locator.click(timeout=timeout_sec * 1000)
                time.sleep(2)
                logger.info("点击菜单「%s」", text)
                return True
        except Exception as e:
            logger.debug("点击「%s」失败: %s", text, e)

        # fallback: 用 JS 找
        try:
            clicked = page.evaluate(f"""() => {{
                const walker = document.createTreeWalker(document.body, 4, null, false);
                let node;
                while (node = walker.nextNode()) {{
                    if (node.textContent.trim() === '{text}' || node.textContent.trim().startsWith('{text}')) {{
                        node.click();
                        return true;
                    }}
                }}
                return false;
            }}""")
            if clicked:
                time.sleep(2)
                return True
        except Exception:
            pass
        return False

    def _navigate_to_video_list(self, page) -> bool:
        """导航到视频列表（直接访问 SPA 路径）。"""
        # 优先直接导航到已知 URL
        if self._try_direct_urls(page):
            return True

        # 兜底：菜单点击
        try:
            if self._click_menu_by_text(page, "内容管理"):
                if self._click_menu_by_text(page, "视频"):
                    time.sleep(3)
                    logger.info("已进入视频列表页: %s", page.url)
                    return True
        except Exception as e:
            logger.error("菜单导航失败: %s", e)
        return False

    _DIRECT_URLS = [
        "https://channels.weixin.qq.com/platform/post/list",
        "https://channels.weixin.qq.com/platform/content",
        "https://channels.weixin.qq.com/platform",
    ]

    def _try_direct_urls(self, page) -> bool:
        for url in self._DIRECT_URLS:
            try:
                page.goto(url, timeout=15000, wait_until="domcontentloaded")
                # 等待 WuJie Shadow DOM 渲染（需约 6-10 秒）
                time.sleep(10)
                if "login" not in page.url.lower():
                    logger.info("直接导航到: %s", page.url)
                    return True
            except Exception:
                continue
        return False

    # ── 数据提取 ──────────────────────────────────────

    _EXTRACT_JS = """
    () => {
        var w = document.querySelector('wujie-app');
        if (!w || !w.shadowRoot) return [];
        var s = w.shadowRoot;
        var body = s.querySelector('body');
        if (!body) return [];

        var items = body.querySelectorAll('.post-feed-item');
        var results = [];

        for (var i = 0; i < items.length; i++) {
            var item = items[i];
            var titleEl = item.querySelector('.post-title');
            var dateEl = item.querySelector('.time-label');
            var countEls = item.querySelectorAll('.post-data .data-item .count');

            var title = titleEl ? titleEl.textContent.trim() : '';
            var dateText = dateEl ? dateEl.textContent.trim() : '';

            var plays = 0, likes = 0, comments = 0, follows = 0, shares = 0;
            if (countEls.length >= 5) {
                plays = parseInt(countEls[0].textContent.trim()) || 0;
                likes = parseInt(countEls[1].textContent.trim()) || 0;
                comments = parseInt(countEls[2].textContent.trim()) || 0;
                follows = parseInt(countEls[3].textContent.trim()) || 0;
                shares = parseInt(countEls[4].textContent.trim()) || 0;
            }

            // 生成唯一 ID
            var cleanTitle = title.replace(/[^0-9a-zA-Z\\u4e00-\\u9fa5]/g, '').substring(0, 20);
            var id = 'wx_' + cleanTitle + '_' + dateText.substring(0, 10);

            results.push({
                title: title,
                date: dateText,
                plays: plays,
                likes: likes,
                comments: comments,
                follows: follows,
                shares: shares,
                id: id
            });
        }
        return results;
    }
    """

    def _extract_video_list(self, page) -> list[dict]:
        """从 WuJie Shadow DOM 的视频列表页提取每条视频数据。
        结构: .post-feed-item → .post-title + .time-label + .post-data .data-item .count x5
        """
        videos = page.evaluate(self._EXTRACT_JS)
        logger.info("提取到 %d 条视频数据", len(videos))
        if videos:
            for v in videos[:3]:
                logger.info("  %s | %s | %d播放 %d赞 %d评",
                            v["title"][:30], v["date"][:12],
                            v["plays"], v["likes"], v["comments"])
        return videos

    # ── 热评提取 ──

    def _extract_top_comment(self, page) -> str:
        """从当前页面（视频详情）提取点赞最高的评论。"""
        try:
            comments = page.evaluate("""() => {
                const sel = [
                    '[class*="comment-item"] [class*="content"]',
                    '[class*="comment"] [class*="text"]',
                    '[class*="CommentItem"]',
                    '[class*="reply-item"]',
                ];
                for (const s of sel) {
                    const els = document.querySelectorAll(s);
                    if (els.length > 0) {
                        const texts = Array.from(els).slice(0, 3).map(e => e.textContent.trim());
                        return {found: true, comments: texts};
                    }
                }
                return {found: false};
            }""")
            if comments.get("found"):
                for c in comments.get("comments", []):
                    if c:
                        logger.info("热评: %s", c[:100])
                        return c
        except Exception as e:
            logger.warning("提取热评失败: %s", e)
        return ""

    # ── dashboard-data.json ──

    def _read_dashboard(self) -> dict:
        if self._dashboard_json.exists():
            try:
                return json.loads(self._dashboard_json.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"data": [], "exportedAt": "", "updatedAt": ""}

    def _write_dashboard(self, data: dict):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        data["updatedAt"] = now
        data["exportedAt"] = now
        self._dashboard_json.parent.mkdir(parents=True, exist_ok=True)
        self._dashboard_json.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("dashboard-data.json 已更新 (%d 条)", len(data.get("data", [])))

    # ── 主流程 ──

    def fetch_latest(self, force_login: bool = False) -> dict:
        """一次完整抓取。返回 {success, new_video, title, error, page_saved}。"""
        from playwright.sync_api import sync_playwright

        result = {"success": False, "new_video": False, "title": "", "error": "", "page_saved": False}

        try:
            headless = not force_login and self._cookies_exist() and not self._needs_login
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )
                page = context.new_page()

                # 登录
                if not self._ensure_login(page, force_login=force_login):
                    result["error"] = "登录失败"
                    browser.close()
                    return result

                self._save_cookies(context)

                # 导航到视频列表
                if not self._navigate_to_video_list(page):
                    result["error"] = "导航到视频列表失败"
                    browser.close()
                    return result

                # 保存页面 HTML 供分析
                raw = page.content()
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                DEBUG_HTML.write_text(raw, encoding="utf-8")
                result["page_saved"] = True

                # 提取视频数据
                videos = self._extract_video_list(page)

                if not videos:
                    logger.warning("未提取到视频数据，调试 HTML 保存到 %s", DEBUG_HTML)
                    result["error"] = "未提取到视频数据"
                    browser.close()
                    return result

                # 最新视频
                latest = videos[0]
                video_id = latest.get("id", "")
                video_title = latest.get("title", "")

                if not video_id:
                    result["error"] = "视频缺少 ID"
                    browser.close()
                    return result

                # 去重
                if not self._has_new_video(video_id):
                    logger.info("无新视频（最新: %s）", video_title)
                    result["success"] = True
                    result["new_video"] = False
                    result["title"] = video_title
                    browser.close()
                    self._save_state(last_video_id=video_id)
                    return result

                # 将中文日期转为 ISO 日期
                raw_date = latest.get("date", "")
                date_iso = raw_date[:10].replace("年", "-").replace("月", "-").replace("日", "")

                # 写入 dashboard
                data = self._read_dashboard()
                record = {
                    "date": date_iso or datetime.now().strftime("%Y-%m-%d"),
                    "title": video_title,
                    "plays": latest.get("plays", 0),
                    "completionRate": 0,   # 暂不可得
                    "avgWatchTime": 0,     # 暂不可得
                    "retention3s": 0,      # 暂不可得
                    "likes": latest.get("likes", 0),
                    "comments": latest.get("comments", 0),
                    "follows": latest.get("follows", 0),
                    "shares": latest.get("shares", 0),
                    "duration": 0,         # 暂不可得
                    "id": video_id,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }

                data["data"].append(record)
                self._write_dashboard(data)

                self.sync_count += 1
                self.last_error = None
                self._save_state(last_video_id=video_id)

                logger.info("新视频已抓取: %s", video_title)
                result["success"] = True
                result["new_video"] = True
                result["title"] = video_title
                browser.close()
                return result

        except Exception as e:
            error_msg = f"抓取异常: {type(e).__name__}: {e}"
            logger.error(error_msg)
            self.last_error = error_msg
            result["error"] = error_msg
            return result

    def _has_new_video(self, video_id: str) -> bool:
        data = self._read_dashboard()
        for r in data.get("data", []):
            if r.get("id") == video_id:
                return False
        return True

    # ── 后台调度 ──

    def start_scheduler(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="wechat-scraper")
        self._thread.start()
        logger.info("微信视频号爬虫调度已启动，间隔 %d 秒", self.interval)

    def stop_scheduler(self):
        self._running = False

    def _run_loop(self):
        if not self._cookies_exist():
            self._needs_login = True
            self.fetch_latest(force_login=True)
        while self._running:
            force = self._needs_login
            self.fetch_latest(force_login=force)
            self._needs_login = False
            for _ in range(self.interval // 10):
                if not self._running:
                    return
                time.sleep(10)

    # ── 状态 ──

    def get_status(self) -> dict:
        state = self._load_state()
        return {
            "running": self._running,
            "cookies_exist": self._cookies_exist(),
            "needs_login": self._needs_login,
            "interval": self.interval,
            "last_check_time": state.get("last_check_time", ""),
            "last_video_id": state.get("last_video_id", ""),
            "last_error": self.last_error,
            "sync_count": self.sync_count,
            "dashboard_json": str(self._dashboard_json),
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="微信视频号数据抓取")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--force-login", action="store_true", help="强制重新扫码")
    args = parser.parse_args()

    if args.status:
        s = WeChatVideoScraper()
        print(json.dumps(s.get_status(), ensure_ascii=False, indent=2))
        return

    scraper = WeChatVideoScraper()
    result = scraper.fetch_latest(force_login=args.force_login)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
