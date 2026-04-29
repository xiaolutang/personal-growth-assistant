"""单容器入口：FastAPI + 静态文件服务

同时服务 API 和前端 SPA，替代独立的 nginx 容器。

路由优先级：
1. SpaFallbackMiddleware 拦截浏览器 HTML 刷新请求，返回 index.html
2. FastAPI 显式路由（API 端点）匹配 API 请求
3. /assets/* 由 StaticFiles 处理（JS/CSS/图片等）
4. catch-all 路由兜底返回 index.html

必须在 app.main 完成所有路由注册之后才能添加 SPA 回退。
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

    # SPA 兜底路由：未匹配 API 的非 HTML 请求返回 index.html
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))


class SpaFallbackMiddleware:
    """SPA 深链路由中间件：浏览器刷新 SPA 路由时返回 index.html。

    问题：FastAPI 的 API 路由（如 GET /entries/{entry_id}）会优先于
    catch-all SPA fallback 匹配浏览器刷新请求，导致返回认证错误 JSON。

    方案：在路由匹配前，对 Accept 含 text/html 的浏览器请求直接返回 index.html。
    API 路由和 SPA 路由共享路径空间，浏览器刷新一律由 SPA 接管。
    """

    def __init__(self, app: ASGIApp, static_dir: str):
        self.app = app
        self.static_dir = static_dir
        # 启动时缓存 index.html 内容，避免每次请求读磁盘
        self._index_body: bytes | None = None
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            with open(index_path, "rb") as f:
                self._index_body = f.read()

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        # 静态资源直接放行
        if path.startswith("/assets/") or path in (
            "/sw.js", "/registerSW.js", "/manifest.webmanifest",
        ):
            await self.app(scope, receive, send)
            return

        # 已知静态文件放行（favicon.ico 等）
        if path and os.path.isfile(os.path.join(self.static_dir, path.lstrip("/"))):
            await self.app(scope, receive, send)
            return

        # 浏览器 HTML 请求（Accept 含 text/html）→ 返回 index.html
        accept_value: bytes | None = None
        for name, value in scope.get("headers", []):
            if name == b"accept":
                accept_value = value
                break
        if accept_value and b"text/html" in accept_value:
            if self._index_body is not None:
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        [b"content-type", b"text/html; charset=utf-8"],
                        [b"content-length", str(len(self._index_body)).encode()],
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": self._index_body,
                })
                return

        # API 请求等正常走路由匹配
        await self.app(scope, receive, send)


class TrailingSlashRedirectMiddleware:
    """ASGI 中间件：去掉路径末尾的斜杠，让 FastAPI 显式路由能正确匹配。"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if len(path) > 1 and path.endswith("/"):
                scope["path"] = path.rstrip("/")
                if "raw_path" in scope:
                    raw = scope["raw_path"]
                    if raw.endswith(b"/"):
                        scope["raw_path"] = raw.rstrip(b"/")
                scope.setdefault("query_string", b"")
        await self.app(scope, receive, send)


class CacheControlMiddleware:
    """为 HTML 和 service worker 关键入口添加 no-store，避免浏览器卡在旧版本。"""

    NO_STORE_PATHS = {"/", "/index.html", "/sw.js", "/registerSW.js", "/manifest.webmanifest"}

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path not in self.NO_STORE_PATHS and not path.endswith(".html"):
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            await send(message)

        await self.app(scope, receive, send_wrapper)


# 在最外层包装中间件，确保在路由匹配之前生效
if os.path.isdir(static_dir):
    app.add_middleware(SpaFallbackMiddleware, static_dir=static_dir)
app.add_middleware(TrailingSlashRedirectMiddleware)
app.add_middleware(CacheControlMiddleware)
