"""Personal Growth Assistant API"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.callers import APICaller
from app.graphs.task_parser_graph import TaskParserGraph
from app.routers import entries_router, search_router, knowledge_router, review_router
from app.storage import init_storage
from app.middleware import setup_middlewares

# 全局实例
graph: TaskParserGraph | None = None
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
            sqlite_path=os.getenv("SQLITE_PATH"),  # 可选，默认 {DATA_DIR}/index.db
            neo4j_uri=os.getenv("NEO4J_URI"),
            neo4j_username=os.getenv("NEO4J_USERNAME"),
            neo4j_password=os.getenv("NEO4J_PASSWORD"),
            qdrant_url=os.getenv("QDRANT_URL"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            llm_caller=graph.caller,
        )

        # 注入到共享依赖模块
        from app.routers import deps
        deps.storage = storage

        print("存储服务初始化成功")
    except Exception as e:
        print(f"存储服务初始化失败（部分功能不可用）: {e}")

    yield


app = FastAPI(
    title="Personal Growth Assistant",
    description="个人成长管理助手 - 从自然语言解析任务（LangGraph 版）",
    version="0.3.0",
    lifespan=lifespan,
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


# === 响应模型 ===

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str


class ParseRequest(BaseModel):
    """解析请求"""
    text: str = Field(..., min_length=1, description="自然语言文本")
    session_id: str = Field(default="default", description="会话 ID（对应 LangGraph thread_id）")


class SessionResponse(BaseModel):
    """会话操作响应"""
    status: str
    message: str = ""


# === 路由 ===

@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.post("/parse")
async def parse(request: ParseRequest):
    """
    解析自然语言文本，流式返回结果（SSE）

    使用 LangGraph Checkpointer 管理对话历史，
    通过 thread_id（session_id）实现多轮对话。
    """
    if not graph:
        raise HTTPException(status_code=503, detail="服务未初始化")

    return StreamingResponse(
        graph.stream_parse(request.text, request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.delete("/session/{session_id}", response_model=SessionResponse)
async def clear_session(session_id: str):
    """
    清空指定会话的对话历史

    Args:
        session_id: 会话 ID（对应 LangGraph thread_id）
    """
    if not graph:
        raise HTTPException(status_code=503, detail="服务未初始化")
    graph.clear_thread(session_id)
    return {"status": "ok", "message": f"会话 {session_id} 已清空"}
