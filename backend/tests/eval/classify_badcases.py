"""Bad Cases 分类与回流脚本

读取 data/eval_transcripts/bad_cases/ 下的 JSON 文件，
按 reason 字段自动分类，生成分类报告。
对于可转化为测试用例的坏例，输出符合 TestCase/NegativeTestCase schema 的 JSON 模板。

功能:
- 按 reason 字段分类统计
- 去重：相同 message_id 只保留最新一条（按 created_at 排序）
- 输出 Markdown 分类报告
- 输出 JSON 测试用例模板（待人工完善）
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── 常量 ──

REPORT_FILENAME = "badcase_classification.md"
TESTCASE_FILENAME = "badcase_to_testcase.json"

# ── 数据读取 ──


def load_badcases(badcases_dir: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    """读取 bad_cases 目录下所有 JSON 文件，返回有效记录和跳过文件列表。

    Args:
        badcases_dir: bad_cases 目录路径

    Returns:
        (records, skipped_files) - 有效记录列表和跳过的文件名列表
    """
    records: List[Dict[str, Any]] = []
    skipped: List[str] = []

    if not badcases_dir.exists():
        return records, skipped

    for json_file in sorted(badcases_dir.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                skipped.append(f"{json_file.name}: 不是 JSON 对象")
                continue
            # 必须有 message_id 和 reason
            if "message_id" not in data or "reason" not in data:
                skipped.append(f"{json_file.name}: 缺少 message_id 或 reason 字段")
                continue
            data["_source_file"] = json_file.name
            records.append(data)
        except json.JSONDecodeError:
            skipped.append(f"{json_file.name}: JSON 解析失败")
        except Exception as e:
            skipped.append(f"{json_file.name}: 读取异常 - {e}")

    return records, skipped


def dedup_by_message_id(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按 message_id 去重，保留 created_at 最新的一条。

    Args:
        records: 原始记录列表

    Returns:
        去重后的记录列表
    """
    latest_by_id: Dict[str, Dict[str, Any]] = {}

    for record in records:
        mid = record["message_id"]
        created = record.get("created_at", "")

        if mid not in latest_by_id:
            latest_by_id[mid] = record
        else:
            existing_created = latest_by_id[mid].get("created_at", "")
            if created > existing_created:
                latest_by_id[mid] = record

    # 按 message_id 排序，保持稳定输出
    return [latest_by_id[k] for k in sorted(latest_by_id)]


# ── 分类统计 ──


