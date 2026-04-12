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
