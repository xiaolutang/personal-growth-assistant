"""SQLite 日志 Handler - 异步批量写入"""

import atexit
import json
import logging
import queue
import threading
import traceback
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

from app.infrastructure.logging.storage import LogStorage


class SQLiteLogHandler(logging.Handler):
    """
    SQLite 日志处理器

    特性：
    - 使用队列异步写入，避免阻塞主线程
    - 支持批量写入（默认 100 条）
    - 进程退出时自动 flush
    """

    def __init__(
        self,
        storage: LogStorage,
        batch_size: int = 100,
        flush_interval: float = 1.0,
    ):
        super().__init__()
        self.storage = storage
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._queue: queue.Queue[Optional[dict[str, Any]]] = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 启动后台写入线程
        self._start_worker()

        # 注册退出处理
        atexit.register(self.close)

    def _start_worker(self):
        """启动后台写入线程"""
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def _worker_loop(self):
        """后台写入循环"""
        batch: list[dict[str, Any]] = []

        while not self._stop_event.is_set():
            try:
                # 等待新日志或超时
                try:
                    log = self._queue.get(timeout=self.flush_interval)
                    if log is not None:
                        batch.append(log)
                except queue.Empty:
                    pass

                # 批量写入条件：达到批量大小 或 超时
                if len(batch) >= self.batch_size or (
                    batch and self._queue.empty()
                ):
                    self._flush_batch(batch)
                    batch = []

            except Exception as e:
                # 避免日志系统本身的错误导致崩溃
                print(f"[SQLiteLogHandler] Error in worker loop: {e}")

        # 退出前写入剩余日志
        if batch:
            self._flush_batch(batch)

    def _flush_batch(self, batch: list[dict[str, Any]]):
        """批量写入日志"""
        try:
            self.storage.insert_logs(batch)
        except Exception as e:
            print(f"[SQLiteLogHandler] Error flushing batch: {e}")

    def emit(self, record: logging.LogRecord):
        """处理日志记录"""
        try:
            log_entry = self._record_to_dict(record)
            self._queue.put(log_entry)
        except Exception:
            self.handleError(record)

    def _record_to_dict(self, record: logging.LogRecord) -> dict[str, Any]:
        """将 LogRecord 转换为字典"""
        # 获取异常信息
        exc_info = record.exc_info
        exception_type = None
        exception_message = None
        stack_trace = None

        if exc_info and exc_info[0] is not None:
            exception_type = exc_info[0].__name__
            exception_message = str(exc_info[1])
            stack_trace = "".join(traceback.format_exception(*exc_info))

        # 获取额外字段
        extra: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "message",
                "taskName",
                # 自定义字段
                "request_id",
                "method",
                "path",
                "status_code",
                "process_time_ms",
                "client_ip",
            }:
                try:
                    # 确保值可序列化
                    json.dumps({key: value})
                    extra[key] = value
                except (TypeError, ValueError):
                    extra[key] = str(value)

        return {
            "level": record.levelname,
            "message": self.format(record),
            "logger_name": record.name,
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "request_id": getattr(record, "request_id", None),
            "method": getattr(record, "method", None),
            "path": getattr(record, "path", None),
            "status_code": getattr(record, "status_code", None),
            "process_time_ms": getattr(record, "process_time_ms", None),
            "client_ip": getattr(record, "client_ip", None),
            "exception_type": exception_type,
            "exception_message": exception_message,
            "stack_trace": stack_trace,
            "extra": extra if extra else None,
        }

    def close(self):
        """关闭处理器"""
        self._stop_event.set()
        # 发送 None 信号让 worker 退出
        self._queue.put(None)
        if self._worker:
            self._worker.join(timeout=5)
        super().close()

    def flush(self):
        """强制刷新（等待队列清空）"""
        while not self._queue.empty():
            import time

            time.sleep(0.1)
