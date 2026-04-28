"""模拟用户（Simulated User）

两种模式:
- PresetReplyUser: 预设固定回复序列，用于确定性测试
- LLMSimulatedUser: 使用 LLM 生成用户回复（mock），用于多样性测试
- MultiTurnRunner: 编排多轮评估，交替调用 Agent 和 SimulatedUser
"""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Awaitable


# ── 消息类型 ──


@dataclass
class ConversationTurn:
    """一轮对话记录

    Attributes:
        role: 角色（user / agent）
        content: 文本内容
        tool_calls: 工具调用记录（agent 角色时使用）
        turn_index: 轮次索引
    """

    role: str
    content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    turn_index: int = 0


@dataclass
class MultiTurnResult:
    """多轮对话评估结果

    Attributes:
        test_id: 测试用例 ID
        turns: 所有轮次记录
        final_tool_calls: 最终的工具调用汇总
        passed: 是否通过最终状态检查
        judge_result: LLM-as-Judge 评分结果（如果有）
        error: 错误信息
    """

    test_id: str = ""
    turns: List[ConversationTurn] = field(default_factory=list)
    final_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    passed: bool = False
    judge_result: Optional[Any] = None
    error: Optional[str] = None

    @property
    def total_turns(self) -> int:
        return len(self.turns)

    @property
    def user_turns(self) -> List[ConversationTurn]:
        return [t for t in self.turns if t.role == "user"]

    @property
    def agent_turns(self) -> List[ConversationTurn]:
        return [t for t in self.turns if t.role == "agent"]


# ── 模拟用户基类 ──


class SimulatedUser(ABC):
    """模拟用户基类"""

    @abstractmethod
    async def get_reply(
        self,
        agent_message: str,
        conversation_history: List[ConversationTurn],
        turn_index: int,
    ) -> str:
        """根据 Agent 消息生成用户回复

        Args:
            agent_message: Agent 的回复
            conversation_history: 对话历史
            turn_index: 当前轮次

        Returns:
            用户回复文本
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """重置模拟用户状态"""
        ...


# ── 预设回复模式 ──


class PresetReplyUser(SimulatedUser):
    """预设回复模式

    传入回复列表，按顺序返回。用于确定性测试。

    用法:
        user = PresetReplyUser(["我想学习 Rust", "谢谢"])
        reply1 = await user.get_reply("你好", [], 0)  # "我想学习 Rust"
        reply2 = await user.get_reply("好的", [...], 1)  # "谢谢"
    """

    def __init__(self, replies: List[str], loop: bool = False):
        """初始化

        Args:
            replies: 预设回复列表
            loop: 是否在回复用尽后循环使用
        """
        self.replies = list(replies)
        self.loop = loop
        self._index = 0

    async def get_reply(
        self,
        agent_message: str,
        conversation_history: List[ConversationTurn],
        turn_index: int,
    ) -> str:
        """按顺序返回预设回复"""
        if not self.replies:
            return ""

        if self._index >= len(self.replies):
            if self.loop:
                self._index = 0
            else:
                # 回复用尽，返回最后一个
                return self.replies[-1]

        reply = self.replies[self._index]
        self._index += 1
        return reply

    def reset(self) -> None:
        """重置到第一个回复"""
        self._index = 0

    @property
    def current_index(self) -> int:
        """当前回复索引"""
        return self._index

    @property
    def remaining_replies(self) -> int:
        """剩余可用回复数"""
        if self.loop:
            return len(self.replies)
        return max(0, len(self.replies) - self._index)


# ── LLM 模拟用户模式 ──


class LLMSimulatedUser(SimulatedUser):
    """LLM 模拟用户模式

    使用 LLM 生成用户回复（测试中 mock LLM）。
    根据 agent 消息和对话历史生成合理的用户回复。

    用法:
        # 测试环境（mock）
        user = LLMSimulatedUser(inject_llm_response="我想学习 Python")
        reply = await user.get_reply("你好，有什么可以帮你？", [], 0)

        # 自定义用户角色 prompt
        user = LLMSimulatedUser(
            user_persona="一个前端开发者，正在学习后端技术",
            inject_llm_response=mock_response,
        )
    """

    DEFAULT_USER_PERSONA = """你是一个使用个人成长助手的用户。你会：
- 用简洁自然的中文回复
- 提供具体的技术话题和学习内容
- 有时会改变主意或补充信息
- 回复长度在 10-50 字之间

请直接输出你的回复，不要有额外解释。"""

    def __init__(
        self,
        user_persona: Optional[str] = None,
        inject_llm_response: Optional[str] = None,
    ):
        """初始化

        Args:
            user_persona: 用户角色描述 prompt
            inject_llm_response: 注入的 LLM 回复（用于测试 mock）
        """
        self.user_persona = user_persona or self.DEFAULT_USER_PERSONA
        self.inject_llm_response = inject_llm_response
        self._call_count = 0

    def _build_prompt(
        self,
        agent_message: str,
        conversation_history: List[ConversationTurn],
        turn_index: int,
    ) -> str:
        """构建 LLM prompt"""
        history_lines = []
        for turn in conversation_history:
            role_label = "用户" if turn.role == "user" else "助手"
            history_lines.append(f"{role_label}: {turn.content}")

        history_text = "\n".join(history_lines) if history_lines else "（无历史对话）"

        return f"""{self.user_persona}

