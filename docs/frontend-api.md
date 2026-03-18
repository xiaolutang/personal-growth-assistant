# 前端跟进开发指南

> 后端新增了 MCP Server + 知识图谱功能，前端需要配合调用新接口

---

## 一、后端新增功能

### 1. 条目管理 API（需要后端实现 REST 端点）

MCP Server 已实现，但前端需要 REST API。需要在 FastAPI 中新增：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/entries` | GET | 列出条目，支持 `type`、`status`、`limit` 参数 |
| `/entries/{id}` | GET | 获取单个条目 |
| `/entries` | POST | 创建条目 |
| `/entries/{id}` | PUT | 更新条目 |
| `/entries/{id}` | DELETE | 删除条目 |
| `/search` | POST | 语义搜索 |
| `/knowledge-graph/{concept}` | GET | 获取知识图谱 |

### 2. 数据模型变化

```typescript
interface Entry {
  id: string;                    // 文件名（不再是 int）
  title: string;                 // 标题（原 name）
  content: string;               // 正文内容（原 description）
  category: 'project' | 'task' | 'note' | 'inbox';
  status: 'waitStart' | 'doing' | 'complete';
  tags: string[];                // 新增：标签
  created_at: string;
  updated_at: string;
  planned_date?: string;         // Task 专用
  completed_at?: string;         // Task 专用
  time_spent?: number;           // Task 专用
  parent_id?: string;            // 父条目 ID
  file_path: string;             // 文件路径
}
```

---

## 二、前端需要做的改动

### 1. API Service 层

新增 API 调用：

```typescript
// services/api.ts
const API_BASE = 'http://localhost:8000';

export const api = {
  // 条目管理
  getEntries: (params?) =>
    fetch(`${API_BASE}/entries?${new URLSearchParams(params)}`).then(r => r.json()),

  getEntry: (id: string) =>
    fetch(`${API_BASE}/entries/${id}`).then(r => r.json()),

  createEntry: (data) =>
    fetch(`${API_BASE}/entries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => r.json()),

  updateEntry: (id, data) =>
    fetch(`${API_BASE}/entries/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => r.json()),

  deleteEntry: (id) =>
    fetch(`${API_BASE}/entries/${id}`, { method: 'DELETE' }).then(r => r.json()),

  // 搜索
  search: (query, limit = 5) =>
    fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, limit })
    }).then(r => r.json()),

  // 知识图谱
  getKnowledgeGraph: (concept, depth = 2) =>
    fetch(`${API_BASE}/knowledge-graph/${concept}?depth=${depth}`).then(r => r.json()),
};
```

### 2. 状态管理

如果用 Zustand，新增 entryStore：

```typescript
interface EntryStore {
  entries: Entry[];
  currentEntry: Entry | null;
  isLoading: boolean;

  fetchEntries: (type?, status?) => Promise<void>;
  getEntry: (id: string) => Promise<void>;
  createEntry: (data) => Promise<void>;
  updateEntry: (id, data) => Promise<void>;
  deleteEntry: (id: string) => Promise<void>;
  search: (query: string) => Promise<void>;
}
```

### 3. 新增页面（可选）

| 页面 | 说明 |
|------|------|
| 条目列表 | 展示所有条目，支持筛选 |
| 条目详情 | 查看/编辑单个条目 |
| 搜索 | 语义搜索 |
| 知识图谱 | 概念关系可视化（P2 优先级）|

---

## 三、开发优先级

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 后端 REST API | 先在 FastAPI 中暴露条目管理接口 |
| P0 | 前端条目列表 | 展示所有条目 |
| P0 | 前端快速输入 | 解析自然语言创建条目（已有 `/parse`）|
| P1 | 条目详情 | 查看/编辑单个条目 |
| P1 | 状态切换 | 更新条目状态 |
| P2 | 语义搜索 | RAG 搜索 |
| P2 | 知识图谱 | 概念关系可视化 |

---

## 四、注意事项

1. **CORS 配置**：后端需要配置 CORS 允许前端访问
2. **id 类型变化**：从 `int` 改为 `string`（文件名）
3. **字段名变化**：`name` → `title`，`description` → `content`
