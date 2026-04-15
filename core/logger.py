"""
应用日志模块
提供统一的日志记录功能，支持：
- 控制台输出（INFO 级别，带颜色）
- 文件输出（DEBUG 级别，滚动保留最近 10MB）
- 结构化格式：时间 | 级别 | 模块 | 消息

日志文件：logs/app.log（自动创建，按大小滚动）
"""

import os
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "app.log")

# 日志格式
_FORMATTER = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def setup_logger(name: str = "growthloop", level: int = logging.DEBUG) -> logging.Logger:
    """
    创建或获取日志记录器。

    Args:
        name: 记录器名称（通常用模块名）
        level: 日志级别

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 文件 handler（滚动保留，单文件最大 10MB，保留 3 个备份）
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_FORMATTER)
    logger.addHandler(file_handler)

    # 控制台 handler（只输出 INFO 及以上）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(_FORMATTER)
    logger.addHandler(console_handler)

    return logger


# 全局默认记录器
default_logger = setup_logger()


def get_logger(name: str = None) -> logging.Logger:
    """
    获取模块专用记录器。

    用法：
        logger = get_logger("FunnelAgent")
        logger.info("开始漏斗分析")
    """
    if name is None:
        return default_logger
    child_logger = logging.getLogger(f"growthloop.{name}")
    if not child_logger.handlers:
        child_logger.setLevel(logging.DEBUG)
        # 继承父记录器的 handlers
        child_logger.propagate = True
    return child_logger
