# MCP (Model Context Protocol) 学习笔记

> Week 2 Day 4 - MCP 协议学习

---

## 一、MCP 是什么？

**MCP (Model Context Protocol)** 是 Anthropic 推出的开放协议，用于连接 AI 助手和外部系统。

核心问题：大模型需要访问外部数据、调用外部工具，但每个系统接口不同，集成成本高。

MCP 解决方案：提供统一标准，让 AI 助手能连接任何支持 MCP 的数据源和工具。

---

## 二、MCP 架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   MCP Host      │────▶│   MCP Client    │────▶│   MCP Server    │
│ (Claude Code)   │     │    (内置)        │     │  (开发者写的)    │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

| 角色 | 职责 | 例子 |
|------|------|------|
| **Host** | AI 助手应用，用户交互入口 | Claude Code、Claude Desktop |
| **Client** | 协议客户端，内置在 Host 中 | Claude Code 内置的 MCP Client |
| **Server** | 提供具体能力，开发者编写 | 文件系统、数据库、API 接口 |

---

## 三、MCP 三大核心能力

| 能力 | 用途 | 例子 |
|------|------|------|
| **Resources** | 暴露数据，只读访问 | 文件内容、数据库记录、API 响应 |
| **Tools** | 执行操作，可读写 | 发送邮件、查询天气、执行代码 |
| **Prompts** | 预定义提示词模板 | 代码审查模板、文档生成模板 |

---

## 四、传输方式

### 1. stdio（标准输入输出）

- **适用场景**：本地 MCP Server
- **原理**：Host 启动 Server 进程，通过 stdin/stdout 通信
- **优点**：简单、安全、无需网络端口
- **配置示例**：
  ```json
  {
    "mcpServers": {
      "my-server": {
        "command": "uv",
        "args": ["run", "my-server"]
      }
    }
  }
  ```

### 2. Streamable HTTP（推荐）

- **适用场景**：远程 MCP Server
- **原理**：HTTP + SSE，支持无状态和有状态模式
- **优点**：支持负载均衡、CDN 分发

### 3. SSE（已弃用）

- 旧版传输方式，已被 Streamable HTTP 取代

---

## 五、MCP 协议（JSON-RPC 2.0）

### 消息类型

```json
// 1. Request（请求）
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}

// 2. Result（成功响应）
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [{"name": "greet", "description": "..."}]
  }
}

// 3. Error（错误响应）
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}

// 4. Notification（通知，无需响应）
{
  "jsonrpc": "2.0",
  "method": "notifications/message",
  "params": {"level": "info", "data": "..."}
}
```

### 连接生命周期

```
1. 初始化阶段
   Client → Server: initialize 请求（协议版本、能力）
   Client → Server: notifications/initialized 通知

2. 消息交换阶段
   双向通信：请求/响应、通知

3. 终止阶段
   任意一方关闭连接
```

---

## 六、MCP vs Function Calling vs Skill

| 概念 | 是什么 | 谁提供 | 用途 |
|------|--------|--------|------|
| **Function Calling** | LLM 能调用函数的能力 | 模型厂商 | 让模型能执行结构化操作 |
| **MCP** | 暴露工具的标准协议 | Anthropic | 让 AI 助手连接外部系统 |
| **Skill** | 预定义的提示词模板 | 用户/平台 | 快速完成特定任务 |

**关系**：
- Function Calling 是 LLM 的**底层能力**
- MCP 是**标准协议**，让 Host 能发现和调用工具
- Skill 是**提示词模板**，不需要写代码

**选择建议**：
- 需要调用外部 API/系统 → **MCP**
- 只需要预设好的提示词 → **Skill**
- 直接在代码中调用 LLM → **Function Calling**

---

## 七、大模型如何知道 MCP 能力？

1. **发现阶段**：Host 启动时，Client 连接所有 MCP Server，调用 `tools/list` 获取工具列表
2. **注入阶段**：Host 把工具描述注入到 System Prompt 中
3. **调用阶段**：用户提问时，LLM 决定是否调用工具
4. **执行阶段**：Host 调用 `tools/call`，把结果返回给 LLM

```
用户提问 → LLM 决定调用工具 → Host 执行 tools/call
    → Server 返回结果 → LLM 生成回答
```

---

## 八、实战：创建简单 MCP Server

### 项目结构

```
mcp_servers/simple_server/
├── pyproject.toml          # 项目配置
├── src/
│   └── simple_server/
│       ├── __init__.py     # 入口
│       └── server.py       # Server 实现
└── .venv/                  # 虚拟环境
```

### pyproject.toml

```toml
[project]
name = "simple-mcp-server"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["mcp>=1.0.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
simple-server = "simple_server:main"

[tool.hatch.build.targets.wheel]
packages = ["src/simple_server"]
```

### server.py 核心代码

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("simple-server")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="greet",
            description="向某人打招呼",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "要打招呼的人名"}
                },
                "required": ["name"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "greet":
        return [TextContent(
            type="text",
            text=f"你好，{arguments['name']}！很高兴见到你！"
        )]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)
```

### 配置到 Claude Code

```bash
claude mcp add --scope user simple-server -- uv --directory /path/to/simple_server run simple-server
```

---

## 九、关键理解

1. **MCP 不是 API**，是协议标准
2. **Host 负责"翻译"**：把 MCP 工具描述转换成 LLM 能理解的格式
3. **stdio 传输最简单**：本地开发首选
4. **独立虚拟环境**：每个 MCP Server 可以有自己的依赖

---

## 十、项目开发注意事项

### 1. 连接断开处理

| 传输方式 | 断开原因 | 处理策略 |
|----------|----------|----------|
| **stdio** | Server 进程崩溃、代码报错 | Host 自动重启 |
| **HTTP** | 网络中断、Server 宕机 | 指数退避重连 |

**重连策略**：
```python
# 指数退避：1s → 2s → 4s → 8s → 16s（最大 30s）
delay = min(base_delay * (2 ** retry_count), 30)
```

### 2. Server 设计原则

| 原则 | 说明 | 好处 |
|------|------|------|
| **无状态优先** | 每次请求自包含，不依赖内存 | 断开后可立即恢复 |
| **幂等设计** | 同一请求多次执行结果相同 | 便于安全重试 |
| **持久化状态** | 用数据库/文件保存状态 | Server 重启后可恢复 |

### 3. 错误处理

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        result = await process(arguments)
        return [TextContent(type="text", text=result)]
    except ValidationError as e:
        # 参数错误，返回明确提示
        return [TextContent(type="text", text=f"参数错误: {e}")]
    except ExternalAPIError as e:
        # 外部服务错误，提示用户稍后重试
        return [TextContent(type="text", text=f"服务暂时不可用，请稍后重试")]
    except Exception as e:
        # 未知错误，记录日志
        logger.exception(f"Tool {name} failed")
        return [TextContent(type="text", text=f"执行失败: {e}")]
```

### 4. 生产环境 Checklist

- [ ] 实现健康检查（HTTP 模式）
- [ ] 设置合理的超时时间
- [ ] 记录详细日志
- [ ] 关键状态持久化
- [ ] 错误提示用户友好
- [ ] 监控 Server 状态

---

## 十一、下一步

- [ ] Day 5: CS146S Week 3 作业
- [ ] Day 6: 实战 - 写一个实用的 MCP Server
- [ ] 探索 Streamable HTTP 传输方式
