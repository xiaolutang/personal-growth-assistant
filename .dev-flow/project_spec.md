# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.38.0
> 状态：规划中（R038）
> 活跃分支：chore/R038-engineering-health

## 当前范围

R038 工程健康收口 + 小功能补齐：工程债务清理 + 笔记模板 + 成功指标埋点 + 质量收口。

### Phase 1: 工程债务清理（3 tasks）

1. **B108 architecture.md 更新**：版本升级 + R037 新增内容 + 压缩到 120 行
2. **B109 .gitignore 修复**：checkpoints*.db* 加入 gitignore + untrack 运行时文件
3. **S36 plan 文档清理**：api_contracts 归档、project_spec 重置、feature_map 修正

### Phase 2: 笔记模板（2 tasks）

4. **B110 笔记模板后端 API**：扩展 CATEGORY_TEMPLATES + GET /entries/templates 端点
5. **F148 笔记模板前端选择器**：创建笔记时模板选择 + content 预填

### Phase 3: 成功指标埋点（2 tasks）

6. **B111 成功指标后端**：analytics_events 表 + POST /analytics/event
7. **F149 成功指标前端**：useAnalytics hook + 6 个关键动作埋点

### Phase 4: 质量收口（1 task）

8. **S37 全量测试 + build + Docker smoke**

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 8 |
| P0 | 1（S37 质量收口）|
| P1 | 5 |
| P2 | 2 |

## 技术约束

- 笔记模板为预定义常量，不新增数据库表
- 成功指标写入为 best-effort，不影响业务逻辑
- 工程债务清理不改变现有功能行为
- workflow: B/codex_plugin/skill_orchestrated
