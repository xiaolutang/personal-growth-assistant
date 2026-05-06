"""backfill_judge.py 单元测试

测试覆盖:
- 正常路径：mock judge 返回正常结果，验证补填写入
- 幂等性：已补填的 record 不重复处理
- dry-run：不修改任何文件，只输出统计
- 错误处理：judge 调用失败时不阻塞，标记 error 继续
- limit 参数：正确限制处理条数
"""

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.eval.backfill_judge import backfill_date
from tests.eval.judge import JudgeDimension, JudgeResult, JudgeScore, LLMJudge
from tests.eval.transcript import AgentTrace, EvalTranscript, TranscriptStore


# ── Fixtures ──


def _make_transcript(
    transcript_id: str = "eval-001",
    test_case_id: str = "ST-001",
    judge_result: Any = None,
    user_input: str = "帮我记录一个想法",
    agent_response: str = "已记录到收件箱",
    tool_calls: Any = None,
) -> EvalTranscript:
    """创建测试用 transcript"""
    tc = tool_calls or [{"tool": "create_entry", "args": {"content": "想法"}, "result": None, "latency_ms": 0.0}]
    return EvalTranscript(
        transcript_id=transcript_id,
        timestamp="2026-04-29T13:38:55.000000",
        test_case_id=test_case_id,
        test_case_category="tool_selection",
        agent_trace=AgentTrace(
            input=user_input,
            output=agent_response,
            tool_calls=[],
        ),
        judge_result=judge_result,
        outcome_grade={"passed": True},
    )


def _make_mock_judge_result(test_id: str = "ST-001") -> JudgeResult:
    """创建 mock JudgeResult"""
    scores = {}
    for dim in JudgeDimension.base_dimensions():
        scores[dim.value] = JudgeScore(
            dimension=dim, score=4, reasoning="mock评分"
        )
    return JudgeResult(scores=scores, test_id=test_id)


@pytest.fixture
def tmp_store(tmp_path: Path) -> TranscriptStore:
    """创建临时 TranscriptStore"""
    return TranscriptStore(base_dir=tmp_path)


@pytest.fixture
def populated_store(tmp_path: Path) -> TranscriptStore:
    """创建包含多条 transcript 的临时 store"""
    store = TranscriptStore(base_dir=tmp_path)
    date_str = "2026-04-29"

    # 3 条无 judge_result（需补填）
    for i in range(1, 4):
        t = _make_transcript(
            transcript_id=f"eval-{i:03d}",
            test_case_id=f"ST-{i:03d}",
        )
        store.save(t)

    # 2 条已有 judge_result（应跳过）
    for i in range(4, 6):
        t = _make_transcript(
            transcript_id=f"eval-{i:03d}",
            test_case_id=f"ST-{i:03d}",
            judge_result={
                "test_id": f"ST-{i:03d}",
                "average_score": 4.0,
                "total_score": 28,
                "dimension_scores": {},
            },
        )
        store.save(t)

    return store


# ── 测试 ──


@pytest.mark.asyncio
async def test_backfill_writes_judge_result(populated_store: TranscriptStore):
    """正常路径：mock judge 返回正常结果，验证补填写入"""
    mock_result = _make_mock_judge_result()

    mock_judge = MagicMock(spec=LLMJudge)
    mock_judge.is_degraded = False
    mock_judge.degraded_reason = ""
    mock_judge.evaluate = AsyncMock(return_value=mock_result)

    date_str = "2026-04-29"
    stats = await backfill_date(
        date_str=date_str,
        dry_run=False,
        transcripts_dir=populated_store.base_dir,
        judge=mock_judge,
    )

    # 统计正确
    assert stats["total"] == 5
    assert stats["filled"] == 3
    assert stats["skipped"] == 2
    assert stats["failed"] == 0

    # 验证文件被写入
    for i in range(1, 4):
        loaded = populated_store.load(f"eval-{i:03d}", date_str)
        assert loaded.judge_result is not None
        assert loaded.judge_result["average_score"] == mock_result.to_dict()["average_score"]

    # 已有评分的不变
    for i in range(4, 6):
        loaded = populated_store.load(f"eval-{i:03d}", date_str)
        assert loaded.judge_result["average_score"] == 4.0

    # judge.evaluate 被调用 3 次
    assert mock_judge.evaluate.call_count == 3


