"""Neo4j 知识图谱客户端"""
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.models import Task, Concept, ConceptRelation

# 合法的 Neo4j 关系类型白名单，防止 Cypher 注入
VALID_RELATION_TYPES = frozenset({
    "RELATED_TO",
    "PART_OF",
    "PREREQUISITE",
    "BELONGS_TO",
    "DEPENDS_ON",
    "APPLIED_IN",
    "EXAMPLE_OF",
    "CONTRASTS_WITH",
    "SUPPORTS",
    "DERIVED_FROM",
})


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
                # 验证连接是否真的可用（driver 创建是惰性的）
                await self._driver.verify_connectivity()
            except Exception as e:
                # 连接失败时记录日志，将 _driver 设为 None
                import logging
                logging.warning(f"Neo4j 连接失败: {e}")
                self._driver = None
                # 不抛出异常，允许优雅降级

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._driver is not None

    async def verify_connectivity(self) -> bool:
        """验证连接是否真正可用（公共接口）"""
        if not self._driver:
            return False
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    async def close(self):
        """关闭连接"""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def _get_session(self):
        """获取会话

        当 _driver 为 None 时（连接失败或未初始化），抛出 ConnectionError
        而非让后续代码触发 AttributeError。
        """
        if not self._driver:
            await self.connect()
        if not self._driver:
            raise ConnectionError("Neo4j 驱动未初始化或连接失败")
        return self._driver.session()

    # ==================== Entry 节点操作 ====================

    async def create_entry(self, entry: Task, user_id: str = "_default") -> bool:
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
            e.parent_id = $parent_id,
            e.user_id = $user_id
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
                user_id=user_id,
            )
            return await result.single() is not None

    async def update_entry(self, entry: Task, user_id: str = "_default") -> bool:
        """更新条目节点"""
        return await self.create_entry(entry, user_id=user_id)  # MERGE 会自动更新

    async def delete_entry(self, entry_id: str, user_id: str = "_default") -> bool:
        """删除条目节点及其关系"""
        query = """
        MATCH (e:Entry {id: $id, user_id: $user_id})
        DETACH DELETE e
        RETURN count(e) as deleted
        """
        async with await self._get_session() as session:
            result = await session.run(query, id=entry_id, user_id=user_id)
            record = await result.single()
            return record and record["deleted"] > 0

    async def get_entry(self, entry_id: str, user_id: str = "_default") -> Optional[Dict[str, Any]]:
        """获取单个条目"""
        query = """
        MATCH (e:Entry {id: $id, user_id: $user_id})
        RETURN e.id as id, e.title as title, e.type as type,
               e.status as status, e.tags as tags,
               e.created_at as created_at, e.updated_at as updated_at,
               e.file_path as file_path, e.parent_id as parent_id
        """
        async with await self._get_session() as session:
            result = await session.run(query, id=entry_id, user_id=user_id)
            record = await result.single()
            if record:
                return dict(record)
            return None

    async def list_entries(
        self,
        entry_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        user_id: str = "_default",
    ) -> List[Dict[str, Any]]:
        """列出条目"""
        conditions = ["e.user_id = $user_id"]
        params = {"limit": limit, "user_id": user_id}

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

    async def create_concept(self, concept: Concept, user_id: str = "_default") -> bool:
        """创建概念节点"""
        query = """
        MERGE (c:Concept {name: $name, user_id: $user_id})
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
                user_id=user_id,
            )
            return await result.single() is not None

    async def get_or_create_concept(self, name: str, category: str = "技术", user_id: str = "_default") -> bool:
        """获取或创建概念"""
        return await self.create_concept(Concept(
            name=name,
            category=category,
        ), user_id=user_id)

    async def get_concept(self, name: str, user_id: str = "_default") -> Optional[Dict[str, Any]]:
        """获取概念"""
        query = """
        MATCH (c:Concept {name: $name, user_id: $user_id})
        RETURN c.name as name, c.description as description, c.category as category
        """
        async with await self._get_session() as session:
            result = await session.run(query, name=name, user_id=user_id)
            record = await result.single()
            if record:
                return dict(record)
            return None

    # ==================== 关系操作 ====================

    async def create_entry_mentions(
        self,
        entry_id: str,
        concept_names: List[str],
        user_id: str = "_default",
    ) -> bool:
        """创建条目与概念的 MENTIONS 关系"""
        if not concept_names:
            return True

        query = """
        MATCH (e:Entry {id: $entry_id})
        UNWIND $concepts as concept_name
        MERGE (c:Concept {name: concept_name, user_id: $user_id})
        MERGE (e)-[:MENTIONS]->(c)
        """
        async with await self._get_session() as session:
            result = await session.run(
                query,
                entry_id=entry_id,
                concepts=concept_names,
                user_id=user_id,
            )
            return True

    async def create_concept_relation(self, relation: ConceptRelation) -> bool:
        """创建概念之间的关系"""
        if relation.relation_type not in VALID_RELATION_TYPES:
            raise ValueError(
                f"非法关系类型: {relation.relation_type}，"
                f"合法值: {sorted(VALID_RELATION_TYPES)}"
            )
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
        if relation_type not in VALID_RELATION_TYPES:
            raise ValueError(
                f"非法关系类型: {relation_type}，"
                f"合法值: {sorted(VALID_RELATION_TYPES)}"
            )
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
        depth: int = 2,
        user_id: str = "_default",
    ) -> Dict[str, Any]:
        """获取概念的知识图谱"""
        if not isinstance(depth, int) or depth < 1 or depth > 5:
            raise ValueError(f"depth 必须是 1-5 的整数，当前值: {depth}")
        query = f"""
        MATCH path = (c:Concept {{name: $name, user_id: $user_id}})-[*1..{depth}]-(related)
        RETURN c as center,
               collect(DISTINCT {{
                   node: related,
                   relationship: [rel in relationships(path) | type(rel)]
               }}) as connections
        """
        async with await self._get_session() as session:
            result = await session.run(query, name=concept_name, user_id=user_id)
            record = await result.single()
            if record:
                return {
                    "center": dict(record["center"]),
                    "connections": [dict(conn) for conn in record["connections"]]
                }
            return {"center": None, "connections": []}

    async def get_related_concepts(self, concept_name: str, user_id: str = "_default") -> List[Dict[str, Any]]:
        """获取相关概念"""
        query = """
        MATCH (c:Concept {name: $name, user_id: $user_id})-[:RELATED_TO|PART_OF|PREREQUISITE]-(related)
        RETURN related.name as name,
               related.description as description,
               related.category as category,
               type(related) as relation_type
        """
        async with await self._get_session() as session:
            result = await session.run(query, name=concept_name, user_id=user_id)
            return [dict(record) async for record in result]

    async def get_entries_by_concept(self, concept_name: str, user_id: str = "_default") -> List[Dict[str, Any]]:
        """获取提及某概念的所有条目"""
        query = """
        MATCH (c:Concept {name: $name, user_id: $user_id})<-[:MENTIONS]-(e:Entry)
        RETURN e.id as id, e.title as title, e.type as type,
               e.status as status, e.tags as tags,
               e.created_at as created_at, e.updated_at as updated_at
        ORDER BY e.updated_at DESC
        """
        async with await self._get_session() as session:
            result = await session.run(query, name=concept_name, user_id=user_id)
            return [dict(record) async for record in result]

    async def get_entry_with_relations(self, entry_id: str, user_id: str = "_default") -> Dict[str, Any]:
        """获取条目及其所有关系"""
        query = """
        MATCH (e:Entry {id: $id, user_id: $user_id})
        OPTIONAL MATCH (e)-[r]-(related)
        RETURN e as entry,
               collect({
                   node: related,
                   relationship: type(r),
                   direction: CASE WHEN startNode(r) = e THEN 'outgoing' ELSE 'incoming' END
               }) as relations
        """
        async with await self._get_session() as session:
            result = await session.run(query, id=entry_id, user_id=user_id)
            record = await result.single()
            if record:
                return {
                    "entry": dict(record["entry"]),
                    "relations": [dict(r) for r in record["relations"] if r["node"]]
                }
            return {"entry": None, "relations": []}

    # ==================== 全局图谱查询 ====================

    async def get_all_concepts_with_stats(self, user_id: str = "_default") -> List[Dict[str, Any]]:
        """获取所有概念及其统计信息"""
        query = """
        MATCH (c:Concept {user_id: $user_id})
        OPTIONAL MATCH (e:Entry {user_id: $user_id})-[m:MENTIONS]->(c)
        RETURN c.name as name,
               c.category as category,
               count(DISTINCT e) as entry_count,
               count(DISTINCT m) as mention_count
        ORDER BY entry_count DESC
        """
        async with await self._get_session() as session:
            result = await session.run(query, user_id=user_id)
            concepts = []
            async for record in result:
                concepts.append({
                    "name": record["name"],
                    "category": record["category"],
                    "entry_count": record["entry_count"],
                    "mention_count": record["mention_count"],
                })
            return concepts

    async def get_all_relationships(self, user_id: str = "_default") -> List[Dict[str, Any]]:
        """获取所有概念之间的关系"""
        query = """
        MATCH (c1:Concept {user_id: $user_id})-[r]->(c2:Concept {user_id: $user_id})
        WHERE NOT type(r) = ''
        RETURN c1.name as source, c2.name as target, type(r) as type
        """
        async with await self._get_session() as session:
            result = await session.run(query, user_id=user_id)
            relationships = []
            async for record in result:
                relationships.append({
                    "source": record["source"],
                    "target": record["target"],
                    "type": record["type"],
                })
            return relationships

    # ==================== 图算法查询 ====================

    async def find_prerequisite_gaps(self, user_id: str = "_default") -> List[Dict[str, Any]]:
        """查找知识缺口：有前置关系(PREREQUISITE)但用户未学习的概念

        返回格式: [{"concept": "概念名", "missing_prerequisites": ["前置1", "前置2"]}]
        """
        query = """
        MATCH (c:Concept {user_id: $user_id})<-[:PREREQUISITE]-(prereq:Concept)
        WHERE NOT (prereq)<-[:MENTIONS]-(:Entry {user_id: $user_id})
        WITH c, collect(DISTINCT prereq.name) AS missing
        RETURN c.name AS concept, missing AS missing_prerequisites
        ORDER BY size(missing) DESC
        LIMIT 20
        """
        async with await self._get_session() as session:
            result = await session.run(query, user_id=user_id)
            gaps = []
            async for record in result:
                missing = record["missing_prerequisites"]
                # Neo4j driver 可能返回 List 对象，确保转为 Python list
                if missing and not isinstance(missing, list):
                    missing = list(missing)
                gaps.append({
                    "concept": record["concept"],
                    "missing_prerequisites": missing if missing else [],
                })
            return gaps

    async def get_concept_centrality(self, user_id: str = "_default", limit: int = 20) -> List[Dict[str, Any]]:
        """获取概念中心度排序（基于关系数量）

        返回格式: [{"name": "概念名", "centrality": 关系数, "category": "类别"}]
        """
        query = """
        MATCH (c:Concept {user_id: $user_id})-[r]-(other)
        WITH c, count(DISTINCT other) AS degree
        ORDER BY degree DESC
        LIMIT $limit
        RETURN c.name AS name, degree AS centrality, c.category AS category
        """
        async with await self._get_session() as session:
            result = await session.run(query, user_id=user_id, limit=limit)
            centrality_list = []
            async for record in result:
                centrality_list.append({
                    "name": record["name"],
                    "centrality": record["centrality"],
                    "category": record["category"],
                })
            return centrality_list

    # ==================== 初始化 ====================

    async def create_indexes(self):
        """创建索引"""
        queries = [
            "CREATE INDEX IF NOT EXISTS FOR (e:Entry) ON (e.id)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Entry) ON (e.type)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Entry) ON (e.status)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Entry) ON (e.user_id)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.user_id)",
        ]
        async with await self._get_session() as session:
            for query in queries:
                await session.run(query)
