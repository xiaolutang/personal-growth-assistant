"""日志配置模块"""

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.logging.handler import SQLiteLogHandler
    from app.infrastructure.logging.storage import LogStorage

# 全局 SQLite Handler 引用
_sqlite_handler: "SQLiteLogHandler" = None
_log_storage: "LogStorage" = None


def setup_logging(
    level: str = "INFO",
    log_storage: "LogStorage" = None,
) -> "SQLiteLogHandler":
    """
    配置日志系统

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_storage: 日志存储实例

    Returns:
        SQLiteLogHandler 实例，用于后续关闭
    """
    global _sqlite_handler, _log_storage

    _log_storage = log_storage

    # 获取 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除已有的 handlers
    root_logger.handlers.clear()

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # SQLite Handler（如果提供了存储）
    if log_storage:
        from app.infrastructure.logging.handler import SQLiteLogHandler

        _sqlite_handler = SQLiteLogHandler(
            storage=log_storage,
            batch_size=100,
            flush_interval=1.0,
        )
        _sqlite_handler.setLevel(logging.DEBUG)  # 记录所有级别
        root_logger.addHandler(_sqlite_handler)

    return _sqlite_handler


def get_log_storage() -> "LogStorage":
    """获取日志存储实例"""
    return _log_storage


def get_sqlite_handler() -> "SQLiteLogHandler":
    """获取 SQLite Handler 实例"""
    return _sqlite_handler


def shutdown_logging():
    """关闭日志系统"""
    global _sqlite_handler

    if _sqlite_handler:
        _sqlite_handler.flush()
        _sqlite_handler.close()
        _sqlite_handler = None
