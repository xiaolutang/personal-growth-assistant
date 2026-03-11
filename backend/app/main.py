"""Personal Growth Assistant API"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.callers import APICaller
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


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.post("/parse")
async def parse(text: str):
    """
    解析自然语言文本，提取结构化任务

    Args:
        text: 自然语言文本，如 "明天下午3点开会，讨论项目进度"

    Returns:
        解析后的任务列表
    """
    if not parser:
        return {"error": "Service not initialized"}

    tasks = await parser.parse(text)
    return {"tasks": tasks}
