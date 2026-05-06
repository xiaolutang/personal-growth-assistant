"""B02 backfill_judge 集成测试

使用真实 LLM API 补填 transcript 的 judge_result。
标记为 slow，需网络和 LLM_API_KEY 环境变量。

覆盖场景:
1. 真实 LLM 补填：创建 transcript → backfill → 验证 judge_result 写入
2. 幂等性：已补填的记录不重复处理
3. 降级检测：API 不可用时 graceful fallback
4. 端到端：transcript 文件持久化 → 重新加载 → 数据一致
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from tests.eval.backfill_judge import backfill_date
from tests.eval.judge import LLMJudge
from tests.eval.transcript import AgentTrace, EvalTranscript, TranscriptStore


# ── 标记 ──

pytestmark = pytest.mark.slow


# ── helpers ──


def _has_llm_api_key() -> bool:
    return bool(os.getenv("LLM_API_KEY"))


def _save_transcript(
    store: TranscriptStore,
    date_str: str,
    seq: int,
    test_id: str = "ST-001",
    category: str = "tool_selection",
    judge_result: Optional[Dict[str, Any]] = None,
) -> EvalTranscript:
    """构造并保存一条 transcript，使用 eval-NNN 命名以兼容 TranscriptStore.list()。"""
    t = EvalTranscript(
        transcript_id=f"eval-{seq:03d}",
        test_case_id=test_id,
        test_case_category=category,
        agent_trace=AgentTrace(
            input="帮我创建一个任务：明天去超市买菜",
            output='好的，已为你创建任务"明天去超市买菜"。需要设置截止日期为明天吗？',
            tool_calls=[],
        ),
        outcome_grade="pass",
    )
    if judge_result is not None:
        t.judge_result = judge_result

    date_dir = store._date_dir(date_str)
    date_dir.mkdir(parents=True, exist_ok=True)
    filepath = date_dir / f"eval-{seq:03d}.json"
    filepath.write_text(t.to_json(), encoding="utf-8")
    return t


def _make_judge_result() -> Dict[str, Any]:
    """构造一个合法的 judge_result（模拟已补填状态）。"""
    return {
        "dimensions": {
            "relevance": 5,
            "accuracy": 5,
            "completeness": 4,
            "clarity": 5,
            "tool_usage": 4,
            "safety": 5,
            "efficiency": 4,
        },
        "total_score": 32,
        "average_score": 4.57,
        "reasoning": "Agent correctly identified the task creation intent.",
    }


# ── 集成测试 ──


class TestBackfillRealLLM:
    """真实 LLM API 集成测试。"""

    @pytest.fixture()
    def store(self, tmp_path: Path) -> TranscriptStore:
        return TranscriptStore(base_dir=tmp_path)

    @pytest.fixture()
    def date_str(self) -> str:
        return "2026-05-06"

    @pytest.mark.skipif(
        not _has_llm_api_key(),
        reason="需要 LLM_API_KEY 环境变量",
    )
    @pytest.mark.asyncio()
    async def test_real_llm_backfill_writes_judge_result(
        self,
        store: TranscriptStore,
        tmp_path: Path,
        date_str: str,
    ):
        """真实 LLM: 创建 transcript → backfill → 验证 judge_result 写入。"""
        _save_transcript(store, date_str, 1, "ST-INT-001")

        # 补填
        stats = await backfill_date(
            date_str=date_str,
            transcripts_dir=tmp_path,
        )

        assert stats["total"] == 1
        assert stats["filled"] == 1
        assert stats["skipped"] == 0
        assert stats["failed"] == 0

        # 重新加载验证
        transcripts = store.list(date_str)
        assert len(transcripts) == 1
        loaded = transcripts[0]
        assert loaded.judge_result is not None
        assert "average_score" in loaded.judge_result
        assert loaded.judge_result["average_score"] > 0

    @pytest.mark.skipif(
        not _has_llm_api_key(),
        reason="需要 LLM_API_KEY 环境变量",
    )
    @pytest.mark.asyncio()
    async def test_real_llm_idempotent(
        self,
        store: TranscriptStore,
        tmp_path: Path,
        date_str: str,
    ):
        """幂等性：已补填的记录不重复处理。"""
        _save_transcript(store, date_str, 1, "ST-INT-002", judge_result=_make_judge_result())

        stats = await backfill_date(
            date_str=date_str,
            transcripts_dir=tmp_path,
        )

        assert stats["total"] == 1
        assert stats["filled"] == 0
        assert stats["skipped"] == 1

    @pytest.mark.asyncio()
    async def test_backfill_with_mock_judge(
        self,
        store: TranscriptStore,
        tmp_path: Path,
        date_str: str,
    ):
        """Mock judge: 不需要真实 API，验证完整 backfill 流程。"""
        from unittest.mock import AsyncMock, MagicMock

        _save_transcript(store, date_str, 1, "ST-INT-003")

        # mock judge
        mock_result = MagicMock()
        mock_result.to_dict.return_value = _make_judge_result()
        mock_result.average_score = 4.57
        mock_result.total_score = 32

        mock_judge = MagicMock(spec=LLMJudge)
        mock_judge.is_degraded = False
        mock_judge.evaluate = AsyncMock(return_value=mock_result)

        stats = await backfill_date(
            date_str=date_str,
            transcripts_dir=tmp_path,
            judge=mock_judge,
        )

        assert stats["filled"] == 1
        assert stats["skipped"] == 0

        # 验证持久化和重新加载一致
        transcripts = store.list(date_str)
        assert len(transcripts) == 1
        loaded = transcripts[0]
        assert loaded.judge_result is not None
        assert loaded.judge_result["average_score"] == 4.57
        assert loaded.judge_result["total_score"] == 32

    @pytest.mark.asyncio()
    async def test_backfill_persists_to_disk(
        self,
        store: TranscriptStore,
        tmp_path: Path,
        date_str: str,
    ):
        """端到端持久化：backfill → 文件写入 → 新 TranscriptStore 加载 → 数据一致。"""
        from unittest.mock import AsyncMock, MagicMock

        _save_transcript(store, date_str, 1, "ST-INT-004", category="boundary")

        mock_result = MagicMock()
        mock_result.to_dict.return_value = _make_judge_result()
        mock_result.average_score = 4.57
        mock_result.total_score = 32

        mock_judge = MagicMock(spec=LLMJudge)
        mock_judge.is_degraded = False
        mock_judge.evaluate = AsyncMock(return_value=mock_result)

        await backfill_date(
            date_str=date_str,
            transcripts_dir=tmp_path,
            judge=mock_judge,
        )

        # 用全新的 TranscriptStore 实例加载
        store2 = TranscriptStore(base_dir=tmp_path)
        transcripts2 = store2.list(date_str)
        assert len(transcripts2) == 1
        assert transcripts2[0].judge_result is not None
        assert transcripts2[0].judge_result["average_score"] == 4.57

    @pytest.mark.asyncio()
    async def test_backfill_judge_error_continues(
        self,
        store: TranscriptStore,
        tmp_path: Path,
        date_str: str,
    ):
        """降级: Judge 抛异常时记录失败但不中断。"""
        from unittest.mock import AsyncMock, MagicMock

        # 创建 2 条 transcript
        _save_transcript(store, date_str, 1, "ST-INT-005")
        _save_transcript(store, date_str, 2, "ST-INT-006")

        # judge 第 1 次成功，第 2 次失败
        mock_result = MagicMock()
        mock_result.to_dict.return_value = _make_judge_result()
        mock_result.average_score = 4.57
        mock_result.total_score = 32

        mock_judge = MagicMock(spec=LLMJudge)
        mock_judge.is_degraded = False
        mock_judge.evaluate = AsyncMock(
            side_effect=[mock_result, RuntimeError("API timeout")]
        )

        stats = await backfill_date(
            date_str=date_str,
            transcripts_dir=tmp_path,
            judge=mock_judge,
        )

        assert stats["filled"] == 1
        assert stats["failed"] == 1

        # 验证成功的记录仍然被写入
        transcripts = store.list(date_str)
        filled = [t for t in transcripts if t.judge_result is not None]
        assert len(filled) == 1
