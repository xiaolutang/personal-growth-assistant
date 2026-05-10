# 测试覆盖清单

## R055: 交互基础补齐

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| SkeletonLoading 组件 | F01 | unit+F1 | list-card 模式渲染/text-line 模式渲染/SkeletonList 指定数量/深色模式适配 | pending | — |
| Debouncer 工具 | F02 | unit | 300ms 内多次调用只执行最后/immediateRun 立即执行/dispose 取消 Timer | pending | — |
| 列表页骨架屏 | F03 | manual | 9 页面全屏 loading 替换验证 | pending | — |
| Notes 搜索防抖 | F04 | unit+F2 | 快速连续输入只触发一次/清空立即 fetch/页面销毁资源释放 | pending | — |
| 列表滑动操作 | F05 | unit+F2 | Tasks 左滑完成/右滑删除/Inbox 左滑删除/撤销恢复 | pending | — |
| 页面转场动画 | F06 | manual | 详情页 slide/设置页 fade/iOS swipe back | pending | — |
| 质量收口 | S07 | integration | flutter analyze 0 warnings/全量测试通过 | pending | — |
