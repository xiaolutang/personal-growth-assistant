"""意图识别 API 路由"""
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from app.routers.deps import get_intent_service, get_current_user
from app.models.user import User
from app.services.intent_service import IntentResult

router = APIRouter(tags=["intent"])


class IntentRequest(BaseModel):
    """意图识别请求"""
    text: str = Field(..., min_length=1, description="用户输入文本")
    context: Optional[dict] = Field(default=None, description="上下文信息")


class IntentResponse(BaseModel):
    """意图识别响应"""
    intent: str = Field(description="识别的意图类型")
    confidence: float = Field(default=1.0, description="置信度")
    entities: dict = Field(default_factory=dict, description="提取的实体")
    query: Optional[str] = Field(default=None, description="搜索/操作关键词")
    response_hint: Optional[str] = Field(default=None, description="响应提示")


def _result_to_response(result: IntentResult) -> IntentResponse:
    """将 IntentResult 转换为 IntentResponse"""
    return IntentResponse(
        intent=result.intent,
        confidence=result.confidence,
        entities=result.entities,
        query=result.query,
        response_hint=result.response_hint,
    )


@router.post("/intent", response_model=IntentResponse)
async def detect_intent(request: IntentRequest, user: User = Depends(get_current_user)):
    """
    检测用户输入的意图

    使用 LLM 进行智能意图识别，支持：
    - create: 创建任务/笔记
    - read: 搜索/查询
    - update: 更新条目
    - delete: 删除条目
    - knowledge: 知识图谱
    - review: 回顾总结
    - help: 帮助说明
    """
    intent_service = get_intent_service()
    result = await intent_service.detect(request.text)
    return _result_to_response(result)


# 保持向后兼容的函数
async def detect_intent_service(text: str) -> IntentResponse:
    """
    意图检测服务函数（可被其他模块复用）

    Args:
        text: 用户输入文本

    Returns:
        IntentResponse: 意图检测结果
    """
    intent_service = get_intent_service()
    result = await intent_service.detect(text)
    return _result_to_response(result)
