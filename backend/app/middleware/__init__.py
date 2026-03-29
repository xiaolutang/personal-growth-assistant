"""中间件模块 - 错误处理、请求日志、请求追踪"""

import logging
import time
import traceback
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

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


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求 ID 中间件 - 为每个请求分配唯一 ID"""

    async def dispatch(self, request: Request, call_next):
        # 从请求头获取或生成新的 request_id
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 从请求头获取 uid（匿名用户标识）
        uid = request.headers.get("X-UID")

        # 设置到上下文
        set_request_id(request_id)
        uid_var.set(uid)

        # 执行请求
        response = await call_next(request)

        # 添加到响应头
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    # 不记录日志的路径前缀
    SKIP_PATH_PREFIXES = (
        "/health",  # 健康检查
        "/favicon",  # 图标
    )

    # 不记录日志的路径后缀（静态资源）
    SKIP_SUFFIXES = (
        ".js",
        ".css",
        ".ico",
        ".png",
        ".jpg",
        ".svg",
        ".woff",
        ".woff2",
    )

    async def dispatch(self, request: Request, call_next):
        # 记录请求开始时间
        start_time = time.time()

        # 获取请求信息
        request_id = get_request_id()
        client_ip = self._get_client_ip(request)
        path = request.url.path

        # 检查是否跳过日志记录
        should_skip = self._should_skip_logging(path)

        if not should_skip:
            # 设置日志额外信息
            extra = {
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "client_ip": client_ip,
                "uid": uid_var.get(),
            }

            # 记录请求信息
            logger.info(
                f"Request started: {request.method} {path}",
                extra=extra,
            )

        try:
            response = await call_next(request)

            # 计算处理时间
            process_time_ms = int((time.time() - start_time) * 1000)

            if not should_skip:
                # 更新日志额外信息
                extra = {
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "client_ip": client_ip,
                    "status_code": response.status_code,
                    "process_time_ms": process_time_ms,
                    "uid": uid_var.get(),
                }

                # 记录响应信息
                logger.info(
                    f"Request completed: {request.method} {path} - {response.status_code} ({process_time_ms}ms)",
                    extra=extra,
                )

            # 添加处理时间头
            response.headers["X-Process-Time"] = f"{process_time_ms}ms"

            return response

        except Exception as e:
            process_time_ms = int((time.time() - start_time) * 1000)

            if not should_skip:
                extra = {
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "client_ip": client_ip,
                    "status_code": 500,
                    "process_time_ms": process_time_ms,
                    "uid": uid_var.get(),
                }

                logger.error(
                    f"Request failed: {request.method} {path} - Error after {process_time_ms}ms: {e}",
                    extra=extra,
                    exc_info=True,
                )
            raise

    def _should_skip_logging(self, path: str) -> bool:
        """检查是否应该跳过日志记录"""
        return (
            any(path.startswith(p) for p in self.SKIP_PATH_PREFIXES) or
            any(path.endswith(s) for s in self.SKIP_SUFFIXES)
        )

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        # 优先从代理头获取
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # 从真实 IP 头获取
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 直接获取
        if request.client:
            return request.client.host

        return "unknown"


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """统一错误处理中间件"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # 获取请求信息
            request_id = get_request_id()
            client_ip = getattr(request, "client", None)
            client_ip = client_ip.host if client_ip else "unknown"

            # 设置日志额外信息
            extra = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "client_ip": client_ip,
                "uid": uid_var.get(),
            }

            # 记录错误日志
            logger.error(
                f"Unhandled exception: {request.method} {request.url.path}: {e}",
                extra=extra,
                exc_info=True,
            )

            # 返回标准错误响应
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": str(e),
                        "type": type(e).__name__,
                        "request_id": request_id,
                    },
                },
                headers={"X-Request-ID": request_id} if request_id else None,
            )


def setup_middlewares(app):
    """配置中间件"""
    # 注意：FastAPI 的中间件顺序是后添加的先执行
    # 所以错误处理应该最后添加
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
