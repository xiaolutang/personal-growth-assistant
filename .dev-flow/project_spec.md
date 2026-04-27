# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.42.0
> 状态：规划中（R042）
> 活跃分支：feat/R042-flutter-entry-detail

## 当前范围

R042 Flutter 条目详情交互升级：将移动端 EntryDetailPage 从只读展示升级为完整交互页面，支持编辑、AI 摘要、关联条目和反向引用。

### Phase 1: API + Provider 层（2 tasks）

1. **F172 api_client.dart 条目交互 API**：补齐 8 个 API 方法（updateEntry/fetchRelatedEntries/fetchBacklinks/fetchEntryLinks/createEntryLink/deleteEntryLink/fetchKnowledgeContext/generateAISummary）+ 单元测试
2. **F173 entry_detail_provider.dart 扩展**：编辑状态管理/保存/AI摘要/关联操作/反向引用加载 + Provider 测试

### Phase 2: EntryDetail UI 升级（3 tasks）

3. **F174 EntryDetail 编辑模式**：标题/内容/状态/标签可编辑，保存到后端
4. **F175 EntryDetail AI 摘要 + 知识上下文**：AI 摘要生成按钮+展示，知识上下文卡片
5. **F176 EntryDetail 关联条目 + 反向引用**：关联条目列表/手动关联/反向引用展示

### Phase 3: 质量收口（1 task）

6. **S43 flutter test + analyze + build + Docker smoke**

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 6 |
| P0 | 1（S43 质量收口）|
| P1 | 3（F172, F173, F174）|
| P2 | 2（F175, F176）|

## 技术约束

- 后端 API 全部就绪，无需后端改动
- EntryDetail 遵循 ConsumerStatefulWidget + Riverpod 模式
- 编辑模式在 AppBar 切换，不新增页面
- AI 摘要 / 知识上下文 / 关联条目以 Section 形式嵌入同一页面
- workflow: B/codex_plugin/skill_orchestrated
