# 测试用例设计指南

> 本文档总结自实际踩坑经验，用于指导后续测试用例设计。

---

## 一、核心原则

> **测试不是为了通过，而是为了发现问题。**

1. **Mock 测试通过 ≠ 系统能工作** - 需要集成测试验证真实依赖
2. **测试覆盖要包含"异常路径"** - 不可用、配置错误、数据不一致
3. **每个 Bug 都应该转化为测试用例** - 防止回归，也是最好的文档

---

## 二、测试金字塔

```
              前后端 E2E
           (Playwright)
          ┌─────────────────┐
         ┌───────────────────┐
        │    后端集成测试      │  Testcontainers (Qdrant/Neo4j)
       ┌─────────────────────┐
      │     服务层单元测试     │  Mock 外部依赖
     ┌───────────────────────┐
    │    数据层组件测试        │  Mock 外部依赖
   └─────────────────────────┘
```

### L1: 数据层组件测试 (Mock)

**目标**：验证单个组件的正确性和优雅降级能力

**必须覆盖的场景**：

| 场景 | 说明 | 示例 |
|------|------|------|
| 正常操作 | 依赖可用时功能正常 | `test_upsert_vectors_success` |
| 依赖不可用 | 返回空/None，不抛异常 | `test_search_when_unavailable` |
| 配置不匹配 | 自动修复或明确提示 | `test_dimension_mismatch_recreates_collection` |
| 边界条件 | 空输入、超长输入、特殊字符 | `test_search_empty_query` |

**Fixture 设计**：

```python
# 每个外部依赖提供两套 fixture
@pytest.fixture
def mock_qdrant_available():
    """Mock 正常可用状态"""
    ...

@pytest.fixture
def mock_qdrant_unavailable():
    """Mock 不可用状态（连接失败）"""
    ...
```

### L2: 服务层单元测试 (Mock)

**目标**：验证业务逻辑和错误处理

**必须覆盖的场景**：

| 场景 | 说明 |
|------|------|
| 部分依赖失败 | Qdrant 失败但 Neo4j 成功时的行为 |
| 优雅降级 | 可选服务失败时核心功能仍可用 |
| 并发竞态 | 同时创建/更新同一条目 |
| 数据一致性 | 多存储之间的同步状态 |

### L3: 后端集成测试 (Testcontainers)

**目标**：验证真实依赖的集成

**必须覆盖的场景**：

| 场景 | 说明 |
|------|------|
| 真实存储操作 | 使用真实的 Qdrant/Neo4j 容器 |
| 配置变更迁移 | 维度变更后的数据迁移 |
| API 端到端 | 从 HTTP 请求到响应的完整链路 |

### L4: 前后端 E2E 测试 (Playwright)

**目标**：验证用户真实操作路径

**必须覆盖的场景**：

| 场景 | 说明 |
|------|------|
| 核心用户流程 | 创建任务 → 搜索 → 更新 → 删除 |
| 问题场景回归 | 历史问题的复现和验证 |

---

## 三、可标准化流程

### 3.1 配置一致性检查

**触发时机**：系统启动时

```
1. 读取 embedding 模型配置 → 确定 vector_size
2. 检查 Qdrant collection 维度
3. 如果不匹配：
   - 记录警告日志
   - 自动重建（或提示用户确认）
   - 触发数据重新同步
4. 健康检查端点暴露配置状态
```

**实现示例**：

```python
async def validate_config_consistency():
    """启动时校验配置一致性"""
    issues = []

    expected_dim = get_embedding_dimension(EMBEDDING_MODEL)
    actual_dim = await qdrant.get_vector_dimension()

    if expected_dim != actual_dim:
        issues.append({
            "type": "dimension_mismatch",
            "expected": expected_dim,
            "actual": actual_dim,
            "auto_fix": True,
        })

    return issues
```

### 3.2 问题修复闭环

```
┌─────────────────────────────────────────────────────────┐
│  Bug 修复 → 测试补充 → 文档更新                          │
├─────────────────────────────────────────────────────────┤
│  1. 发现 Bug                                            │
│  2. 定位根因                                            │
│  3. 修复代码                                            │
│  4. ★ 添加测试用例（防止回归）                           │
│  5. ★ 检查是否有类似的未覆盖场景                         │
│  6. ★ 更新相关文档/配置说明                              │
└─────────────────────────────────────────────────────────┘
```

**关键原则**：每个 Bug 修复必须伴随至少一个测试用例。

### 3.3 破坏性操作保护

```python
async def rebuild_collection_if_needed():
    if needs_rebuild:
        # 1. 记录当前数据量
        old_count = await qdrant.get_stats()["points_count"]

        # 2. 执行重建
        await qdrant.delete_collection()
        await qdrant.create_collection()

        # 3. 触发数据重新同步（而不是静默丢失）
        logger.warning(f"Collection rebuilt, {old_count} points lost. Triggering resync...")
        await sync_service.sync_all()
```

---

## 四、测试用例模板

### 4.1 组件测试模板

```python
class TestComponentName:
    """组件名称测试"""

    # === 正常流程 ===
    async def test_operation_success(self, mock_dependency):
        """测试正常操作"""

    # === 异常流程 ===
    async def test_operation_when_unavailable(self, mock_unavailable):
        """测试依赖不可用时的优雅降级"""

    async def test_operation_with_invalid_input(self):
        """测试无效输入的处理"""

    # === 配置相关 ===
    async def test_config_mismatch_auto_fix(self):
        """测试配置不匹配时的自动修复"""
```

### 4.2 集成测试模板

```python
@pytest.mark.integration
class TestFeatureIntegration:
    """功能集成测试"""

    async def test_end_to_end_flow(self, real_container):
        """测试端到端流程"""

    async def test_data_persistence(self, real_container):
        """测试数据持久化"""
```

---

## 五、常见问题检查清单

### 5.1 测试设计时

- [ ] 是否覆盖了依赖不可用的场景？
- [ ] 是否覆盖了配置错误/不匹配的场景？
- [ ] 是否覆盖了边界条件（空、超长、特殊字符）？
- [ ] 是否覆盖了并发/竞态场景？
- [ ] Mock 行为是否与真实行为一致？

### 5.2 Bug 修复后

- [ ] 是否添加了防止回归的测试用例？
- [ ] 是否检查了类似的未覆盖场景？
- [ ] 集成测试是否通过？

### 5.3 发布前

- [ ] 单元测试全部通过
- [ ] 集成测试全部通过（需要 Docker）
- [ ] 配置一致性检查通过
- [ ] 健康检查端点正常

---

## 六、目录结构

```
backend/tests/
├── conftest.py              # 共享 fixtures
├── unit/                    # 单元测试
│   ├── storage/             # 数据层组件
│   │   ├── test_qdrant_client.py
│   │   ├── test_neo4j_client.py
│   │   └── test_embedding_service.py
│   └── services/            # 服务层
│       └── test_sync_service_errors.py
├── integration/             # 集成测试 (需要 Docker)
│   ├── conftest.py          # Testcontainers 配置
│   ├── test_search_integration.py
│   └── test_knowledge_integration.py
└── flow/                    # 业务流程测试
    └── test_entry_flow.py
```

---

## 七、运行命令

```bash
# 单元测试
pytest tests/ -v -k "not integration"

# 集成测试 (需要 Docker)
pytest tests/integration/ -v

# 覆盖率报告
pytest --cov=app --cov-report=html

# 全量测试
pytest tests/ -v
```
