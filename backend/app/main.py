"""Personal Growth Assistant API"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.callers import APICaller
from app.graphs.task_parser_graph import TaskParserGraph

# 全局实例
graph: TaskParserGraph | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global graph
    graph = TaskParserGraph(caller=APICaller())
    yield


app = FastAPI(
    title="Personal Growth Assistant",
    description="个人成长管理助手 - 从自然语言解析任务（LangGraph 版）",
    version="0.2.0",
    lifespan=lifespan,
)


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
