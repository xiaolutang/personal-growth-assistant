# 对齐清单

## R038: 工程健康收口 + 小功能补齐

### 契约对齐

- [ ] B110: CONTRACT-TEMPLATE01 (GET /entries/templates) — 模板为预定义常量，不存数据库；支持 ?category 过滤
- [ ] F148: CONTRACT-TEMPLATE01 — 前端消费模板列表 + template_id 传递
- [ ] B111: CONTRACT-ANALYTICS01 (POST /analytics/event) — best-effort 写入；422 校验
- [ ] F149: CONTRACT-ANALYTICS01 — useAnalytics hook 消费埋点端点；离线时丢弃

### 依赖对齐

- [ ] B108 无外部依赖
- [ ] B109 无外部依赖
- [ ] S36 depends_on B108 ✓（先更新 architecture.md 再清理文档）
- [ ] B110 无外部依赖
- [ ] F148 depends_on B110 ✓（前端依赖后端模板端点）
- [ ] B111 无外部依赖
- [ ] F149 depends_on B111 ✓（前端依赖后端埋点端点）
- [ ] S37 depends_on 全部任务 ✓

### 架构对齐

- [ ] B108: 压缩 architecture.md 但不改变不变量和禁止模式
- [ ] B109: 不改变功能行为，只修 git 跟踪
- [ ] S36: 归档历史契约不删除数据，只移动位置；R038 契约保持 planned
- [ ] B110: 不改变现有 create flow（不传 template_id 行为不变）
- [ ] B110: template_id 优先于 CATEGORY_TEMPLATES；无效时不生效，使用 request.content
- [ ] B111: 新增路由不与现有路由冲突
- [ ] B111: 写入失败不影响业务（try/except 静默）
- [ ] B111: routers/__init__.py 导出 analytics_router
- [ ] F148: 创建链路通过 taskStore.ts → api.ts，不通过 ContentSection.tsx
- [ ] F149: 6 个事件源文件与实际组件一致
- [ ] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫

### 执行顺序

- [ ] Phase 1: B108 + B109（可并行）→ S36
- [ ] Phase 2: B110 → F148
- [ ] Phase 3: B111 → F149
- [ ] Phase 4: S37
