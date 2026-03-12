import json
from datetime import datetime
from typing import AsyncGenerator

from app.callers import LLMCaller
from app.models import Task, ParsedTaskInput


class TaskParser:
    """
    任务解析服务

    职责：
    1. 构造 prompt
    2. 调用 LLM（通过 LLMCaller）
    3. 解析结果

    使用方式：
        # 生产环境
        parser = TaskParser(caller=APICaller())

        # 测试环境
        parser = TaskParser(caller=MockCaller())
    """

    SYSTEM_PROMPT_TEMPLATE = """你是一个任务解析助手。用户会输入一段文字，你需要从中提取出任务、灵感、笔记或项目。

当前时间：{current_time}

## 分类规则

- task: 可执行的具体任务
- inbox: 灵感、想法，暂时不确定是否执行
- note: 学习笔记、知识点
- project: 长期项目，可拆解为多个任务

## 状态规则

- waitStart: 待开始
- doing: 进行中
- complete: 已完成

## 输出要求

根据用户输入，提取出对应的条目，输出 JSON 格式，包含 tasks 数组。
每个 task 包含：
- name: 名称（必填）
- description: 描述（可选，用于补充说明任务细节）
- category: 分类（task/inbox/note/project）
- status: 状态（默认 waitStart）
- planned_date: 计划日期，格式为 YYYY-MM-DD HH:MM（根据当前时间计算相对日期，如"明天"转换为具体日期）

注意：
1. 只输出 JSON，不要有其他内容
2. 根据当前时间将相对日期（明天、下周等）转换为具体日期"""

    def __init__(self, caller: LLMCaller):
        self.caller = caller

    def _build_messages(self, text: str) -> list[dict[str, str]]:
        """构造消息列表"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(current_time=current_time)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

    def _parse_result(self, json_str: str) -> list[Task]:
        """解析 LLM 返回的 JSON"""
        parsed = ParsedTaskInput.model_validate_json(json_str)
        return parsed.tasks

    async def parse(self, text: str) -> list[Task]:
        """
        解析用户输入文本，返回结构化任务列表

        Args:
            text: 用户输入文本

        Returns:
            解析后的任务列表
        """
        # 1. 构造消息
        messages = self._build_messages(text)

        # 2. 调用 LLM
        response_format = {"type": "json_object"}
        response = await self.caller.call(messages, response_format)

        # 3. 解析结果
        return self._parse_result(response)

    async def stream_parse(self, text: str) -> AsyncGenerator[str, None]:
        """
        流式解析用户输入文本，返回 SSE 格式数据

        Args:
            text: 用户输入文本

        Yields:
            SSE 格式数据：data: {"content": "..."}\n\n
        """
        # 1. 构造消息
        messages = self._build_messages(text)

        # 2. 流式调用 LLM
        response_format = {"type": "json_object"}
        async for token in self.caller.stream(messages, response_format):
            data = json.dumps({"content": token}, ensure_ascii=False)
            yield f"data: {data}\n\n"

        # 3. 发送结束信号
        yield "data: [DONE]\n\n"
