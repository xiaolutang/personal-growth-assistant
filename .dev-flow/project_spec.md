# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.26.1
> 状态：空闲（R026 已归档）
- 架构重构

## 修复来源

R025 simplify 阶段发现的 5 个收敛问题：

1. **[critical] 掌握度算法不一致**：review_service 使用加权评分式，knowledge_service 使用阈值式
2. **[critical] N+1 查询**：knowledge_service 4 个方法逐概念调用 get_entries_by_concept
3. **[major] 重复 API 请求**：InsightCard + AiSummaryCard 各自独立调用 getInsights
4. **[major] GraphPage 状态膨胀**：18 个 useState 跨 5 个功能域
5. **[major] 错误信息泄露**：knowledge.py 9 个路由直接返回 str(e)

## 技术约束

- 不新建服务文件，在现有文件内修改
- 前端组件拆分在文件内完成，不新建文件
- 验证走标准 Docker 发布流程（./deploy/deploy.sh）
- workflow: B/codex_plugin/skill_orchestrated
