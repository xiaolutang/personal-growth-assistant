# 个人成长助手 - MCP Server

> Claude Code / Cursor 可直接操作你的成长数据

## 功能

- **list_entries** - 查询条目列表
- **get_entry** - 获取单个条目
- **create_entry** - 创建条目
- **update_entry** - 更新条目
- **delete_entry** - 删除条目
- **search_entries** - 语义搜索（RAG）
- **get_knowledge_graph** - 获取知识图谱
- **get_related_concepts** - 获取相关概念

## 安装

```bash
cd backend
pip install -r requirements.txt
```

## 配置

### 1. 环境变量

创建 `.env` 文件：

```bash
# Neo4j（知识图谱）
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Qdrant（向量检索）
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key  # 可选

# LLM（用于概念提取）
DASHSCOPE_API_KEY=your_api_key

# 数据目录
DATA_DIR=./data
```

### 2. 启动依赖服务

```bash
# Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest

# Qdrant
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  qdrant/qdrant:latest
```

### 3. 配置 Claude Code

编辑 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "personal-growth": {
      "command": "python",
      "args": ["/path/to/personal-growth-assistant/backend/app/mcp/server.py"],
      "env": {
        "DATA_DIR": "/path/to/personal-growth-assistant/data",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "your_password",
        "QDRANT_URL": "http://localhost:6333",
        "DASHSCOPE_API_KEY": "your_api_key"
      }
    }
  }
}
```

## 使用示例

在 Claude Code 中：

```
你: 帮我看看今天有什么任务
Claude: [调用 list_entries] 今天要做...

你: 记个想法，可以做个 MCP Server 来管理个人数据
Claude: [调用 create_entry] 已记录到 inbox

你: 搜索关于 RAG 的笔记
Claude: [调用 search_entries] 找到 3 条相关笔记...

你: MCP 和什么概念相关？
Claude: [调用 get_related_concepts] MCP 和 LLM应用开发、工具调用、上下文管理相关...
```

## 数据结构

```
data/
├── projects/
│   └── ai-transition.md
├── tasks/
│   └── 2026-03.md
├── notes/
│   ├── mcp-learning.md
│   └── rag-learning.md
└── inbox.md
```

## 架构

```
Markdown 文件（Source of Truth）
        ↓ 同步
┌───────────────────────────────────┐
│  Neo4j（知识图谱）  Qdrant（向量） │
└───────────────────────────────────┘
        ↑ MCP 协议
  Claude Code / Cursor
```

## 开发

```bash
# 测试 MCP Server
cd backend
python -m app.mcp.server

# 运行测试
pytest tests/
```

## License

MIT
