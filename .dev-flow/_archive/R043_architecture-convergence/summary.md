# R043 架构收敛

- 归档时间: 2026-04-28
- 状态: completed
- 总任务: 10
- 分支: `chore/R043-architecture-convergence`
- workflow: B / skill_orchestrated
- providers: codex_plugin / codex_plugin / codex_plugin

## 仓库提交

- personal-growth-assistant: `83b7ac8` (HEAD on main)

## Phase 1: 存储层拆分

| 任务 | 描述 | commit |
|------|------|--------|
| B177 | sqlite.py 领域拆分 + 连接上下文管理器 | af59f5d |

## Phase 2: 依赖注入 + 模型提取

| 任务 | 描述 | commit |
|------|------|--------|
| B180 | knowledge_service 模型提取到 models/ | 25cb84e |
| B178 | MCP handlers 统一通过 deps 获取 service 实例 | 54ca5d9 |
| B179 | entry_service/chat_service/morning_digest 消除 deps 反向依赖 | 54ca5d9 |

## Phase 3: N+1 优化 + 模板提取

| 任务 | 描述 | commit |
|------|------|--------|
| B183 | entry_service batch 查询优化 | e0c6b08 |
| B184 | sqlite.py 重复模式合并 | b5c61bc |
| B181 | goal_service N+1 修复 + 进度计算统一 | 1bf056b |
| B182 | review_service 三报告模板提取 | 1bf056b |

## Phase 4: 前端 API 统一

| 任务 | 描述 | commit |
|------|------|--------|
| F177 | api.ts 里程碑 API 统一 openapi-fetch | 25cb84e |

## Phase 5: 质量收口

| 任务 | 描述 | commit |
|------|------|--------|
| S44 | 全量测试 + 构建 | 5391f7e |

## 关键交付

- sqlite.py 2229 行拆分为 5 个 Mixin 模块（base/entries/goals/feedback/links），对外接口不变
- MCP 14 handler 统一通过 deps 获取 service 实例，消除裸 new
- entry/chat/morning_digest 消除对 routers.deps 的反向依赖，改为构造注入
- knowledge_service 18 个 Pydantic 模型提取到 models/knowledge.py
- goal_service N+1 消除：3 个 batch SQL 方法替代逐条查询
- review_service 三报告模板提取，降低复杂度
- api.ts 里程碑/进度/推荐统一 openapi-fetch
- 新增 60 个单元测试覆盖所有重构代码（27 storage + 19 goal_service + 12 review_service + 2 progress）
- 验证: pytest 1336 + vitest 612 + build 通过
