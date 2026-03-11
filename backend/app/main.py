"""Personal Growth Assistant API"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
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


@app.post("/parse", response_model=ParseResponse)
async def parse(request: ParseRequest):
    """
    解析自然语言文本，提取结构化任务

    - **text**: 自然语言文本，如 "明天下午3点开会，讨论项目进度"
    """
    # 服务状态检查
    if not parser:
        raise HTTPException(status_code=503, detail="服务未初始化")

    # 调用解析服务
    try:
        tasks = await parser.parse(request.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

    return {"tasks": tasks}
