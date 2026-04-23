# 测试覆盖清单

## R029: Simplify 收敛检查

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 四视角审查报告 | S26a | 四视角审查 | 复用/质量/效率/架构各一份报告，结构化发现列表含 finding_id/dimension/severity/affected_files/reason/recommended_action/disposition | done | L1, 16 findings |
| 收敛修复+全量验证 | S26b | unit+integration+smoke | 按finding_id逐条闭环must_fix/can_residual, pytest全量, vitest全量, build, smoke(首页晨报首屏/回顾页异步链路/GraphPage能力地图Tab切换+加载+重试), auth(未登录或失效token访问晨报/回顾接口返回401, 前端正确处理登录态失效) | done | L4, pytest 953, vitest 347, build success, F-004 全部 7 处迁移 |

## R027: 数据导出 + 反馈追踪

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 导出 API 增强 | B83 | unit+integration | 单条目导出正常/404/跨用户/长文件名/成长报告4section/空数据报告/Neo4j降级/未认证401(entry导出+报告导出) | planned | L2, ~10 tests |
| 反馈状态同步 | B84 | unit+contract | 同步成功/pending→reported/in_progress映射/resolved映射/未变更不更新/首次写入updated_at/计数断言/GET回读/超时跳过/远程404/未知status/in_progress遇404不变/批量20+/幂等/认证隔离 | done | L2, 20 tests, risk: network covered |
| 条目导出按钮 | F114 | unit+manual | 导出点击/loading/错误提示 | planned | F2, ~3 tests |
| Review 导出入口 | F115 | unit+manual | 全量ZIP/成长报告/loading/错误 | planned | F2, ~3 tests |
| 反馈状态增强 | F116 | unit+manual | 自动同步/4状态渲染/updated_at=null不显示时间/非null相对时间/synced_count=0降级不报错/网络错误显示本地缓存 | planned | F2, ~6 tests |
| 质量收口 | S21 | integration+smoke | pytest全量/vitest全量/build/Docker E2E | planned | L4 |

## R026: 收敛修复

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 统一掌握度算法 | S18 | unit | 阈值矩阵(effective_count/note_ratio/recent_count)/relationship_count 折算/重写旧加权断言/全量回归 | done | 13 tests, test_review_b53.py 重写为阈值断言 |
| 消除 N+1 查询 | S19 | unit | mock 验证 get_entries_by_concept 不调用/批量 stats 只取一次/Neo4j 降级不变/死代码确认删除 | done | 0 new, refactoring only, regression via existing knowledge tests |
| 错误信息脱敏 | B82 | unit | 9 个泛化异常返回固定文案/3 个 ValueError 分支 503 不变/logger.error 记录 | done | 0 new, error message change, regression via existing API tests |
| 消除重复请求 | F112 | unit | InsightCard/AiSummaryCard 消费 props/只触发一次 getInsights/切换取消保护 | done | 0 new, refactoring, regression via existing Review tests |
| GraphPage 状态拆分 | F113 | unit+manual | Tab 切换/领域展开/筛选/重试/非能力地图视图回归 | done | 0 new, refactoring, regression via existing GraphPage tests |
| 构建验证 | S20 | integration+smoke | pytest/vitest/build/Docker 部署 | done | pytest 923 passed, vitest 347 passed, build success, Docker E2E passed |
