# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.37.0
> 状态：规划中（R037）
> 活跃分支：feat/R037-comprehensive-completion

## 当前范围

R037 全面补齐与功能增强：遗留问题收口 + R022 体验打磨 + P1 功能补齐。

### 已取消（代码验证后发现已实现）

- ~~B103 搜索迁移~~ → HybridSearchService 已集成到 search.py
- ~~F133 FloatingChat 触摸拖拽~~ → 已有 touch 事件处理
- ~~B106 成长曲线 API~~ → GET /review/growth-curve 已实现
- ~~F146 成长曲线可视化~~ → GrowthCurveCard.tsx 已渲染 AreaChart

### Phase 1: 技术债 + 搜索前端（2 tasks）

1. **B104 技术债清理**：import * 通配符、NotImplementedError 降级、文档状态同步
2. **F132 搜索 Tab 过滤透传**：Explore 页 Tab 过滤传递到搜索 API

### Phase 2: R022 体验打磨（8 tasks）

3. **F134 Home 统计卡片响应式**
4. **F135 Explore Tab 栏横向滚动**
5. **F136 TaskCard 触摸目标增大**
6. **F137 Review 加载态 + 错误状态**
7. **F138 Explore 错误状态处理**
8. **F139 TaskList 空状态增强**
9. **F140 NotificationCenter 时间戳 + 后台轮询**（已有 60s 面板内轮询，需增强）
10. **F141 搜索结果内容摘要**

### Phase 3: 离线 + 批量操作（3 tasks）

11. **F142 离线更新/删除拦截 + 队列扩展**
12. **F143 多选框架 + 选择状态**
13. **F144 批量删除/转分类执行**

### Phase 4: P1 功能补齐（4 tasks）

14. **B105 任务到期查询 API**：基于已有 planned_date 字段的到期查询（不新增 due_date）
15. **F145 任务截止日期 UI**：日期选择器 + 到期/过期标识
16. **B107 笔记双链引用后端**：[[note-id]] 解析 + 反向引用
17. **F147 笔记双链引用前端**：引用补全 + 反向引用面板

### Phase 5: 质量收口（1 task）

18. **S35 全量测试 + build + Docker smoke**

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 22（4 cancelled + 18 pending）|
| 待执行 | 18 |
| P0 | 1（S35 质量收口）|
| P1 | 10 |
| P2 | 7 |

### Codex Plugin 审核修复记录

审核结果：conditional_pass（修复后从 fail 提升）

| # | 发现 | 修复措施 |
|---|------|---------|
| 1 | 双链语法 B107/F147 不一致 | B107 统一支持 `[[note-id]]` 和 `[[note-id\|标题]]` 两种语法 |
| 2 | 缺少 R037 契约文档和对齐块 | 补齐 api_contracts.md 3 个契约定义 + alignment_checklist.md R037 块 |
| 3 | F144 未依赖 F142，离线批量缝隙 | F144 添加 F142 依赖，补齐离线批量行为描述 |
| 4 | F142 测试缺少失败分支 | 增补 5xx/超时/快速切换/用户反馈测试场景 |

## 技术约束

- 搜索前端增强不改变后端 API 契约（HybridSearchService 已集成）
- 截止日期复用已有 planned_date 字段（不新增 due_date），向后兼容
- 笔记双链不改变 Markdown 存储架构，新增 note_references 表
- B107 含已有笔记回填路径（reindex_backlinks 延迟初始化）
- workflow: B/codex_plugin/skill_orchestrated
- 笔记双链不改变 Markdown 存储架构，新增 note_references 表
- workflow: B/codex_plugin/skill_orchestrated
