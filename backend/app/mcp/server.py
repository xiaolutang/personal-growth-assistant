"""MCP Server - 个人成长助手（初始化 + 路由分发 + main）"""
import asyncio
import logging
import os
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent

from app.services import init_storage, SyncService
from app.mcp.tools import TOOLS
from app.mcp.handlers import (
    handle_list_entries,
    handle_get_entry,
    handle_create_entry,
    handle_update_entry,
    handle_delete_entry,
    handle_search_entries,
    handle_get_knowledge_graph,
    handle_get_related_concepts,
    handle_get_project_progress,
    handle_get_review_summary,
    handle_get_knowledge_stats,
)


# 配置日志（输出到 stderr，避免干扰 MCP 通信）
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 全局存储服务
storage: SyncService = None

# 认证后的用户 ID
authenticated_user_id: str | None = None


def _verify_token() -> str:
    """
    从环境变量 MCP_AUTH_TOKEN 读取 JWT token 并验证。

    Returns:
        验证通过时返回 user_id (str)

    Raises:
        SystemExit: token 缺失或无效时终止进程
    """
    from app.services.auth_service import decode_access_token
    import jwt as pyjwt

    token = os.getenv("MCP_AUTH_TOKEN", "").strip()
    if not token:
        logger.error("MCP_AUTH_TOKEN 环境变量未设置")
        raise SystemExit(1)

    try:
        token_data = decode_access_token(token)
        logger.info(f"MCP 认证成功, user_id={token_data.sub}")
        return token_data.sub
    except pyjwt.ExpiredSignatureError:
        logger.error("MCP_AUTH_TOKEN 已过期")
        raise SystemExit(1)
    except pyjwt.InvalidTokenError as e:
        logger.error(f"MCP_AUTH_TOKEN 无效: {e}")
        raise SystemExit(1)


# Tool name → handler 映射
TOOL_HANDLERS = {
    "list_entries": handle_list_entries,
    "get_entry": handle_get_entry,
    "create_entry": handle_create_entry,
    "update_entry": handle_update_entry,
    "delete_entry": handle_delete_entry,
    "search_entries": handle_search_entries,
    "get_knowledge_graph": handle_get_knowledge_graph,
    "get_related_concepts": handle_get_related_concepts,
    "get_project_progress": handle_get_project_progress,
    "get_review_summary": handle_get_review_summary,
    "get_knowledge_stats": handle_get_knowledge_stats,
}


async def init():
    """初始化存储服务"""
    global storage, authenticated_user_id
    storage = await init_storage(
        data_dir=os.getenv("DATA_DIR", "./data"),
        neo4j_uri=os.getenv("NEO4J_URI"),
        neo4j_username=os.getenv("NEO4J_USERNAME"),
        neo4j_password=os.getenv("NEO4J_PASSWORD"),
        qdrant_url=os.getenv("QDRANT_URL"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY"),
    )
    # 验证 JWT token
    authenticated_user_id = _verify_token()
    logger.info("Storage initialized")


# 创建 MCP Server
server = Server("personal-growth-assistant")


@server.list_tools()
async def list_tools() -> tuple:
    """列出可用的工具"""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """调用工具"""
    global storage, authenticated_user_id

    if not storage:
        await init()

    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=f"未知工具: {name}")]

    try:
        return await handler(storage, arguments, authenticated_user_id)
    except Exception as e:
        logger.error(f"工具调用失败: {e}")
        return [TextContent(type="text", text=f"错误: {str(e)}")]


async def main():
    """主函数"""
    await init()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
