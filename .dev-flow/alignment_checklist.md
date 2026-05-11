# 对齐清单

## R056: 品牌重命名（个人助手 → 日知）

### 用户路径对齐

- [ ] S01: 应用安装/启动 → 包名和 bundle id 正确 → 不崩溃
- [ ] F01: 打开应用 → 看到「日知」作为应用名 → 各页面标题正确
- [ ] S02: 后端 API 文档展示「日知」→ 部署脚本使用「日知」→ 文档统一

### 升级路径决策

- [x] applicationId/bundleId 变更后，已安装用户需卸载重装（个人开发项目，无应用商店发布，无正式用户需要迁移）
- [x] 不需要数据迁移工具（本地数据随 app 重装清空，云端数据不受影响）

### 架构对齐

- [ ] S01: 包名变更不影响架构分层（MVVM 不变）
- [ ] S02: OpenAPI 生成产物（api-schema.json 和 api.generated.ts）通过 `npm run gen:types` 重新生成，不手改。类型权威是 api.generated.ts
- [ ] S02: `frontend/vite.config.ts` 中 `FRONTEND_BASE_PATH` 路径名 `/growth/` 不改（部署路径，非品牌名）
- [ ] 所有任务不违反 architecture.md 禁止模式
- [ ] 不修改 `data/` 目录用户数据
- [ ] 不修改 `.dev-flow/_archive/` 历史快照

### 依赖对齐

- [ ] S01: 无依赖 ✓
- [ ] F01 depends_on S01 ✓（import 路径必须先改完）
- [ ] S02 depends_on S01 ✓（同上）
- [ ] S03 depends_on F01 + S02 ✓

### 命名范围对齐

- [ ] 改：Flutter 包名、applicationId、bundle identifier、展示名称、文档描述
- [ ] 不改：仓库目录名 personal-growth-assistant、用户数据 data/、归档快照 _archive/
- [ ] 不改：API 路径中 growth 相关（如 /review/growth-curve）— 这是功能路径不是品牌名
- [ ] 不改：FRONTEND_BASE_PATH=/growth/ — 部署路径，非品牌名
- [ ] 不改：frontend api-schema.json — 生成产物，由 npm run gen:types 重新生成

### 完成性检查

- [ ] 所有 P0 任务有 acceptance_criteria
- [ ] 依赖链完整无循环
- [ ] S01 有 config risk test_tasks
- [ ] S03 是纯验证任务，不承担发现新遗漏职责
