"""数据同步服务 - 精简版"""
import asyncio
import logging
from typing import List, Optional, Dict, Any

from app.core.config import get_settings
from app.models import Task
from app.models.user import DefaultDataClaimResult, User
from app.infrastructure.storage.markdown import MarkdownStorage
from app.infrastructure.storage.storage_factory import StorageFactory
from app.services.knowledge_service import KnowledgeService
from app.services.session_meta_store import SessionMetaStore

logger = logging.getLogger(__name__)

# 可选依赖
try:
    from app.infrastructure.storage.neo4j_client import Neo4jClient
except ImportError:
    Neo4jClient = None

try:
    from app.infrastructure.storage.qdrant_client import QdrantClient
except ImportError:
    QdrantClient = None

try:
    from app.infrastructure.storage.sqlite import SQLiteStorage
except ImportError:
    SQLiteStorage = None


class SyncService:
    """数据同步服务 - Markdown → SQLite → Neo4j + Qdrant"""

    def __init__(
        self,
        markdown_storage: MarkdownStorage,
        storage_factory: StorageFactory | None = None,
        sqlite_storage=None,
        neo4j_client=None,
        qdrant_client=None,
        llm_caller=None,
    ):
        self.markdown = markdown_storage
        self.storage_factory = storage_factory
        self.sqlite = sqlite_storage
        self.neo4j = neo4j_client
        self.qdrant = qdrant_client
        self.llm_caller = llm_caller

        # 创建知识服务（用于知识提取）
        self._knowledge_service = KnowledgeService(
            neo4j_client=neo4j_client,
            sqlite_storage=sqlite_storage,
            llm_caller=llm_caller,
        )

    def get_markdown_storage(self, user_id: str = "_default") -> MarkdownStorage:
        """按 user_id 获取 Markdown 存储"""
        if self.storage_factory is not None:
            return self.storage_factory.get_markdown_storage(user_id)
        return self.markdown

    def claim_default_data(self, user: User) -> DefaultDataClaimResult:
        """将 `_default` 历史数据认领到指定用户"""
        if not user.id or user.id == "_default":
            return DefaultDataClaimResult(claimed=False, reason="invalid_target_user")

        settings = get_settings()

        sqlite_entries_claimed = 0
        if self.sqlite is not None:
            sqlite_entries_claimed = self.sqlite.claim_default_entries(user.id)

        storage_factory = self.storage_factory or StorageFactory(settings.DATA_DIR)
        markdown_files_copied, markdown_files_skipped = storage_factory.claim_default_user(user.id)

        session_meta_store = SessionMetaStore(
            settings.sqlite_checkpoints_path.replace(".db", "_meta.db")
        )
        session_count_claimed = session_meta_store.claim_default_sessions(user.id)

        claimed = any(
            [
                sqlite_entries_claimed,
                markdown_files_copied,
                session_count_claimed,
            ]
        )
        reason = "" if claimed else "no_default_data"

        return DefaultDataClaimResult(
            claimed=claimed,
            reason=reason,
            sqlite_entries_claimed=sqlite_entries_claimed,
            markdown_files_copied=markdown_files_copied,
            markdown_files_skipped=markdown_files_skipped,
            session_count_claimed=session_count_claimed,
        )

    async def sync_entry(self, entry: Task, user_id: str = "_default") -> bool:
        """
        同步单个条目到 SQLite + Neo4j + Qdrant

        流程：
        1. 写入 Markdown（Source of Truth）
        2. 同步到 SQLite（快速索引）- 失败时记录 warning，Markdown 保留不丢失
        3. 提取知识（tags, concepts, relations）
        4. 并行同步到 Neo4j + Qdrant - 失败时不影响主流程返回
        """
        # 1. 写入 Markdown（Source of Truth）— 必须成功
        try:
            markdown = self.get_markdown_storage(user_id)
            markdown.write_entry(entry)
        except Exception as e:
            logger.error(f"Markdown 写入失败（Source of Truth），中止同步: {e}")
            return False

        # 2. 同步到 SQLite（索引层）— 失败时 Markdown 保留，记录 warning
        if self.sqlite:
            try:
                self.sqlite.upsert_entry(entry, user_id=user_id)
            except Exception as e:
                logger.warning(f"SQLite 索引写入失败（Markdown 已保留，可稍后 sync_all 重建）: {e}")

        # 3. 提取知识（委托给 KnowledgeService）
        try:
            knowledge = await self._knowledge_service.extract_knowledge(entry)
        except Exception as e:
            logger.warning(f"知识提取失败（跳过图谱/向量同步）: {e}")
            return True

        # 4. 并行同步到 Neo4j 和 Qdrant（索引层，失败不阻塞主流程）
        tasks = []

        if self.neo4j and self.neo4j._driver:
            tasks.append(self._sync_to_neo4j(entry, knowledge, user_id))

        if self.qdrant:
            try:
                tasks.append(self.qdrant.upsert_entry(entry, user_id=user_id))
            except Exception as e:
                logger.warning(f"Qdrant 任务创建失败，忽略: {e}")

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.warning(f"图谱/向量同步任务 {i} 失败（可稍后 sync_all 重建）: {r}")

        return True

    async def sync_to_graph_and_vector(self, entry: Task, user_id: str = "_default") -> bool:
        """
        仅同步到 Neo4j + Qdrant（后台执行，不阻塞响应）

        用于创建条目后立即返回响应，但后台继续同步到知识图谱和向量库
        """
        try:
            # 提取知识（委托给 KnowledgeService）
            knowledge = await self._knowledge_service.extract_knowledge(entry)

            # 并行同步到 Neo4j 和 Qdrant
            tasks = []

            if self.neo4j and self.neo4j._driver:
                tasks.append(self._sync_to_neo4j(entry, knowledge, user_id))

            if self.qdrant:
                try:
                    tasks.append(self.qdrant.upsert_entry(entry, user_id=user_id))
                except Exception as e:
                    logger.warning(f"Qdrant 同步失败，忽略: {e}")

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            return True
        except Exception as e:
            logger.error(f"图谱/向量同步失败: {e}")
            return False

    async def _sync_to_neo4j(self, entry: Task, knowledge, user_id: str = "_default"):
        """同步到 Neo4j（内部方法）"""
        await self.neo4j.create_entry(entry, user_id=user_id)

        # 并行创建概念节点
        if knowledge.concepts:
            concept_tasks = [
                self.neo4j.create_concept(concept, user_id=user_id)
                for concept in knowledge.concepts
            ]
            await asyncio.gather(*concept_tasks, return_exceptions=True)

            # 创建条目与概念的关系
            concept_names = [c.name for c in knowledge.concepts]
            await self.neo4j.create_entry_mentions(entry.id, concept_names, user_id=user_id)

        # 并行创建概念关系
        if knowledge.relations:
            relation_tasks = [
                self.neo4j.create_concept_relation(relation)
                for relation in knowledge.relations
            ]
            await asyncio.gather(*relation_tasks, return_exceptions=True)

    async def delete_entry(self, entry_id: str, user_id: str = "_default") -> bool:
        """
        删除条目及其关联数据

        顺序：Markdown（Source of Truth）→ SQLite → Neo4j/Qdrant
        - Markdown 删除即确认删除意图
        - SQLite 删除失败时记录 error 并返回 False（索引残留需手动清理）
        - Neo4j/Qdrant 删除失败时记录 warning（索引残留，需手动清理或重启后重新全量同步）
        """
        # 1. 删除 Markdown（Source of Truth）— 先删，确认删除意图
        markdown_deleted = False
        try:
            markdown_deleted = self.get_markdown_storage(user_id).delete_entry(entry_id)
        except Exception as e:
            logger.error(f"Markdown 删除失败: {e}")
            return False

        # 2. 删除 SQLite 索引（同步，因为很快）
        if self.sqlite:
            try:
                self.sqlite.delete_entry(entry_id, user_id=user_id)
            except Exception as e:
                logger.error(f"SQLite 索引删除失败，索引残留 entry_id=%s: %s", entry_id, e)
                # SQLite 删除失败是异常情况，但仍继续清理 Neo4j/Qdrant
                # 注意：此时索引中有残留数据，需手动清理

        # 3. 并行删除 Neo4j 和 Qdrant 索引
        tasks = []

        if self.neo4j:
            try:
                tasks.append(self.neo4j.delete_entry(entry_id, user_id=user_id))
            except Exception as e:
                logger.warning(f"Neo4j 删除任务创建失败，忽略: {e}")

        if self.qdrant:
            try:
                tasks.append(self.qdrant.delete_entry(entry_id))
            except Exception as e:
                logger.warning(f"Qdrant 删除任务创建失败，忽略: {e}")

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.warning(f"图谱/向量索引删除失败（可稍后 sync_all 重建）: {r}")

        # 返回值反映 Markdown 是否删除成功
        return markdown_deleted

    async def sync_all(self) -> Dict[str, int]:
        """同步所有 Markdown 文件"""
        success = 0
        failed = 0

        if self.storage_factory:
            user_ids = self.storage_factory.list_user_ids() or ["_default"]
        else:
            user_ids = ["_default"]

        for user_id in user_ids:
            entries = self.get_markdown_storage(user_id).scan_all()
            for entry in entries:
                if await self.sync_entry(entry, user_id=user_id):
                    success += 1
                else:
                    failed += 1

        return {"success": success, "failed": failed}

    async def resync_entry(self, entry_id: str, user_id: str = "_default") -> bool:
        """重新同步单个条目（用于文件编辑后）"""
        entry = self.get_markdown_storage(user_id).read_entry(entry_id)
        if entry:
            return await self.sync_entry(entry, user_id=user_id)
        return False

    @property
    def driver(self):
        """向后兼容：返回 Neo4j driver"""
        return self.neo4j._driver if self.neo4j else None


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
    import os

    # 先迁移根目录遗留数据到 users/_default，再统一走按用户目录读写
    storage_factory = StorageFactory(data_dir)
    migrated_count = storage_factory.migrate_default_user(data_dir)
    if migrated_count:
        print(f"根目录历史 Markdown 已迁移到 users/_default: {migrated_count} 个文件")

    markdown_storage = storage_factory.get_markdown_storage("_default")

    # 初始化 SQLite（默认开启）
    sqlite_storage = None
    if SQLiteStorage:
        try:
            db_path = sqlite_path or f"{data_dir}/index.db"
            sqlite_storage = SQLiteStorage(db_path)
            total_count = 0
            for user_id in storage_factory.list_user_ids() or ["_default"]:
                count = sqlite_storage.sync_from_markdown(
                    storage_factory.get_markdown_storage(user_id),
                    user_id=user_id,
                )
                total_count += count
            print(f"SQLite 索引同步完成: {total_count} 条记录")
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
        storage_factory=storage_factory,
        sqlite_storage=sqlite_storage,
        neo4j_client=neo4j_client,
        qdrant_client=qdrant_client,
        llm_caller=llm_caller,
    )

    return sync_service
