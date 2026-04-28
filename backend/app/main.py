"""Personal Growth Assistant API"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel

from app.callers import APICaller
from app.core.config import get_settings
from app.graphs.task_parser_graph import TaskParserGraph
from app.routers import (
    entries_router,
    search_router,
    knowledge_router,
    review_router,
    intent_router,
    parse_router,
    playground_router,
    feedback_router,
    auth_router,
    ai_chat_router,
    notifications_router,
    goals_router,
    analytics_router,
)
from app.routers import deps
from app.services import init_storage
from app.services.auth_service import token_blacklist
from app.middleware import setup_middlewares
from log_service_sdk import setup_remote_logging

# 获取 logger
logger = logging.getLogger(__name__)

# 全局实例
graph = None
storage = None
_log_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global graph, storage, _log_handler

    settings = get_settings()

    # 校验 JWT 配置（阻塞式，空密钥拒绝启动）
    try:
        settings.validate_jwt()
    except ValueError as e:
        logger.error("JWT 配置校验失败: %s，应用无法启动", e)
        raise

    # 启动 Token 黑名单定时清理
    await token_blacklist.start_cleanup_task()

    # 初始化远程日志（log-service SDK，非阻塞，即使服务不可达也不影响启动）
    try:
        _log_handler = setup_remote_logging(
            endpoint=settings.LOG_SERVICE_URL,
            service_name="personal-growth-assistant",
            component="backend",
            level=settings.LOG_LEVEL,
        )
        logger.info("远程日志初始化完成, endpoint=%s", settings.LOG_SERVICE_URL)
    except Exception as e:
        logger.error("远程日志初始化失败（不影响启动）: %s", e)

    # 配置 LangSmith 可观测性（LangGraph 自动读取这些环境变量）
    if settings.LANGSMITH_API_KEY:
        os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGSMITH_TRACING"] = "true" if settings.LANGSMITH_TRACING else "false"
        os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
        logger.info("LangSmith tracing enabled, project=%s", settings.LANGSMITH_PROJECT)

    # 初始化解析图（使用工厂方法，异步创建）
    graph = await TaskParserGraph.create(caller=APICaller())

    # 初始化存储服务（可选，依赖环境变量）
    try:
        storage = await init_storage(
            data_dir=settings.DATA_DIR,
            neo4j_uri=settings.NEO4J_URI,
            neo4j_username=settings.NEO4J_USERNAME,
            neo4j_password=settings.NEO4J_PASSWORD,
            qdrant_url=settings.QDRANT_URL,
            qdrant_api_key=settings.QDRANT_API_KEY,
            llm_caller=graph.caller,
            embedding_model=settings.EMBEDDING_MODEL,
        )

        # 注入到共享依赖模块
        deps.storage = storage

        # 注入 LLM Caller 到意图识别服务（通过 deps）
        deps.reset_all_services()

        # 初始化 UserStorage（必须在 reset_all_services 之后，否则会被清空）
        from app.infrastructure.storage.user_storage import UserStorage
        deps._user_storage = UserStorage(f"{settings.DATA_DIR}/users.db")

        # 迁移 onboarding_completed 列（幂等），已有数据用户自动标记为已完成
        try:
            from app.infrastructure.storage.user_storage import check_user_markdown_data

            def _has_user_data(user_id: str) -> bool:
                """检查用户是否有历史数据：同时检查 SQLite 和 Markdown 目录。"""
                # 1. 检查 SQLite 中的 entry 数量
                if storage and storage.sqlite:
                    try:
                        if storage.sqlite.count_entries(user_id=user_id) > 0:
                            return True
                    except Exception:
                        pass

                # 2. 兜底检查 Markdown 数据目录（白名单）
                user_data_dir = os.path.join(settings.DATA_DIR, "users", user_id)
                return check_user_markdown_data(user_data_dir)

            deps._user_storage.migrate_onboarding_column(
                has_user_data_fn=_has_user_data
            )
        except Exception as e:
            logger.warning("onboarding_completed 迁移失败（不影响启动）: %s", e)
        intent_service = deps.get_intent_service()
        if graph.caller:
            intent_service.set_llm_caller(graph.caller)

        # 初始化 Analytics 埋点表（幂等，失败不影响启动）
        try:
            analytics_svc = deps.get_analytics_service()
            if analytics_svc:
                analytics_svc.ensure_table()
        except Exception as e:
            logger.warning("analytics_events 表创建失败（不影响启动）: %s", e)

        # 注入 Graph 到解析模块
        from app.routers import parse as parse_module

        entry_svc = deps.get_entry_service()
        intent_svc = deps.get_intent_service()
        parse_module.set_graph(graph, entry_service=entry_svc, intent_service=intent_svc)

        logger.info("存储服务初始化成功")
    except Exception as e:
        logger.error("存储服务初始化失败（部分功能不可用）: %s", e)

    yield

    # 停止 Token 黑名单定时清理
    token_blacklist.stop_cleanup_task()

    # 关闭远程日志 handler，flush 剩余日志
    if _log_handler is not None:
        logger.info("正在关闭远程日志 handler...")
        _log_handler.close()


app = FastAPI(
    title="Personal Growth Assistant",
    description="个人成长管理助手 - 从自然语言解析任务（LangGraph 版）",
    version="0.3.0",
    lifespan=lifespan,
    root_path=os.getenv("ROOT_PATH", ""),
)


def _json_safe(value: Any) -> Any:
    """将异常细节递归转换为可 JSON 序列化的数据。"""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    try:
        return jsonable_encoder(value)
    except Exception:
        return str(value)


# 422 验证错误日志
@app.exception_handler(RequestValidationError)
async def debug_validation_error(request: Request, exc: RequestValidationError):
    safe_errors = _json_safe(exc.errors())
    safe_body = _json_safe(exc.body)
    logger.error("VALIDATION_422 path=%s errors=%s body=%s", request.url.path, safe_errors, safe_body)
    return JSONResponse(status_code=422, content={"detail": safe_errors, "body": safe_body})

# ResponseValidationError 捕获（response_model 验证失败时触发 500）
from fastapi.exceptions import ResponseValidationError

@app.exception_handler(ResponseValidationError)
async def response_validation_error(request: Request, exc: ResponseValidationError):
    safe_errors = _json_safe(exc.errors())
    logger.error("RESPONSE_VALIDATION_500 path=%s errors=%s", request.url.path, safe_errors)
    return JSONResponse(status_code=500, content={"detail": safe_errors})

# 兜底异常处理（替代原 ErrorHandlerMiddleware，避免 BaseHTTPMiddleware 的 body 消费 bug）
from app.middleware import get_request_id, uid_var

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """统一未捕获异常处理 — 生产环境脱敏，DEBUG 模式暴露详情"""
    from app.core.config import get_settings

    request_id = get_request_id()
    client_ip = getattr(request, "client", None)
    client_ip = client_ip.host if client_ip else "unknown"

    extra = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": 500,
        "client_ip": client_ip,
        "uid": uid_var.get(),
    }
    logger.error(
        f"Unhandled exception: {request.method} {request.url.path}: {exc}",
        extra=extra,
        exc_info=True,
    )

    debug = get_settings().DEBUG
    if debug:
        error_message = str(exc)
        error_type = type(exc).__name__
    else:
        error_message = "Internal Server Error"
        error_type = "INTERNAL_ERROR"

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": error_message,
                "type": error_type,
                "request_id": request_id,
            },
        },
        headers={"X-Request-ID": request_id} if request_id else None,
    )

# CORS 中间件
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-UID", "X-Request-ID"],
)

# 添加自定义中间件（错误处理和日志）
setup_middlewares(app)

# 注册路由
app.include_router(entries_router)
app.include_router(search_router)
app.include_router(knowledge_router)
app.include_router(review_router)
app.include_router(intent_router)
app.include_router(parse_router)
app.include_router(playground_router)
app.include_router(feedback_router)
app.include_router(auth_router)
app.include_router(ai_chat_router)
app.include_router(notifications_router)
app.include_router(goals_router)
app.include_router(analytics_router)


# === 健康检查 ===

class ServiceStatus(BaseModel):
    """单个服务状态"""
    status: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    services: dict[str, str]


async def _check_services(storage) -> dict:
    """检查各存储后端连接状态"""
    services = {}

    # SQLite — 核心依赖
    try:
        if storage and storage.sqlite is not None:
            conn = storage.sqlite.get_connection()
            try:
                conn.execute("SELECT 1")
                services["sqlite"] = "ok"
            finally:
                conn.close()
        else:
            services["sqlite"] = "error"
    except Exception:
        services["sqlite"] = "error"

    # Neo4j — 非核心，降级（真实连接探测）
    try:
        if storage and storage.neo4j is not None and storage.neo4j.is_connected:
            if await storage.neo4j.verify_connectivity():
                services["neo4j"] = "ok"
            else:
                services["neo4j"] = "error"
        else:
            services["neo4j"] = "unavailable"
    except Exception:
        services["neo4j"] = "error"

    # Qdrant — 非核心，降级（真实连接探测）
    try:
        if storage and storage.qdrant is not None and storage.qdrant.is_connected:
            if await storage.qdrant.check_alive():
                services["qdrant"] = "ok"
            else:
                services["qdrant"] = "error"
        else:
            services["qdrant"] = "unavailable"
    except Exception:
        services["qdrant"] = "error"

    return services


@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查 — 返回服务状态和依赖连接检查"""
    storage = deps.storage
    services = await _check_services(storage)

    # 核心依赖不可达 → 503
    if services.get("sqlite") == "error":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "services": services},
        )

    # 非核心降级 → 200 + degraded
    overall = "ok" if all(v == "ok" for v in services.values()) else "degraded"
    return {"status": overall, "services": services}
