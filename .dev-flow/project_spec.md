# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.41.0
> 状态：规划中（R041）
> 活跃分支：feat/R041-health-flutter-pages

## 当前范围

R041 工程健康 + Flutter 页面补齐：修复已知代码质量问题，补齐 Flutter 移动端缺失的 4 个核心页面。

### Phase 1: 工程健康修复（3 tasks）

1. **B117 Fix flaky test + 收窄异常**：test_isolation_user_data 改用随机 ID；knowledge_service.py(2处) + qdrant_client.py(1处) except Exception: pass 收窄
2. **F163 修复 eslint-disable**：审查 5 处 react-hooks/exhaustive-deps 抑制
3. **F164 Flutter 死代码清理**：删除 placeholder_page.dart

### Phase 2: Flutter API + Providers（2 tasks）

4. **F165 api_client.dart 扩展**：添加 createEntry/fetchGoals/fetchMilestones/fetchReviewSummary/fetchTrends 等方法
5. **F166 创建 4 个 Provider**：notes_provider + inbox_provider + review_provider + goals_provider

### Phase 3: Flutter 页面（4 tasks）

6. **F167 NotesPage**：笔记列表 + 搜索 + 详情跳转
7. **F168 InboxPage**：灵感列表 + 快速录入 + 转分类
8. **F169 ReviewPage**：统计回顾 + 趋势图 + AI 洞察
9. **F170 GoalsPage**：目标列表 + 里程碑管理

### Phase 4: 导航集成（1 task）

10. **F171 路由注册 + 底部导航扩展**：GoRouter 新路由 + 5 Tab 布局 + 更多菜单

### Phase 5: 质量收口（1 task）

11. **S42 全量测试 + flutter test + build + Docker smoke**

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 11 |
| P0 | 1（S42 质量收口）|
| P1 | 4（B117, F165, F166, F171）|
| P2 | 6（F163, F164, F167-F170）|

## 技术约束

- Flutter 页面遵循现有 Riverpod State+Notifier+Provider 三件套模式
- Flutter 页面使用 ConsumerStatefulWidget + 三态渲染
- 底部导航采用 5 Tab + 更多菜单布局
- ReviewPage 趋势图使用纯 Widget 实现（不引入 fl_chart）
- workflow: B/codex_plugin/skill_orchestrated
