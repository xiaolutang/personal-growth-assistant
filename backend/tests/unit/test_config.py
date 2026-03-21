"""Config 单元测试"""
import pytest
import os
from unittest.mock import patch

from app.core.config import Settings, get_settings


class TestSettings:
    """Settings 测试"""

    def test_default_values(self):
        """测试默认值"""
        settings = Settings()

        assert settings.APP_NAME == "Personal Growth Assistant"
        assert settings.APP_VERSION == "0.3.0"
        assert settings.DEBUG is False
        # DATA_DIR 现在使用绝对路径（基于项目根目录）
        assert settings.DATA_DIR.endswith("/data")
        assert settings.EMBEDDING_MODEL == "text-embedding-v3"

    def test_sqlite_db_path_default(self):
        """测试 SQLite 路径默认值"""
        settings = Settings(DATA_DIR="/custom/data")
        assert settings.sqlite_db_path == "/custom/data/index.db"

    def test_sqlite_db_path_custom(self):
        """测试自定义 SQLite 路径"""
        settings = Settings(SQLITE_PATH="/custom/path.db")
        assert settings.sqlite_db_path == "/custom/path.db"

    def test_validate_llm_success(self):
        """测试 LLM 配置验证成功"""
        settings = Settings(
            LLM_API_KEY="test-key",
            LLM_BASE_URL="https://api.example.com",
            LLM_MODEL="gpt-4",
        )
        assert settings.validate_llm() is True

    def test_validate_llm_missing(self):
        """测试 LLM 配置验证失败"""
        # 使用空字符串显式设置，因为 pydantic-settings 默认值是空字符串
        settings = Settings(LLM_API_KEY="", LLM_BASE_URL="", LLM_MODEL="")
        with pytest.raises(ValueError) as exc_info:
            settings.validate_llm()
        assert "LLM_API_KEY" in str(exc_info.value)

    def test_get_settings_cached(self):
        """测试配置单例缓存"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_env_override(self):
        """测试环境变量覆盖"""
        with patch.dict(os.environ, {"DATA_DIR": "/env/data"}):
            # 清除缓存并重新获取
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.DATA_DIR == "/env/data"
            # 恢复缓存
            get_settings.cache_clear()
