"""元演心智 · AI 自动化引擎入口。

用法：
  python -m engine.main          # 启动 watchdog 持续监控
  python -m engine.main --scan   # 只扫描已有文件，不启动 watchdog
"""

import sys
from engine.config import DEEPSEEK_API_KEY


def main():
    # 检查 API Key 是否已配置
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your-api-key-here":
        print("❌ 请先在 .env 中配置 DEEPSEEK_API_KEY")
        sys.exit(1)

    from engine.watchdog import scan_existing, start_watchdog

    if "--scan" in sys.argv:
        print("🔍 扫描已有日输入文件...")
        scan_existing()
        print("\n✅ 扫描完成")
    else:
        # 启动前先扫描已有文件
        print("🔍 启动前扫描已有文件...")
        scan_existing()
        print()
        start_watchdog()


if __name__ == "__main__":
    main()
