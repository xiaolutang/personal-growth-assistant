# 测试覆盖清单

## R030: AI 晨报增强

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 晨报缓存 | B85 | unit | 缓存命中/缓存失效(跨日)/cached_at字段/并发去重(asyncio.Lock)/缓存清理(LRU)/回归 | done | L2, 10 tests, 1062 passed |
| AI 建议个性化 | B86 | unit | 有目标/无目标/高频标签/LLM降级/超时/5xx/异常结构 | done | L2, 9 tests |
| 模式洞察 LLM 增强 | B87 | unit | LLM正常(最多5条string[])/LLM降级(规则引擎)/超时/空数据/5xx/异常结构/回归 | done | L2, 9 tests |
| 晨报展示优化 | F117 | unit+manual | cached_at非null/null/缺失(旧后端)/5条洞察/空洞察/加载态 | done | F2, vitest 347 passed, build success |
| 质量收口 | S27 | integration+smoke | pytest全量/vitest全量/build/Docker smoke | pending | L4 |

## R029: Simplify 收敛检查

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 四视角审查报告 | S26a | 四视角审查 | 复用/质量/效率/架构各一份报告 | done | L1, 16 findings |
| 收敛修复+全量验证 | S26b | unit+integration+smoke | must_fix逐条闭环/pytest全量/vitest全量/build/Docker smoke | done | L4, pytest 953, vitest 347, build success |

## R027: 数据导出 + 反馈追踪

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 导出 API 增强 | B83 | unit+integration | 单条目导出正常/404/跨用户/长文件名/成长报告/空数据/Neo4j降级/未认证401 | planned | L2, ~10 tests |
| 反馈状态同步 | B84 | unit+contract | 同步成功/pending→reported/in_progress映射/resolved映射/未变更不更新/首次写入updated_at/计数断言/GET回读/超时跳过/远程404/未知status/批量20+/幂等/认证隔离 | done | L2, 20 tests |
| 条目导出按钮 | F114 | unit+manual | 导出点击/loading/错误提示 | planned | F2, ~3 tests |
| Review 导出入口 | F115 | unit+manual | 全量ZIP/成长报告/loading/错误 | planned | F2, ~3 tests |
| 反馈状态增强 | F116 | unit+manual | 自动同步/4状态渲染/updated_at=null不显示时间/非null相对时间/synced_count=0降级/网络错误显示本地缓存 | planned | F2, ~6 tests |
| 质量收口 | S21 | integration+smoke | pytest全量/vitest全量/build/Docker E2E | planned | L4 |

## R026: 收敛修复

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 统一掌握度算法 | S18 | unit | 阈值矩阵/relationship_count折算/全量回归 | done | 13 tests |
| 消除 N+1 查询 | S19 | unit | mock验证/批量stats/死代码确认删除 | done | refactoring only |
| 错误信息脱敏 | B82 | unit | 9个泛化异常/3个ValueError/logger.error | done | error message change |
| 消除重复请求 | F112 | unit | InsightCard/AiSummaryCard消费props | done | refactoring |
| GraphPage 状态拆分 | F113 | unit+manual | Tab切换/领域展开/筛选/重试 | done | refactoring |
| 构建验证 | S20 | integration+smoke | pytest/vitest/build/Docker | done | 923+347+build+Docker |
