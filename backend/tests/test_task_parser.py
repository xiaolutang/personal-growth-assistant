"""测试 TaskParser 服务"""
import pytest
from datetime import datetime

from app.callers import MockCaller
from app.services import TaskParser


class TestTaskParser:
    """TaskParser 单元测试"""

    @pytest.mark.asyncio
    async def test_parse_task(self):
        """测试解析任务类型"""
        mock_response = '''{"tasks": [
            {"name": "完成报告", "category": "task", "status": "waitStart"}
        ]}'''
        caller = MockCaller(response=mock_response)
        parser = TaskParser(caller=caller)

        result = await parser.parse("明天完成报告")
        assert len(result) == 1
        assert result[0].name == "完成报告"
        assert result[0].category.value == "task"

    @pytest.mark.asyncio
    async def test_parse_inbox(self):
        """测试解析灵感类型"""
        mock_response = '''{"tasks": [
            {"name": "学习 Rust", "category": "inbox", "status": "waitStart"}
        ]}'''
        caller = MockCaller(response=mock_response)
        parser = TaskParser(caller=caller)

        result = await parser.parse("有个想法：学习 Rust")
        assert len(result) == 1
        assert result[0].category.value == "inbox"

    @pytest.mark.asyncio
    async def test_parse_note(self):
        """测试解析笔记类型"""
        mock_response = '''{"tasks": [
            {"name": "RAG 笔记", "category": "note", "status": "waitStart"}
        ]}'''
        caller = MockCaller(response=mock_response)
        parser = TaskParser(caller=caller)

        result = await parser.parse("记录一下 RAG 的学习笔记")
        assert len(result) == 1
        assert result[0].category.value == "note"

    @pytest.mark.asyncio
    async def test_parse_project(self):
        """测试解析项目类型"""
        mock_response = '''{"tasks": [
            {"name": "个人成长助手", "category": "project", "status": "waitStart"}
        ]}'''
        caller = MockCaller(response=mock_response)
        parser = TaskParser(caller=caller)

        result = await parser.parse("启动个人成长助手项目")
        assert len(result) == 1
        assert result[0].category.value == "project"

    @pytest.mark.asyncio
    async def test_parse_multiple_items(self):
        """测试解析多个条目"""
        mock_response = '''{"tasks": [
            {"name": "任务1", "category": "task", "status": "waitStart"},
            {"name": "灵感1", "category": "inbox", "status": "waitStart"},
            {"name": "笔记1", "category": "note", "status": "waitStart"}
        ]}'''
        caller = MockCaller(response=mock_response)
        parser = TaskParser(caller=caller)

        result = await parser.parse("今天要做的：任务1。有个想法：灵感1。记一下：笔记1")
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_parse_empty_input(self):
        """测试空输入"""
        mock_response = '{"tasks": []}'
        caller = MockCaller(response=mock_response)
        parser = TaskParser(caller=caller)

        result = await parser.parse("")
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_parse_with_planned_date(self):
        """测试带计划日期的解析"""
        mock_response = '''{"tasks": [
            {"name": "开会", "category": "task", "status": "waitStart", "planned_date": "2026-03-12 15:00"}
        ]}'''
        caller = MockCaller(response=mock_response)
        parser = TaskParser(caller=caller)

        result = await parser.parse("明天下午3点开会")
        assert len(result) == 1
        assert result[0].planned_date == datetime(2026, 3, 12, 15, 0)
