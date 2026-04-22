"""单容器入口：FastAPI + 静态文件服务

同时服务 API 和前端 SPA，替代独立的 nginx 容器。

路由优先级：
1. FastAPI 显式路由（API 端点）优先匹配
2. /assets/* 由 StaticFiles 处理（JS/CSS/图片等）
3. 根路径下的静态文件（favicon.ico 等）直接 FileResponse
4. 其余路径返回 index.html（SPA 深链路由回退）

必须在 app.main 完成所有路由注册之后才能添加 SPA 回退，
否则会拦截未匹配的 API 请求。
"""
import os

from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.datastructures import MutableHeaders

from app.main import app

static_dir = os.environ.get("STATIC_DIR", "/app/static/frontend")

if os.path.isdir(static_dir):
    # 挂载 /assets 为严格静态文件服务
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # SPA 回退：所有未匹配 API 路由和 /assets 的路径返回 index.html
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))


class TrailingSlashRedirectMiddleware:
    """ASGI 中间件：去掉路径末尾的斜杠，让 FastAPI 显式路由能正确匹配。

    问题：FastAPI 的 redirect_slashes 机制在路由匹配阶段处理，
    但 catch-all 路由 /{full_path:path} 会先匹配带斜杠的 API 路径。
    此中间件在路由匹配前统一去掉末尾斜杠。
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            # 去掉末尾斜杠（但保留根路径 "/"）
            if len(path) > 1 and path.endswith("/"):
                scope["path"] = path.rstrip("/")
                # 更新 raw_path 以保持一致
                if "raw_path" in scope:
                    raw = scope["raw_path"]
                    if raw.endswith(b"/"):
                        scope["raw_path"] = raw.rstrip(b"/")
                # 更新 query_string 中的 path（如有）
                scope.setdefault("query_string", b"")

        await self.app(scope, receive, send)


# 在最外层包装中间件，确保在路由匹配之前生效
app.add_middleware(TrailingSlashRedirectMiddleware)
