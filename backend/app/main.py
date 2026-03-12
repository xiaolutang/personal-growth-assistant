"""Personal Growth Assistant API"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.callers import APICaller
from app.models import Task
from app.services import TaskParser

# 全局实例
parser: TaskParser | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global parser
    parser = TaskParser(caller=APICaller())
    yield


app = FastAPI(
    title="Personal Growth Assistant",
    description="个人成长管理助手 - 从自然语言解析任务",
    version="0.1.0",
    lifespan=lifespan,
)


# === 响应模型 ===

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str


class ParseRequest(BaseModel):
    """解析请求"""
    text: str = Field(..., min_length=1, description="自然语言文本")


class ParseResponse(BaseModel):
    """解析响应"""
    tasks: list[Task]


# === 路由 ===

@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.post("/parse")
async def parse(request: ParseRequest):
    """
    解析自然语言文本，流式返回结果（SSE）

    返回 Server-Sent Events 格式的流式响应：
    - data: {"content": "..."}\n\n（JSON 内容片段）
    - data: [DONE]\n\n（结束信号）

    前端需要累积完整 JSON 后解析。
    """
    if not parser:
        raise HTTPException(status_code=503, detail="服务未初始化")

    return StreamingResponse(
        parser.stream_parse(request.text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
