"""真实 Agent 评估运行脚本

连接 Docker 中运行的真实 Agent，跑完全部测试用例并输出评估报告。

用法:
    cd backend
    uv run python -m tests.eval.run_eval --username <user> --password <pwd>

参数:
    --base-url   Agent 地址 (默认 http://localhost:8001)
    --dataset    评估范围: single / negative / all (默认 all)
    --output     报告输出路径 (默认输出到终端)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx

# 确保可以 import 项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.eval.framework import (
    DatasetLoader,
    EvaluationReport,
    GoldenDatasetRunner,
    NegativeReport,
    NegativeTestCase,
    TestCase,
    judge_negative_case,
    judge_test_case,
)
from tests.eval.transcript import (
    AgentTrace,
    EvalTranscript,
    ToolCallRecord,
    TranscriptStore,
)


# ── SSE 解析 ──


def parse_sse_stream(lines: List[str]) -> dict:
    """解析 SSE 流，提取 tool_calls 和 agent 回复

    Returns:
        {"tools": [str], "args": [dict], "content": str}
    """
    tool_calls = []
    content_parts = []
    current_event = ""

    for line in lines:
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            raw = line[6:]
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if current_event == "tool_call":
                tool_calls.append({
                    "id": data.get("id", ""),
                    "tool": data.get("tool", ""),
                    "args": data.get("args", {}),
                })
            elif current_event == "content":
                content_parts.append(data.get("content", ""))
            elif current_event == "error":
                print(f"  [Agent Error] {data.get('message', '')}", file=sys.stderr)

    return {
        "tools": [tc["tool"] for tc in tool_calls],
        "args": [tc["args"] for tc in tool_calls],
        "content": "".join(content_parts),
    }


# ── 真实 Agent 调用 ──


class RealAgentClient:
    """通过 HTTP SSE 调用真实 Agent"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._used_sessions: List[str] = []

    async def call(self, text: str, session_id: str) -> dict:
        """调用 Agent 并返回 {"tools": [...], "args": [...], "content": "..."}"""
        self._used_sessions.append(session_id)
        payload = {
            "text": text,
            "session_id": session_id,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat",
                headers=self._headers,
                json=payload,
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    return {
                        "tools": [],
                        "args": [],
                        "content": "",
                        "error": f"HTTP {resp.status_code}: {body.decode()[:200]}",
                    }

                lines = []
                async for line in resp.aiter_lines():
                    lines.append(line)

                return parse_sse_stream(lines)

    async def cleanup_sessions(self) -> tuple[int, int]:
        """清理所有评估创建的会话，返回 (成功数, 失败数)"""
        if not self._used_sessions:
            return 0, 0

        print(f"\n=== 清理评估会话 ({len(self._used_sessions)} 个) ===")
        ok, fail = 0, 0
        async with httpx.AsyncClient(timeout=30.0) as http:
            for sid in self._used_sessions:
                try:
                    resp = await http.delete(
                        f"{self.base_url}/sessions/{sid}",
                        headers=self._headers,
                    )
                    if resp.status_code in (200, 404):
                        ok += 1
                    else:
                        fail += 1
                except Exception:
                    fail += 1
        print(f"  清理完成: {ok} 成功, {fail} 失败")
        self._used_sessions.clear()
        return ok, fail


# ── 评估运行 ──


async def run_single_turn(
    client: RealAgentClient,
    cases: List[TestCase],
    transcript_store: TranscriptStore | None = None,
) -> EvaluationReport:
    """运行单轮正向评估"""

    # 缓存每次调用的完整结果（含 content），用于 transcript
    _call_cache: Dict[str, dict] = {}

    async def invoke_fn(user_input: str, thread_id: str) -> dict:
        result = await client.call(user_input, thread_id)
        _call_cache[thread_id] = result
        return result

    runner = GoldenDatasetRunner(invoke_fn=invoke_fn, k=1, num_trials=1)

    all_results = []
    category_results: Dict[str, list] = {}

    total = len(cases)
    for idx, tc in enumerate(cases):
        print(f"  [{idx + 1}/{total}] {tc.id}: {tc.user_input[:40]}...", end=" ", flush=True)
        start = time.time()
        case_results = await runner.run_single_case(tc)
        elapsed = time.time() - start
        passed = case_results[0].passed if case_results else False
        actual_tools = case_results[0].actual_tools if case_results else []
        mark = "PASS" if passed else "FAIL"
        tools_str = ",".join(actual_tools) if actual_tools else "(none)"
        print(f"{mark} [{elapsed:.1f}s] tools=[{tools_str}]")

        # 保存 EvalTranscript
        if transcript_store and case_results:
            r = case_results[0]
            call_data = _call_cache.get(r.thread_id, {})
            trace = AgentTrace(
                input=tc.user_input,
                output=call_data.get("content", ""),
                tool_calls=[
                    ToolCallRecord(tool=t, args=a)
                    for t, a in zip(
                        r.actual_tools,
                        r.actual_args if r.actual_args else [{}] * len(r.actual_tools),
                    )
                ],
                total_latency_ms=elapsed * 1000,
                iteration_count=len(actual_tools),
            )
            transcript = EvalTranscript(
                test_case_id=tc.id,
                test_case_category=tc.category,
                agent_trace=trace,
                outcome_grade={"passed": passed},
                metadata={"behavior_checks": tc.behavior_checks} if tc.behavior_checks else {},
            )
            transcript_store.save(transcript)

        all_results.extend(case_results)
        for r in case_results:
            category_results.setdefault(tc.category, []).append(r)

    # 构建报告
    from tests.eval.framework import CategoryStats, pass_at_k, pass_hat_k

    category_stats: Dict[str, CategoryStats] = {}
    for cat, cat_results in category_results.items():
        by_case_id: Dict[str, List[bool]] = {}
        for r in cat_results:
            by_case_id.setdefault(r.test_id, []).append(r.passed)

        case_pass_rates = [pass_at_k(v, runner.k) for v in by_case_id.values()]
        case_pass_hat_rates = [pass_hat_k(v, runner.k) for v in by_case_id.values()]

        total_cat = len(by_case_id)
        passed_cat = sum(1 for v in by_case_id.values() if any(v))

        category_stats[cat] = CategoryStats(
            category=cat,
            total=total_cat,
            passed=passed_cat,
            pass_at_k_value=sum(case_pass_rates) / len(case_pass_rates) if case_pass_rates else 0.0,
            pass_hat_k_value=sum(case_pass_hat_rates) / len(case_pass_hat_rates) if case_pass_hat_rates else 0.0,
        )

    by_case_all: Dict[str, List[bool]] = {}
    for r in all_results:
        by_case_all.setdefault(r.test_id, []).append(r.passed)
    total_passed = sum(1 for v in by_case_all.values() if any(v))

    return EvaluationReport(
        dataset_name="single_turn_68",
        total_cases=len(cases),
        total_passed=total_passed,
        k=runner.k,
        category_stats=category_stats,
        results=all_results,
    )


async def run_negative(
    client: RealAgentClient,
    cases: List[NegativeTestCase],
) -> NegativeReport:
    """运行负面评估"""

    all_results = []
    total = len(cases)

    for idx, tc in enumerate(cases):
        print(f"  [{idx + 1}/{total}] {tc.id}: {tc.user_input[:40]}...", end=" ", flush=True)
        start = time.time()

        result = await client.call(tc.user_input, f"eval-neg-{tc.id}")
        elapsed = time.time() - start

        violated, violated_tools = judge_negative_case(tc, result["tools"])
        mark = "OK" if not violated else "VIOLATED"
        tools_str = ",".join(result["tools"]) if result["tools"] else "(none)"
        print(f"{mark} [{elapsed:.1f}s] tools=[{tools_str}]", end="")
        if violated:
            print(f" violated=[{','.join(violated_tools)}]")
        else:
            print()

        from tests.eval.framework import NegativeEvalResult

        all_results.append(NegativeEvalResult(
            test_id=tc.id,
            violated=violated,
            actual_tools=result["tools"],
            violated_tools=violated_tools,
        ))

    total_violations = sum(1 for r in all_results if r.violated)
    return NegativeReport(
        dataset_name="negative_24",
        total_cases=len(cases),
        total_violations=total_violations,
        results=all_results,
    )


# ── 报告输出 ──


def print_failed_details(report: EvaluationReport, cases: List[TestCase]):
    """输出失败用例详情"""
    failed_ids = set()
    for r in report.results:
        if not r.passed:
            failed_ids.add(r.test_id)

    if not failed_ids:
        print("\n  全部通过！")
        return

    case_map = {c.id: c for c in cases}
    print(f"\n  失败用例 ({len(failed_ids)} 条):")
    for fid in sorted(failed_ids):
        tc = case_map.get(fid)
        if not tc:
            continue
        # 找到对应的结果
        result = next((r for r in report.results if r.test_id == fid), None)
        actual_tools = result.actual_tools if result else []
        print(f"    {fid} [{tc.category}]")
        print(f"      输入: {tc.user_input}")
        print(f"      期望: {tc.expected_tools}")
        print(f"      实际: {actual_tools}")
        if tc.unacceptable:
            violated = [t for t in actual_tools if t in tc.unacceptable]
            if violated:
                print(f"      违规: 调用了不可接受的 {violated}")
        print()


def print_negative_details(report: NegativeReport, cases: List[NegativeTestCase]):
    """输出负面违规详情"""
    violated = [r for r in report.results if r.violated]
    if not violated:
        print("\n  无违规！")
        return

    case_map = {c.id: c for c in cases}
    print(f"\n  违规用例 ({len(violated)} 条):")
    for v in violated:
        tc = case_map.get(v.test_id)
        if not tc:
            continue
        print(f"    {v.test_id} [{tc.category}]")
        print(f"      输入: {tc.user_input}")
        print(f"      不应调用: {tc.should_not_call}")
        print(f"      实际调用了: {v.violated_tools}")
        print(f"      原因: {tc.reason}")
        print()


# ── 主入口 ──


async def main():
    parser = argparse.ArgumentParser(description="真实 Agent 评估运行脚本")
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--dataset", choices=["single", "negative", "all"], default="all")
    parser.add_argument("--output", help="报告输出 JSON 文件路径")
    args = parser.parse_args()

    # 1. 登录
    print("=== 登录获取 Token ===")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{args.base_url}/auth/login",
            json={"username": args.username, "password": args.password},
        )
        if resp.status_code != 200:
            print(f"登录失败: {resp.status_code} {resp.text}")
            sys.exit(1)
        token = resp.json()["access_token"]
    print(f"  Token 获取成功")

    client = RealAgentClient(args.base_url, token)

    # 2. 验证连接
    print("\n=== 验证 Agent 连通性 ===")
    test_result = await client.call("你好", "eval-ping")
    if "error" in test_result:
        print(f"  连接失败: {test_result['error']}")
        sys.exit(1)
    print(f"  连通 OK，Agent 回复: {test_result['content'][:60]}")

    output_data = {}

    # 初始化 TranscriptStore
    transcript_store = TranscriptStore()

    # 3. 单轮正向评估
    if args.dataset in ("single", "all"):
        print("\n=== 单轮正向评估 (68 条) ===")
        cases = DatasetLoader.load_single_turn()
        start = time.time()
        report = await run_single_turn(client, cases, transcript_store=transcript_store)
        elapsed = time.time() - start

        print(f"\n{report.to_text()}")
        print(f"\n  总耗时: {elapsed:.1f}s")
        print_failed_details(report, cases)

        output_data["single_turn"] = {
            "total": report.total_cases,
            "passed": report.total_passed,
            "pass_rate": f"{report.overall_pass_rate:.1%}",
            "elapsed_seconds": round(elapsed, 1),
            "failed_ids": list({
                r.test_id for r in report.results if not r.passed
            }),
        }

    # 4. 负面评估
    if args.dataset in ("negative", "all"):
        print("\n=== 负面评估 (24 条) ===")
        neg_cases = DatasetLoader.load_negative()
        start = time.time()
        neg_report = await run_negative(client, neg_cases)
        elapsed = time.time() - start

        print(f"\n{neg_report.to_text()}")
        print(f"\n  总耗时: {elapsed:.1f}s")
        print_negative_details(neg_report, neg_cases)

        output_data["negative"] = {
            "total": neg_report.total_cases,
            "violations": neg_report.total_violations,
            "violation_rate": f"{neg_report.violation_rate:.1%}",
            "elapsed_seconds": round(elapsed, 1),
            "violated_ids": [r.test_id for r in neg_report.results if r.violated],
        }

    # 5. 输出 JSON 报告
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存到: {args.output}")

    print("\n=== 评估完成 ===")
    return client


if __name__ == "__main__":
    agent_client = None
    try:
        agent_client = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n  评估被中断，正在清理...")
    finally:
        if agent_client:
            asyncio.run(agent_client.cleanup_sessions())