@pytest.mark.asyncio
async def test_backfill_skips_already_filled(populated_store: TranscriptStore):
    """幂等性：已有 judge_result 的不重复处理"""
    mock_result = _make_mock_judge_result()

    mock_judge = MagicMock(spec=LLMJudge)
    mock_judge.is_degraded = False
    mock_judge.degraded_reason = ""
    mock_judge.evaluate = AsyncMock(return_value=mock_result)

    stats = await backfill_date(
        date_str="2026-04-29",
        dry_run=False,
        transcripts_dir=populated_store.base_dir,
        judge=mock_judge,
    )

    # 只处理了 3 条无评分的
    assert stats["filled"] == 3
    assert stats["skipped"] == 2

    # 已有评分的不会被 evaluate
    assert mock_judge.evaluate.call_count == 3


@pytest.mark.asyncio
async def test_dry_run_does_not_modify(populated_store: TranscriptStore):
    """dry-run 模式不修改文件，只输出统计"""
    mock_result = _make_mock_judge_result()

    mock_judge = MagicMock(spec=LLMJudge)
    mock_judge.is_degraded = False
    mock_judge.degraded_reason = ""
    mock_judge.evaluate = AsyncMock(return_value=mock_result)

    date_str = "2026-04-29"
    stats = await backfill_date(
        date_str=date_str,
        dry_run=True,
        transcripts_dir=populated_store.base_dir,
        judge=mock_judge,
    )

    # 统计正确
    assert stats["filled"] == 3
    assert stats["skipped"] == 2

    # 但文件没有被修改（judge_result 仍为 None）
    for i in range(1, 4):
        loaded = populated_store.load(f"eval-{i:03d}", date_str)
        assert loaded.judge_result is None


@pytest.mark.asyncio
async def test_backfill_handles_judge_error(populated_store: TranscriptStore):
    """judge 调用失败时不阻塞，标记 error 继续"""
    call_count = 0

    async def _failing_evaluate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("LLM API timeout")
        return _make_mock_judge_result()

    mock_judge = MagicMock(spec=LLMJudge)
    mock_judge.is_degraded = False
    mock_judge.degraded_reason = ""
    mock_judge.evaluate = AsyncMock(side_effect=_failing_evaluate)

    date_str = "2026-04-29"
    stats = await backfill_date(
        date_str=date_str,
        dry_run=False,
        transcripts_dir=populated_store.base_dir,
        judge=mock_judge,
    )

    # 2 成功，1 失败
    assert stats["filled"] == 2
    assert stats["failed"] == 1

    # 失败的那条 judge_result 不变
    # 验证至少有一条被成功写入
    loaded = populated_store.load("eval-001", date_str)
    assert loaded.judge_result is not None

    # 失败的 eval-002 judge_result 仍为 None
    loaded2 = populated_store.load("eval-002", date_str)
    assert loaded2.judge_result is None


@pytest.mark.asyncio
async def test_limit_respected(populated_store: TranscriptStore):
    """--limit 参数正确限制处理条数"""
    mock_result = _make_mock_judge_result()

    mock_judge = MagicMock(spec=LLMJudge)
    mock_judge.is_degraded = False
    mock_judge.degraded_reason = ""
    mock_judge.evaluate = AsyncMock(return_value=mock_result)

    date_str = "2026-04-29"
    stats = await backfill_date(
        date_str=date_str,
        dry_run=False,
        limit=1,
        transcripts_dir=populated_store.base_dir,
        judge=mock_judge,
    )

    # 只处理 1 条
    assert stats["filled"] == 1
    assert stats["skipped"] == 2
    assert mock_judge.evaluate.call_count == 1


@pytest.mark.asyncio
async def test_backfill_no_transcripts(tmp_path: Path):
    """日期目录为空时返回全零统计"""
    stats = await backfill_date(
        date_str="2026-04-29",
        dry_run=False,
        transcripts_dir=tmp_path,
    )

    assert stats["total"] == 0
    assert stats["filled"] == 0
    assert stats["skipped"] == 0
    assert stats["failed"] == 0
