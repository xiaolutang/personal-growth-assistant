# 缺陷回流记录

- issue_id: DF-2026-04-13-001
- source: real_use
- related_task: B04,B05,S02
- symptom: 生产环境发布后可正常登录，但已迁移的历史内容对真实账号不可见，前端表现为空数据。
- escape_path: R002 只验证了 `_default` 迁移成立，未验证“真实注册用户如何看到 `_default` 历史数据”；同时缺少远程部署后数据存在性 smoke。
- fix_level: L2
- root_cause_summary: 迁移方案只定义了“历史数据写入 `_default`”，未定义从 `_default` 到真实用户的归属过渡规则；同时服务层仍直接读写根目录 Markdown，导致“根目录 Markdown 主数据”和“SQLite 用户索引”长期分叉；部署侧也未把数据目录与目标账号映射作为发布门禁。
- upstream_actions: 新增认领/回填修复任务；将 Entry/Sync/HybridSearch 切换为按用户目录读写；启动时先把根目录历史文件迁入 `users/_default` 再参与同步；新增部署前 dry-run 与发布后 smoke；更新测试覆盖与对齐清单。
- rules_to_update: R002/R003 规划模板中，凡涉及匿名到实名迁移的数据都必须定义 owner claim 策略；多租户改造必须明确“唯一主数据存储路径”，禁止服务层继续直接读写根目录旧路径；高风险迁移任务必须补生产数据存在性 smoke。
- owner: xlfoundry-plan
- status: closed

---

## 待处理：项目条目详情页无内容

- 发现日期：2026-04-14
- source: real_use
- symptom: 访问 `/entries/project-79b2cb23` 时，项目详情页没有展示具体内容（应该显示项目描述、子任务进度、关联笔记等）。
- 处理计划: 随项目重构（R004）一并处理，详情页增强方案见 `docs/product-design-analysis.md` 第七章「条目详情页增强」。
