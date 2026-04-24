# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.30.0
> 状态：规划中（R030）
> 活跃分支：feat/R030-ai-morning-report

## 当前范围

R030 AI 晨报增强：缓存 + AI 建议个性化 + 模式洞察 LLM 增强。

1. **B85 晨报缓存**：按 user_id + date 内存缓存，同天重复请求不重算，缓存命中添加 cached_at 时间戳
2. **B86 AI 建议个性化**：LLM prompt 注入活跃目标和高频标签，使建议更贴合用户
3. **B87 模式洞察 LLM 增强**：将规则引擎增强为 LLM 驱动行为分析，保留规则降级
4. **F117 晨报展示优化**：缓存感知加载、展示增强
5. **S27 质量收口**：全量测试 + 构建 + Docker smoke

## 技术约束

- 不引入外部缓存依赖（不用 Redis），使用模块级内存缓存
- 不改 API 端点路径和请求格式，仅 MorningDigestResponse 添加可选 cached_at 字段
- 所有 LLM 改动保留现有降级机制（10 秒超时 + 模板兜底）
- workflow: B/codex_plugin/skill_orchestrated

## 用户路径

```
打开首页 → 自动加载晨报（首次计算并缓存/后续返回缓存）
         → 查看 AI 建议（个性化内容）
         → 查看模式洞察（LLM 增强分析）
         → 缓存命中时显示"上次更新于 HH:mm"
```
