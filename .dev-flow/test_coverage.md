# 测试覆盖清单

## R038: 工程健康收口 + 小功能补齐

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| architecture.md 更新 | B108 | review | 版本号正确/R037 内容包含/≤120 行/不变量完整 | pending | L1 |
| .gitignore 修复 | B109 | unit+manual | gitignore 条目正确/git status 干净/pytest+vitest 回归 | pending | L1 |
| plan 文档清理 | S36 | review | api_contracts R037=done+R038=planned/归档快照存在/project_spec R038/feature_map 数据正确 | pending | L1 |
| 笔记模板后端 | B110 | unit | GET 模板列表/category 过滤/POST 带 template_id/POST 不带/无效 template_id/不匹配/category 优先/认证隔离 | pending | L2 |
| 笔记模板前端 | F148 | unit | 模板列表渲染/content 预填/非 note 不显示/默认行为不变/API 失败降级/空列表/category 切换/已有 content 不覆盖 | pending | F2 |
| 成功指标后端 | B111 | unit | POST 存储/user_id 隔离/metadata 可选/401/写入失败不影响/表自动创建/422 无效 event_type/422 非 object metadata | pending | L2 |
| 成功指标前端 | F149 | unit | trackEvent 调用/API 失败静默/6 埋点位置正确/离线丢弃不发请求 | pending | F2 |
| 质量收口 | S37 | integration+smoke | pytest 全量/vitest 全量/build/scripts/test-docker.sh | pending | L4 |
