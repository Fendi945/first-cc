"""统一日志配置工具 —— 提供一致的日志格式和级别管理。

用法:
    from engine.log_utils import setup_logging, get_logger

    setup_logging()              # 在程序入口调用一次
    logger = get_logger("server")
    logger.info("服务已启动")
"""

import logging
import sys
from typing import Optional


# 日志格式：时间 [级别] [模块名] 消息
CONSOLE_FORMAT = "%(asctime)s [%(levelname)-5s] [%(name)s] %(message)s"
DATE_FORMAT = "%H:%M:%S"

# 日志级别映射（环境变量友好）
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

_root_configured = False


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> None:
    """配置根 logger 的格式和级别（全局调用一次即可）。

    Args:
        level: 日志级别，默认 logging.INFO
        log_file: 可选日志文件路径，指定后同时写入文件
    """
    global _root_configured
    if _root_configured:
        return
    _root_configured = True

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有 handler，防止重复
    root_logger.handlers.clear()

    # 控制台 handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(CONSOLE_FORMAT, datefmt=DATE_FORMAT))
    root_logger.addHandler(console)

    # 可选的日志文件 handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)-5s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """获取带模块名的 logger。

    在模块级别调用:
        logger = get_logger("module_name")
    """
    return logging.getLogger(name)


__all__ = ["setup_logging", "get_logger"]
