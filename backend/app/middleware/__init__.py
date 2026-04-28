"""中间件模块 - 请求日志、请求追踪

全部使用纯 ASGI 实现，避免 BaseHTTPMiddleware 的 body 消费 bug。
错误处理由 main.py 的 @app.exception_handler(Exception) 负责。
"""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# 请求 ID 上下文变量
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# 用户 UID 上下文变量
uid_var: ContextVar[Optional[str]] = ContextVar("uid", default=None)


def get_request_id() -> Optional[str]:
    """获取当前请求的 request_id"""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """设置当前请求的 request_id"""
    request_id_var.set(request_id)


def get_uid() -> Optional[str]:
    """获取当前请求的 uid"""
    return uid_var.get()


logger = logging.getLogger(__name__)


class RequestIDMiddleware:
    """请求 ID 中间件 - 纯 ASGI 实现"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # 从请求头获取或生成新的 request_id
        request_id = None
        uid = None
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                request_id = value.decode("latin-1")
            elif key == b"x-uid":
                uid = value.decode("latin-1")

        if not request_id:
            request_id = str(uuid.uuid4())

        # 设置到上下文
        set_request_id(request_id)
        uid_var.set(uid)

        # 包装 send 以添加响应头
        async def send_with_request_id(message: Message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_request_id)


class RequestLoggingMiddleware:
    """请求日志中间件 - 纯 ASGI 实现"""

    SKIP_PATH_PREFIXES = ("/health", "/favicon")
    SKIP_SUFFIXES = (".js", ".css", ".ico", ".png", ".jpg", ".svg", ".woff", ".woff2")

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        path = scope.get("path", "")
        method = scope.get("method", "")
        request_id = get_request_id()

        # 获取客户端 IP
        headers_dict = dict(scope.get("headers", []))
        client_ip = "unknown"
        forwarded = headers_dict.get(b"x-forwarded-for")
        if forwarded:
            client_ip = forwarded.decode("latin-1").split(",")[0].strip()
        else:
            real_ip = headers_dict.get(b"x-real-ip")
            if real_ip:
                client_ip = real_ip.decode("latin-1")
            elif scope.get("client"):
                client_ip = scope["client"][0]

        should_skip = self._should_skip_logging(path)

        if not should_skip:
            extra = {
                "request_id": request_id,
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "uid": uid_var.get(),
            }
            logger.info(f"Request started: {method} {path}", extra=extra)

        status_code = None

        async def send_with_logging(message: Message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status")
                # 添加处理时间头
                pt = int((time.time() - start_time) * 1000)
                headers = list(message.get("headers", []))
                headers.append((b"x-process-time", f"{pt}ms".encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
        except Exception as e:
            process_time_ms = int((time.time() - start_time) * 1000)
            if not should_skip:
                extra = {
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                    "status_code": 500,
                    "process_time_ms": process_time_ms,
                    "uid": uid_var.get(),
                }
                logger.error(
                    f"Request failed: {method} {path} - Error after {process_time_ms}ms: {e}",
                    extra=extra,
                    exc_info=True,
                )
            raise

        process_time_ms = int((time.time() - start_time) * 1000)
        if not should_skip and status_code is not None:
            extra = {
                "request_id": request_id,
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "status_code": status_code,
                "process_time_ms": process_time_ms,
                "uid": uid_var.get(),
            }
            logger.info(
                f"Request completed: {method} {path} - {status_code} ({process_time_ms}ms)",
                extra=extra,
            )

    def _should_skip_logging(self, path: str) -> bool:
        """检查是否应该跳过日志记录"""
        return (
            any(path.startswith(p) for p in self.SKIP_PATH_PREFIXES)
            or any(path.endswith(s) for s in self.SKIP_SUFFIXES)
        )


def setup_middlewares(app):
    """配置中间件（全部纯 ASGI，无 BaseHTTPMiddleware）"""
    # 注意：FastAPI 的中间件顺序是后添加的先执行
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
