# 个人成长助手 - 后端架构设计

> 最后更新：2026-03-16

---

## 1. 类图 (Class Diagram)

```mermaid
classDiagram
    %% 数据模型
    class Category {
        <<enumeration>>
        PROJECT
        TASK
        NOTE
        INBOX
    }

    class TaskStatus {
        <<enumeration>>
        WAIT_START
        DOING
        COMPLETE
    }

    class Task {
        +str id
        +str title
        +str content
        +Category category
        +TaskStatus status
        +List~str~ tags
        +datetime created_at
        +datetime updated_at
        +datetime planned_date
        +datetime completed_at
        +int time_spent
        +str parent_id
        +str file_path
    }

    class Concept {
        +str name
        +str description
        +str category
    }

    class ConceptRelation {
        +str from_concept
        +str to_concept
        +str relation_type
    }

    class ExtractedKnowledge {
        +List~str~ tags
        +List~Concept~ concepts
        +List~ConceptRelation~ relations
    }

    Task --> Category
    Task --> TaskStatus

    %% 存储层
    class MarkdownStorage {
        -Path data_dir
        +read_entry(entry_id, category) Task
        +write_entry(entry) str
        +delete_entry(entry_id, category) bool
        +list_entries(category, status, limit) List~Task~
        +scan_all() List~Task~
        -_extract_title(content) str
        -_extract_tags(content) List~str~
        -_extract_created_at(content, file_path) datetime
    }

    class Neo4jClient {
        -str uri
        -str username
        -str password
        -AsyncDriver _driver
        +connect()
        +close()
        +create_entry(entry) bool
        +update_entry(entry) bool
        +delete_entry(entry_id) bool
        +get_entry(entry_id) Dict
        +list_entries(type, status, limit) List
        +create_concept(concept) bool
        +create_entry_mentions(entry_id, concepts) bool
        +create_concept_relation(relation) bool
        +get_knowledge_graph(concept, depth) Dict
        +get_related_concepts(concept) List
        +create_indexes()
    }

    class QdrantClient {
        -str url
        -str api_key
        -AsyncQdrantClient _client
        -embedding_func
        +connect()
        +close()
        +upsert_entry(entry) bool
        +delete_entry(entry_id) bool
        +get_entry(entry_id) Dict
        +search(query, limit, filters) List
        +batch_upsert(entries) int
        +get_stats() Dict
    }

    class SyncService {
        +MarkdownStorage markdown
        +Neo4jClient neo4j
        +QdrantClient qdrant
        +llm_caller
        +sync_entry(entry) bool
        +delete_entry(entry_id) bool
        +sync_all() Dict
        +resync_entry(entry_id) bool
        -_extract_knowledge(entry) ExtractedKnowledge
        -_extract_with_llm(entry) ExtractedKnowledge
        -_extract_with_rules(entry) ExtractedKnowledge
    }

    SyncService --> MarkdownStorage
    SyncService --> Neo4jClient
    SyncService --> QdrantClient

    %% API 路由层
    class EntriesRouter {
        +list_entries(type, status, limit) EntryListResponse
        +get_entry(entry_id) EntryResponse
        +create_entry(request) EntryResponse
        +update_entry(entry_id, request) SuccessResponse
        +delete_entry(entry_id) SuccessResponse
    }

    class SearchRouter {
        +search_entries(request) SearchResponse
    }

    class KnowledgeRouter {
        +get_knowledge_graph(concept, depth) KnowledgeGraphResponse
        +get_related_concepts(concept) RelatedConceptsResponse
    }

    %% LLM 调用层
    class LLMCaller {
        <<interface>>
        +call(messages, response_format) str
    }

    class APICaller {
        +call(messages, response_format) str
    }

    class TaskParserGraph {
        +LLMCaller caller
        +AsyncSqliteSaver checkpointer
        +StateGraph graph
        +stream_parse(text, thread_id) AsyncGenerator
        +clear_thread(thread_id)
        -_build_graph()
        -_parse_node(state)
    }

    LLMCaller <|.. APICaller
    TaskParserGraph --> LLMCaller

    %% MCP Server
    class MCPServer {
        +Server server
        +list_tools() List~Tool~
        +call_tool(name, arguments) List~TextContent~
        -handle_list_entries(args)
        -handle_get_entry(args)
        -handle_create_entry(args)
        -handle_update_entry(args)
        -handle_delete_entry(args)
        -handle_search_entries(args)
        -handle_get_knowledge_graph(args)
    }

    MCPServer --> SyncService
```

---

## 2. 创建条目时序图 (Sequence Diagram)

