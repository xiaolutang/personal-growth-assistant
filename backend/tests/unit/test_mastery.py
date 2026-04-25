"""B97: 掌握度共享模块测试 — app/utils/mastery.py"""
import pytest

from app.utils.mastery import calculate_mastery_from_stats


class TestCalculateMastery:
    """calculate_mastery_from_stats 阈值矩阵测试"""

    # === 基础阈值矩阵 ===

    def test_zero_entry_returns_new(self):
        assert calculate_mastery_from_stats(0, 0, 0) == "new"

    def test_entry1_no_recent_no_note_returns_beginner(self):
        assert calculate_mastery_from_stats(1, 0, 0) == "beginner"

    def test_entry3_recent1_returns_intermediate(self):
        assert calculate_mastery_from_stats(3, 1, 0) == "intermediate"

    def test_entry6_note3_returns_advanced(self):
        """6 entries + 3 notes → note_ratio = 0.5 > 0.3 → advanced"""
        assert calculate_mastery_from_stats(6, 0, 3) == "advanced"

    # === relationship_count 折算 ===

    def test_relationship_count_converted_to_entry(self):
        """4 relationships ≈ 2 entries → effective=3, recent>0 → intermediate"""
        assert calculate_mastery_from_stats(1, 1, 0, relationship_count=4) == "intermediate"

    def test_relationship_count_alone(self):
        """12 relationships ≈ 6 entries → effective=6, 但 no note → intermediate"""
        result = calculate_mastery_from_stats(0, 1, 0, relationship_count=12)
        assert result == "intermediate"

    def test_relationship_negative_treated_as_zero(self):
        """负数 relationship_count 按 max(0, ...) 处理"""
        assert calculate_mastery_from_stats(1, 0, 0, relationship_count=-10) == "beginner"

    # === KnowledgeService 调用路径（3 参数版本） ===

    def test_knowledge_service_3arg_new(self):
        """KnowledgeService 调用路径：3 参数，无 entry"""
        assert calculate_mastery_from_stats(0, 0, 0) == "new"

    def test_knowledge_service_3arg_beginner(self):
        assert calculate_mastery_from_stats(1, 0, 0) == "beginner"

    # === ReviewService 调用路径（4 参数版本） ===

    def test_review_service_4arg_advanced(self):
        """ReviewService 调用路径：含 relationship_count"""
        assert calculate_mastery_from_stats(4, 1, 2, relationship_count=4) == "advanced"

    # === 回归 ===

    def test_review_service_static_delegates_correctly(self):
        """ReviewService._calculate_mastery_from_stats 委托到 utils 后结果不变"""
        from app.services.review_service import ReviewService
        assert ReviewService._calculate_mastery_from_stats(6, 1, 3) == "advanced"
        assert ReviewService._calculate_mastery_from_stats(3, 1, 0) == "intermediate"
        assert ReviewService._calculate_mastery_from_stats(1, 0, 0) == "beginner"
        assert ReviewService._calculate_mastery_from_stats(0, 0, 0) == "new"


class TestServiceWrapperDelegation:
    """验证 service wrapper 委托到 utils.mastery 的行为"""

    def test_knowledge_service_wrapper_delegates(self):
        """KnowledgeService._calculate_mastery_from_stats 直接调 utils.mastery"""
        from unittest.mock import patch
        from app.services import knowledge_service as ks_module

        svc = ks_module.KnowledgeService.__new__(ks_module.KnowledgeService)
        with patch.object(ks_module, "_calc_mastery", return_value="beginner") as mock_fn:
            result = svc._calculate_mastery_from_stats(1, 0, 0)
            assert result == "beginner"
            mock_fn.assert_called_once_with(
                entry_count=1, recent_count=0, note_count=0, relationship_count=0,
            )

    def test_knowledge_service_wrapper_with_relationship(self):
        """KnowledgeService._calculate_mastery_from_stats 支持传 relationship_count"""
        from unittest.mock import patch
        from app.services import knowledge_service as ks_module

        svc = ks_module.KnowledgeService.__new__(ks_module.KnowledgeService)
        with patch.object(ks_module, "_calc_mastery", return_value="intermediate") as mock_fn:
            result = svc._calculate_mastery_from_stats(1, 1, 0, relationship_count=4)
            assert result == "intermediate"
            mock_fn.assert_called_once_with(
                entry_count=1, recent_count=1, note_count=0, relationship_count=4,
            )

    def test_review_service_wrapper_delegates(self):
        """ReviewService._calculate_mastery_from_stats 委托到 utils.mastery"""
        from unittest.mock import patch
        from app.services import review_service as rs_module

        with patch.object(rs_module, "calculate_mastery_from_stats", return_value="advanced") as mock_fn:
            result = rs_module.ReviewService._calculate_mastery_from_stats(4, 1, 2, relationship_count=4)
            assert result == "advanced"
            mock_fn.assert_called_once_with(
                entry_count=4, recent_count=1, note_count=2, relationship_count=4,
            )

    def test_knowledge_service_no_review_service_import(self):
        """验证 KnowledgeService 不再从 review_service 导入"""
        import inspect
        from app.services.knowledge_service import KnowledgeService

        source = inspect.getsource(KnowledgeService._calculate_mastery_from_stats)
        assert "from app.services.review_service" not in source
        assert "_calc_mastery" in source
