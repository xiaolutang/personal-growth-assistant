# 测试架构文档

## 测试金字塔

```
                    ┌─────────────────┐
                   │   E2E (Playwright) │      ← 前后端联动
                  ┌─────────────────────┐
                 │  集成测试 (Testcontainers) │  ← 真实外部服务
                ┌───────────────────────┐
               │    服务层单元测试        │    ← Mock 外部依赖
              ┌─────────────────────────┐
             │     数据层组件测试         │   ← Mock 外部依赖
            └───────────────────────────┘
```

## 目录结构

```
backend/tests/
├── conftest.py                    # 根目录共享 fixtures
├── README.md                      # 本文档
│
├── unit/                          # 单元测试 (Mock)
│   ├── models/                    # L0: 基础组件
│   │   ├── test_models.py         # 数据模型
│   │   └── test_dto.py            # DTO 转换
│   │
│   ├── storage/                   # L1: 数据层
│   │   ├── test_storage_sqlite.py     # SQLite 存储
│   │   ├── test_storage_markdown.py   # Markdown 存储
│   │   ├── test_qdrant_client.py      # [新增] Qdrant 向量库
│   │   ├── test_neo4j_client.py       # [新增] Neo4j 知识图谱
│   │   └── test_embedding_service.py  # [新增] Embedding 服务
│   │
│   ├── services/                  # L2: 服务层
│   │   ├── test_entry_service.py      # EntryService 业务逻辑
│   │   ├── test_intent.py             # 意图检测
│   │   ├── test_sync_service_errors.py # [新增] 同步错误处理
│   │   └── test_storage_sync.py       # 同步服务
│   │
│   ├── api/                       # L3: API 层
│   │   ├── test_api_entries.py        # Entries API
│   │   ├── test_review_api.py         # 日报 API
│   │   └── test_routers_entries.py    # 路由测试
│   │
│   └── test_callers.py            # LLM Caller 测试
│
├── flow/                          # 流程/场景测试
│   ├── test_entry_crud.py         # CRUD 完整流程
│   ├── test_entry_api_flow.py     # API 流程测试
│   ├── test_entries_sync.py       # 条目同步流程
│   ├── test_list_sync.py          # 列表同步流程
│   ├── test_concurrency.py        # 并发场景
│   ├── test_date_filter.py        # 日期过滤
│   ├── test_search_eval.py        # 搜索评估
│   ├── test_sync_blocking.py      # 同步阻塞
│   └── test_llm_blocking.py       # LLM 阻塞
│
└── integration/                   # 集成测试 (需要 Docker)
    ├── conftest.py                # Testcontainers 配置
    ├── test_search_integration.py # Qdrant 真实搜索
    └── test_knowledge_integration.py # Neo4j 真实图谱
```

---

## 测试分类

### L0: 基础组件测试
| 文件 | 测试目标 | 依赖 |
|------|----------|------|
| `unit/models/test_models.py` | 数据模型 | 无 |
| `unit/models/test_dto.py` | DTO 转换 | 无 |
| `unit/test_callers.py` | LLM Caller | 无 |

### L1: 数据层组件测试 (Mock)
| 文件 | 测试目标 | 依赖 | 状态 |
|------|----------|------|------|
| `unit/storage/test_storage_sqlite.py` | SQLite 存储 | SQLite | ✅ 原有 |
| `unit/storage/test_storage_markdown.py` | Markdown 存储 | 文件系统 | ✅ 原有 |
| `unit/storage/test_qdrant_client.py` | Qdrant 向量库 | Mock | ✅ **新增** |
| `unit/storage/test_neo4j_client.py` | Neo4j 知识图谱 | Mock | ✅ **新增** |
| `unit/storage/test_embedding_service.py` | Embedding 服务 | Mock | ✅ **新增** |