```mermaid
sequenceDiagram
    participant Client as 前端/Claude Code
    participant API as FastAPI Router
    participant Sync as SyncService
    participant MD as MarkdownStorage
    participant Neo4j as Neo4jClient
    participant Qdrant as QdrantClient
    participant LLM as LLM Service

    Client->>API: POST /entries {type, title, content, tags}
    API->>API: 验证请求参数
    API->>API: 生成 entry_id (type-uuid8)
    API->>API: 计算 file_path

    API->>Sync: 创建 Task 对象
    Sync->>MD: write_entry(entry)
    MD->>MD: 格式化内容 (添加标题、日期)
    MD->>MD: 写入 .md 文件
    MD-->>Sync: 返回文件路径

    API->>Sync: sync_entry(entry) [异步]

    par 知识提取
        Sync->>LLM: 调用 LLM 提取 concepts, relations
        LLM-->>Sync: ExtractedKnowledge
    and Neo4j 同步
        Sync->>Neo4j: create_entry(entry)
        Neo4j-->>Sync: OK
        Sync->>Neo4j: create_concept(concepts)
        Neo4j-->>Sync: OK
        Sync->>Neo4j: create_entry_mentions(entry_id, concepts)
        Neo4j-->>Sync: OK
        Sync->>Neo4j: create_concept_relation(relations)
        Neo4j-->>Sync: OK
    and Qdrant 同步
        Sync->>Qdrant: upsert_entry(entry)
        Qdrant->>LLM: 获取 embedding
        LLM-->>Qdrant: vector
        Qdrant->>Qdrant: 存储向量
        Qdrant-->>Sync: OK
    end

    API-->>Client: EntryResponse {id, title, ...}
```

---

## 3. 数据流图 (Data Flow Diagram)

```mermaid
flowchart TB
    subgraph 用户层
        A1[Claude Code<br/>MCP Client]
        A2[Web 前端<br/>REST API]
        A3[直接编辑<br/>Markdown 文件]
    end

    subgraph 服务层
        B1[MCP Server<br/>stdio 协议]
        B2[FastAPI<br/>REST API]
        B3[TaskParserGraph<br/>LLM 解析]
    end

    subgraph 存储层
        C1[MarkdownStorage<br/>Source of Truth]
        C2[Neo4jClient<br/>知识图谱]
        C3[QdrantClient<br/>向量检索]
    end

    subgraph 数据库
        D1[(data/<br/>.md 文件)]
        D2[(Neo4j<br/>图数据库)]
        D3[(Qdrant<br/>向量数据库)]
    end

    A1 <-->|MCP 协议| B1
    A2 <-->|HTTP/JSON| B2
    A3 -->|文件监听| C1

    B1 --> C1
    B2 --> B3
    B3 --> C1
    B2 --> C1

    C1 -->|写入| D1
    C1 -->|读取| D1

    C1 -->|同步| C2
    C2 <-->|Cypher| D2

    C1 -->|同步| C3
    C3 <-->|gRPC| D3
```

---

## 4. API 请求处理流程图

```mermaid
flowchart LR
    subgraph 请求处理
        A[HTTP Request] --> B{路由匹配}
        B -->|/entries| C[EntriesRouter]
        B -->|/search| D[SearchRouter]
        B -->|/knowledge-graph| E[KnowledgeRouter]
        B -->|/parse| F[TaskParserGraph]
    end

    subgraph 业务逻辑
        C --> G[SyncService]
        D --> G
        E --> G
        F --> H[LLM Caller]
    end

    subgraph 存储操作
        G --> I{操作类型}
        I -->|CRUD| J[MarkdownStorage]
        I -->|搜索| K[QdrantClient]
        I -->|图谱| L[Neo4jClient]
    end

    subgraph 响应
        J --> M[JSON Response]
        K --> M
        L --> M
        H --> N[SSE Stream]
    end
```

---

## 5. MCP Tools 调用流程图

```mermaid
flowchart TD
    A[Claude Code 发送 Tool Call] --> B[MCP Server 接收]
    B --> C{Tool Name}

    C -->|list_entries| D1[MarkdownStorage.list_entries]
    C -->|get_entry| D2[MarkdownStorage.read_entry]
    C -->|create_entry| D3[SyncService.sync_entry]
    C -->|update_entry| D4[SyncService.sync_entry]
    C -->|delete_entry| D5[SyncService.delete_entry]
    C -->|search_entries| D6[QdrantClient.search]
    C -->|get_knowledge_graph| D7[Neo4jClient.get_knowledge_graph]
    C -->|get_related_concepts| D8[Neo4jClient.get_related_concepts]

    D3 --> E1[写入 Markdown]
    D3 --> E2[同步 Neo4j]
    D3 --> E3[同步 Qdrant]

    D5 --> F1[删除 Markdown]
    D5 --> F2[删除 Neo4j 节点]
    D5 --> F3[删除 Qdrant 向量]

    D1 --> G[格式化返回 TextContent]
    D2 --> G
    D3 --> G
    D4 --> G
    D5 --> G
    D6 --> G
    D7 --> G
    D8 --> G

    G --> H[返回给 Claude Code]
```