def classify_by_reason(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """按 reason 字段分类。

    Args:
        records: 去重后的记录列表

    Returns:
        {reason: [records...]} 字典
    """
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[record["reason"]].append(record)
    return dict(groups)


# ── 报告生成 ──


def generate_markdown_report(
    total_files: int,
    total_records: int,
    deduped_count: int,
    groups: Dict[str, List[Dict[str, Any]]],
    skipped: List[str],
) -> str:
    """生成 Markdown 分类报告。

    Args:
        total_files: 总文件数
        total_records: 有效记录数（去重前）
        deduped_count: 去重后记录数
        groups: 按 reason 分类的字典
        skipped: 跳过的文件列表

    Returns:
        Markdown 格式报告字符串
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = []

    lines.append("# Bad Case 分类报告")
    lines.append("")
    lines.append(f"> 生成时间: {now}")
    lines.append("")

    # 概览
    lines.append("## 概览")
    lines.append("")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总文件数 | {total_files} |")
    lines.append(f"| 有效记录数（去重前） | {total_records} |")
    lines.append(f"| 去重后记录数 | {deduped_count} |")
    lines.append(f"| 分类数 | {len(groups)} |")
    if skipped:
        lines.append(f"| 跳过文件数 | {len(skipped)} |")
    lines.append("")

    # 按 reason 分类详情
    lines.append("## 按 reason 分类")
    lines.append("")

    # 汇总表
    lines.append("### 汇总")
    lines.append("")
    lines.append("| reason | 数量 | 占比 |")
    lines.append("|--------|------|------|")
    for reason in sorted(groups.keys()):
        count = len(groups[reason])
        pct = f"{count / deduped_count * 100:.1f}%" if deduped_count > 0 else "0%"
        lines.append(f"| {reason} | {count} | {pct} |")
    lines.append("")

    # 详情
    lines.append("### 详情")
    lines.append("")
    for reason in sorted(groups.keys()):
        records = groups[reason]
        lines.append(f"#### {reason}（{len(records)} 条）")
        lines.append("")
        for i, r in enumerate(records, 1):
            lines.append(f"**{i}. {r['message_id']}**")
            lines.append(f"- 标题: {r.get('title', 'N/A')}")
            lines.append(f"- 详情: {r.get('detail', 'N/A')}")
            lines.append(f"- 创建时间: {r.get('created_at', 'N/A')}")
            lines.append(f"- 来源文件: {r.get('_source_file', 'N/A')}")
            lines.append("")

    # 跳过的文件
    if skipped:
        lines.append("## 跳过的文件")
        lines.append("")
        for s in skipped:
            lines.append(f"- {s}")
        lines.append("")

    return "\n".join(lines)


# ── 测试用例模板生成 ──


def _infer_category(reason: str) -> str:
    """根据 reason 推断测试用例分类。

    Args:
        reason: 坏例原因

    Returns:
        推断的 category 字符串
    """
    mapping = {
        "信息不准确": "accuracy",
        "不完整": "completeness",
        "理解错了": "comprehension",
    }
    return mapping.get(reason, "other")


def generate_testcase_templates(
    deduped_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """为每条去重后的坏例生成测试用例 JSON 模板。

    模板包含原始信息，关键字段留待人工填充。

    Args:
        deduped_records: 去重后的记录列表

    Returns:
        测试用例模板列表
    """
    templates: List[Dict[str, Any]] = []

    for i, record in enumerate(deduped_records, 1):
        reason = record["reason"]
        message_id = record["message_id"]
        category = _infer_category(reason)

        template = {
            "id": f"BAD-{i:03d}",
            "source_message_id": message_id,
            "source_reason": reason,
            "source_detail": record.get("detail", ""),
            "suggested_category": category,
            "template_type": "negative",
            "user_input": "<待填充：该 badcase 对应的用户输入>",
            "should_not_call": [],
            "reason": f"<待填充：基于原始反馈 '{reason}' 细化>",
            "behavior_checks": [
                "<待填充：Agent 应该做的行为>",
            ],
            "unacceptable": [
                "<待填充：Agent 不应该做的行为>",
            ],
            "status": "draft",
            "note": f"自动生成自 badcase {message_id}，需人工完善",
        }
        templates.append(template)

    return templates


# ── 主函数 ──


def classify_badcases(badcases_dir: Path, output_dir: Path) -> Dict[str, Any]:
    """主函数：读取、分类、生成报告。

    Args:
        badcases_dir: bad_cases 目录路径
        output_dir: 报告输出目录

    Returns:
        统计摘要字典
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 读取
    records, skipped = load_badcases(badcases_dir)
    total_files = len(list(badcases_dir.glob("*.json"))) if badcases_dir.exists() else 0
    total_records = len(records)

    # 2. 去重
    deduped = dedup_by_message_id(records)
    deduped_count = len(deduped)

    # 3. 分类
    groups = classify_by_reason(deduped)

    # 4. 生成 Markdown 报告
    report = generate_markdown_report(
        total_files=total_files,
        total_records=total_records,
        deduped_count=deduped_count,
        groups=groups,
        skipped=skipped,
    )
    report_path = output_dir / REPORT_FILENAME
    report_path.write_text(report, encoding="utf-8")

    # 5. 生成测试用例模板
    templates = generate_testcase_templates(deduped)
    testcase_path = output_dir / TESTCASE_FILENAME
    with open(testcase_path, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)

    return {
        "total_files": total_files,
        "total_records": total_records,
        "deduped_count": deduped_count,
        "categories": {k: len(v) for k, v in groups.items()},
        "skipped_count": len(skipped),
        "report_path": str(report_path),
        "testcase_path": str(testcase_path),
    }


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="Bad Cases 分类与回流脚本",
    )
    parser.add_argument(
        "--badcases-dir",
        type=Path,
        default=Path("data/eval_transcripts/bad_cases"),
        help="bad_cases 目录路径（默认: data/eval_transcripts/bad_cases）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/eval_reports"),
        help="报告输出目录（默认: data/eval_reports）",
    )
    args = parser.parse_args()

    summary = classify_badcases(args.badcases_dir, args.output_dir)

    print(f"处理完成:")
    print(f"  总文件数: {summary['total_files']}")
    print(f"  有效记录: {summary['total_records']}")
    print(f"  去重后: {summary['deduped_count']}")
    print(f"  分类: {summary['categories']}")
    print(f"  跳过: {summary['skipped_count']}")
    print(f"  报告: {summary['report_path']}")
    print(f"  模板: {summary['testcase_path']}")


if __name__ == "__main__":
    main()
