# Session S004: 技术债务清理规划

> 日期: 2026-04-10
> 触发: 用户要求规划解决前面分析中识别的技术债务
> 模式: workflow A (local)

## 需求总结

清理个人成长助手项目的全部技术债务，覆盖四个维度：

- **A. 死代码/冗余文件**: ChatBox.tsx 旧组件、根目录 nginx/ 冗余配置、Docker sed hack
- **B. 代码结构/可维护性**: MCP Server 654行单文件、deps.py 全局变量、前端 API 层未用生成类型
- **C. 测试覆盖**: taskStore 无测试、关键 hooks 无测试、E2E 容错 skip
- **D. 健壮性/安全性**: 存储 503 无降级 UI、CORS 配置宽松

## 架构校验

无冲突。所有变更在现有架构范围内：
- 不改变三层存储架构
- 不改变 LangGraph 任务解析流程
- 不改变 SSE 流式通信协议
- 不改变 MCP 协议实现

## 运行模式

```json
{
  "workflow": { "name": "A", "mode": "local/local/local" }
}
```