---

## 6. 知识图谱数据模型 (ER Diagram)

```mermaid
erDiagram
    ENTRY {
        string id PK
        string title
        string type
        string status
        string tags
        datetime created_at
        datetime updated_at
        string file_path
        string parent_id FK
    }

    CONCEPT {
        string name PK
        string description
        string category
    }

    ENTRY ||--o{ ENTRY : BELONGS_TO
    ENTRY }o--o{ CONCEPT : MENTIONS
    ENTRY ||--o{ ENTRY : REFERENCES
    ENTRY ||--o{ ENTRY : DEPENDS_ON

    CONCEPT }o--o{ CONCEPT : PART_OF
    CONCEPT }o--o{ CONCEPT : RELATED_TO
    CONCEPT }o--o{ CONCEPT : PREREQUISITE
```

**字段说明**：
- `ENTRY.type`: project / task / note / inbox
- `ENTRY.status`: waitStart / doing / complete
- `CONCEPT.category`: 技术 / 方法 / 工具

---

## 7. 整体架构图

```mermaid
flowchart TB
    subgraph 用户层
        U1[Claude Code CLI]
        U2[Web 前端]
        U3[Markdown 编辑器]
    end

    subgraph 接入层
        A1[MCP Server<br/>8 个 Tools]
        A2[FastAPI<br/>REST API]
    end

    subgraph 业务层
        B1[SyncService<br/>数据同步]
        B2[TaskParserGraph<br/>LLM 解析]
        B3[LLMCaller<br/>AI 调用]
    end

    subgraph 存储层
        C1[MarkdownStorage]
        C2[Neo4jClient]
        C3[QdrantClient]
    end

    subgraph 数据层
        D1[(.md 文件)]
        D2[(Neo4j)]
        D3[(Qdrant)]
    end

    U1 -->|stdio| A1
    U2 -->|HTTP| A2
    U3 -->|文件系统| D1

    A1 --> B1
    A2 --> B1
    A2 --> B2
    B2 --> B3

    B1 --> C1
    B1 --> C2
    B1 --> C3

    C1 --> D1
    C2 --> D2
    C3 --> D3
```

---

## 项目结构

```
backend/
├── app/
│   ├── main.py                 # FastAPI 入口 + 生命周期管理
│   ├── config.py               # 配置管理
│   ├── models/
│   │   ├── __init__.py
│   │   └── task.py             # Task, Concept, ConceptRelation 模型
│   ├── routers/
│   │   ├── __init__.py         # 导出 routers
│   │   ├── entries.py          # CRUD /entries
│   │   ├── search.py           # POST /search
│   │   └── knowledge.py        # GET /knowledge-graph, /related-concepts
│   ├── storage/
│   │   ├── __init__.py         # 导出 + init_storage()
│   │   ├── markdown.py         # Markdown 文件读写
│   │   ├── neo4j_client.py     # Neo4j 知识图谱操作
│   │   ├── qdrant_client.py    # Qdrant 向量检索
│   │   └── sync.py             # 三层存储同步逻辑
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── server.py           # MCP Server + 8 个 Tools
│   ├── callers/
│   │   ├── __init__.py
│   │   ├── base.py             # LLMCaller 接口
│   │   ├── api_caller.py       # API 调用实现
│   │   └── mock_caller.py      # Mock 实现
│   ├── graphs/
│   │   ├── __init__.py
│   │   └── task_parser_graph.py # LangGraph 任务解析
│   └── services/
│       └── __init__.py
├── data/                       # Markdown 数据目录
│   ├── projects/
│   ├── tasks/
│   ├── notes/
│   └── inbox.md
├── .env                        # 环境变量
└── pyproject.toml              # 依赖配置
```

---

## API 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/parse` | POST | LLM 解析自然语言（SSE 流式） |
| `/session/{id}` | DELETE | 清空会话历史 |
| `/entries` | GET | 列出条目 |
| `/entries` | POST | 创建条目 |
| `/entries/{id}` | GET | 获取条目 |
| `/entries/{id}` | PUT | 更新条目 |
| `/entries/{id}` | DELETE | 删除条目 |
| `/search` | POST | 语义搜索 |
| `/knowledge-graph/{concept}` | GET | 获取知识图谱 |
| `/related-concepts/{concept}` | GET | 获取相关概念 |

---

## MCP Tools 列表

| Tool | 说明 |
|------|------|
| `list_entries` | 查询条目列表 |
| `get_entry` | 获取单个条目 |
| `create_entry` | 创建新条目 |
| `update_entry` | 更新条目 |
| `delete_entry` | 删除条目 |
| `search_entries` | 语义搜索 |
| `get_knowledge_graph` | 获取知识图谱 |
| `get_related_concepts` | 获取相关概念 |
