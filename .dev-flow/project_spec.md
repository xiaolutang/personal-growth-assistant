# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.47.0
> 状态：规划中（R047）
> 活跃分支：feat/R047-task-explore-reboundary

## 当前范围

R047 任务/探索 Tab 边界重新划分：按「行动性」维度重新定义两个 Tab 的职责。任务 Tab 升级为"行动中心"（task + decision + project），探索 Tab 精简为"知识空间"（inbox + note + reflection + question）。

### Phase 1: 后端基础（2 tasks）

1. **S01 type_history + 类型转换 API**：模型字段 + POST /entries/{id}/convert + OpenAPI 类型同步
2. **B02 category_group 查询参数**：GET /entries?category_group=actionable/knowledge + OpenAPI 类型同步

### Phase 2: 任务 Tab 扩展（3 tasks）

3. **F03 数据层重构 + 类型子 Tab**：actionable 列表 + 全部/任务/决策/项目子 Tab
4. **F04 Decision 专属卡片**：YES/NO/延后按钮 + 结果对话框 + 拆任务
5. **F05 Project 卡片 + 进度**：进度条（后端 progress API）+ 子任务展开

### Phase 3: 探索 Tab 精简 + 转化（2 tasks）

6. **F06 探索 Tab 精简**：移除 project/decision tab，搜索保留全类型
7. **F07 转化对话框**：ConvertDialog + inbox 转任务/决策按钮

### Phase 4: 视图模式 + 高级交互（3 tasks）

8. **F08 视图选择器 + 按项目分组**
9. **F09 时间线视图 + 逾期提醒**
10. **F10 task→reflection 完成流**

### Phase 5: 搜索 + 详情页 + 集成（3 tasks）

11. **F11 条目详情页类型感知**
12. **F12 搜索结果分组展示**
13. **S13 集成验证 + 配套产物更新**

## 用户路径

1. 探索页创建灵感 → 点击「转为任务」→ 任务页出现新条目 → 完成任务 → 写复盘
2. 任务页看到决策 → 决定 YES → 拆出子任务 → 推进完成
3. 探索页搜索 → 结果包含任务/决策/项目 → 点击跳转任务页

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 4 |
| P0 | 4（B196, F188, F189, F190）|

## 技术约束

- is_new_user 通过 router → AgentService → Agent → prompt 链路透传，不新增 API
- __greeting__ 为隐藏触发消息，不存入对话历史
- 聊天面板重构后不再影响主内容区布局（无 paddingBottom）
- 复用现有 ONBOARDING_PROMPT，不重写 prompt 内容
- workflow: A/codex_plugin/skill_orchestrated
