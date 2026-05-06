"""classify_badcases 单元测试

覆盖场景:
- 正常路径：3 个 badcase 文件，验证分类输出
- 空目录：无 badcase 时不报错
- 去重：相同 message_id 只输出一条分析
- 损坏文件：JSON 格式异常时跳过不崩溃
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.eval.classify_badcases import (
    TESTCASE_FILENAME,
    REPORT_FILENAME,
    classify_badcases,
    dedup_by_message_id,
    generate_markdown_report,
    generate_testcase_templates,
    load_badcases,
)


# ── helpers ──


def _write_badcase(path: Path, data: dict) -> None:
    """写一个 badcase JSON 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ── 固定 fixture ──


@pytest.fixture()
def sample_badcases(tmp_path: Path) -> dict:
    """创建 3 个不同 message_id 的 badcase 文件。"""
    badcases_dir = tmp_path / "bad_cases"
    badcases_dir.mkdir()

    cases = [
        {
            "feedback_id": 1,
            "message_id": "msg-001",
            "reason": "信息不准确",
            "detail": "Agent 说有 5 个任务，实际只有 2 个",
            "title": "回复不准确",
            "description": None,
            "user_id": "user-a",
            "created_at": "2026-05-01T10:00:00+00:00",
            "exported_at": "2026-05-01T10:00:01+00:00",
        },
        {
            "feedback_id": 2,
            "message_id": "msg-002",
            "reason": "不完整",
            "detail": "缺少关键信息",
            "title": "回复不完整",
            "description": None,
            "user_id": "user-b",
            "created_at": "2026-05-01T11:00:00+00:00",
            "exported_at": "2026-05-01T11:00:01+00:00",
        },
        {
            "feedback_id": 3,
            "message_id": "msg-003",
            "reason": "理解错了",
            "detail": "Agent 把任务理解成了笔记",
            "title": "理解错误",
            "description": None,
            "user_id": "user-c",
            "created_at": "2026-05-01T12:00:00+00:00",
            "exported_at": "2026-05-01T12:00:01+00:00",
        },
    ]

    for i, case in enumerate(cases):
        _write_badcase(badcases_dir / f"{case['message_id']}_{i}.json", case)

    output_dir = tmp_path / "output"
    return {"badcases_dir": badcases_dir, "output_dir": output_dir, "count": 3}


# ── 测试用例 ──


class TestClassifyNormal:
    """正常路径：给定 3 个 badcase 文件，验证分类输出。"""

    def test_classify_produces_report_and_template(self, sample_badcases: dict):
        result = classify_badcases(
            sample_badcases["badcases_dir"],
            sample_badcases["output_dir"],
        )

        assert result["total_files"] == 3
        assert result["total_records"] == 3
        assert result["deduped_count"] == 3
        assert result["skipped_count"] == 0

        # 报告文件存在
        report_path = sample_badcases["output_dir"] / REPORT_FILENAME
        assert report_path.exists()
        report_text = report_path.read_text(encoding="utf-8")
        assert "# Bad Case 分类报告" in report_text
        assert "信息不准确" in report_text
        assert "不完整" in report_text
        assert "理解错了" in report_text
        assert "msg-001" in report_text
        assert "msg-002" in report_text
        assert "msg-003" in report_text

        # 模板文件存在
        testcase_path = sample_badcases["output_dir"] / TESTCASE_FILENAME
        assert testcase_path.exists()
        templates = json.loads(testcase_path.read_text(encoding="utf-8"))
        assert len(templates) == 3
        # 每条模板有 id 和 source_message_id
        for t in templates:
            assert "id" in t
            assert "source_message_id" in t
            assert "status" in t
            assert t["status"] == "draft"

    def test_categories_in_summary(self, sample_badcases: dict):
        result = classify_badcases(
            sample_badcases["badcases_dir"],
            sample_badcases["output_dir"],
        )
        cats = result["categories"]
        assert "信息不准确" in cats
        assert "不完整" in cats
        assert "理解错了" in cats
        assert cats["信息不准确"] == 1
        assert cats["不完整"] == 1
        assert cats["理解错了"] == 1


class TestClassifyEmptyDir:
    """空目录：无 badcase 时不报错。"""

    def test_empty_directory(self, tmp_path: Path):
        badcases_dir = tmp_path / "empty_bad_cases"
        badcases_dir.mkdir()
        output_dir = tmp_path / "output"

        result = classify_badcases(badcases_dir, output_dir)

        assert result["total_files"] == 0
        assert result["total_records"] == 0
        assert result["deduped_count"] == 0
        assert result["categories"] == {}
        assert result["skipped_count"] == 0

        # 报告和模板仍然生成
        assert (output_dir / REPORT_FILENAME).exists()
        assert (output_dir / TESTCASE_FILENAME).exists()

    def test_nonexistent_directory(self, tmp_path: Path):
        badcases_dir = tmp_path / "does_not_exist"
        output_dir = tmp_path / "output"

        result = classify_badcases(badcases_dir, output_dir)

        assert result["total_files"] == 0
        assert result["total_records"] == 0
        assert result["deduped_count"] == 0


