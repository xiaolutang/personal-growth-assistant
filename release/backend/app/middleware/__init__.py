"""错误处理中间件"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import traceback
import time


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """统一错误处理中间件"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # 记录错误日志（包含 traceback 仅在 debug 模式）
            is_debug = hasattr(request.app.state, "debug") and request.app.state.debug
            if is_debug:
                print(f"[ERROR] {request.method} {request.url.path}: {e}\n{traceback.format_exc()}")
            else:
                print(f"[ERROR] {request.method} {request.url.path}: {e}")

            # 返回标准错误响应
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": str(e),
                        "type": type(e).__name__,
                    },
                },
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        # 记录请求开始时间
        start_time = time.time()

        # 记录请求信息
        print(f"[REQUEST] {request.method} {request.url.path}")

        try:
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 记录响应信息
            print(f"[RESPONSE] {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")

            # 添加处理时间头
            response.headers["X-Process-Time"] = f"{process_time:.3f}s"

            return response
        except Exception as e:
            process_time = time.time() - start_time
            print(f"[ERROR] {request.method} {request.url.path} - Error after {process_time:.3f}s: {e}")
            raise


def setup_middlewares(app):
    """配置中间件"""
    # 注意：FastAPI 的中间件顺序是后添加的先执行
    # 所以错误处理应该最后添加
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
