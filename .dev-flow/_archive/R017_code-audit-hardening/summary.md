# R017 code-audit-hardening 归档摘要

- **ID**: R017
- **名称**: code-audit-hardening
- **分支**: fix/R017-code-audit-hardening
- **状态**: 进行中
- **开始时间**: 2026-04-18

## 任务清单（11 个任务）

| ID | 名称 | Phase | 优先级 | 状态 |
|----|------|-------|--------|------|
| B56 | 注入防护：Neo4j Cypher + SQLite 字段名 | security | 1 | pending |
| B57 | 认证加固 + 信息泄露修复 + 部署安全 | security | 1 | pending |
| B58 | 用户隔离修复：MCP handler + entry owner | security | 1 | pending |
| B64 | 路由认证修复：auth/me + sync_vectors | security | 1 | pending |
| B59 | 条目操作修复：分类变更 + 路由冲突 + file_path | data-correctness | 1 | pending |
| B60 | SyncService 写入/删除顺序修复 | data-correctness | 2 | pending |
| B65 | 条目批量创建字段丢失修复 | data-correctness | 2 | pending |
| F56 | SSE AbortController + Review cleanup | frontend | 2 | pending |
| B61 | review_service async 重构 + datetime 统一 | backend-arch | 2 | pending |
| B62 | N+1 查询优化 + StorageFactory LRU | performance | 3 | pending |
| B63 | 修复失效测试 + 补充测试覆盖（收口） | tests | 3 | pending |

## 审计来源

5 区域全面代码审计（2026-04-18），发现 96 个问题（9 Critical + 24 High，其中 4 项 Deferred）。

## 覆盖映射（Critical/High → 任务）

### Critical（9/9 全覆盖）
| # | 发现 | 任务 |
|---|------|------|
| C1 | Neo4j Cypher 注入 | B56 |
| C2 | category 变更 file_path 不更新 | B59 |
| C3 | /search/query 路由不可达 | B59 |
| C4 | SSE 无 AbortController | F56 |
| C5 | _run_async 死锁 | B61 |
| C6 | _get_conn() 绕过抽象 | B61 |
| C7 | SyncService 写入顺序 | B60 |
| C8 | SyncService 删除顺序 | B60 |
| C9 | docker Neo4j 弱密码 | B57 |

### High（24 项：20 已覆盖 + 4 Deferred）
| # | 发现 | 任务 | 备注 |
|---|------|------|------|
| H1 | auth/me 绕过 Depends | B64 | |
| H2 | logout 无服务端失效 | — | Deferred: JWT 7天短过期可接受 |
| H3 | JWT_SECRET 默认空 | B57 | |
| H4 | _verify_entry_owner 放行 | B58 | |
| H5 | file_path 比较错误 | B59 | |
| H6 | addTasks 丢字段 | B65 | |
| H7 | 废弃 asyncio API | B61 | |
| H8 | search 未用混合搜索 | — | Deferred: 功能增强 |
| H9 | Neo4j/Qdrant 连接降级 | — | Deferred: 功能增强 |
| H10 | 移动端拖拽缺失 | — | Deferred: 非安全/正确性 |
| H11 | SSE 冗余解析 | F56 | |
| H12 | 晨报全量加载 | B62 | |
| H13 | utcnow 时区不一致 | B61 | |
| H14 | tag_auto 空 tags | B61 | |
| H15 | N+1 查询(趋势) | B62 | |
| H16 | 无用 DB 查询 | B63 | |
| H17 | StorageFactory 缓存 | B62 | |
| H18 | Feedback 测试不匹配 | B63 | |
| H19 | MCP 回退宽松 | B58 | |
| H20 | 废弃 utcnow | B61 | |
| H21 | SQLite update_goal 注入 | B56 | |
| H22 | 错误中间件泄露 | B57 | |
| H23 | sync_vectors 无权限 | B64 | |
| H24 | Neo4j _get_session 递归 | B61 | |

## Deferred 项
- logout 无服务端 Token 失效（JWT 7天短过期 + 黑名单复杂度高）
- search 混合搜索（功能增强，非安全/正确性）
- Neo4j/Qdrant 降级策略（功能增强）
- 移动端拖拽缺失（体验优化，非安全/正确性）