### L2: 服务层单元测试
| 文件 | 测试目标 | 依赖 | 状态 |
|------|----------|------|------|
| `unit/services/test_entry_service.py` | EntryService 业务逻辑 | Mock | ✅ 原有 |
| `unit/services/test_intent.py` | 意图检测服务 | Mock | ✅ 原有 |
| `unit/services/test_sync_service_errors.py` | 同步服务错误处理 | Mock | ✅ **新增** |
| `unit/services/test_storage_sync.py` | 同步服务正常流程 | SQLite/Markdown | ✅ 原有 |

### L3: API/路由层测试
| 文件 | 测试目标 | 依赖 | 状态 |
|------|----------|------|------|
| `unit/api/test_api_entries.py` | Entries API | Mock | ✅ 原有 |
| `unit/api/test_review_api.py` | 日报 API | Mock | ✅ 原有 |
| `unit/api/test_routers_entries.py` | 路由测试 | Mock | ✅ 原有 |

### L4: 流程/场景测试
| 文件 | 测试目标 | 依赖 |
|------|----------|------|
| `flow/test_entry_crud.py` | CRUD 完整流程 | Mock |
| `flow/test_entry_api_flow.py` | API 流程测试 | Mock |
| `flow/test_entries_sync.py` | 条目同步流程 | Mock |
| `flow/test_list_sync.py` | 列表同步流程 | Mock |
| `flow/test_concurrency.py` | 并发场景 | Mock |
| `flow/test_date_filter.py` | 日期过滤 | SQLite |
| `flow/test_search_eval.py` | 搜索评估 | SQLite |
| `flow/test_sync_blocking.py` | 同步阻塞 | Mock |
| `flow/test_llm_blocking.py` | LLM 阻塞 | Mock |

### L5: 集成测试 (需要 Docker)
| 文件 | 测试目标 | 依赖 | 状态 |
|------|----------|------|------|
| `integration/test_search_integration.py` | Qdrant 真实搜索 | Qdrant 容器 | ✅ **新增** |
| `integration/test_knowledge_integration.py` | Neo4j 真实图谱 | Neo4j 容器 | ✅ **新增** |

### L6: E2E 测试 (需要前端)
| 文件 | 测试目标 | 依赖 | 状态 |
|------|----------|------|------|
| `e2e/tests/user_flows.spec.ts` | 用户流程 | 前端+后端 | ✅ **新增** |

---

## 新增测试与原有测试的关系

### 互补关系 ✅

| 新增测试 | 互补的原有测试 | 说明 |
|----------|----------------|------|
| `test_qdrant_client.py` | `test_storage_sqlite.py` | SQLite 已覆盖，Qdrant **新增覆盖** |
| `test_neo4j_client.py` | `test_storage_sqlite.py` | SQLite 已覆盖，Neo4j **新增覆盖** |
| `test_embedding_service.py` | `test_callers.py` | Caller 已覆盖，Embedding **新增覆盖** |
| `test_sync_service_errors.py` | `test_storage_sync.py` | 正常流程已覆盖，**错误处理新增覆盖** |

---

## 运行命令

```bash
# 运行所有单元测试
pytest unit/ -v

# 运行特定层级
pytest unit/models/ -v           # L0 基础组件
pytest unit/storage/ -v          # L1 数据层
pytest unit/services/ -v         # L2 服务层
pytest unit/api/ -v              # L3 API 层
pytest flow/ -v                  # L4 流程测试

# 运行集成测试（需要 Docker）
pytest integration/ -v

# 运行所有测试（排除集成测试）
pytest unit/ flow/ -v

# 运行 E2E 测试
cd e2e && npm install && npx playwright test
```

---

## 覆盖率目标

| 层级 | 当前覆盖率 | 目标 |
|------|-----------|------|
| L0 基础组件 | ~90% | 95% |
| L1 数据层 | ~60% | 80% |
| L2 服务层 | ~70% | 85% |
| L3 API 层 | ~80% | 90% |
| L5 集成测试 | 新增 | 关键路径 |