## 对话历史
{history_text}

## 助手最新回复
{agent_message}

## 请生成你的回复（第 {turn_index + 1} 轮）
直接输出回复内容："""

    async def get_reply(
        self,
        agent_message: str,
        conversation_history: List[ConversationTurn],
        turn_index: int,
    ) -> str:
        """使用 LLM 生成用户回复"""
        _prompt = self._build_prompt(
            agent_message, conversation_history, turn_index
        )

        if self.inject_llm_response is not None:
            reply = self.inject_llm_response
        else:
            # 无注入时返回默认回复（框架模式）
            reply = "好的，谢谢"

        self._call_count += 1
        return reply

    def reset(self) -> None:
        """重置调用计数"""
        self._call_count = 0

    @property
    def call_count(self) -> int:
        """LLM 调用次数"""
        return self._call_count


# ── 多轮测试用例加载 ──


@dataclass
class MultiTurnTestCase:
    """多轮测试用例

    Attributes:
        id: 用例 ID
        category: 分类
        turns: 预定义的对话轮次
        final_state_check: 最终状态检查配置
        reference_scores: 参考评分
    """

    id: str
    category: str
    turns: List[Dict[str, Any]] = field(default_factory=list)
    final_state_check: Dict[str, Any] = field(default_factory=dict)
    reference_scores: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MultiTurnTestCase":
        return cls(
            id=data["id"],
            category=data["category"],
            turns=data.get("turns", []),
            final_state_check=data.get("final_state_check", {}),
            reference_scores=data.get("reference_scores", {}),
        )

    @property
    def user_turns(self) -> List[Dict[str, Any]]:
        """获取所有用户轮次"""
        return [t for t in self.turns if t.get("role") == "user"]

    @property
    def expected_agent_turns(self) -> List[Dict[str, Any]]:
        """获取所有期望的 Agent 轮次"""
        return [t for t in self.turns if t.get("role") == "agent"]


# ── 多轮执行器 ──


# Agent 调用函数类型：接收用户消息和对话历史，返回 Agent 输出
AgentInvokeFn = Callable[
    [str, List[ConversationTurn]],
    Awaitable[Dict[str, Any]],
]


class MultiTurnRunner:
    """多轮评估执行器

    编排多轮对话评估：交替调用 Agent 和 SimulatedUser。
    支持 preset 模式（直接从测试用例中读取用户回复）和
    simulated 模式（使用 SimulatedUser 生成回复）。

    用法:
        # Preset 模式（确定性测试）
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent)
        result = await runner.run_preset(test_case)

        # Simulated 模式（多样性测试）
        user = PresetReplyUser(["想法1", "想法2"])
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent)
        result = await runner.run_simulated(test_case, user)
    """

    def __init__(
        self,
        agent_invoke_fn: Optional[AgentInvokeFn] = None,
    ):
        """初始化

        Args:
            agent_invoke_fn: Agent 调用函数
                接收 (user_input, conversation_history)
                返回 {"response": str, "tool_calls": list}
        """
        self.agent_invoke_fn = agent_invoke_fn

    async def _call_agent(
        self,
        user_input: str,
        history: List[ConversationTurn],
    ) -> Dict[str, Any]:
        """调用 Agent"""
        if self.agent_invoke_fn is not None:
            return await self.agent_invoke_fn(user_input, history)
        # 无 Agent 函数时返回默认
        return {"response": "收到", "tool_calls": []}

    async def run_preset(
        self,
        test_case: MultiTurnTestCase,
    ) -> MultiTurnResult:
        """预设模式运行多轮对话

        直接使用测试用例中预定义的用户回复和期望的 Agent 行为。
        不需要 SimulatedUser，按 turns 顺序执行。

        Args:
            test_case: 多轮测试用例

        Returns:
            MultiTurnResult
        """
        result = MultiTurnResult(test_id=test_case.id)
        conversation_history: List[ConversationTurn] = []
        all_tool_calls: List[Dict[str, Any]] = []

        try:
            turn_index = 0
            for turn_def in test_case.turns:
                role = turn_def.get("role", "")
                content = turn_def.get("content", "")

                if role == "user":
                    # 用户轮次：记录并调用 Agent
                    conv_turn = ConversationTurn(
                        role="user",
                        content=content,
                        turn_index=turn_index,
                    )
                    conversation_history.append(conv_turn)
                    result.turns.append(conv_turn)
                    turn_index += 1

                    # 调用 Agent
                    agent_output = await self._call_agent(
                        content, conversation_history
                    )
                    agent_response = agent_output.get("response", "")
                    agent_tool_calls = agent_output.get("tool_calls", [])
                    all_tool_calls.extend(agent_tool_calls)

                    agent_turn = ConversationTurn(
                        role="agent",
                        content=agent_response,
                        tool_calls=agent_tool_calls,
                        turn_index=turn_index,
                    )
                    conversation_history.append(agent_turn)
                    result.turns.append(agent_turn)
                    turn_index += 1

                elif role == "agent":
                    # Agent 期望轮次（用于验证）
                    expected_tools = turn_def.get("expected_tools", [])
                    agent_turn = ConversationTurn(
                        role="agent",
                        content=content,
                        tool_calls=[{"tool": t} for t in expected_tools],
                        turn_index=turn_index,
                    )
                    conversation_history.append(agent_turn)
                    result.turns.append(agent_turn)
                    turn_index += 1

            result.final_tool_calls = all_tool_calls

        except Exception as e:
            result.error = str(e)

        return result

    async def run_simulated(
        self,
        test_case: MultiTurnTestCase,
        simulated_user: SimulatedUser,
    ) -> MultiTurnResult:
        """模拟模式运行多轮对话

        使用 SimulatedUser 生成用户回复，Agent 用注入的 invoke_fn。

        Args:
            test_case: 多轮测试用例
            simulated_user: 模拟用户实例

        Returns:
            MultiTurnResult
        """
        result = MultiTurnResult(test_id=test_case.id)
        conversation_history: List[ConversationTurn] = []
        all_tool_calls: List[Dict[str, Any]] = []

        # 提取初始用户输入
        user_turns = test_case.user_turns
        if not user_turns:
            result.error = "测试用例没有用户轮次"
            return result

        try:
            turn_index = 0

            # 第一轮：使用测试用例的第一个用户输入
            first_user_content = user_turns[0].get("content", "")
            conv_turn = ConversationTurn(
                role="user",
                content=first_user_content,
                turn_index=turn_index,
            )
            conversation_history.append(conv_turn)
            result.turns.append(conv_turn)
            turn_index += 1

            # 交替调用 Agent 和 SimulatedUser
            max_rounds = len(user_turns)
            user_reply_index = 1  # 已经用了第一个

            for round_idx in range(max_rounds):
                # 调用 Agent
                last_user_msg = conversation_history[-1].content
                agent_output = await self._call_agent(
                    last_user_msg, conversation_history
                )
                agent_response = agent_output.get("response", "")
                agent_tool_calls = agent_output.get("tool_calls", [])
                all_tool_calls.extend(agent_tool_calls)

                agent_turn = ConversationTurn(
                    role="agent",
                    content=agent_response,
                    tool_calls=agent_tool_calls,
                    turn_index=turn_index,
                )
                conversation_history.append(agent_turn)
                result.turns.append(agent_turn)
                turn_index += 1

                # 生成用户回复
                if user_reply_index < len(user_turns):
                    # 还有预设回复
                    user_content = user_turns[user_reply_index].get("content", "")
                    user_reply_index += 1
                else:
                    # 使用模拟用户生成
                    user_content = await simulated_user.get_reply(
                        agent_response, conversation_history, turn_index
                    )

                if not user_content:
                    break

                user_turn = ConversationTurn(
                    role="user",
                    content=user_content,
                    turn_index=turn_index,
                )
                conversation_history.append(user_turn)
                result.turns.append(user_turn)
                turn_index += 1

            result.final_tool_calls = all_tool_calls

        except Exception as e:
            result.error = str(e)

        return result

    async def run_dataset(
        self,
        test_cases: List[MultiTurnTestCase],
        mode: str = "preset",
        simulated_user: Optional[SimulatedUser] = None,
    ) -> List[MultiTurnResult]:
        """运行整个多轮数据集

        Args:
            test_cases: 多轮测试用例列表
            mode: 运行模式（"preset" 或 "simulated"）
            simulated_user: 模拟用户实例（simulated 模式时使用）

        Returns:
            MultiTurnResult 列表
        """
        results = []

        for tc in test_cases:
            if mode == "preset":
                result = await self.run_preset(tc)
            elif mode == "simulated":
                if simulated_user is None:
                    simulated_user = PresetReplyUser(
                        [t.get("content", "") for t in tc.user_turns]
                    )
                # 重置模拟用户
                simulated_user.reset()
                result = await self.run_simulated(tc, simulated_user)
            else:
                result = MultiTurnResult(
                    test_id=tc.id,
                    error=f"Unknown mode: {mode}",
                )

            results.append(result)

        return results


# ── 数据集加载 ──


import json
from pathlib import Path


DATASETS_DIR = Path(__file__).parent / "datasets"


def load_multi_turn_dataset(
    filepath: Optional[str] = None,
) -> List[MultiTurnTestCase]:
    """加载多轮测试数据集

    Args:
        filepath: JSON 文件路径（默认 multi_turn_30.json）

    Returns:
        MultiTurnTestCase 列表
    """
    if filepath is None:
        filepath = str(DATASETS_DIR / "multi_turn_30.json")

    path = Path(filepath)
    if not path.is_absolute():
        path = DATASETS_DIR / path

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [MultiTurnTestCase.from_dict(item) for item in data]
