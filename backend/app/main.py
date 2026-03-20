"""Personal Growth Assistant API"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.callers import APICaller
from app.graphs.task_parser_graph import TaskParserGraph
from app.routers import (
    entries_router,
    search_router,
    knowledge_router,
    review_router,
    intent_router,
    parse_router,
)
from app.services import init_storage
from app.middleware import setup_middlewares

# 全局实例
graph = None
storage = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global graph, storage

    # 初始化解析图
    graph = TaskParserGraph(caller=APICaller())

    # 初始化存储服务（可选，依赖环境变量）
    try:
        storage = await init_storage(
            data_dir=os.getenv("DATA_DIR", "./data"),
            neo4j_uri=os.getenv("NEO4J_URI"),
            neo4j_username=os.getenv("NEO4J_USERNAME"),
            neo4j_password=os.getenv("NEO4J_PASSWORD"),
            qdrant_url=os.getenv("QDRANT_URL"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            llm_caller=graph.caller,
            embedding_model=os.getenv("EMBEDDING_MODEL"),
        )

        # 注入到共享依赖模块
        from app.routers import deps
        deps.storage = storage

        # 注入 LLM Caller 到意图识别服务（通过 deps）
        deps.reset_all_services()
        intent_service = deps.get_intent_service()
        if graph.caller:
            intent_service.set_llm_caller(graph.caller)

        # 注入 Graph 到解析模块
        from app.routers import parse as parse_module
        parse_module.set_graph(graph)

        print("存储服务初始化成功")
    except Exception as e:
        print(f"存储服务初始化失败（部分功能不可用）: {e}")

    yield


app = FastAPI(
    title="Personal Growth Assistant",
    description="个人成长管理助手 - 从自然语言解析任务（LangGraph 版）",
    version="0.3.0",
    lifespan=lifespan,
    root_path=os.getenv("ROOT_PATH", ""),
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# === 健康检查 ===

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str


@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查"""
    return {"status": "ok"}
