"""数据同步逻辑"""
import asyncio
import json
import os
from typing import List, Optional, Dict, Any

from app.models import Task, Concept, ConceptRelation, ExtractedKnowledge
from app.storage.markdown import MarkdownStorage

# 可选依赖
try:
    from app.storage.neo4j_client import Neo4jClient
except ImportError:
    Neo4jClient = None

try:
    from app.storage.qdrant_client import QdrantClient
except ImportError:
    QdrantClient = None

try:
    from app.storage.sqlite import SQLiteStorage
except ImportError:
    SQLiteStorage = None


class SyncService:
    """数据同步服务 - Markdown → SQLite → Neo4j + Qdrant"""

    def __init__(
        self,
        markdown_storage: MarkdownStorage,
        sqlite_storage=None,
        neo4j_client=None,
        qdrant_client=None,
        llm_caller=None,
    ):
        self.markdown = markdown_storage
        self.sqlite = sqlite_storage
        self.neo4j = neo4j_client
        self.qdrant = qdrant_client
        self.llm_caller = llm_caller

    async def sync_entry(self, entry: Task) -> bool:
        """
        同步单个条目到 SQLite + Neo4j + Qdrant

        流程：
        1. 同步到 SQLite（快速索引）- 同步执行
        2. 提取知识（tags, concepts, relations）
        3. 并行同步到 Neo4j + Qdrant
        """
        try:
            # 1. 同步到 SQLite（如果可用）- 同步执行，因为 SQLite 操作很快
            if self.sqlite:
                self.sqlite.upsert_entry(entry)

            # 2. 提取知识
            knowledge = await self._extract_knowledge(entry)

            # 3. 并行同步到 Neo4j 和 Qdrant
            tasks = []

            if self.neo4j and self.neo4j.driver:
                tasks.append(self._sync_to_neo4j(entry, knowledge))

            if self.qdrant:
                try:
                    tasks.append(self.qdrant.upsert_entry(entry))
                except Exception as e:
                    import logging
                    logging.warning(f"Qdrant 同步失败，忽略: {e}")

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            return True
        except Exception as e:
            print(f"同步失败: {e}")
            return False

    async def sync_to_graph_and_vector(self, entry: Task) -> bool:
        """
        仅同步到 Neo4j + Qdrant（后台执行，不阻塞响应）

        用于创建条目后立即返回响应，但后台继续同步到知识图谱和向量库
        """
        try:
            # 提取知识
            knowledge = await self._extract_knowledge(entry)

            # 并行同步到 Neo4j 和 Qdrant
            tasks = []

            if self.neo4j and self.neo4j.driver:
                tasks.append(self._sync_to_neo4j(entry, knowledge))

            if self.qdrant:
                try:
                    tasks.append(self.qdrant.upsert_entry(entry))
                except Exception as e:
                    import logging
                    logging.warning(f"Qdrant 同步失败，忽略: {e}")

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            return True
        except Exception as e:
            print(f"图谱/向量同步失败: {e}")
            return False

    async def _sync_to_neo4j(self, entry: Task, knowledge: ExtractedKnowledge):
        """同步到 Neo4j（内部方法）"""
        await self.neo4j.create_entry(entry)

        # 并行创建概念节点
        if knowledge.concepts:
            concept_tasks = [
                self.neo4j.create_concept(concept)
                for concept in knowledge.concepts
            ]
            await asyncio.gather(*concept_tasks, return_exceptions=True)

            # 创建条目与概念的关系
            concept_names = [c.name for c in knowledge.concepts]
            await self.neo4j.create_entry_mentions(entry.id, concept_names)

        # 并行创建概念关系
        if knowledge.relations:
            relation_tasks = [
                self.neo4j.create_concept_relation(relation)
                for relation in knowledge.relations
            ]
            await asyncio.gather(*relation_tasks, return_exceptions=True)

    async def delete_entry(self, entry_id: str) -> bool:
        """删除条目及其关联数据（并行删除）"""
        try:
            tasks = []

            # 1. 删除 SQLite 索引（同步，因为很快)
            if self.sqlite:
                self.sqlite.delete_entry(entry_id)

            # 2. 并行删除 Neo4j 和 Qdrant
            # Neo4j: 优雅处理连接失败
            if self.neo4j:
                try:
                    tasks.append(self.neo4j.delete_entry(entry_id))
                except Exception as e:
                    # Neo4j 删除失败，记录日志但继续
                    import logging
                    logging.warning(f"Neo4j 删除失败，忽略: {e}")

            # Qdrant: 优雅处理连接失败
            if self.qdrant:
                try:
                    tasks.append(self.qdrant.delete_entry(entry_id))
                except Exception as e:
                    # Qdrant 删除失败，记录日志但继续
                    import logging
                    logging.warning(f"Qdrant 删除失败，忽略: {e}")

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # 3. 删除 Markdown 文件
            self.markdown.delete_entry(entry_id)

            return True
        except Exception as e:
            print(f"删除失败: {e}")
            return False

    async def sync_all(self) -> Dict[str, int]:
        """同步所有 Markdown 文件"""
        entries = self.markdown.scan_all()
        success = 0
        failed = 0

        for entry in entries:
            if await self.sync_entry(entry):
                success += 1
            else:
                failed += 1

        return {"success": success, "failed": failed}

    async def _extract_knowledge(self, entry: Task) -> ExtractedKnowledge:
        """
        从条目中提取知识（tags, concepts, relations）

        优先使用 LLM 提取，如果没有 LLM 则使用简单规则
        """
        if self.llm_caller:
            return await self._extract_with_llm(entry)
        else:
            return self._extract_with_rules(entry)

    async def _extract_with_llm(self, entry: Task) -> ExtractedKnowledge:
        """使用 LLM 提取知识"""
        prompt = f"""请从以下文本中提取：
1. 标签（keywords）
2. 技术概念（concepts）
3. 概念之间的关系（relations）

文本：
{entry.title}
{entry.content}

返回 JSON 格式：
{{
  "tags": ["MCP", "LLM应用开发"],
  "concepts": [
    {{"name": "MCP", "category": "技术"}},
    {{"name": "Host", "category": "概念"}}
  ],
  "relations": [
    {{"from": "MCP", "to": "LLM应用开发", "type": "PART_OF"}},
    {{"from": "Host", "to": "MCP", "type": "PART_OF"}}
  ]
}}

只输出 JSON，不要有其他内容。"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm_caller.call(messages, {"type": "json_object"})
            data = json.loads(response)

            concepts = [
                Concept(
                    name=c["name"],
                    category=c.get("category", "技术"),
                )
                for c in data.get("concepts", [])
            ]

            relations = [
                ConceptRelation(
                    from_concept=r["from"],
                    to_concept=r["to"],
                    relation_type=r.get("type", "RELATED_TO"),
                )
                for r in data.get("relations", [])
            ]

            return ExtractedKnowledge(
                tags=data.get("tags", []),
                concepts=concepts,
                relations=relations,
            )
        except Exception as e:
            print(f"LLM 提取失败: {e}")
            return self._extract_with_rules(entry)

    def _extract_with_rules(self, entry: Task) -> ExtractedKnowledge:
        """使用简单规则提取知识"""
        import re

        # 从内容中提取 #标签
        content = entry.content
        tags = re.findall(r"#(\w+)", content)
        tags = list(set(tags))  # 去重

        # 使用已有标签作为概念
        concepts = [
            Concept(name=tag, category="技术")
            for tag in tags
        ]

        # 不推断关系
        relations = []

        return ExtractedKnowledge(
            tags=tags,
            concepts=concepts,
            relations=relations,
        )

    async def resync_entry(self, entry_id: str) -> bool:
        """重新同步单个条目（用于文件编辑后）"""
        entry = self.markdown.read_entry(entry_id)
        if entry:
            return await self.sync_entry(entry)
        return False


async def init_storage(
    data_dir: str = "./data",
    sqlite_path: str = None,
    neo4j_uri: str = None,
    neo4j_username: str = None,
    neo4j_password: str = None,
    qdrant_url: str = None,
    qdrant_api_key: str = None,
    llm_caller=None,
    embedding_model: str = None,
) -> SyncService:
    """初始化存储服务"""
    # 创建存储实例
    markdown_storage = MarkdownStorage(data_dir)

    # 初始化 SQLite（默认开启）
    sqlite_storage = None
    if SQLiteStorage:
        try:
            db_path = sqlite_path or f"{data_dir}/index.db"
            sqlite_storage = SQLiteStorage(db_path)
            # 从 Markdown 同步到 SQLite
            count = sqlite_storage.sync_from_markdown(markdown_storage)
            print(f"SQLite 索引同步完成: {count} 条记录")
        except Exception as e:
            print(f"SQLite 初始化失败: {e}")
            sqlite_storage = None

    # 初始化 Neo4j（如果配置了）
    neo4j_client = None
    if neo4j_uri and Neo4jClient:
        try:
            neo4j_client = Neo4jClient(neo4j_uri, neo4j_username, neo4j_password)
            await neo4j_client.connect()
            await neo4j_client.create_indexes()
        except Exception as e:
            print(f"Neo4j 连接失败: {e}")
            neo4j_client = None

    # 初始化 Embedding 服务
    embedding_service = None
    embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

    if os.getenv("LLM_API_KEY"):
        try:
            from app.services.embedding import EmbeddingService, get_embedding_dimension
            embedding_service = EmbeddingService(model=embedding_model)
            vector_size = get_embedding_dimension(embedding_model)
            print(f"Embedding 服务初始化成功: model={embedding_model}, dimension={vector_size}")
        except Exception as e:
            print(f"Embedding 服务初始化失败: {e}")

    # 初始化 Qdrant（如果配置了）
    qdrant_client = None
    if qdrant_url and QdrantClient:
        try:
            from app.services.embedding import get_embedding_dimension
            vector_size = get_embedding_dimension(embedding_model) if embedding_service else 1024
            qdrant_client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                embedding_service=embedding_service,
                vector_size=vector_size,
            )
            await qdrant_client.connect()
            print(f"Qdrant 连接成功: {qdrant_url}")
        except Exception as e:
            print(f"Qdrant 连接失败: {e}")
            qdrant_client = None

    # 创建同步服务
    sync_service = SyncService(
        markdown_storage=markdown_storage,
        sqlite_storage=sqlite_storage,
        neo4j_client=neo4j_client,
        qdrant_client=qdrant_client,
        llm_caller=llm_caller,
    )

    return sync_service
