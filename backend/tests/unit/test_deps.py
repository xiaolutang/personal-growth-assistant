"""deps.py 服务获取统一化测试"""
import pytest

from app.routers import deps


@pytest.fixture(autouse=True)
def reset_deps():
    """每个测试前后重置 deps 状态"""
    original_storage = deps.storage
    deps.reset_all_services()
    yield
    deps.storage = original_storage
    deps.reset_all_services()


def _setup_mock_storage():
    """创建 mock storage"""
    from unittest.mock import MagicMock

    storage = MagicMock()
    storage.sqlite = MagicMock()
    storage.neo4j = MagicMock()
    storage.llm_caller = MagicMock()
    deps.storage = storage
    return storage


class TestGetReviewService:
    def test_returns_same_instance(self):
        """多次调用返回同一实例"""
        _setup_mock_storage()
        s1 = deps.get_review_service()
        s2 = deps.get_review_service()
        assert s1 is s2

    def test_sqlite_set_at_creation(self):
        """存储引用在创建时注入，无需每次 setter"""
        _setup_mock_storage()
        service = deps.get_review_service()
        assert service._sqlite is deps.storage.sqlite

    def test_no_side_effect_on_repeated_calls(self):
        """多次调用不触发 setter（_sqlite 不被覆盖为不同引用）"""
        _setup_mock_storage()
        s1 = deps.get_review_service()
        original_sqlite = s1._sqlite
        s2 = deps.get_review_service()
        assert s2._sqlite is original_sqlite


class TestGetKnowledgeService:
    def test_returns_same_instance(self):
        """多次调用返回同一实例"""
        _setup_mock_storage()
        s1 = deps.get_knowledge_service()
        s2 = deps.get_knowledge_service()
        assert s1 is s2

    def test_storages_set_at_creation(self):
        """Neo4j 和 SQLite 在创建时注入"""
        _setup_mock_storage()
        service = deps.get_knowledge_service()
        assert service._neo4j is deps.storage.neo4j
        assert service._sqlite is deps.storage.sqlite

    def test_reset_then_recreate(self):
        """reset 后重新获取，新实例引用正确"""
        _setup_mock_storage()
        s1 = deps.get_knowledge_service()
        deps.reset_all_services()
        s2 = deps.get_knowledge_service()
        assert s1 is not s2
        assert s2._neo4j is deps.storage.neo4j
        assert s2._sqlite is deps.storage.sqlite


class TestStorageNotInitialized:
    def test_review_service_raises_503(self):
        """storage=None 时 get_review_service 抛 503"""
        deps.storage = None
        with pytest.raises(Exception) as exc_info:
            deps.get_review_service()
        assert exc_info.value.status_code == 503

    def test_knowledge_service_raises_503(self):
        """storage=None 时 get_knowledge_service 抛 503"""
        deps.storage = None
        with pytest.raises(Exception) as exc_info:
            deps.get_knowledge_service()
        assert exc_info.value.status_code == 503
