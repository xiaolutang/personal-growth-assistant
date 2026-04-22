"""AI 对话服务 — 页面角色 prompt 分支测试"""
import pytest

from app.services.ai_chat_service import AIChatService, PAGE_ROLE_PROMPTS


@pytest.fixture
def service():
    return AIChatService(llm_caller=None)


class TestBuildSystemPromptPageRoles:
    """验证 _build_system_prompt 对各页面角色的注入"""

    def test_home_role_injected(self, service):
        prompt = service._build_system_prompt({"page": "home"})
        assert "晨报助手" in prompt
        assert PAGE_ROLE_PROMPTS["home"] in prompt

    def test_explore_role_injected(self, service):
        prompt = service._build_system_prompt({"page": "explore"})
        assert "搜索助手" in prompt
        assert PAGE_ROLE_PROMPTS["explore"] in prompt

    def test_review_role_injected(self, service):
        prompt = service._build_system_prompt({"page": "review"})
        assert "分析助手" in prompt
        assert PAGE_ROLE_PROMPTS["review"] in prompt

    def test_entry_detail_role_injected(self, service):
        prompt = service._build_system_prompt({"page": "entry_detail"})
        assert "编辑助手" in prompt
        assert PAGE_ROLE_PROMPTS["entry_detail"] in prompt

    def test_unknown_page_fallback(self, service):
        prompt = service._build_system_prompt({"page": "unknown_page"})
        assert "unknown_page" in prompt
        # 不应包含任何已知角色
        for role_prompt in PAGE_ROLE_PROMPTS.values():
            assert role_prompt not in prompt

    def test_no_context(self, service):
        prompt = service._build_system_prompt(None)
        # 仅包含基础 system prompt
        assert "日知" in prompt
        for role_prompt in PAGE_ROLE_PROMPTS.values():
            assert role_prompt not in prompt

    def test_empty_context(self, service):
        prompt = service._build_system_prompt({})
        assert "日知" in prompt
        for role_prompt in PAGE_ROLE_PROMPTS.values():
            assert role_prompt not in prompt

    def test_page_data_injected(self, service):
        prompt = service._build_system_prompt({
            "page": "home",
            "page_data": {"todo_count": 5, "completion_rate": 60},
        })
        assert "todo_count" in prompt
        assert "5" in prompt
        assert "completion_rate" in prompt
        assert "60" in prompt

    def test_all_page_roles_have_content(self):
        """确保所有已知页面角色 prompt 非空"""
        for page, role in PAGE_ROLE_PROMPTS.items():
            assert role.strip(), f"PAGE_ROLE_PROMPTS['{page}'] 不应为空"
