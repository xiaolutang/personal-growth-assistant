"""Personal Growth Assistant API"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
)
from app.routers import deps
from app.services import init_storage
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

    # 初始化远程日志（log-service SDK，非阻塞，即使服务不可达也不影响启动）
    _log_handler = setup_remote_logging(
        endpoint=settings.LOG_SERVICE_URL,
        service_name="personal-growth-assistant",
        component="backend",
        level=settings.LOG_LEVEL,
    )
    logger.info("远程日志初始化完成, endpoint=%s", settings.LOG_SERVICE_URL)

    # 配置 LangSmith 可观测性（LangGraph 自动读取这些环境变量）
    if settings.LANGSMITH_API_KEY:
        os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGSMITH_TRACING"] = "true" if settings.LANGSMITH_TRACING else "false"
        os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
        logger.info(f"LangSmith tracing enabled, project: {settings.LANGSMITH_PROJECT}")

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
        intent_service = deps.get_intent_service()
        if graph.caller:
            intent_service.set_llm_caller(graph.caller)

        # 注入 Graph 到解析模块
        from app.routers import parse as parse_module

        parse_module.set_graph(graph)

        logger.info("存储服务初始化成功")
    except Exception as e:
        logger.error(f"存储服务初始化失败（部分功能不可用）: {e}")

    yield

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


# === 健康检查 ===

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str


@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查"""
    return {"status": "ok"}
