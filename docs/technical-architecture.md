# 个人成长助手 - 技术架构文档

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  React + TypeScript + shadcn/ui + Tailwind CSS     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓ REST API
┌─────────────────────────────────────────────────────────────┐
│                        后端层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ FastAPI      │  │ MCP Server   │  │ LLM Service  │      │
│  │ (REST API)   │  │ (MCP 协议)   │  │ (AI 解析)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        存储层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Markdown     │  │ SQLite       │  │ ChromaDB     │      │
│  │ (原始数据)   │  │ (元数据索引) │  │ (向量检索)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ↑ MCP 协议
┌─────────────────────────────────────────────────────────────┐
│                    AI 工具集成层                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Claude Code  │  │ Cursor       │  │ Codex        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、存储架构

### 2.1 三层存储

| 存储 | 用途 | 特点 |
|------|------|------|
| **Markdown 文件** | 原始数据（Source of Truth） | 用户可见、可编辑 |
| **SQLite** | 元数据索引 | 快速查询（状态、标签） |
| **ChromaDB** | 向量索引 | 语义搜索（RAG） |

### 2.2 文件结构

```
data/
├── projects/
│   ├── proj-001-ai-transition.md
│   └── proj-002-side-project.md
├── tasks/
│   ├── 2026-03-01.md
│   ├── 2026-03-02.md
│   └── 2026-03-12.md
├── notes/
│   ├── note-001-fastapi-learning.md
│   └── note-002-rag-deep-dive.md
├── decisions/
│   ├── dec-001-choose-rag-framework.md
│   └── dec-002-choose-vector-db.md
├── meetings/
│   └── mtg-001-product-sync.md
└── inbox.md
```

### 2.3 Markdown 格式规范

```markdown
---
id: proj-001
type: project
status: doing
priority: high
created_at: 2026-03-01
updated_at: 2026-03-12
tags: [AI, 转型, 学习]
related:
  - note-001
  - task-015
---

# AI 应用开发转型

## 目标
8周内转型为 AI 应用开发工程师，目标薪资 25-32k

## 当前状态
- Week 2 进行中
- 已完成 Prompt 工程

## 里程碑
- [ ] Week 4: MCP Server 完成
- [ ] Week 5: RAG 检索可用
- [ ] Week 7: 产品上线

## 决策记录
- [[dec-001]] 选择 FastAPI 而非 Flask
- [[dec-002]] 选择 ChromaDB 而非 Pinecone
```

---

## 三、数据库设计

### 3.1 SQLite 表结构

```sql
-- 主索引表：所有条目
CREATE TABLE entries (
    id TEXT PRIMARY KEY,           -- proj-001, task-015, note-001
    type TEXT NOT NULL,            -- project, task, note, decision, meeting
    file_path TEXT NOT NULL,       -- projects/ai-transition.md
    title TEXT,                    -- AI转型项目
    status TEXT,                   -- doing, waitStart, complete
    priority TEXT,                 -- high, medium, low
    created_at DATETIME,
    updated_at DATETIME,
    parent_id TEXT,                -- 任务归属项目
    FOREIGN KEY (parent_id) REFERENCES entries(id)
);

-- 标签表
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL      -- RAG, FastAPI, AI
);

-- 条目-标签关联
CREATE TABLE entry_tags (
    entry_id TEXT,
    tag_id INTEGER,
    PRIMARY KEY (entry_id, tag_id),
    FOREIGN KEY (entry_id) REFERENCES entries(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- 概念关联（知识图谱）
CREATE TABLE relations (
    source_id TEXT,
    target_id TEXT,
    relation_type TEXT,            -- belongs_to, relates_to, references
    PRIMARY KEY (source_id, target_id, relation_type)
);

-- 索引
CREATE INDEX idx_entries_type ON entries(type);
CREATE INDEX idx_entries_status ON entries(status);
CREATE INDEX idx_entries_parent ON entries(parent_id);
CREATE INDEX idx_entries_created ON entries(created_at);
```

---

## 四、API 设计

### 4.1 REST API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/parse` | 解析自然语言 |
| GET | `/entries` | 查询条目列表 |
| GET | `/entries/{id}` | 获取单个条目 |
| POST | `/entries` | 创建条目 |
| PUT | `/entries/{id}` | 更新条目 |
| DELETE | `/entries/{id}` | 删除条目 |
| POST | `/search` | 语义搜索 |
| GET | `/stats/time` | 时间统计 |

