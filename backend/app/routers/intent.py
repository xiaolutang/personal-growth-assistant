"""意图识别 API 路由"""
import json
import re
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app.callers import APICaller

router = APIRouter(tags=["intent"])

# 全局 LLM Caller（由 main.py 注入）
_llm_caller: Optional[APICaller] = None


def set_llm_caller(caller: APICaller):
    """设置 LLM Caller"""
    global _llm_caller
    _llm_caller = caller


# 意图类型
INTENT_TYPES = ["create", "read", "update", "delete", "knowledge", "review", "help"]


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


INTENT_SYSTEM_PROMPT = """你是一个意图识别助手。分析用户输入，识别意图并提取相关信息。

## 意图类型

1. **create** - 创建新条目
   关键词：新建、创建、添加、记录、记一下
   例："明天开会" → intent: create, query: "明天开会"

2. **read** - 查询/搜索
   关键词：帮我找、搜索、有没有、查找、寻找、查看、显示
   例："帮我找MCP的笔记" → intent: read, query: "MCP"

3. **update** - 更新条目
   关键词：修改、更新、改为、标记、完成、设为、添加标签
   例："把MCP笔记标记为完成" → intent: update, query: "MCP笔记", field: "status", value: "complete"

4. **delete** - 删除条目
   关键词：删除、移除、去掉、删掉、不要了
   例："删除测试任务" → intent: delete, query: "测试任务"

5. **knowledge** - 知识图谱
   关键词：知识图谱、相关概念、什么关系、学习路径
   例："MCP的知识图谱" → intent: knowledge, query: "MCP"

6. **review** - 回顾总结
   关键词：今天做了什么、本周进度、月报、回顾、统计
   例："今天做了什么" → intent: review, period: "daily"

7. **help** - 帮助说明
   关键词：帮助、能做什么、怎么用、使用说明
   例："你能做什么" → intent: help

## 输出格式

返回 JSON：
```json
{
  "intent": "意图类型",
  "confidence": 0.95,
  "query": "提取的关键词（如果有）",
  "entities": {
    "field": "要更新的字段（update 意图）",
    "value": "新值（update 意图）",
    "period": "时间范围（review 意图：daily/weekly/monthly）"
  },
  "response_hint": "可选的响应提示"
}
```

只输出 JSON，不要有其他内容。"""


@router.post("/intent", response_model=IntentResponse)
async def detect_intent(request: IntentRequest):
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
    if not _llm_caller:
        raise HTTPException(status_code=503, detail="LLM 服务未初始化")

    return await detect_intent_service(request.text)


async def detect_intent_service(text: str) -> IntentResponse:
    """
    意图检测服务函数（可被其他模块复用）

    Args:
        text: 用户输入文本

    Returns:
        IntentResponse: 意图检测结果
    """
    if not _llm_caller:
        return _fallback_intent_detection(text)

    try:
        messages = [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]

        response = await _llm_caller.call(messages, {"type": "json_object"})

        # 解析响应
        result = json.loads(response)

        # 验证意图类型
        intent = result.get("intent", "create")
        if intent not in INTENT_TYPES:
            intent = "create"

        return IntentResponse(
            intent=intent,
            confidence=result.get("confidence", 1.0),
            entities=result.get("entities", {}),
            query=result.get("query"),
            response_hint=result.get("response_hint")
        )

    except json.JSONDecodeError:
        return _fallback_intent_detection(text)
    except Exception:
        return _fallback_intent_detection(text)


def _fallback_intent_detection(text: str) -> IntentResponse:
    """回退的规则意图检测"""
    # 关键词匹配
    if any(k in text for k in ["帮助", "能做什么", "怎么用"]):
        return IntentResponse(intent="help", confidence=0.8)
    if any(k in text for k in ["今天做了", "本周进度", "月报", "回顾"]):
        return IntentResponse(intent="review", confidence=0.8)
    if any(k in text for k in ["知识图谱", "相关概念"]):
        return IntentResponse(intent="knowledge", confidence=0.8, query=text.replace("知识图谱", "").replace("相关概念", "").strip())
    if any(k in text for k in ["删除", "移除", "去掉"]):
        query = re.sub(r"(删除|移除|去掉|掉|了)", "", text).strip()
        return IntentResponse(intent="delete", confidence=0.8, query=query or text)

    # 更新意图 - 提取 field, value 和 query
    # 注意：更具体的模式要放在前面
    update_patterns = [
        # "把xxx标记为完成/已完成" - 状态改为完成（最具体，放最前）
        (r"把\s*(.+?)\s*标记为\s*(?:已完成|完成)", "status", "complete"),
        # "给xxx添加标签yyy" 或 "xxx添加标签yyy" 或 "添加标签yyy"
        (r"(?:给\s*)?(.*?)\s*添加标签\s*(.+)$", "tags", None),
        # "xxx改为yyy" - 更新字段
        (r"(.+?)\s*改为\s*(.+)$", "status", None),  # value 从匹配中提取
        # "xxx更新为yyy"
        (r"(.+?)\s*更新为\s*(.+)$", "status", None),
        # "完成了xxx" - 以"完成了"开头
        (r"^完成(?:了|度)?\s*(.+)$", "status", "complete"),
        # "xxx完成了" / "xxx已完成" - 以"完成了"或"已完成"结尾
        (r"(.+?)\s*(?:已|经)?完成(?:了|度)?$", "status", "complete"),
        # "修改xxx"
        (r"(?:修改|更新)\s*(.+)$", None, None),
    ]

    for pattern, field, value in update_patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            # 取第一个非空的 group 作为 query
            query = next((g.strip() for g in groups if g and g.strip()), text)

            # 如果 pattern 没有预设 field/value，从匹配中提取
            if len(groups) > 1:
                if field is None:
                    field = "status"
                if value is None:
                    value = groups[1].strip()

            entities = {}
            if field:
                entities["field"] = field
            if value:
                entities["value"] = value

            return IntentResponse(
                intent="update",
                confidence=0.8,
                query=query or text,
                entities=entities,
            )

    if any(k in text for k in ["帮我找", "搜索", "查找", "有没有"]):
        query = re.sub(r"(帮我找|搜索|查找|有没有|一下)", "", text).strip()
        return IntentResponse(intent="read", confidence=0.8, query=query or text)

    # 默认创建
    return IntentResponse(intent="create", confidence=0.6, query=text)
