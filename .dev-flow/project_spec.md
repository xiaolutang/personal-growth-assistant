# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.32.0
> 状态：规划中（R032）
> 活跃分支：feat/R032-search-filter-batch

## 当前范围

R032 搜索增强 + Explore 批量操作（R022 收尾 + 产品 P0 功能）：

1. **B89 搜索过滤增强（后端）**：搜索 API 新增 start_time/end_time/tags 参数，后过滤逻辑
2. **F119 搜索过滤 UI（前端）**：时间范围快选 + 标签筛选 chip + 过滤条件管理
3. **F120 Explore 批量操作（前端）**：多选模式 + 批量删除/转分类
4. **S29 质量收口**：全量测试 + 构建

## 技术约束

- 搜索过滤采用后过滤模式（合并分数后过滤），不改变搜索相关性计算
- 时间过滤基于 entry 的 created_at 字段
- 标签过滤基于 entry 的 tags 数组交集
- Explore 批量操作复用 Tasks.tsx 已有的多选模式实现
- TaskCard 组件已支持 selectable/selected/onSelect props
- workflow: B/codex_plugin/skill_orchestrated

## 用户路径

```
搜索增强：
用户打开 Explore 页 → 输入搜索词 → 点击"本周"时间快选
         → 搜索结果自动过滤为本周条目
         → 点击热门标签 "python"
         → 搜索结果进一步过滤为本周含 python 标签的条目
         → 搜索栏下方显示 "本周 ×" "#python ×" 过滤条件
         → 点击 × 移除某个条件，重新搜索

批量操作：
用户打开 Explore 页 → 点击右上角"编辑"按钮
         → 条目卡片出现 checkbox
         → 勾选多个条目
         → 底部操作栏：已选 3 项 | 转笔记 | 转灵感 | 删除
         → 点击"删除" → 确认弹窗 → 批量删除
         → ESC 退出多选模式
```
