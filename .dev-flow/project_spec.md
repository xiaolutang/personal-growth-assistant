# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.36.0
> 状态：规划中（R036）
> 活跃分支：chore/R036-residual-cleanup

## 当前范围

R036 残留问题全面收口：处理项目中所有已记录但未解决的 8 项残留风险和技术债务。

### Backend 架构修复

1. **B100 消除私有属性访问**：为 Neo4jClient/QdrantClient 添加 is_connected 公共属性，ReviewService 添加 getter，entries.py/notification_service.py 改用公共方法
2. **B101 get_growth_curve SQL 聚合**：将 list_entries(limit=10000) 替换为按周+tag 分组的 SQL 聚合查询
3. **B102 review_service 进一步拆分**：1845 行拆分到 services/review/ 子模块，目标 1200 行以内

### 前端基础设施

4. **F128 503 降级共享 hook**：创建 useServiceUnavailable hook，应用到 7 个缺失页面

### 前端页面拆分

5. **F129 EntryDetail.tsx 拆分**：1201 行 → 子目录 entry-detail/
6. **F130 Home.tsx + Explore.tsx 拆分**：730+729 行 → 子目录 home/ + explore/
7. **F131 Review + Tasks + Goals 拆分去重**：ProgressRing 去重 + 子目录拆分

### 移动端

8. **M100 移动端拖拽排序**：Flutter 任务列表长按拖拽

### 测试补齐 + 质量收口

9. **S33 R032 + R027 测试覆盖补齐**：~55 场景
10. **S34 质量收口**：全量测试 + build + Docker smoke

## 技术约束

- 全部为修复/补齐/重构，不引入新业务功能
- 不改变 API 契约
- workflow: B/codex_plugin/skill_orchestrated

## 用户路径

```
无新增用户路径。改善现有体验：
- 503 降级覆盖所有页面 → 服务不可用时所有页面展示友好提示
- 页面拆分 → 开发体验改善，不改变用户功能
- 性能优化 → get_growth_curve 更快的响应时间
```