### 4.2 请求/响应示例

**POST /parse**
```json
// Request
{
  "text": "今天学了 RAG，重点是向量检索"
}

// Response
{
  "tasks": [
    {
      "id": "note-003",
      "type": "note",
      "title": "RAG 学习笔记",
      "status": "complete",
      "tags": ["RAG", "向量检索"],
      "file_path": "notes/note-003-rag-learning.md"
    }
  ]
}
```

**POST /search**
```json
// Request
{
  "query": "上周关于 RAG 的笔记",
  "limit": 5
}

// Response
{
  "results": [
    {
      "id": "note-003",
      "title": "RAG 学习笔记",
      "content": "...",
      "score": 0.92
    }
  ]
}
```

---

## 五、MCP Server 设计

### 5.1 Tools 定义

| Tool | 说明 | 参数 |
|------|------|------|
| `list_entries` | 查询条目列表 | type, status, limit |
| `get_entry` | 获取单个条目 | id |
| `create_entry` | 创建条目 | type, title, content, tags |
| `update_entry` | 更新条目 | id, updates |
| `delete_entry` | 删除条目 | id |
| `search_entries` | 语义搜索 | query, limit |
| `get_time_stats` | 时间统计 | start_date, end_date |

### 5.2 Resources 定义

| Resource | URI | 说明 |
|----------|-----|------|
| 所有项目 | `growth://projects` | 项目列表 |
| 所有任务 | `growth://tasks` | 任务列表 |
| 所有笔记 | `growth://notes` | 笔记列表 |
| 单个条目 | `growth://entry/{id}` | 条目详情 |

### 5.3 配置示例（Claude Desktop）

```json
{
  "mcpServers": {
    "personal-growth": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "DATA_DIR": "/path/to/data"
      }
    }
  }
}
```

---

## 六、技术选型

| 层级 | 技术 | 版本 | 理由 |
|------|------|------|------|
| 后端框架 | FastAPI | 0.109+ | 高性能、自动文档、异步支持 |
| MCP SDK | mcp | latest | 官方 Python SDK |
| 数据库 | SQLite | 3.40+ | 轻量、本地、无需部署 |
| 向量库 | ChromaDB | 0.4+ | 轻量、本地、Python 原生 |
| 前端 | React | 18+ | 生态完善 |
| UI 组件 | shadcn/ui | latest | 美观、可定制 |
| LLM | OpenAI 兼容 API | - | 通义千问/DeepSeek |

---

## 七、部署架构

### 7.1 开发环境

```
本地开发
├── backend/     (FastAPI :8000)
├── frontend/    (Vite :5173)
└── data/        (本地文件)
```

### 7.2 生产环境

```
部署架构（MVP）
├── Railway/Render (FastAPI)
├── Vercel/Netlify (React)
└── 本地文件 → 后续迁移到云存储
```

---

## 八、数据流

### 8.1 写入流程

```
用户输入 "今天学了 RAG"
    ↓
LLM 解析 → 生成 Markdown 内容
    ↓
┌─────────────────────────────────────┐
│ 1. 写入 Markdown 文件                │
│    notes/note-003-rag-learning.md   │
├─────────────────────────────────────┤
│ 2. 解析 YAML front matter           │
│    提取: id, type, tags, status     │
├─────────────────────────────────────┤
│ 3. 更新 SQLite 索引                  │
│    INSERT INTO entries...           │
├─────────────────────────────────────┤
│ 4. 向量化存入 ChromaDB              │
│    用于语义搜索                      │
└─────────────────────────────────────┘
```

### 8.2 查询流程

```
用户查询 "所有进行中的项目"
    ↓
┌─────────────────────────────────────┐
│ 1. SQLite 查询                       │
│    SELECT * FROM entries            │
│    WHERE type='project'             │
│    AND status='doing'               │
├─────────────────────────────────────┤
│ 2. 获取 file_path 列表               │
├─────────────────────────────────────┤
│ 3. 读取 Markdown 文件（可选）         │
└─────────────────────────────────────┘
```

### 8.3 同步机制

```
用户直接编辑 Markdown 文件
    ↓
文件监听 / 启动时扫描
    ↓
重新解析 YAML front matter
    ↓
更新 SQLite 索引
    ↓
更新 ChromaDB 向量
```
