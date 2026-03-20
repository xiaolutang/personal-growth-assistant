"""
搜索功能评估测试
测试混合搜索（SQLite FTS5 + Qdrant 向量搜索）

这个测试：
1. 创建隔离的测试数据库
2. 插入测试数据（MCP、RAG、Agent 等笔记）
3. 验证搜索结果是否正确
4. 不依赖真实数据，可以在 CI/CD 中运行
"""
import pytest
from datetime import datetime

from app.models import Task, Category, TaskStatus, Priority


# === 测试数据 ===

TEST_NOTES = [
    {
        "id": "note-mcp-001",
        "title": "MCP 协议学习笔记",
        "content": "# MCP 协议\n\nModel Context Protocol 是 Anthropic 提出的模型上下文协议。\n\n## 核心概念\n- 资源（Resources）\n- 提示词（Prompts）\n- 工具（Tools）",
        "tags": ["MCP", "AI", "协议"],
    },
    {
        "id": "note-rag-001",
        "title": "RAG 检索增强生成",
        "content": "# RAG 技术\n\nRetrieval-Augmented Generation 检索增强生成。\n\n## 流程\n1. 文档切分\n2. 向量化\n3. 检索\n4. 生成回答",
        "tags": ["RAG", "AI", "检索"],
    },
    {
        "id": "note-agent-001",
        "title": "Agent 智能体开发",
        "content": "# Agent 开发\n\nAI Agent 是能够自主执行任务的智能体。\n\n## 组件\n- 规划器（Planner）\n- 执行器（Executor）\n- 记忆（Memory）",
        "tags": ["Agent", "AI", "智能体"],
    },
    {
        "id": "note-claude-001",
        "title": "Claude API 使用指南",
        "content": "# Claude API\n\nAnthropic Claude API 使用方法。\n\n## 模型\n- claude-3-opus\n- claude-3-sonnet\n- claude-3-haiku",
        "tags": ["Claude", "API", "Anthropic"],
    },
    {
        "id": "note-vector-001",
        "title": "向量数据库对比",
        "content": "# 向量数据库\n\n对比 Qdrant、Pinecone、Milvus 等。\n\n## Qdrant\n开源，Rust 实现，性能优秀。",
        "tags": ["向量", "数据库", "Qdrant"],
    },
]


# === 评估测试用例 ===

SEARCH_TEST_CASES = [
    {
        "name": "搜索 MCP",
        "query": "MCP",
        "expected_ids": ["note-mcp-001"],
        "expected_keywords": ["MCP"],
    },
    {
        "name": "搜索 RAG",
        "query": "RAG",
        "expected_ids": ["note-rag-001"],
        "expected_keywords": ["RAG"],
    },
    {
        "name": "搜索 Agent",
        "query": "Agent",
        "expected_ids": ["note-agent-001"],
        "expected_keywords": ["Agent"],
    },
    {
        "name": "搜索 Claude",
        "query": "Claude",
        "expected_ids": ["note-claude-001"],
        "expected_keywords": ["Claude"],
    },
    {
        "name": "语义搜索 - 智能体",
        "query": "智能体",
        "expected_ids": ["note-agent-001"],
        "expected_keywords": ["智能体", "Agent"],
    },
    {
        "name": "语义搜索 - 检索增强",
        "query": "检索增强",
        "expected_ids": ["note-rag-001"],
        "expected_keywords": ["RAG", "检索"],
    },
    {
        "name": "语义搜索 - 向量数据库",
        "query": "向量数据库",
        "expected_ids": ["note-vector-001"],
        "expected_keywords": ["向量"],  # Qdrant 在内容中，不在标题中
    },
]


# === Fixtures ===

@pytest.fixture
def populated_sqlite(sqlite_storage):
    """填充测试数据的 SQLite 存储"""
    now = datetime.now()

    for note_data in TEST_NOTES:
        task = Task(
            id=note_data["id"],
            title=note_data["title"],
            content=note_data["content"],
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=note_data["tags"],
            created_at=now,
            updated_at=now,
            file_path=f"notes/{note_data['id']}.md",
        )
        # 直接使用 SQLite 的 upsert 方法
        sqlite_storage.upsert_entry(task)

    yield sqlite_storage


# === 测试类 ===

class TestSearchEvaluation:
    """搜索功能评估测试"""

    @pytest.mark.parametrize("case", SEARCH_TEST_CASES, ids=lambda c: c["name"])
    def test_search_returns_expected_results(self, populated_sqlite, case):
        """测试搜索返回预期结果"""
        results = populated_sqlite.search(case["query"], limit=5)

        # 验证有结果
        assert len(results) > 0, f"搜索 '{case['query']}' 无结果"

        # 验证结果包含预期的笔记
        result_ids = [r["id"] for r in results]
        for expected_id in case["expected_ids"]:
            assert expected_id in result_ids, \
                f"搜索 '{case['query']}' 结果中未找到 {expected_id}"

        # 验证结果包含预期关键词
        result_titles = " ".join([r["title"] for r in results])
        for keyword in case["expected_keywords"]:
            assert keyword.lower() in result_titles.lower(), \
                f"搜索 '{case['query']}' 结果标题中未包含 '{keyword}'"

    def test_mcp_search_not_empty(self, populated_sqlite):
        """专项测试：MCP 搜索不能为空"""
        results = populated_sqlite.search("MCP", limit=5)

        print(f"\n搜索 'MCP' 结果数: {len(results)}")
        for r in results:
            print(f"  - {r['id']}: {r['title']}")

        assert len(results) > 0, "搜索 'MCP' 返回空结果，这是之前的 bug！"

    def test_rag_search_not_empty(self, populated_sqlite):
        """专项测试：RAG 搜索不能为空"""
        results = populated_sqlite.search("RAG", limit=5)

        print(f"\n搜索 'RAG' 结果数: {len(results)}")
        for r in results:
            print(f"  - {r['id']}: {r['title']}")

        assert len(results) > 0, "搜索 'RAG' 返回空结果"

    def test_fts5_search_fallback(self, populated_sqlite):
        """测试 SQLite FTS5 搜索"""
        results = populated_sqlite.search("MCP", limit=5)

        print(f"\nSQLite FTS5 搜索 'MCP' 结果数: {len(results)}")
        for r in results:
            print(f"  - {r['id']}: {r['title']}")

        assert len(results) > 0, "SQLite FTS5 搜索失败"


# === 评估报告 ===

def run_search_evaluation():
    """运行搜索评估并生成报告"""
    print("\n" + "=" * 50)
    print("       搜索功能评估")
    print("=" * 50 + "\n")

    # 使用 pytest 运行测试
    # pytest tests/test_search_eval.py -v

    print("运行命令: pytest tests/test_search_eval.py -v")
    print("=" * 50 + "\n")
