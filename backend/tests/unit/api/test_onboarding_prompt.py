"""B88: Onboarding AI Prompt 测试 — 验证 is_new_user 引导段落注入"""
import pytest

from app.services.ai_chat_service import (
    AIChatService,
    SYSTEM_PROMPT,
    PAGE_ROLE_PROMPTS,
    ONBOARDING_PROMPT,
)


@pytest.fixture
def service():
    return AIChatService()


class TestOnboardingPromptInjection:
    """is_new_user 触发 onboarding 引导段注入"""

    def test_new_user_prompt_contains_onboarding(self, service):
        """is_new_user=true 时 prompt 包含 onboarding 引导文本"""
        ctx = {"is_new_user": True}
        prompt = service._build_system_prompt(ctx)
        assert ONBOARDING_PROMPT in prompt
        assert "日知" in prompt
        assert "灵感" in prompt or "任务" in prompt or "笔记" in prompt

    def test_existing_user_no_onboarding(self, service):
        """is_new_user=false 时 prompt 不包含 onboarding 文本"""
        ctx = {"is_new_user": False}
        prompt = service._build_system_prompt(ctx)
        assert ONBOARDING_PROMPT not in prompt

    def test_missing_is_new_user_same_as_false(self, service):
        """is_new_user 缺失时行为与 false 一致"""
        ctx = {"page": "home"}
        prompt = service._build_system_prompt(ctx)
        assert ONBOARDING_PROMPT not in prompt

    def test_no_context_same_as_false(self, service):
        """context 为 None 时行为与 false 一致"""
        prompt = service._build_system_prompt(None)
        assert ONBOARDING_PROMPT not in prompt


class TestOnboardingWithPageHome:
    """page=home + is_new_user=true 组合验证"""

    def test_all_three_parts_injected(self, service):
        """SYSTEM_PROMPT、home role prompt、onboarding 段三者都注入"""
        ctx = {"page": "home", "is_new_user": True}
        prompt = service._build_system_prompt(ctx)

        # 三部分都存在
        assert SYSTEM_PROMPT in prompt
        assert PAGE_ROLE_PROMPTS["home"] in prompt
        assert ONBOARDING_PROMPT in prompt

    def test_correct_order(self, service):
        """三部分注入顺序：SYSTEM_PROMPT -> home role -> onboarding"""
        ctx = {"page": "home", "is_new_user": True}
        prompt = service._build_system_prompt(ctx)

        idx_system = prompt.find(SYSTEM_PROMPT)
        idx_home = prompt.find(PAGE_ROLE_PROMPTS["home"])
        idx_onboarding = prompt.find(ONBOARDING_PROMPT)

        assert idx_system >= 0
        assert idx_home >= 0
        assert idx_onboarding >= 0
        assert idx_system < idx_home < idx_onboarding, (
            f"顺序错误: system={idx_system}, home={idx_home}, onboarding={idx_onboarding}"
        )


class TestOnboardingPromptLength:
    """prompt 长度约束验证"""

    def test_total_prompt_under_500_chars(self, service):
        """is_new_user=true + page=home 时完整 prompt 不超过 500 字"""
        ctx = {"page": "home", "is_new_user": True}
        prompt = service._build_system_prompt(ctx)
        assert len(prompt) <= 500, (
            f"Prompt 长度 {len(prompt)} 超过 500 字限制"
        )


class TestOnboardingPromptContent:
    """onboarding prompt 内容断言"""

    def test_contains_example_keywords(self):
        """onboarding prompt 包含灵感/任务/笔记示例关键词"""
        assert "灵感" in ONBOARDING_PROMPT
        assert "任务" in ONBOARDING_PROMPT
        assert "笔记" in ONBOARDING_PROMPT

    def test_contains_self_introduction(self):
        """onboarding prompt 包含自我介绍"""
        assert "日知" in ONBOARDING_PROMPT

    def test_contains_encouragement(self):
        """onboarding prompt 包含鼓励用户尝试"""
        assert "试试" in ONBOARDING_PROMPT or "随意" in ONBOARDING_PROMPT

    def test_onboarding_prompt_length(self):
        """onboarding 段本身不超过 300 字"""
        assert len(ONBOARDING_PROMPT) <= 300, (
            f"ONBOARDING_PROMPT 长度 {len(ONBOARDING_PROMPT)} 超过 300 字限制"
        )


class TestOnboardingNoRegression:
    """回归验证：现有功能不受影响"""

    def test_page_role_without_onboarding(self, service):
        """有 page 但 is_new_user 缺失时，page role 正常注入"""
        ctx = {"page": "review"}
        prompt = service._build_system_prompt(ctx)
        assert PAGE_ROLE_PROMPTS["review"] in prompt
        assert ONBOARDING_PROMPT not in prompt

    def test_page_data_still_appended(self, service):
        """is_new_user=true 时 page_data 仍然正常注入"""
        ctx = {"page": "home", "is_new_user": True, "page_data": {"tasks": 5}}
        prompt = service._build_system_prompt(ctx)
        assert "tasks: 5" in prompt

    def test_filters_still_appended(self, service):
        """is_new_user=true 时 filters 仍然正常注入"""
        ctx = {"is_new_user": True, "filters": {"status": "doing"}}
        prompt = service._build_system_prompt(ctx)
        assert "doing" in prompt

    def test_unknown_page_with_onboarding(self, service):
        """未知 page + is_new_user=true 时，通用 page 段 + onboarding 都注入"""
        ctx = {"page": "settings", "is_new_user": True}
        prompt = service._build_system_prompt(ctx)
        assert "settings" in prompt
        assert ONBOARDING_PROMPT in prompt
