"""意图识别服务"""
import json
import re
from typing import Optional, Tuple, List

from pydantic import BaseModel, Field

from app.callers import APICaller


# 意图类型
INTENT_TYPES = ["create", "read", "update", "delete", "knowledge", "review", "help"]


class IntentResult(BaseModel):
    """意图识别结果"""
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


class IntentService:
    """意图识别服务"""

    def __init__(self, llm_caller: Optional[APICaller] = None):
        self._llm_caller = llm_caller
        self._update_patterns = self._compile_update_patterns()
        self._search_patterns = self._compile_search_patterns()

    def _compile_update_patterns(self) -> List[Tuple[str, Optional[str], Optional[str]]]:
        """编译更新意图匹配模式"""
        return [
            # (pattern, field, value)
            # "把xxx标记为完成/已完成"
            (r"把\s*(.+?)\s*标记为\s*(?:已完成|完成)", "status", "complete"),
            # "给xxx添加标签yyy"
            (r"(?:给\s*)?(.*?)\s*添加标签\s*(.+)$", "tags", None),
            # "xxx改为yyy"
            (r"(.+?)\s*改为\s*(.+)$", "status", None),
            # "xxx更新为yyy"
            (r"(.+?)\s*更新为\s*(.+)$", "status", None),
            # "完成了xxx"
            (r"^完成(?:了|度)?\s*(.+)$", "status", "complete"),
            # "xxx完成了"
            (r"(.+?)\s*(?:已|经)?完成(?:了|度)?$", "status", "complete"),
            # "修改xxx"
            (r"(?:修改|更新)\s*(.+)$", None, None),
        ]

    def _compile_search_patterns(self) -> List[str]:
        """编译搜索意图匹配模式"""
        return [
            r"帮我找(.+)",
            r"搜索(.+)",
            r"查找(.+)",
            r"有没有(.+)",
        ]

    def set_llm_caller(self, caller: APICaller):
        """设置 LLM Caller"""
        self._llm_caller = caller

    async def detect(self, text: str) -> IntentResult:
        """检测用户输入的意图"""
        if not self._llm_caller:
            return self._fallback_detection(text)

        try:
            messages = [
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ]
            response = await self._llm_caller.call(messages, {"type": "json_object"})
            result = json.loads(response)
            intent = result.get("intent", "create")
            if intent not in INTENT_TYPES:
                intent = "create"
            return IntentResult(
                intent=intent,
                confidence=result.get("confidence", 1.0),
                entities=result.get("entities", {}),
                query=result.get("query"),
                response_hint=result.get("response_hint")
            )
        except (json.JSONDecodeError, Exception):
            return self._fallback_detection(text)

    def _detect_update_intent(self, text: str) -> Optional[IntentResult]:
        """检测更新意图"""
        for pattern, field, value in self._update_patterns:
            match = re.search(pattern, text)
            if match:
                return self._extract_update_match(match, text, field, value)
        return None

    def _extract_update_match(
        self, match, text: str, field: Optional[str], value: Optional[str]
    ) -> IntentResult:
        """提取更新匹配结果"""
        groups = match.groups()
        query = next((g.strip() for g in groups if g and g.strip()), text)
        entities = {}
        if field:
            entities["field"] = field
        if value:
            entities["value"] = value
        elif len(groups) > 1 and groups[1]:
            entities["value"] = groups[1].strip()
        return IntentResult(
            intent="update",
            confidence=0.8,
            query=query or text,
            entities=entities,
        )

    def _fallback_detection(self, text: str) -> IntentResult:
        """回退的规则意图检测"""
        # 帮助
        if any(k in text for k in ["帮助", "能做什么", "怎么用"]):
            return IntentResult(intent="help", confidence=0.8)
        # 回顾
        if any(k in text for k in ["今天做了", "本周进度", "月报", "回顾"]):
            return IntentResult(intent="review", confidence=0.8)
        # 知识图谱
        if any(k in text for k in ["知识图谱", "相关概念"]):
            return IntentResult(
                intent="knowledge",
                confidence=0.8,
                query=text.replace("知识图谱", "").replace("相关概念", "").strip()
            )
        # 删除
        if any(k in text for k in ["删除", "移除", "去掉"]):
            query = re.sub(r"(删除|移除|去掉|掉|了)", "", text).strip()
            return IntentResult(intent="delete", confidence=0.8, query=query or text)
        # 更新
        update_result = self._detect_update_intent(text)
        if update_result:
            return update_result
        # 搜索
        for pattern in self._search_patterns:
            if re.search(pattern, text):
                query = re.sub(pattern, "", text).strip()
                return IntentResult(intent="read", confidence=0.8, query=query or text)
        # 默认创建
        return IntentResult(intent="create", confidence=0.6, query=text)