class TestDedupByMessageId:
    """去重：相同 message_id 只保留最新一条。"""

    def test_dedup_keeps_latest(self, tmp_path: Path):
        records = [
            {
                "message_id": "msg-dup",
                "reason": "信息不准确",
                "detail": "旧反馈",
                "created_at": "2026-05-01T10:00:00+00:00",
            },
            {
                "message_id": "msg-dup",
                "reason": "信息不准确",
                "detail": "新反馈",
                "created_at": "2026-05-02T10:00:00+00:00",
            },
            {
                "message_id": "msg-dup",
                "reason": "信息不准确",
                "detail": "中间反馈",
                "created_at": "2026-05-01T15:00:00+00:00",
            },
        ]
        deduped = dedup_by_message_id(records)
        assert len(deduped) == 1
        assert deduped[0]["detail"] == "新反馈"

    def test_dedup_output_count(self, tmp_path: Path):
        """3 个文件，2 个相同 message_id，去重后应为 2 条。"""
        badcases_dir = tmp_path / "bad_cases"
        badcases_dir.mkdir()

        _write_badcase(
            badcases_dir / "msg-dup_old.json",
            {
                "message_id": "msg-dup",
                "reason": "信息不准确",
                "detail": "旧",
                "created_at": "2026-05-01T10:00:00+00:00",
            },
        )
        _write_badcase(
            badcases_dir / "msg-dup_new.json",
            {
                "message_id": "msg-dup",
                "reason": "信息不准确",
                "detail": "新",
                "created_at": "2026-05-02T10:00:00+00:00",
            },
        )
        _write_badcase(
            badcases_dir / "msg-unique.json",
            {
                "message_id": "msg-unique",
                "reason": "不完整",
                "detail": "唯一",
                "created_at": "2026-05-01T10:00:00+00:00",
            },
        )

        output_dir = tmp_path / "output"
        result = classify_badcases(badcases_dir, output_dir)

        assert result["total_files"] == 3
        assert result["total_records"] == 3
        assert result["deduped_count"] == 2

        # 验证模板只有 2 条
        templates = json.loads(
            (output_dir / TESTCASE_FILENAME).read_text(encoding="utf-8")
        )
        assert len(templates) == 2

        # 验证去重保留了新的那条
        report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
        assert "新" in report


class TestCorruptFileSkipped:
    """损坏文件：JSON 格式异常时跳过不崩溃。"""

    def test_corrupt_json_skipped(self, tmp_path: Path):
        badcases_dir = tmp_path / "bad_cases"
        badcases_dir.mkdir()

        # 正常文件
        _write_badcase(
            badcases_dir / "msg-ok.json",
            {
                "message_id": "msg-ok",
                "reason": "不完整",
                "detail": "正常",
                "created_at": "2026-05-01T10:00:00+00:00",
            },
        )

        # 损坏文件
        (badcases_dir / "corrupt.json").write_text("{bad json!!!", encoding="utf-8")

        # 非对象文件
        (badcases_dir / "array.json").write_text("[1,2,3]", encoding="utf-8")

        output_dir = tmp_path / "output"
        result = classify_badcases(badcases_dir, output_dir)

        assert result["total_files"] == 3
        assert result["total_records"] == 1  # 只有 1 条有效
        assert result["deduped_count"] == 1
        assert result["skipped_count"] == 2

        # 报告中包含跳过信息
        report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
        assert "跳过的文件" in report
        assert "corrupt.json" in report
        assert "array.json" in report

    def test_missing_required_fields_skipped(self, tmp_path: Path):
        badcases_dir = tmp_path / "bad_cases"
        badcases_dir.mkdir()

        # 正常文件
        _write_badcase(
            badcases_dir / "msg-ok.json",
            {
                "message_id": "msg-ok",
                "reason": "不完整",
                "detail": "正常",
                "created_at": "2026-05-01T10:00:00+00:00",
            },
        )

        # 缺少 reason
        _write_badcase(
            badcases_dir / "no-reason.json",
            {"message_id": "msg-x", "detail": "无 reason"},
        )

        # 缺少 message_id
        _write_badcase(
            badcases_dir / "no-mid.json",
            {"reason": "信息不准确", "detail": "无 mid"},
        )

        output_dir = tmp_path / "output"
        result = classify_badcases(badcases_dir, output_dir)

        assert result["total_records"] == 1
        assert result["skipped_count"] == 2


class TestTemplateGeneration:
    """测试模板生成质量。"""

    def test_template_has_all_required_fields(self):
        records = [
            {
                "message_id": "msg-001",
                "reason": "信息不准确",
                "detail": "Agent 说有 5 个任务",
                "title": "回复不准确",
                "_source_file": "msg-001_001.json",
            },
        ]
        templates = generate_testcase_templates(records)
        assert len(templates) == 1
        t = templates[0]
        assert t["id"] == "BAD-001"
        assert t["source_message_id"] == "msg-001"
        assert t["source_reason"] == "信息不准确"
        assert t["source_detail"] == "Agent 说有 5 个任务"
        assert t["suggested_category"] == "accuracy"
        assert t["template_type"] == "negative"
        assert t["status"] == "draft"

    def test_empty_records_produce_empty_templates(self):
        templates = generate_testcase_templates([])
        assert templates == []
