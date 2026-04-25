# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.34.0
> 状态：规划中（R034）
> 活跃分支：feat/R034-tech-debt-residual

## 当前范围

R034 技术债收敛（R029 Residual Risks）：

1. **F122 useMorningDigest error 增强**：error 从 boolean 改为 string | null
2. **F123 Review 组件统一导出**：5 个组件移除 export default
3. **B93 export_growth_report 依赖注入**：消除反向依赖 deps
4. **F124 Home.tsx 合并遍历**：4 个 useMemo 合并为单次遍历
5. **B94 _recommend_from_tags 优化**：全量遍历改为定向查询
6. **F125 GraphPage 拆分**：1016 行拆为 5 个文件 + useGraphState hook
7. **B95 review_service 模型拆分**：Pydantic 模型独立到 models/review.py
8. **F126 api.ts 类型迁移**：手动类型替换为 api.generated.ts 生成类型
9. **F127 GraphPage Tab 测试**：4 个 Tab 切换自动化测试
10. **S31 质量收口**：全量测试 + 构建 + Docker smoke

## 技术约束

- 所有改动为现有模块内代码质量提升，不改业务逻辑
- 大型重构采用渐进策略，保持每步可验证
- workflow: B/codex_plugin/skill_orchestrated

## 用户路径

```
无新增用户路径。所有改动为内部代码质量提升，
用户可见行为不变。
```
