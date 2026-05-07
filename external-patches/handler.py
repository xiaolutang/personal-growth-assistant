"""RemoteLogHandler: logging.Handler that batches and sends logs via HTTP.

修复：使用 urllib.request 替代 httpx，避免 httpx 内部 asyncio 事件循环
在守护线程中出现 epoll(timeout=0) 忙轮询导致 CPU 100% 的问题。
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from log_service_sdk.constants import DEFAULT_COMPONENT


class RemoteLogHandler(logging.Handler):
    """A logging handler that batches log records and sends them to a remote
    log-service via HTTP POST.

    - Non-blocking: ``emit()`` puts records into an in-memory queue.
    - A daemon worker thread drains the queue and sends batches.
    - Flush on ``batch_size`` or every ``flush_interval`` seconds.
    - Retries with exponential back-off on failure (up to ``max_retries``).
    - ``close()`` / ``flush()`` ensure remaining records are sent before exit.
    """

    def __init__(
        self,
        endpoint: str,
        service_name: str,
        component: str = DEFAULT_COMPONENT,
        batch_size: int = 50,
        flush_interval: float = 2.0,
        max_retries: int = 3,
        level: int = logging.NOTSET,
    ) -> None:
        super().__init__(level)
        self.endpoint = endpoint.rstrip("/")
        self.service_name = service_name
        self.component = component
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_retries = max_retries
        self._consecutive_failures = 0

        self._queue: queue.Queue[logging.LogRecord | None] = queue.Queue()
        self._shutdown_event = threading.Event()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    # ------------------------------------------------------------------
    # logging.Handler interface
    # ------------------------------------------------------------------

    def emit(self, record: logging.LogRecord) -> None:
        """Enqueue a log record without blocking the caller."""
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            # Drop the record rather than blocking the business thread.
            pass

    def flush(self) -> None:
        """Immediately send everything currently in the queue."""
        batch: list[logging.LogRecord] = []
        while True:
            try:
                record = self._queue.get_nowait()
            except queue.Empty:
                break
            if record is not None:
                batch.append(record)
        if batch:
            self._send_batch(batch)

    def close(self) -> None:
        """Flush remaining records and stop the worker thread."""
        # Signal the worker to stop.
        self._shutdown_event.set()
        # Put a sentinel so the worker wakes up immediately.
        self._queue.put(None)
        self._worker.join(timeout=10)
        # Flush anything the worker didn't consume.
        self.flush()
        super().close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        """Background thread: accumulate records and send in batches."""
        batch: list[logging.LogRecord] = []
        last_send = time.monotonic()

        while not self._shutdown_event.is_set() or not self._queue.empty():
            timeout = max(0.0, self.flush_interval - (time.monotonic() - last_send))
            try:
                record = self._queue.get(timeout=timeout)
            except queue.Empty:
                # Timed out – flush if we have anything.
                if batch:
                    self._send_batch(batch)
                    batch = []
                last_send = time.monotonic()
                continue

            if record is None:
                # Sentinel – flush and continue to drain.
                if batch:
                    self._send_batch(batch)
                    batch = []
                    last_send = time.monotonic()
                continue

            batch.append(record)
            if len(batch) >= self.batch_size:
                self._send_batch(batch)
                batch = []
                last_send = time.monotonic()

        # Final drain after shutdown signal.
        if batch:
            self._send_batch(batch)

    def _send_batch(self, batch: list[logging.LogRecord]) -> None:
        """Send a batch of records with exponential-back-off retry."""
        # 连续失败时减少重试避免 DNS 风暴
        effective_retries = max(
            0, self.max_retries - min(self._consecutive_failures, self.max_retries)
        )

        logs = [self._record_to_dict(r) for r in batch]
        payload: dict[str, Any] = {
            "service_name": self.service_name,
            "component": self.component,
            "logs": logs,
        }

        url = f"{self.endpoint}/api/logs/ingest"
        data = json.dumps(payload, default=str).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        for attempt in range(effective_retries + 1):
            try:
                resp = urllib.request.urlopen(req, timeout=5)
                if resp.status < 300:
                    self._consecutive_failures = 0
                    return
            except Exception:
                if attempt == effective_retries:
                    self._consecutive_failures += 1
                    return
                backoff = 0.5 * (2 ** attempt)
                time.sleep(backoff)

    @staticmethod
    def _record_to_dict(record: logging.LogRecord) -> dict[str, Any]:
        """Convert a ``logging.LogRecord`` to the API's ``IngestLogEntry`` dict."""
        entry: dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "logger_name": record.name,
        }

        # Optional HTTP fields (set via ``extra={...}`` in the logger call).
        for field in (
            "request_id",
            "method",
            "path",
            "status_code",
            "process_time_ms",
            "client_ip",
            "uid",
        ):
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value

        # Exception info.
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception_type"] = record.exc_info[0].__name__
            entry["exception_message"] = str(record.exc_info[1])

        if record.exc_text:
            entry["stack_trace"] = record.exc_text

        # Arbitrary extra metadata.
        extra_fields = getattr(record, "extra", None)
        if isinstance(extra_fields, dict):
            entry["extra"] = extra_fields

        return entry
