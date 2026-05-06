"""transcript judge_result 补填脚本

读取历史 transcript，对 judge_result=null 的记录调用 LLMJudge 补填评分。
用于补全历史数据，使趋势报告从第一轮就有 judge 维度。

用法:
    # 补填 2026-04-29 的所有缺失 judge 记录
    uv run python -m tests.eval.backfill_judge --date 2026-04-29

    # dry-run 模式，只输出统计不修改文件
    uv run python -m tests.eval.backfill_judge --date 2026-04-29 --dry-run

    # 限制单次处理 10 条
    uv run python -m tests.eval.backfill_judge --date 2026-04-29 --limit 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from tests.eval.judge import LLMJudge
from tests.eval.transcript import EvalTranscript, TranscriptStore


# ── 默认数据目录 ──

DEFAULT_TRANSCRIPTS_DIR = (
    Path(__file__).resolve().parents[3] / "data" / "eval_transcripts"
)


async def backfill_date(
    date_str: str,
    dry_run: bool = False,
    limit: Optional[int] = None,
    transcripts_dir: Optional[Path] = None,
    judge: Optional[LLMJudge] = None,
) -> Dict[str, int]:
    """补填指定日期 transcript 的 judge_result

    Args:
        date_str: 日期字符串，如 "2026-04-29"
        dry_run: 是否只输出统计不修改文件
        limit: 限制处理条数，避免一次性消耗过多 token
        transcripts_dir: transcript 存储目录，默认使用 data/eval_transcripts
        judge: LLMJudge 实例，默认创建 use_real_llm=True 的实例

    Returns:
        统计信息字典，包含 total / filled / skipped / failed / degraded
    """
    base_dir = transcripts_dir or DEFAULT_TRANSCRIPTS_DIR
    store = TranscriptStore(base_dir=base_dir)

    # 加载指定日期所有 transcript
    transcripts = store.list(date_str)
    if not transcripts:
        print(f"[backfill] 日期 {date_str} 无 transcript 记录")
        return {"total": 0, "filled": 0, "skipped": 0, "failed": 0, "degraded": 0}

    # 创建 judge（如果未提供）
    if judge is None:
        judge = LLMJudge(use_real_llm=True)

    # 检查降级
    if judge.is_degraded:
        print(f"[backfill] LLMJudge 处于降级状态: {judge.degraded_reason}")
        print("[backfill] 继续使用降级模式（将产生默认评分）")

    # 过滤需要补填的记录
    need_fill: List[EvalTranscript] = [
        t for t in transcripts if t.judge_result is None
    ]

    already_filled = len(transcripts) - len(need_fill)
    print(
        f"[backfill] 日期 {date_str}: "
        f"共 {len(transcripts)} 条, 需补填 {len(need_fill)} 条, "
        f"已有评分 {already_filled} 条"
    )

    # 应用 limit
    if limit is not None and limit > 0:
        need_fill = need_fill[:limit]
        print(f"[backfill] 应用 --limit={limit}，本次处理 {len(need_fill)} 条")

    # 统计
    stats = {
        "total": len(transcripts),
        "filled": 0,
        "skipped": already_filled,
        "failed": 0,
        "degraded": 0,
    }

    for i, transcript in enumerate(need_fill, 1):
        tid = transcript.transcript_id
        test_id = transcript.test_case_id

        try:
            # 从 agent_trace 提取数据
            agent_trace = transcript.agent_trace
            user_input = agent_trace.input
            agent_response = agent_trace.output

            # 构建 tool_calls 列表（序列化为字典）
            tool_calls: List[Dict[str, Any]] = [
                tc.to_dict() for tc in agent_trace.tool_calls
            ]

            print(
                f"[backfill] ({i}/{len(need_fill)}) "
                f"处理 {tid} (test_case={test_id})..."
            )

            # 调用 LLMJudge 评分
            result = await judge.evaluate(
                user_input=user_input,
                agent_response=agent_response,
                tool_calls=tool_calls,
                test_id=test_id,
            )

            # 检查降级
            if judge.is_degraded:
                stats["degraded"] += 1

            # 写入 judge_result
            transcript.judge_result = result.to_dict()

            if not dry_run:
                store.save(transcript)
                print(
                    f"[backfill]   -> 已写入, "
                    f"average_score={result.average_score:.2f}, "
                    f"total_score={result.total_score}"
                )
            else:
                print(
                    f"[backfill]   -> [dry-run] 未写入, "
                    f"average_score={result.average_score:.2f}"
                )

            stats["filled"] += 1

        except Exception as e:
            stats["failed"] += 1
            print(f"[backfill]   -> 失败: {e}")

    # 输出汇总
    print("\n[backfill] 汇总:")
    print(f"  总数:     {stats['total']}")
    print(f"  已补填:   {stats['filled']}")
    print(f"  已跳过:   {stats['skipped']} (已有 judge_result)")
    print(f"  失败:     {stats['failed']}")
    if stats["degraded"] > 0:
        print(f"  降级评分: {stats['degraded']}")

    return stats


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="补填历史 transcript 的 judge_result 评分"
    )
    parser.add_argument(
        "--date",
        required=True,
        help="要补填的日期，格式 YYYY-MM-DD（如 2026-04-29）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="只输出统计，不修改任何文件",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制单次处理条数，避免一次性消耗过多 token",
    )
    parser.add_argument(
        "--transcripts-dir",
        type=str,
        default=None,
        help="transcript 存储目录（默认 data/eval_transcripts）",
    )

    args = parser.parse_args()

    transcripts_dir = None
    if args.transcripts_dir:
        transcripts_dir = Path(args.transcripts_dir)

    stats = asyncio.run(
        backfill_date(
            date_str=args.date,
            dry_run=args.dry_run,
            limit=args.limit,
            transcripts_dir=transcripts_dir,
        )
    )

    # 失败数 > 0 时返回非零退出码
    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
