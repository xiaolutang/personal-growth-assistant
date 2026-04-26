# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.39.0
> 状态：规划中（R039）
> 活跃分支：feat/R039-flutter-explore

## 当前范围

R039 Flutter Explore 页 + 工程维护：补齐 Flutter 移动端最大缺失页面（Explore 条目浏览/搜索/批量操作）+ 清理历史分支和过时文档。

### Phase 1: 工程维护（1 task）

1. **S38 分支清理 + 文档修正**：删除 20 个已合并历史分支 + 更新 project_spec

### Phase 2: Flutter API 基础（1 task）

2. **F151 Flutter Explore API 层**：条目列表过滤、全文搜索、删除 API 对接

### Phase 3: Flutter Explore 页面（3 tasks）

3. **F152 Explore 页面框架**：5 Tab + 条目列表 + 三态 + 路由注册
4. **F153 Explore 搜索**：搜索栏 + 搜索历史 + 搜索结果展示
5. **F154 Explore 批量操作**：多选模式 + 批量删除 + 批量转分类

### Phase 4: 质量收口（1 task）

6. **S39 全量测试 + build + Docker smoke**

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 6 |
| P0 | 1（S39 质量收口）|
| P1 | 4 |
| P2 | 1 |

## 技术约束

- Flutter Explore 页面复用现有 Riverpod Provider 模式
- 底部导航栏从 3 Tab 扩展到 4 Tab（今天/日知/探索/任务）
- 搜索历史使用内存 List（MVP 不引入 SharedPreferences）
- 批量操作在 explore_provider 中编排，ExplorePage 仅作 View 层
- workflow: B/codex_plugin/skill_orchestrated
