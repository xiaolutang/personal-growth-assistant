# F08 视图选择器 + 按项目分组视图 — 执行证据

## Task Snapshot

| 字段 | 值 |
|------|----|
| ID | F08 |
| 名称 | 视图选择器 + 按项目分组视图 |
| 模块 | tasks |
| 验证级别 | F2 |
| 优先级 | medium |
| 依赖 | F03 (sub-tabs), F05 (ProjectCard) |
| 风险 | low |

## Execution Evidence

### 变更文件

| 文件 | 变更说明 |
|------|---------|
| frontend/src/pages/tasks/ViewSelector.tsx | **新增** — 视图选择器组件（列表/按项目，可扩展） |
| frontend/src/pages/tasks/GroupedView.tsx | **新增** — 按项目分组视图组件（分组头+进度条+展开折叠） |
| frontend/src/pages/Tasks.tsx | 修改 — 集成 ViewSelector + GroupedView，根据 activeView 切换渲染 |
| frontend/src/pages/tasks/useTaskFilters.ts | 修改 — 新增 activeView/setActiveView 状态 + URL ?view= 同步 |
| frontend/src/pages/tasks/constants.ts | 修改 — 新增 ViewKey 类型 + VALID_VIEW_KEYS + ViewOption 接口 |
| frontend/src/pages/tasks/__tests__/ViewSelector.test.tsx | **新增** — 4 个组件测试 |
| frontend/src/pages/tasks/__tests__/GroupedView.test.tsx | **新增** — 6 个组件测试 |
| frontend/src/pages/tasks/__tests__/useTaskFilters.test.ts | 修改 — 新增 4 个 view state 测试 |

### 实现要点

- ViewSelector: 可扩展的 `ViewOption[]` 配置，F09 可追加 timeline 选项
- GroupedView: 按 parent_id 分组，project 作为分组头内嵌进度条（调用 getProjectProgress API）
- 无 parent_id 条目归入"独立任务"分组
- 分组头可展开/折叠（ChevronDown/ChevronRight 切换）
- activeView 同步到 URL ?view=grouped（list 为默认不写 URL）
- GroupedView 中 TaskCard 设置 showParent={false} 避免与分组头重复

### tests_run

```
npm run build  →  ✓ built in 2.74s (构建通过)
npm run test:run  →  65 files, 684 tests passed
```

### test_results（F08 专属 14 项）

**ViewSelector 测试（4 项）**

| 测试场景 | 结果 |
|---------|------|
| 渲染所有选项 | passed |
| 高亮当前活跃视图 | passed |
| 点击触发 onViewChange 回调 | passed |
| 支持扩展选项（F09 timeline） | passed |

**GroupedView 测试（6 项）**

| 测试场景 | 结果 |
|---------|------|
| 无任务时显示空状态 | passed |
| 按 parent_id 分组到父项目下 | passed |
| 无 parent_id 归入独立任务 | passed |
| decision 正确归组到父项目 | passed |
| 混合分组（项目组+独立任务） | passed |
| 分组头展开/折叠 | passed |

**useTaskFilters view state 测试（4 项）**

| 测试场景 | 结果 |
|---------|------|
| activeView 默认为 list | passed |
| setActiveView 切换视图 | passed |
| setActiveView 同步到 URL params | passed |
| setActiveView('list') 移除 view URL param | passed |

### acceptance_check

| 验收条件 | 状态 | 核对依据 |
|---------|------|---------|
| 视图选择器在 Tasks 页面工具栏 | satisfied | Tasks.tsx CardHeader 内 ViewSelector |
| 可扩展设计（F09 timeline） | satisfied | ViewOption 接口 + DEFAULT_VIEW_OPTIONS 可追加 |
| 按项目分组 | satisfied | GroupedView groups by parent_id |
| project 作为分组头（标题+进度条） | satisfied | ProjectGroupHeader 内嵌进度条 |
| 无 parent_id 归入独立任务 | satisfied | GroupedView standalone group |
| 分组头可展开/折叠 | satisfied | collapsed state + toggleGroup |
| 视图同步到 URL ?view=grouped | satisfied | setActiveView URL 同步 |
| decision 正确归组 | satisfied | 测试覆盖 decision+parent_id |
| 基于前端已加载数据渲染 | satisfied | GroupedView 接收 tasks prop |
