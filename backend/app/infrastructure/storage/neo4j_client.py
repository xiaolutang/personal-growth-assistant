"""Neo4j 知识图谱客户端"""
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.models import Task, Concept, ConceptRelation


class Neo4jClient:
    """Neo4j 知识图谱客户端"""

    def __init__(
        self,
        uri: str = None,
        username: str = None,
        password: str = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self._driver: Optional[AsyncDriver] = None

    async def connect(self):
        """连接数据库"""
        if not self._driver:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.username, self.password)
                )
            except Exception as e:
                # 连接失败时记录日志，将 _driver 设为 None
                import logging
                logging.warning(f"Neo4j 连接失败: {e}")
                self._driver = None
                # 不抛出异常，允许优雅降级

    async def close(self):
        """关闭连接"""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def _get_session(self):
        """获取会话"""
        if not self._driver:
            await self.connect()
        return self._driver.session()

    # ==================== Entry 节点操作 ====================

    async def create_entry(self, entry: Task) -> bool:
        """创建条目节点"""
        query = """
        MERGE (e:Entry {id: $id})
        SET e.title = $title,
            e.type = $type,
            e.status = $status,
            e.tags = $tags,
            e.created_at = datetime($created_at),
            e.updated_at = datetime($updated_at),
            e.file_path = $file_path,
            e.parent_id = $parent_id
        RETURN e
        """
        async with await self._get_session() as session:
            result = await session.run(
                query,
                id=entry.id,
                title=entry.title,
                type=entry.category.value,
                status=entry.status.value,
                tags=entry.tags,
                created_at=entry.created_at.isoformat(),
                updated_at=entry.updated_at.isoformat(),
                file_path=entry.file_path,
                parent_id=entry.parent_id,
            )
            return await result.single() is not None

    async def update_entry(self, entry: Task) -> bool:
        """更新条目节点"""
        return await self.create_entry(entry)  # MERGE 会自动更新

    async def delete_entry(self, entry_id: str) -> bool:
        """删除条目节点及其关系"""
        query = """
        MATCH (e:Entry {id: $id})
        DETACH DELETE e
        RETURN count(e) as deleted
        """
        async with await self._get_session() as session:
            result = await session.run(query, id=entry_id)
            record = await result.single()
            return record and record["deleted"] > 0

    async def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """获取单个条目"""
        query = """
        MATCH (e:Entry {id: $id})
        RETURN e.id as id, e.title as title, e.type as type,
               e.status as status, e.tags as tags,
               e.created_at as created_at, e.updated_at as updated_at,
               e.file_path as file_path, e.parent_id as parent_id
        """
        async with await self._get_session() as session:
            result = await session.run(query, id=entry_id)
            record = await result.single()
            if record:
                return dict(record)
            return None

    async def list_entries(
        self,
        entry_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """列出条目"""
        conditions = []
        params = {"limit": limit}

        if entry_type:
            conditions.append("e.type = $type")
            params["type"] = entry_type
        if status:
            conditions.append("e.status = $status")
            params["status"] = status

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
        MATCH (e:Entry)
        {where_clause}
        RETURN e.id as id, e.title as title, e.type as type,
               e.status as status, e.tags as tags,
               e.created_at as created_at, e.updated_at as updated_at,
               e.file_path as file_path, e.parent_id as parent_id
        ORDER BY e.updated_at DESC
        LIMIT $limit
        """
        async with await self._get_session() as session:
            result = await session.run(query, **params)
            entries = []
            async for record in result:
                entries.append(dict(record))
            return entries

    # ==================== Concept 节点操作 ====================

    async def create_concept(self, concept: Concept) -> bool:
        """创建概念节点"""
        query = """
        MERGE (c:Concept {name: $name})
        SET c.description = $description,
            c.category = $category
        RETURN c
        """
        async with await self._get_session() as session:
            result = await session.run(
                query,
                name=concept.name,
                description=concept.description or "",
                category=concept.category or "技术",
            )
            return await result.single() is not None

    async def get_or_create_concept(self, name: str, category: str = "技术") -> bool:
        """获取或创建概念"""
        return await self.create_concept(Concept(
            name=name,
            category=category,
        ))

    async def get_concept(self, name: str) -> Optional[Dict[str, Any]]:
        """获取概念"""
        query = """
        MATCH (c:Concept {name: $name})
        RETURN c.name as name, c.description as description, c.category as category
        """
        async with await self._get_session() as session:
            result = await session.run(query, name=name)
            record = await result.single()
            if record:
                return dict(record)
            return None

    # ==================== 关系操作 ====================

    async def create_entry_mentions(
        self,
        entry_id: str,
        concept_names: List[str]
    ) -> bool:
        """创建条目与概念的 MENTIONS 关系"""
        if not concept_names:
            return True

        query = """
        MATCH (e:Entry {id: $entry_id})
        UNWIND $concepts as concept_name
        MERGE (c:Concept {name: concept_name})
        MERGE (e)-[:MENTIONS]->(c)
        """
        async with await self._get_session() as session:
            result = await session.run(
                query,
                entry_id=entry_id,
                concepts=concept_names,
            )
            return True

    async def create_concept_relation(self, relation: ConceptRelation) -> bool:
        """创建概念之间的关系"""
        query = f"""
        MATCH (from:Concept {{name: $from_concept}})
        MATCH (to:Concept {{name: $to_concept}})
        MERGE (from)-[r:{relation.relation_type}]->(to)
        RETURN r
        """
        async with await self._get_session() as session:
            result = await session.run(
                query,
                from_concept=relation.from_concept,
                to_concept=relation.to_concept,
            )
            return await result.single() is not None

    async def create_concept_relations(
        self,
        relations: List[ConceptRelation]
    ) -> bool:
        """批量创建概念关系"""
        for relation in relations:
            await self.create_concept_relation(relation)
        return True

    async def create_entry_relation(
        self,
        from_id: str,
        to_id: str,
        relation_type: str = "BELONGS_TO"
    ) -> bool:
        """创建条目之间的关系"""
        query = f"""
        MATCH (from:Entry {{id: $from_id}})
        MATCH (to:Entry {{id: $to_id}})
        MERGE (from)-[:{relation_type}]->(to)
        """
        async with await self._get_session() as session:
            result = await session.run(
                query,
                from_id=from_id,
                to_id=to_id,
            )
            return await result.single() is not None

    # ==================== 知识图谱查询 ====================

    async def get_knowledge_graph(
        self,
        concept_name: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """获取概念的知识图谱"""
        query = f"""
        MATCH path = (c:Concept {{name: $name}})-[*1..{depth}]-(related)
        RETURN c as center,
               collect(DISTINCT {{
                   node: related,
                   relationship: [rel in relationships(path) | type(rel)]
               }}) as connections
        """
        async with await self._get_session() as session:
            result = await session.run(query, name=concept_name)
            record = await result.single()
            if record:
                return {
                    "center": dict(record["center"]),
                    "connections": [dict(conn) for conn in record["connections"]]
                }
            return {"center": None, "connections": []}

    async def get_related_concepts(self, concept_name: str) -> List[Dict[str, Any]]:
        """获取相关概念"""
        query = """
        MATCH (c:Concept {name: $name})-[:RELATED_TO|PART_OF|PREREQUISITE]-(related)
        RETURN related.name as name,
               related.description as description,
               related.category as category,
               type(related) as relation_type
        """
        async with await self._get_session() as session:
            result = await session.run(query, name=concept_name)
            return [dict(record) async for record in result]

    async def get_entries_by_concept(self, concept_name: str) -> List[Dict[str, Any]]:
        """获取提及某概念的所有条目"""
        query = """
        MATCH (c:Concept {name: $name})<-[:MENTIONS]-(e:Entry)
        RETURN e.id as id, e.title as title, e.type as type,
               e.status as status, e.tags as tags,
               e.created_at as created_at, e.updated_at as updated_at
        ORDER BY e.updated_at DESC
        """
        async with await self._get_session() as session:
            result = await session.run(query, name=concept_name)
            return [dict(record) async for record in result]

    async def get_entry_with_relations(self, entry_id: str) -> Dict[str, Any]:
        """获取条目及其所有关系"""
        query = """
        MATCH (e:Entry {id: $id})
        OPTIONAL MATCH (e)-[r]-(related)
        RETURN e as entry,
               collect({
                   node: related,
                   relationship: type(r),
                   direction: CASE WHEN startNode(r) = e THEN 'outgoing' ELSE 'incoming' END
               }) as relations
        """
        async with await self._get_session() as session:
            result = await session.run(query, id=entry_id)
            record = await result.single()
            if record:
                return {
                    "entry": dict(record["entry"]),
                    "relations": [dict(r) for r in record["relations"] if r["node"]]
                }
            return {"entry": None, "relations": []}

    # ==================== 初始化 ====================

    async def create_indexes(self):
        """创建索引"""
        queries = [
            "CREATE INDEX IF NOT EXISTS FOR (e:Entry) ON (e.id)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Entry) ON (e.type)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Entry) ON (e.status)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.name)",
        ]
        async with await self._get_session() as session:
            for query in queries:
                await session.run(query)
