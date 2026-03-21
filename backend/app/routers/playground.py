"""LLM 测试端点 - 用于验证 LLM 配置是否正常工作（仅开发环境）"""
import os
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.infrastructure.llm import APICaller

router = APIRouter(prefix="/playground", tags=["playground"])


class LLMTestResponse(BaseModel):
    """LLM 测试响应"""
    success: bool
    config: dict
    response_content: str | None = None
    error: str | None = None
    response_time_ms: float


@router.get("/llm-test", response_model=LLMTestResponse)
async def test_llm():
    """
    测试 LLM 配置是否正常工作

    发送一个简单的测试消息，返回 LLM 的响应和配置信息
    注意：此端点仅在开发环境可用
    """
    # 仅允许开发环境访问
    if os.getenv("ENV", "development") == "production":
        raise HTTPException(status_code=404, detail="Not Found")

    settings = get_settings()

    # 准备配置信息（隐藏部分 API Key）
    config_info = {
        "base_url": settings.LLM_BASE_URL,
        "model": settings.LLM_MODEL,
        "api_key_prefix": settings.LLM_API_KEY[:4] + "****" if settings.LLM_API_KEY else None,
    }

    # 验证配置
    if not settings.LLM_API_KEY or not settings.LLM_BASE_URL or not settings.LLM_MODEL:
        return LLMTestResponse(
            success=False,
            config=config_info,
            error="LLM 配置不完整，请检查环境变量 LLM_API_KEY, LLM_BASE_URL, LLM_MODEL",
            response_time_ms=0,
        )

    try:
        # 创建调用器
        caller = APICaller()

        # 记录开始时间
        start_time = time.time()

        # 发送测试消息
        messages = [{"role": "user", "content": "Hello, reply with 'OK'"}]
        response = await caller.call(messages)

        # 计算响应时间
        response_time = (time.time() - start_time) * 1000

        return LLMTestResponse(
            success=True,
            config=config_info,
            response_content=response,
            response_time_ms=round(response_time, 2),
        )

    except Exception as e:
        return LLMTestResponse(
            success=False,
            config=config_info,
            error=str(e),
            response_time_ms=0,
        )
